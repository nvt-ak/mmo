"""Background worker for trend discovery jobs."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from videoscout.core_engine.engine import SuggestionEngine
from videoscout.core_engine.keyword_classifier import classify_keyword_type
from videoscout.core_engine.classifier_calibration import build_classifier_calibration
from videoscout.core_engine.keyword_scorer import score_beta_candidates_batch
from videoscout.core_engine.nurture_scorer import score_nurture_candidates_batch
from videoscout.core_engine.candidate_generator import (
    fetch_discovery_sources,
    fetch_google_trends_candidates,
    iter_scored_source_videos,
)
from videoscout.core_engine.discovery_ranker import apply_final_ranking
from videoscout.core_engine.history_prior import build_history_prior
from videoscout.core_engine.trend_discovery import extract_keyword_candidates
from videoscout.core_engine.trend_evidence import (
    SCHEMA_VERSION,
    EvidenceBuilder,
    discovery_source_for_kind,
    serialize_evidence,
    trend_signals_from_evidence,
)
from videoscout.db import get_session
from videoscout.db.models import DiscoveryJobModel, SettingsModel, SuggestionModel, TrendClusterModel
from videoscout.services.tiktok import get_tiktok_service

from videoscout.core_engine.discovery_qualification import qualifies_for_inbox
from videoscout.core_engine.discovery_progress import (
    MAX_KEYWORDS_PER_JOB,
    TRENDING_VIDEO_LIMIT,
    VELOCITY_VIDEO_LIMIT,
)
from videoscout.services.google_trends import google_trends_enabled
from videoscout.core_engine.evidence_enrichment import enrich_top_scored, TOP_N_ENRICHMENT
from videoscout.core_engine.validation_pass import validate_top_scored
from videoscout.core_engine.trend_cluster import (
    build_clusters,
    filter_escalated_ambiguous_pairs,
    find_pair_candidates,
)

logger = logging.getLogger(__name__)


def _upsert_scored_suggestion(
    db: Session,
    scored: Dict[str, Any],
    *,
    cluster_id: Optional[uuid.UUID] = None,
) -> bool:
    """Insert or update suggestion. Returns True when inbox should count this keyword."""
    existing = db.query(SuggestionModel).filter(
        SuggestionModel.keyword == scored["keyword"]
    ).first()
    if existing:
        sources = list(existing.suggested_by or [])
        sources.append({
            "source": "trend_discovery",
            "score": scored["final_score"],
            "timestamp": datetime.utcnow().isoformat(),
        })
        existing.suggested_by = sources
        flag_modified(existing, "suggested_by")
        reactivated = existing.status != "pending"
        if reactivated:
            existing.status = "pending"
            existing.reject_reason = None
            existing.reject_note = None
            existing.rejected_at = None
        if scored["final_score"] > existing.final_score or reactivated:
            existing.final_score = scored["final_score"]
            existing.component_scores = scored["component_scores"]
            existing.tiktok_status = scored["tiktok_status"]
            existing.tiktok_count_at_suggest = scored["tiktok_count"]
            existing.tiktok_stats = scored["tiktok_stats"]
            existing.tiktok_checked_at = datetime.utcnow()
            existing.keyword_type = scored["keyword_type"]
            existing.discovery_source = scored["discovery_source"]
            existing.trend_signals = scored["trend_signals"]
            existing.trend_evidence = scored.get("trend_evidence")
            existing.platform_signals = scored.get("platform_signals")
            existing.gate_profile = scored["gate_profile"]
            existing.tiktok_unverified = scored["tiktok_unverified"]
            if cluster_id is not None:
                existing.cluster_id = cluster_id
        db.commit()
        return reactivated

    suggestion = SuggestionModel(
        keyword=scored["keyword"],
        final_score=scored["final_score"],
        component_scores=scored["component_scores"],
        tiktok_status=scored["tiktok_status"],
        tiktok_count_at_suggest=scored["tiktok_count"],
        tiktok_stats=scored["tiktok_stats"],
        tiktok_checked_at=datetime.utcnow(),
        suggested_by=[{
            "source": "trend_discovery",
            "score": scored["final_score"],
            "timestamp": datetime.utcnow().isoformat(),
        }],
        status="pending",
        keyword_type=scored["keyword_type"],
        discovery_source=scored["discovery_source"],
        trend_signals=scored["trend_signals"],
        trend_evidence=scored.get("trend_evidence"),
        platform_signals=scored.get("platform_signals"),
        gate_profile=scored["gate_profile"],
        tiktok_unverified=scored["tiktok_unverified"],
        cluster_id=cluster_id,
        created_at=datetime.utcnow(),
    )
    db.add(suggestion)
    db.commit()
    return True


def _save_keyword_if_new(
    db: Session,
    job: DiscoveryJobModel,
    scored: Dict[str, Any],
    keywords_generated: int,
    *,
    cluster_registry: Dict[str, TrendClusterModel],
) -> int:
    """Upsert one candidate; commit incrementally when a new row is created."""
    if keywords_generated >= MAX_KEYWORDS_PER_JOB:
        return keywords_generated

    cluster_id: Optional[uuid.UUID] = None
    assignment = scored.get("cluster_assignment")
    if assignment:
        canonical = assignment["canonical_keyword"]
        cluster = cluster_registry.get(canonical)
        if cluster is None:
            cluster = TrendClusterModel(
                canonical_keyword=canonical,
                member_keywords=assignment["member_keywords"],
                member_keyword_ids=[],
                pipeline_run_id=job.id,
                created_at=datetime.utcnow(),
            )
            db.add(cluster)
            db.flush()
            cluster_registry[canonical] = cluster
        cluster_id = cluster.id

    try:
        if _upsert_scored_suggestion(db, scored, cluster_id=cluster_id):
            keywords_generated += 1
            job.keywords_generated = keywords_generated
            if cluster_id is not None:
                cluster = cluster_registry[assignment["canonical_keyword"]]
                members = (
                    db.query(SuggestionModel)
                    .filter(SuggestionModel.cluster_id == cluster_id)
                    .all()
                )
                cluster.member_keyword_ids = [str(member.id) for member in members]
                cluster.member_keywords = [member.keyword for member in members]
            db.commit()
    except IntegrityError:
        db.rollback()
        logger.debug("Duplicate keyword skipped: %s", scored["keyword"])
    return keywords_generated


def _commit_job_progress(db: Session, job: DiscoveryJobModel, **fields: object) -> None:
    for key, value in fields.items():
        setattr(job, key, value)
    db.commit()


def _job_was_cancelled(db: Session, job: DiscoveryJobModel) -> bool:
    db.refresh(job)
    return job.status == "failed"


async def run_trend_discovery(
    job_id: str,
    *,
    keyword_type_filter: str = "both",
    region_code: str = "DE",
) -> None:
    db = get_session()
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        db.close()
        return

    job = db.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_uuid).first()
    if not job:
        db.close()
        return

    job.status = "running"
    job.started_at = datetime.utcnow()
    job.progress_phase = "fetch_trends"
    db.commit()

    engine = SuggestionEngine(db_session=db)
    keywords_generated = 0
    tiktok = get_tiktok_service()
    tiktok.start_batch()

    try:
        _commit_job_progress(db, job, progress_phase="fetch_trends")
        sources = fetch_discovery_sources(
            region_code=region_code,
            popular_limit=TRENDING_VIDEO_LIMIT,
            velocity_limit=VELOCITY_VIDEO_LIMIT,
            db=db,
        )
        sources_scanned = sum(1 for _, videos in sources if videos)
        evidence_builder = EvidenceBuilder(
            pipeline_run_id=str(job_uuid),
            region=region_code,
        )
        logger.info(
            "Discovery job %s trend_evidence schema=%s sources=%d",
            job_id,
            SCHEMA_VERSION,
            sources_scanned,
        )
        _commit_job_progress(
            db,
            job,
            sources_scanned=sources_scanned,
            progress_phase="scan_videos",
        )

        seen: set[str] = set()
        beta_queue: List[Dict[str, Any]] = []
        nurture_queue: List[Dict[str, Any]] = []
        max_word_width = 3 if keyword_type_filter == "nurture" else 5
        videos_scanned = 0

        calibration = build_classifier_calibration(db)

        for source_kind, video, velocity_percentiles in iter_scored_source_videos(
            sources,
            region_code=region_code,
        ):
            videos_scanned += 1
            discovery_source = discovery_source_for_kind(source_kind)
            for candidate in extract_keyword_candidates(
                video["title"],
                max_word_width=max_word_width,
                discovery_source=discovery_source,
            ):
                keyword = candidate["keyword"].lower()
                if keyword in seen:
                    continue
                seen.add(keyword)

                history_prior = build_history_prior(db, candidate["keyword"])
                trend_evidence = serialize_evidence(
                    evidence_builder.build(
                        keyword=candidate["keyword"],
                        source_video=video,
                        source_kind=source_kind,
                        velocity_percentile=velocity_percentiles.get(str(video.get("id") or "")),
                        history_prior=history_prior,
                    )
                )
                trend_signals = trend_signals_from_evidence(trend_evidence)

                enriched_candidate = {
                    **candidate,
                    "keyword": candidate["keyword"],
                    "discovery_source": discovery_source,
                    "trend_evidence": trend_evidence,
                    "trend_signals": {
                        **trend_signals,
                        "video_id": video.get("id"),
                        "channel_id": video.get("channel_id"),
                    },
                }

                provisional_type = classify_keyword_type(
                    enriched_candidate["keyword"],
                    trend_source=discovery_source,
                    calibration=calibration,
                )
                gate_profile = "light" if provisional_type == "nurture" else "full"
                tiktok_gate = await engine.check_tiktok_gate(
                    enriched_candidate["keyword"],
                    gate_profile,
                )
                job.candidates_checked = (job.candidates_checked or 0) + 1
                db.commit()

                if provisional_type == "beta":
                    if keyword_type_filter != "nurture":
                        beta_queue.append({
                            "candidate": enriched_candidate,
                            "tiktok_gate": tiktok_gate,
                        })
                    continue

                nurture_queue.append({
                    "candidate": enriched_candidate,
                    "tiktok_gate": tiktok_gate,
                })

            _commit_job_progress(db, job, videos_scanned=videos_scanned)

        if google_trends_enabled():
            trends_rows = fetch_google_trends_candidates(
                db,
                limit=VELOCITY_VIDEO_LIMIT,
            )
            for trends_raw in trends_rows:
                keyword = str(trends_raw.get("keyword") or "").strip().lower()
                if not keyword or keyword in seen:
                    continue
                seen.add(keyword)

                history_prior = build_history_prior(db, trends_raw["keyword"])
                trend_evidence = serialize_evidence(
                    evidence_builder.build_from_trends(
                        keyword=trends_raw["keyword"],
                        trends_raw=trends_raw,
                        history_prior=history_prior,
                    )
                )
                trend_signals = trend_signals_from_evidence(trend_evidence)
                discovery_source = discovery_source_for_kind("google_trends")

                enriched_candidate = {
                    "keyword": trends_raw["keyword"],
                    "discovery_source": discovery_source,
                    "trend_evidence": trend_evidence,
                    "trend_signals": {
                        **trend_signals,
                        "trends_seed": trends_raw.get("seed_keyword"),
                    },
                }

                provisional_type = classify_keyword_type(
                    enriched_candidate["keyword"],
                    trend_source=discovery_source,
                    calibration=calibration,
                )
                gate_profile = "light" if provisional_type == "nurture" else "full"
                tiktok_gate = await engine.check_tiktok_gate(
                    enriched_candidate["keyword"],
                    gate_profile,
                )
                job.candidates_checked = (job.candidates_checked or 0) + 1
                db.commit()

                if provisional_type == "beta":
                    if keyword_type_filter != "nurture":
                        beta_queue.append({
                            "candidate": enriched_candidate,
                            "tiktok_gate": tiktok_gate,
                        })
                    continue

                nurture_queue.append({
                    "candidate": enriched_candidate,
                    "tiktok_gate": tiktok_gate,
                })

        all_scored: List[Dict[str, Any]] = []

        if (
            nurture_queue
            and keyword_type_filter != "beta"
        ):
            if _job_was_cancelled(db, job):
                logger.info("Discovery job %s cancelled before nurture scoring", job_id)
                return
            _commit_job_progress(db, job, progress_phase="score_nurture")
            nurture_scored = await score_nurture_candidates_batch(
                nurture_queue,
                db=db,
                keyword_type_filter=keyword_type_filter,
                classifier_calibration=calibration,
            )
            all_scored.extend(nurture_scored)

        beta_scored: List[Dict[str, Any]] = []
        if (
            beta_queue
            and keyword_type_filter != "nurture"
        ):
            if _job_was_cancelled(db, job):
                logger.info("Discovery job %s cancelled before beta scoring", job_id)
                return
            _commit_job_progress(db, job, progress_phase="score_beta")
            beta_scored = await score_beta_candidates_batch(
                beta_queue,
                db=db,
                keyword_type_filter=keyword_type_filter,
                classifier_calibration=calibration,
            )
            all_scored.extend(beta_scored)

        if _job_was_cancelled(db, job):
            logger.info("Discovery job %s cancelled before enrichment", job_id)
            return

        if all_scored:
            _commit_job_progress(db, job, progress_phase="enrich_top")
            all_scored = await enrich_top_scored(
                all_scored,
                db=db,
                engine=engine,
                top_n=TOP_N_ENRICHMENT,
            )
            _commit_job_progress(db, job, progress_phase="validate")
            ranked_preview = sorted(
                all_scored,
                key=lambda row: row.get("final_score", 0.0),
                reverse=True,
            )
            top_keywords = {
                row["keyword"]
                for row in ranked_preview[:TOP_N_ENRICHMENT]
            }
            _, ambiguous_pairs = find_pair_candidates(all_scored)
            escalated_pairs = filter_escalated_ambiguous_pairs(
                ambiguous_pairs,
                escalate_keywords=top_keywords,
            )
            all_scored, pair_decisions = await validate_top_scored(
                all_scored,
                db=db,
                top_n=TOP_N_ENRICHMENT,
                ambiguous_pairs=escalated_pairs,
            )
            build_clusters(all_scored, llm_pair_decisions=pair_decisions)
            _commit_job_progress(db, job, progress_phase="rank_final")
            all_scored = apply_final_ranking(all_scored)

            settings = db.query(SettingsModel).first()
            min_score_threshold = float(
                settings.min_score_threshold if settings else 0.55
            )
            min_specificity = float(settings.min_specificity if settings else 0.4)
            min_saturation = float(settings.min_saturation if settings else 0.3)
            qualified_scored = [
                row
                for row in all_scored
                if qualifies_for_inbox(
                    row,
                    min_score_threshold=min_score_threshold,
                    min_specificity=min_specificity,
                    min_saturation=min_saturation,
                )
            ]
            if len(qualified_scored) < len(all_scored):
                logger.info(
                    "Discovery job %s filtered %d/%d keywords below inbox gates "
                    "(min_score=%.2f)",
                    job_id,
                    len(all_scored) - len(qualified_scored),
                    len(all_scored),
                    min_score_threshold,
                )

            cluster_registry: Dict[str, TrendClusterModel] = {}
            for scored in qualified_scored[:MAX_KEYWORDS_PER_JOB]:
                if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                    break
                keywords_generated = _save_keyword_if_new(
                    db,
                    job,
                    scored,
                    keywords_generated,
                    cluster_registry=cluster_registry,
                )

        if _job_was_cancelled(db, job):
            logger.info("Discovery job %s cancelled before completion", job_id)
            return

        if (
            keyword_type_filter == "beta"
            and beta_queue
            and not beta_scored
            and keywords_generated == 0
        ):
            job.status = "failed"
            job.progress_phase = "failed"
            job.error_message = (
                "Beta batch LLM scoring failed (often LLM timeout). "
                "Check LLM settings or set LLM_REQUEST_TIMEOUT_SECONDS."
            )
            job.completed_at = datetime.utcnow()
            db.commit()
            logger.warning(
                "Discovery job %s failed: beta scoring returned no keywords",
                job_id,
            )
            return

        job.status = "completed"
        job.keywords_generated = keywords_generated
        job.progress_phase = "complete"
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(
            "Discovery job %s complete: %d keywords (cap %d, %d beta queued)",
            job_id,
            keywords_generated,
            MAX_KEYWORDS_PER_JOB,
            len(beta_queue),
        )
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.error("Discovery job %s failed: %s", job_id, exc)
        raise
    finally:
        await tiktok.end_batch_async()
        db.close()


def run_trend_discovery_sync(job_id: str, **kwargs) -> None:
    asyncio.run(run_trend_discovery(job_id, **kwargs))
