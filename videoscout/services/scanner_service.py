from datetime import datetime, date, timedelta
from database.db import get_connection
from database.models import Video, ScanResult
from services.youtube_service import fetch_recent_videos
from utils.logger import get_logger

log = get_logger("scanner")

DEFAULT_VIEW_MIN = 150_000
DEFAULT_VIEW_MAX = 200_000
DEFAULT_DAYS     = 30
DEFAULT_MAX_SUBS = 50_000
DEFAULT_MAX_DUR  = 180


def score_video(
    view_count: int,
    upload_date: str,
    channel_subscribers: int,
    tiktok_status: str = "unknown",
) -> int:
    try:
        days_ago = (date.today() - date.fromisoformat(upload_date)).days
    except ValueError:
        days_ago = DEFAULT_DAYS

    recency = max(0, 40 - int((days_ago / DEFAULT_DAYS) * 40))

    midpoint   = (DEFAULT_VIEW_MIN + DEFAULT_VIEW_MAX) / 2
    view_range = (DEFAULT_VIEW_MAX - DEFAULT_VIEW_MIN) / 2
    distance   = abs(view_count - midpoint)
    view_score = max(0, int(30 * (1 - distance / view_range)))

    if channel_subscribers <= 10_000:
        channel_score = 20
    elif channel_subscribers <= 30_000:
        channel_score = 14
    elif channel_subscribers <= DEFAULT_MAX_SUBS:
        channel_score = 8
    else:
        channel_score = 0

    gap = {"fresh": 10, "medium": 5, "saturated": 0, "unknown": 3}.get(tiktok_status, 3)
    total = recency + view_score + channel_score + gap
    log.debug(
        f"score={total} recency={recency} view={view_score} "
        f"channel={channel_score} gap={gap} | views={view_count} date={upload_date}"
    )
    return total


def apply_filters(
    videos: list[dict],
    channel_subscribers: int,
    view_min: int = DEFAULT_VIEW_MIN,
    view_max: int = DEFAULT_VIEW_MAX,
    days: int = DEFAULT_DAYS,
    max_subs: int = DEFAULT_MAX_SUBS,
    max_dur: int = DEFAULT_MAX_DUR,
) -> list[dict]:
    if channel_subscribers > max_subs:
        log.debug(f"Channel skipped: {channel_subscribers} subs > max {max_subs}")
        return []
    cutoff = date.today() - timedelta(days=days)
    result = []
    for v in videos:
        if not (view_min <= v["view_count"] <= view_max):
            log.debug(f"Skip views={v['view_count']:,} title={v['title'][:40]}")
            continue
        try:
            if date.fromisoformat(v["upload_date"]) < cutoff:
                log.debug(f"Skip old date={v['upload_date']} title={v['title'][:40]}")
                continue
        except ValueError:
            continue
        if v["duration_sec"] > max_dur:
            log.debug(f"Skip duration={v['duration_sec']}s title={v['title'][:40]}")
            continue
        log.debug(f"PASS views={v['view_count']:,} date={v['upload_date']} title={v['title'][:50]}")
        result.append(v)
    return result


def scan_all_channels(
    view_min: int = DEFAULT_VIEW_MIN,
    view_max: int = DEFAULT_VIEW_MAX,
    days: int = DEFAULT_DAYS,
    max_subs: int = DEFAULT_MAX_SUBS,
    progress_callback=None,
) -> ScanResult:
    log.info(f"Scan started — filters: views={view_min}-{view_max} days={days} max_subs={max_subs}")
    conn = get_connection()
    channels = conn.execute(
        "SELECT * FROM channels WHERE is_active = 1"
    ).fetchall()
    conn.close()

    total = len(channels)
    log.info(f"Active channels: {total}")

    if total == 0:
        log.warning("No active channels found — add channels first")
        return ScanResult(channels_scanned=0, videos_found=0, top_score=0, videos=[])

    conn = get_connection()
    existing_ids = {r[0] for r in conn.execute("SELECT id FROM videos").fetchall()}
    conn.close()

    found_videos: list[Video] = []

    for idx, ch in enumerate(channels):
        ch_name = ch["name"]
        ch_id   = ch["id"]
        ch_subs = ch["subscribers"]
        log.info(f"[{idx+1}/{total}] Scanning: {ch_name} ({ch_subs:,} subs)")

        if progress_callback:
            progress_callback(idx + 1, total, ch_name)

        raw = fetch_recent_videos(ch_id, days=days)
        log.info(f"  Raw videos fetched: {len(raw)}")

        filtered = apply_filters(
            raw,
            channel_subscribers=ch_subs,
            view_min=view_min,
            view_max=view_max,
            days=days,
            max_subs=max_subs,
        )
        log.info(f"  After filter: {len(filtered)} videos pass")

        for v in filtered:
            if v["id"] in existing_ids:
                log.debug(f"  Already exists: {v['id']}")
                continue
            score = score_video(v["view_count"], v["upload_date"], ch_subs)
            video = Video(
                id=v["id"],
                channel_id=ch_id,
                title=v["title"],
                view_count=v["view_count"],
                upload_date=v["upload_date"],
                youtube_url=v["youtube_url"],
                duration_sec=v["duration_sec"],
                thumbnail_url=v["thumbnail_url"],
                opportunity_score=score,
                tiktok_status="unknown",
                channel_name=ch_name,
                channel_subscribers=ch_subs,
            )
            found_videos.append(video)
            existing_ids.add(v["id"])
            log.info(f"  + NEW video score={score}: {v['title'][:60]}")

    # persist
    conn = get_connection()
    conn.executemany(
        """INSERT OR IGNORE INTO videos
           (id, channel_id, title, view_count, upload_date,
            duration_sec, thumbnail_url, youtube_url,
            opportunity_score, tiktok_status)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [(v.id, v.channel_id, v.title, v.view_count, v.upload_date,
          v.duration_sec, v.thumbnail_url, v.youtube_url,
          v.opportunity_score, v.tiktok_status)
         for v in found_videos],
    )
    top_score = max((v.opportunity_score for v in found_videos), default=0)
    conn.execute(
        "INSERT INTO scan_history (channels_scanned, videos_found, top_score) VALUES (?,?,?)",
        (total, len(found_videos), top_score),
    )
    conn.commit()
    conn.close()

    log.info(f"Scan done — {len(found_videos)} new videos, top score={top_score}")
    return ScanResult(
        channels_scanned=total,
        videos_found=len(found_videos),
        top_score=top_score,
        videos=found_videos,
    )


def get_daily_digest(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT v.*, c.name as channel_name, c.subscribers as channel_subscribers
           FROM videos v
           JOIN channels c ON v.channel_id = c.id
           WHERE v.is_used = 0
           ORDER BY v.opportunity_score DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    log.debug(f"get_daily_digest → {len(result)} videos")
    return result


def mark_video_used(video_id: str):
    conn = get_connection()
    conn.execute("UPDATE videos SET is_used = 1 WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()
    log.info(f"Marked used: {video_id}")


def get_channel_stats() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.name, c.niche_tag, c.subscribers,
                  COUNT(v.id) as video_count,
                  AVG(v.opportunity_score) as avg_score,
                  MAX(v.opportunity_score) as max_score
           FROM channels c
           LEFT JOIN videos v ON c.id = v.channel_id
           WHERE c.is_active = 1
           GROUP BY c.id
           ORDER BY avg_score DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
