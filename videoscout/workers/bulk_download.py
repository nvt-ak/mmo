"""Bulk ingestion worker for downloading recent channel videos."""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence
import logging

import videoscout.db as db_module
from videoscout.db.models import (
    ChannelKeywordLinkModel,
    ChannelModel,
    DownloadJobModel,
    VideoAssetModel,
)
from videoscout.services.download import DownloadService
from videoscout.services.youtube import YouTubeService, get_youtube_service

logger = logging.getLogger(__name__)


@contextmanager
def _session() -> Iterator:
    db = db_module.get_session()
    close_on_exit = getattr(db_module.get_session, "__name__", "") != "<lambda>"
    try:
        yield db
    finally:
        if close_on_exit:
            db.close()


def _select_job(db, job_id: str) -> Optional[DownloadJobModel]:
    jobs = db.query(DownloadJobModel).all()
    return next((candidate for candidate in jobs if str(candidate.id) == str(job_id)), None)


def _resolve_channels(
    db,
    job: DownloadJobModel,
    explicit_channel_ids: Optional[Sequence[str]] = None,
) -> List[ChannelModel]:
    if explicit_channel_ids:
        return (
            db.query(ChannelModel)
            .filter(ChannelModel.channel_id.in_(list(explicit_channel_ids)))
            .all()
        )

    if job.suggestion_id:
        links = (
            db.query(ChannelKeywordLinkModel)
            .filter(ChannelKeywordLinkModel.suggestion_id == job.suggestion_id)
            .all()
        )
        if not links:
            return []
        channel_ids = [link.channel_id for link in links]
        return db.query(ChannelModel).filter(ChannelModel.id.in_(channel_ids)).all()

    return db.query(ChannelModel).filter(ChannelModel.scan_enabled.is_(True)).all()


def _mark_job_failed(job_id: str, exc: Exception, videos_found: int, videos_downloaded: int) -> None:
    with _session() as db:
        job = _select_job(db, job_id)
        if job is None:
            return
        job.status = "failed"
        job.error_message = str(exc)
        job.videos_found = videos_found
        job.videos_downloaded = videos_downloaded
        job.completed_at = datetime.utcnow()
        db.commit()


def run_bulk_download(
    job_id: str,
    channel_ids: Optional[Sequence[str]] = None,
    allowed_video_ids: Optional[Iterable[str]] = None,
    youtube_service: Optional[YouTubeService] = None,
    download_service: Optional[DownloadService] = None,
) -> None:
    """
    Run bulk download job for linked channels or explicit channel list.

    - linked channels when job has suggestion_id
    - explicit channels when channel_ids is passed
    """
    videos_found = 0
    videos_downloaded = 0
    allowed_set = set(allowed_video_ids or [])
    downloader = download_service or DownloadService()
    youtube = youtube_service or get_youtube_service()

    try:
        with _session() as db:
            job = _select_job(db, job_id)
            if not job:
                logger.warning("Download job not found: %s", job_id)
                return

            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

            channels = _resolve_channels(db, job, explicit_channel_ids=channel_ids)
            suggestion_id = job.suggestion_id
            job.channels_total = len(channels)
            db.commit()
            channel_rows = [(channel.id, channel.channel_id) for channel in channels]

        data_dir = downloader.resolve_data_dir()

        for channel_db_id, channel_youtube_id in channel_rows:
            recent_videos = youtube.get_recent_videos(
                channel_youtube_id,
                days=7,
                max_results=5,
            )
            if allowed_set:
                recent_videos = [
                    video for video in recent_videos if video.get("id") in allowed_set
                ]
            videos_found += len(recent_videos)

            for video in recent_videos:
                video_id = video.get("id")
                if not video_id:
                    continue

                with _session() as db:
                    existing = db.query(VideoAssetModel).filter(
                        VideoAssetModel.youtube_video_id == video_id
                    ).first()
                if existing:
                    continue

                output_path = (
                    data_dir
                    / "downloads"
                    / channel_youtube_id
                    / f"{video_id}.mp4"
                )

                ok = downloader.download(
                    video.get("youtube_url", f"https://www.youtube.com/watch?v={video_id}"),
                    Path(output_path),
                )
                if not ok:
                    continue

                with _session() as db:
                    db.add(
                        VideoAssetModel(
                            youtube_video_id=video_id,
                            channel_id=channel_db_id,
                            suggestion_id=suggestion_id,
                            title=video.get("title", video_id),
                            view_count=video.get("view_count") or 0,
                            duration_sec=video.get("duration_sec") or 0,
                            youtube_url=video.get(
                                "youtube_url",
                                f"https://www.youtube.com/watch?v={video_id}",
                            ),
                            file_path=str(output_path),
                            status="downloaded",
                            review_status="pending",
                            downloaded_at=datetime.utcnow(),
                            metadata_json=video,
                        )
                    )
                    db.commit()
                videos_downloaded += 1

        with _session() as db:
            job = _select_job(db, job_id)
            if job is None:
                return
            job.videos_found = videos_found
            job.videos_downloaded = videos_downloaded
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            db.commit()
    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("Bulk download failed for job %s", job_id)
        _mark_job_failed(job_id, exc, videos_found, videos_downloaded)
