"""Background worker for trend discovery jobs."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from videoscout.core_engine.engine import SuggestionEngine
from videoscout.core_engine.keyword_classifier import classify_keyword_type
from videoscout.core_engine.keyword_scorer import score_beta_candidates_batch
from videoscout.core_engine.nurture_scorer import score_nurture_candidates_batch
from videoscout.core_engine.trend_discovery import extract_keyword_candidates
from videoscout.db import get_session
from videoscout.db.models import DiscoveryJobModel, SuggestionModel
from videoscout.services.youtube import get_youtube_service
from videoscout.services.tiktok import get_tiktok_service

from videoscout.core_engine.discovery_progress import (
    MAX_KEYWORDS_PER_JOB,
    TRENDING_VIDEO_LIMIT,
)

logger = logging.getLogger(__name__)


def _upsert_scored_suggestion(db: Session, scored: Dict[str, Any]) -> bool:
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
            existing.platform_signals = scored.get("platform_signals")
            existing.gate_profile = scored["gate_profile"]
            existing.tiktok_unverified = scored["tiktok_unverified"]
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
        platform_signals=scored.get("platform_signals"),
        gate_profile=scored["gate_profile"],
        tiktok_unverified=scored["tiktok_unverified"],
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
) -> int:
    """Upsert one candidate; commit incrementally when a new row is created."""
    if keywords_generated >= MAX_KEYWORDS_PER_JOB:
        return keywords_generated
    try:
        if _upsert_scored_suggestion(db, scored):
            keywords_generated += 1
            job.keywords_generated = keywords_generated
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
        trending = get_youtube_service().get_trending_videos(
            region_code=region_code,
            max_results=TRENDING_VIDEO_LIMIT,
        )
        _commit_job_progress(
            db,
            job,
            sources_scanned=1 if trending else 0,
            progress_phase="scan_videos",
        )

        seen: set[str] = set()
        beta_queue: List[Dict[str, Any]] = []
        nurture_queue: List[Dict[str, Any]] = []
        max_word_width = 3 if keyword_type_filter == "nurture" else 5

        for video_index, video in enumerate(trending):
            if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                break
            for candidate in extract_keyword_candidates(
                video["title"],
                max_word_width=max_word_width,
            ):
                if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                    break
                keyword = candidate["keyword"].lower()
                if keyword in seen:
                    continue
                seen.add(keyword)

                enriched_candidate = {
                    **candidate,
                    "trend_signals": {
                        **(candidate.get("trend_signals") or {}),
                        "video_id": video.get("id"),
                        "channel_id": video.get("channel_id"),
                    },
                }

                provisional_type = classify_keyword_type(
                    enriched_candidate["keyword"],
                    trend_source=enriched_candidate.get("discovery_source", "youtube_trend"),
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

            _commit_job_progress(db, job, videos_scanned=video_index + 1)

        if (
            nurture_queue
            and keyword_type_filter != "beta"
            and keywords_generated < MAX_KEYWORDS_PER_JOB
        ):
            if _job_was_cancelled(db, job):
                logger.info("Discovery job %s cancelled before nurture scoring", job_id)
                return
            _commit_job_progress(db, job, progress_phase="score_nurture")
            nurture_scored = await score_nurture_candidates_batch(
                nurture_queue,
                db=db,
                keyword_type_filter=keyword_type_filter,
            )
            for scored in nurture_scored:
                if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                    break
                keywords_generated = _save_keyword_if_new(
                    db, job, scored, keywords_generated,
                )

        beta_scored: List[Dict[str, Any]] = []
        if (
            beta_queue
            and keyword_type_filter != "nurture"
            and keywords_generated < MAX_KEYWORDS_PER_JOB
        ):
            if _job_was_cancelled(db, job):
                logger.info("Discovery job %s cancelled before beta scoring", job_id)
                return
            _commit_job_progress(db, job, progress_phase="score_beta")
            beta_scored = await score_beta_candidates_batch(
                beta_queue,
                db=db,
                keyword_type_filter=keyword_type_filter,
            )
            for scored in beta_scored:
                if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                    break
                keywords_generated = _save_keyword_if_new(
                    db, job, scored, keywords_generated,
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
