from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler = BackgroundScheduler()
_scan_callback = None


def start(scan_fn, hour: int = 6, minute: int = 0, on_complete=None):
    """
    Start background scheduler.
    scan_fn: callable → runs the scan
    on_complete: callable(ScanResult) → called after scan finishes (UI update)
    """
    global _scan_callback
    _scan_callback = on_complete

    def _job():
        result = scan_fn()
        if on_complete:
            on_complete(result)

    _scheduler.add_job(
        _job,
        CronTrigger(hour=hour, minute=minute),
        id="daily_scan",
        replace_existing=True,
    )
    if not _scheduler.running:
        _scheduler.start()


def update_schedule(hour: int, minute: int):
    if _scheduler.get_job("daily_scan"):
        _scheduler.reschedule_job(
            "daily_scan",
            trigger=CronTrigger(hour=hour, minute=minute),
        )


def stop():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
