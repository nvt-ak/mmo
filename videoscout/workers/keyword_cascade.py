"""Keyword approve cascade worker."""
from datetime import datetime
import logging

import videoscout.db as db_module
from videoscout.db.models import (
    SuggestionModel,
    ChannelModel,
    ChannelKeywordLinkModel,
    KeywordCascadeJobModel,
    DownloadJobModel,
)
from videoscout.core_engine.channel_discovery import discover_channels
from videoscout.workers.bulk_download import run_bulk_download

logger = logging.getLogger(__name__)


def run_keyword_cascade(job_id: str) -> None:
    """Run keyword cascade flow for a queued job."""
    db = db_module.get_session()
    discovered_count = 0
    subscribed_count = 0
    job = None

    try:
        all_jobs = db.query(KeywordCascadeJobModel).all()
        job = next((candidate for candidate in all_jobs if str(candidate.id) == str(job_id)), None)
        if not job:
            logger.warning("Cascade job not found: %s", job_id)
            return

        suggestion = db.query(SuggestionModel).filter(
            SuggestionModel.id == job.suggestion_id
        ).first()
        if not suggestion:
            job.status = "failed"
            job.error_message = "Suggestion not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        candidates = discover_channels(suggestion.keyword, max_results=10)
        discovered_count = len(candidates)

        for candidate in candidates[:5]:
            channel = db.query(ChannelModel).filter(
                ChannelModel.channel_id == candidate.youtube_channel_id
            ).first()
            if not channel:
                channel = ChannelModel(
                    channel_id=candidate.youtube_channel_id,
                    name=candidate.name,
                    description=candidate.description,
                    thumbnail_url=candidate.thumbnail_url,
                    subscriber_count=candidate.subscriber_count,
                    scan_enabled=True,
                )
                db.add(channel)
                db.flush()
                subscribed_count += 1
            else:
                channel.scan_enabled = True
                channel.name = channel.name or candidate.name
                channel.description = channel.description or candidate.description
                channel.thumbnail_url = channel.thumbnail_url or candidate.thumbnail_url
                if candidate.subscriber_count > 0:
                    channel.subscriber_count = candidate.subscriber_count

            existing_link = db.query(ChannelKeywordLinkModel).filter(
                ChannelKeywordLinkModel.suggestion_id == suggestion.id,
                ChannelKeywordLinkModel.channel_id == channel.id,
            ).first()
            if not existing_link:
                db.add(
                    ChannelKeywordLinkModel(
                        suggestion_id=suggestion.id,
                        channel_id=channel.id,
                        youtube_channel_id=candidate.youtube_channel_id,
                        keyword=suggestion.keyword,
                        discovery_score=candidate.discovery_score,
                    )
                )

        download_job = DownloadJobModel(
            job_type="bulk",
            suggestion_id=suggestion.id,
            cascade_job_id=job.id,
            status="started",
            channels_total=subscribed_count,
        )
        db.add(download_job)
        db.flush()

        job.channels_discovered = discovered_count
        job.channels_subscribed = subscribed_count
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()
        run_bulk_download(str(download_job.id))
    except Exception as exc:  # pragma: no cover - defensive path
        db.rollback()
        logger.exception("Keyword cascade failed for job %s", job_id)
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.channels_discovered = discovered_count
            job.channels_subscribed = subscribed_count
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        # get_session() may be overridden to a shared test session.
        # Avoid closing it inside worker.
        pass
