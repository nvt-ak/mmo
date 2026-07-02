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
from videoscout.core_engine.keyword_scorer import (
    BetaScoringError,
    score_beta_candidates_batch,
)
from videoscout.core_engine.trend_discovery import (
    build_scored_candidate,
    extract_keyword_candidates,
)
from videoscout.db import get_session
from videoscout.db.models import DiscoveryJobModel, SuggestionModel
from videoscout.services.youtube import get_youtube_service

logger = logging.getLogger(__name__)

TRENDING_VIDEO_LIMIT = 10
MAX_KEYWORDS_PER_JOB = 10


def _upsert_scored_suggestion(db: Session, scored: Dict[str, Any]) -> bool:
    """Insert or update suggestion. Returns True when a new row was created."""
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
        if scored["final_score"] > existing.final_score:
            existing.final_score = scored["final_score"]
            existing.component_scores = scored["component_scores"]
            existing.tiktok_status = scored["tiktok_status"]
            existing.tiktok_count_at_suggest = scored["tiktok_count"]
            existing.tiktok_stats = scored["tiktok_stats"]
            existing.tiktok_checked_at = datetime.utcnow()
            existing.keyword_type = scored["keyword_type"]
            existing.discovery_source = scored["discovery_source"]
            existing.trend_signals = scored["trend_signals"]
            existing.gate_profile = scored["gate_profile"]
            existing.tiktok_unverified = scored["tiktok_unverified"]
        db.commit()
        return False

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
    db.commit()

    engine = SuggestionEngine(db_session=db)
    keywords_generated = 0

    try:
        trending = get_youtube_service().get_trending_videos(
            region_code=region_code,
            max_results=TRENDING_VIDEO_LIMIT,
        )
        job.sources_scanned = 1 if trending else 0
        db.commit()

        seen: set[str] = set()
        beta_queue: List[Dict[str, Any]] = []

        for video in trending:
            if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                break
            for candidate in extract_keyword_candidates(video["title"]):
                if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                    break
                keyword = candidate["keyword"].lower()
                if keyword in seen:
                    continue
                seen.add(keyword)

                provisional_type = classify_keyword_type(
                    candidate["keyword"],
                    trend_source=candidate.get("discovery_source", "youtube_trend"),
                )
                gate_profile = "light" if provisional_type == "nurture" else "full"
                tiktok_gate = await engine.check_tiktok_gate(
                    candidate["keyword"],
                    gate_profile,
                )

                if provisional_type == "beta":
                    if keyword_type_filter != "nurture":
                        beta_queue.append({
                            "candidate": candidate,
                            "tiktok_gate": tiktok_gate,
                        })
                    continue

                scored = build_scored_candidate(
                    candidate,
                    tiktok_gate=tiktok_gate,
                    keyword_type_filter=keyword_type_filter,
                )
                if scored:
                    keywords_generated = _save_keyword_if_new(
                        db, job, scored, keywords_generated,
                    )

        if (
            beta_queue
            and keyword_type_filter != "nurture"
            and keywords_generated < MAX_KEYWORDS_PER_JOB
        ):
            try:
                beta_scored = await score_beta_candidates_batch(
                    beta_queue,
                    db=db,
                    keyword_type_filter=keyword_type_filter,
                )
            except BetaScoringError as exc:
                logger.warning(
                    "Beta batch scoring failed for job %s: %s",
                    job_id,
                    exc,
                )
                beta_scored = []
            for scored in beta_scored:
                if keywords_generated >= MAX_KEYWORDS_PER_JOB:
                    break
                keywords_generated = _save_keyword_if_new(
                    db, job, scored, keywords_generated,
                )

        job.status = "completed"
        job.keywords_generated = keywords_generated
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
        db.close()


def run_trend_discovery_sync(job_id: str, **kwargs) -> None:
    asyncio.run(run_trend_discovery(job_id, **kwargs))
