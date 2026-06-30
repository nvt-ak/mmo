"""
Channel Discovery Service
Tìm channels phù hợp để follow dựa trên keywords.
Không cần login — dùng YouTube Data API v3.
"""
from utils.logger import get_logger
from services.youtube_service import _build_client
from database.db import get_connection

log = get_logger("discovery")

# Channels đã có trong DB hoặc đã follow → skip
def _existing_channel_ids() -> set[str]:
    conn = get_connection()
    rows = conn.execute("SELECT id FROM channels").fetchall()
    conn.close()
    return {r[0] for r in rows}


def search_channels(
    keyword: str,
    max_results: int = 20,
    max_subs: int = 50_000,
    min_subs: int = 1_000,
) -> list[dict]:
    """
    Search YouTube channels by keyword.
    Filter: subs between min_subs and max_subs.
    Return scored + ranked list.
    """
    log.info(f"Searching channels: '{keyword}' max_subs={max_subs}")
    try:
        yt = _build_client()

        # search channels (100 units)
        resp = yt.search().list(
            part="snippet",
            q=keyword,
            type="channel",
            maxResults=max_results,
            relevanceLanguage="en",
        ).execute()

        channel_ids = [
            item["snippet"]["channelId"]
            for item in resp.get("items", [])
        ]
        log.debug(f"Found {len(channel_ids)} channel IDs")

        if not channel_ids:
            return []

        # fetch stats (1 unit)
        stats_resp = yt.channels().list(
            part="snippet,statistics,contentDetails",
            id=",".join(channel_ids),
        ).execute()

        existing = _existing_channel_ids()
        results = []

        for item in stats_resp.get("items", []):
            ch_id   = item["id"]
            stats   = item.get("statistics", {})
            snippet = item.get("snippet", {})

            subs = int(stats.get("subscriberCount", 0))
            if not (min_subs <= subs <= max_subs):
                log.debug(f"Skip subs={subs:,}: {snippet.get('title')}")
                continue

            video_count = int(stats.get("videoCount", 0))
            view_count  = int(stats.get("viewCount", 0))
            avg_views   = int(view_count / video_count) if video_count > 0 else 0

            score = _score_channel(subs, avg_views, video_count)

            results.append({
                "id":           ch_id,
                "name":         snippet.get("title", ""),
                "description":  snippet.get("description", "")[:120],
                "url":          f"https://www.youtube.com/channel/{ch_id}",
                "subscribers":  subs,
                "video_count":  video_count,
                "avg_views":    avg_views,
                "score":        score,
                "already_tracked": ch_id in existing,
            })
            log.debug(
                f"  score={score} subs={subs:,} avg_views={avg_views:,} "
                f"name={snippet.get('title')}"
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        log.info(f"Returning {len(results)} scored channels for '{keyword}'")
        return results

    except Exception as e:
        log.error(f"search_channels error: {e}", exc_info=True)
        return []


def _score_channel(subs: int, avg_views: int, video_count: int) -> int:
    """
    Score 0-100 for how suitable a channel is to follow.

    avg_views sweet spot: 150K-200K (30 pts)
    subs small:           <10K best (30 pts)
    upload consistency:   more videos = better (20 pts)
    subs/views ratio:     high ratio = engaged audience (20 pts)
    """
    # avg views sweet spot
    if 150_000 <= avg_views <= 200_000:
        view_score = 30
    elif 100_000 <= avg_views < 150_000:
        view_score = 20
    elif 200_000 < avg_views <= 300_000:
        view_score = 15
    elif 50_000 <= avg_views < 100_000:
        view_score = 10
    else:
        view_score = 0

    # smaller channel = less competition, less likely reported
    if subs <= 5_000:
        sub_score = 30
    elif subs <= 15_000:
        sub_score = 24
    elif subs <= 30_000:
        sub_score = 16
    elif subs <= 50_000:
        sub_score = 8
    else:
        sub_score = 0

    # upload consistency (more = regular uploader)
    if video_count >= 100:
        upload_score = 20
    elif video_count >= 50:
        upload_score = 14
    elif video_count >= 20:
        upload_score = 8
    else:
        upload_score = 2

    # engagement ratio: avg_views / subs
    ratio = avg_views / subs if subs > 0 else 0
    if ratio >= 5:
        ratio_score = 20
    elif ratio >= 2:
        ratio_score = 14
    elif ratio >= 1:
        ratio_score = 8
    else:
        ratio_score = 2

    return view_score + sub_score + upload_score + ratio_score


def save_channel(channel: dict, niche_tag: str = "kpop"):
    """Persist discovered channel to DB for tracking."""
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO channels
           (id, name, url, niche_tag, subscribers, avg_views)
           VALUES (?,?,?,?,?,?)""",
        (channel["id"], channel["name"], channel["url"],
         niche_tag, channel["subscribers"], channel["avg_views"]),
    )
    conn.commit()
    conn.close()
    log.info(f"Saved channel: {channel['name']} ({channel['subscribers']:,} subs)")
