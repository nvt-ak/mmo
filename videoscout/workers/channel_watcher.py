"""Watcher worker to ingest newly uploaded videos from tracked channels."""
from datetime import datetime
import logging

import videoscout.db as db_module
from videoscout.db.models import ChannelModel, DownloadJobModel, VideoAssetModel
from videoscout.services.youtube import get_youtube_service
from videoscout.workers.bulk_download import run_bulk_download

logger = logging.getLogger(__name__)


def run_channel_watcher() -> None:
    """Scan enabled channels and queue watcher download jobs for new uploads."""
    db = db_module.get_session()
    youtube = get_youtube_service()

    try:
        channels = db.query(ChannelModel).filter(ChannelModel.scan_enabled.is_(True)).all()
        now = datetime.utcnow()

        for channel in channels:
            videos = youtube.get_recent_videos(channel.channel_id, days=7, max_results=20)
            known_ids = {
                row.youtube_video_id
                for row in db.query(VideoAssetModel.youtube_video_id)
                .filter(VideoAssetModel.channel_id == channel.id)
                .all()
            }

            new_video_ids = []
            for video in videos:
                video_id = video.get("id")
                if not video_id or video_id in known_ids:
                    continue

                if channel.last_scan_at and video.get("upload_date"):
                    try:
                        uploaded = datetime.fromisoformat(video["upload_date"])
                        if uploaded <= channel.last_scan_at:
                            continue
                    except ValueError:
                        pass
                new_video_ids.append(video_id)

            if new_video_ids:
                job = DownloadJobModel(
                    job_type="watcher",
                    status="started",
                    channels_total=1,
                )
                db.add(job)
                db.flush()
                db.commit()
                run_bulk_download(
                    str(job.id),
                    channel_ids=[channel.channel_id],
                    allowed_video_ids=new_video_ids,
                    youtube_service=youtube,
                )

            channel.last_scan_at = now
            channel.last_video_count = len(videos)
            db.commit()
    except Exception as exc:  # pragma: no cover - defensive path
        db.rollback()
        logger.exception("Channel watcher failed: %s", exc)
    finally:
        # get_session can be monkeypatched to a shared session in tests.
        pass
