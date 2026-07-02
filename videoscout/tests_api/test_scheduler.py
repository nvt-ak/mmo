"""APScheduler cron validation tests."""
import os
import uuid
from datetime import datetime
from unittest.mock import patch, AsyncMock

import pytest

from videoscout.scheduler import (
    parse_schedule_time,
    resolve_schedule_time,
    is_scheduler_enabled,
    init_scheduler,
    shutdown_scheduler,
)
from videoscout.db.models import ScanJobModel, SettingsModel


@pytest.fixture(autouse=True)
def reset_scheduler(monkeypatch):
    """Isolate scheduler global state between tests."""
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    shutdown_scheduler()
    yield
    shutdown_scheduler()


# ═══════════════════════════════════════════════════════
# 1. Schedule time parsing
# ═══════════════════════════════════════════════════════

@pytest.mark.parametrize("value,expected", [
    ("09:00", (9, 0)),
    ("14:30", (14, 30)),
    ("00:00", (0, 0)),
    ("23:59", (23, 59)),
])
def test_parse_schedule_time_valid(value, expected):
    assert parse_schedule_time(value) == expected


@pytest.mark.parametrize("value", [
    "9:00",      # missing leading zero ok? int("9") works - actually "9:00".split gives hour=9 - valid
    "25:00",
    "12:60",
    "noon",
    "12",
    "",
])
def test_parse_schedule_time_invalid(value):
    if value == "9:00":
        assert parse_schedule_time(value) == (9, 0)
        return
    with pytest.raises(ValueError):
        parse_schedule_time(value)


def test_resolve_schedule_time_from_env(monkeypatch):
    monkeypatch.setenv("SCHEDULE_TIME", "07:15")
    hour, minute, label = resolve_schedule_time()
    assert (hour, minute) == (7, 15)
    assert label == "07:15"


def test_resolve_schedule_time_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("SCHEDULE_TIME", "bad-time")
    hour, minute, label = resolve_schedule_time()
    assert (hour, minute) == (9, 0)
    assert label == "09:00"


def test_resolve_schedule_time_from_db(db_session, monkeypatch):
    monkeypatch.delenv("SCHEDULE_TIME", raising=False)
    db_session.add(SettingsModel(scheduler_daily_time="06:45"))
    db_session.commit()

    import videoscout.db as db_mod
    db_mod.get_session = lambda: db_session

    hour, minute, label = resolve_schedule_time()
    assert (hour, minute) == (6, 45)
    assert label == "06:45"


# ═══════════════════════════════════════════════════════
# 2. Enable / disable
# ═══════════════════════════════════════════════════════

def test_scheduler_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    assert init_scheduler() is None


def test_scheduler_disabled_by_db_settings(db_session, monkeypatch):
    db_session.add(SettingsModel(scheduler_enabled=False))
    db_session.commit()

    import videoscout.db as db_mod
    db_mod.get_session = lambda: db_session

    assert is_scheduler_enabled() is False
    assert init_scheduler() is None


# ═══════════════════════════════════════════════════════
# 3. Cron trigger configuration
# ═══════════════════════════════════════════════════════

def test_init_scheduler_registers_daily_digest_job(monkeypatch):
    monkeypatch.setenv("SCHEDULE_TIME", "09:00")
    sched = init_scheduler()
    assert sched is not None

    job = sched.get_job("daily_digest")
    assert job is not None
    assert job.id == "daily_digest"


def test_cron_trigger_fires_at_configured_time(monkeypatch):
    monkeypatch.setenv("SCHEDULE_TIME", "14:30")
    sched = init_scheduler()
    job = sched.get_job("daily_digest")

    before = datetime(2026, 7, 2, 14, 29, 0)
    next_fire = job.trigger.get_next_fire_time(None, before)
    assert next_fire.hour == 14
    assert next_fire.minute == 30
    assert next_fire.day == 2


def test_cron_trigger_rolls_to_next_day_after_time(monkeypatch):
    monkeypatch.setenv("SCHEDULE_TIME", "09:00")
    sched = init_scheduler()
    job = sched.get_job("daily_digest")

    after = datetime(2026, 7, 2, 9, 1, 0)
    next_fire = job.trigger.get_next_fire_time(None, after)
    assert next_fire.day == 3
    assert next_fire.hour == 9
    assert next_fire.minute == 0


def test_replace_existing_job_on_reinit(monkeypatch):
    monkeypatch.setenv("SCHEDULE_TIME", "08:00")
    sched1 = init_scheduler()
    assert len(sched1.get_jobs()) == 1

    monkeypatch.setenv("SCHEDULE_TIME", "10:00")
    sched2 = init_scheduler()
    assert sched2 is sched1
    assert len(sched2.get_jobs()) == 1

    job = sched2.get_job("daily_digest")
    next_fire = job.trigger.get_next_fire_time(None, datetime(2026, 7, 2, 7, 0))
    assert next_fire.hour == 10


# ═══════════════════════════════════════════════════════
# 4. Job execution
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch("videoscout.api.scan.run_daily_digest", new_callable=AsyncMock)
@patch("videoscout.core_engine.engine.SuggestionEngine")
async def test_daily_digest_job_invokes_scan(
    mock_engine_cls, mock_run_digest, db_session, monkeypatch
):
    mock_run_digest.return_value = None
    import videoscout.db as db_mod
    db_mod.get_session = lambda: db_session

    sched = init_scheduler()
    job = sched.get_job("daily_digest")
    await job.func()

    mock_run_digest.assert_called_once()
    kwargs = mock_run_digest.call_args.kwargs
    assert kwargs["channel_ids"] == []
    assert kwargs["force"] is False
    assert isinstance(kwargs["job_id"], uuid.UUID)


@pytest.mark.asyncio
@patch("videoscout.api.scan.run_daily_digest", new_callable=AsyncMock)
@patch("videoscout.core_engine.engine.SuggestionEngine")
async def test_scheduled_run_creates_scan_job_record(
    mock_engine_cls, mock_run_digest, db_session, monkeypatch
):
    mock_run_digest.return_value = None
    import videoscout.db as db_mod
    db_mod.get_session = lambda: db_session

    sched = init_scheduler()
    job = sched.get_job("daily_digest")
    await job.func()

    jobs = db_session.query(ScanJobModel).all()
    assert len(jobs) == 1
    assert jobs[0].status == "started"


def test_shutdown_scheduler_clears_global(monkeypatch):
    sched = init_scheduler()
    assert sched is not None
    shutdown_scheduler()

    import videoscout.scheduler as sched_mod
    assert sched_mod.scheduler is None
