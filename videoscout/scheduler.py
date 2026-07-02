"""
APScheduler integration for daily digest scan.
Supports both APScheduler and FastAPI BackgroundTasks.
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

scheduler = None


def parse_schedule_time(schedule_time: str) -> Tuple[int, int]:
    """Parse HH:MM schedule string. Raises ValueError on invalid format."""
    parts = schedule_time.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid schedule time: {schedule_time}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid schedule time: {schedule_time}")
    return hour, minute


def resolve_schedule_time() -> Tuple[int, int, str]:
    """
    Resolve cron schedule from DB settings (if available), then env, then default.
    """
    schedule_time = os.getenv("SCHEDULE_TIME", "09:00")

    try:
        from videoscout.db import get_session
        from videoscout.db.models import SettingsModel

        db = get_session()
        try:
            settings = db.query(SettingsModel).first()
            if settings and settings.scheduler_daily_time:
                schedule_time = settings.scheduler_daily_time
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Could not read schedule from DB: %s", exc)

    try:
        hour, minute = parse_schedule_time(schedule_time)
    except ValueError:
        logger.warning("Invalid schedule '%s', using 09:00", schedule_time)
        schedule_time = "09:00"
        hour, minute = 9, 0

    return hour, minute, schedule_time


def is_scheduler_enabled() -> bool:
    """Check env + DB settings for scheduler enable flag."""
    if os.getenv("SCHEDULER_ENABLED", "true").lower() != "true":
        return False

    try:
        from videoscout.db import get_session
        from videoscout.db.models import SettingsModel

        db = get_session()
        try:
            settings = db.query(SettingsModel).first()
            if settings and settings.scheduler_enabled is False:
                return False
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Could not read scheduler flag from DB: %s", exc)

    return True


async def _run_scheduled_daily_digest():
    """Run daily scan of all enabled channels."""
    logger.info("Scheduled daily digest starting")
    from videoscout.db import get_session
    from videoscout.db.models import ScanJobModel
    from videoscout.core_engine.engine import SuggestionEngine
    from videoscout.api.scan import run_daily_digest

    db = get_session()
    job_id = uuid.uuid4()
    job = ScanJobModel(id=job_id, status="started")
    db.add(job)
    db.commit()

    try:
        engine = SuggestionEngine()
        await run_daily_digest(
            job_id=job_id,
            channel_ids=[],  # All enabled channels
            force=False,
            engine=engine,
        )
        logger.info("Scheduled daily digest complete")
    except Exception as e:
        logger.error("Scheduled daily digest failed: %s", e)
    finally:
        db.close()


def init_scheduler() -> Optional[object]:
    """
    Initialize APScheduler with daily digest cron job.

    Reads schedule time from settings table if available.
    Falls back to env SCHEDULE_TIME or default '09:00'.

    Returns scheduler instance, or None if disabled or APScheduler missing.
    """
    global scheduler

    if not is_scheduler_enabled():
        logger.info("Scheduler disabled via env or settings")
        return None

    hour, minute, schedule_time = resolve_schedule_time()

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("APScheduler not installed — skipping daily cron")
        return None

    if scheduler is None:
        scheduler = AsyncIOScheduler()

    if scheduler.get_job("daily_digest"):
        scheduler.remove_job("daily_digest")
    if scheduler.get_job("channel_watcher"):
        scheduler.remove_job("channel_watcher")

    scheduler.add_job(
        _run_scheduled_daily_digest,
        CronTrigger(hour=hour, minute=minute),
        id="daily_digest",
    )
    from videoscout.workers.channel_watcher import run_channel_watcher
    scheduler.add_job(
        run_channel_watcher,
        IntervalTrigger(hours=6),
        id="channel_watcher",
    )

    logger.info(
        "Scheduler initialized — daily digest at %s + watcher every 6h",
        schedule_time,
    )
    return scheduler


def shutdown_scheduler():
    """Gracefully shutdown scheduler."""
    global scheduler
    if scheduler:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.debug("Scheduler shutdown skipped: %s", exc)
        scheduler = None
        logger.info("Scheduler shutdown complete")
