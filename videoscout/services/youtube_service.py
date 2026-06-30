import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv()
log = get_logger("youtube")

_YT_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


def _build_client():
    key = os.getenv("YOUTUBE_API_KEY", _YT_API_KEY)
    if not key:
        raise ValueError("YOUTUBE_API_KEY not set in .env")
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=key, cache_discovery=False)


def extract_channel_id(url_or_id: str) -> Optional[str]:
    log.debug(f"extract_channel_id: {url_or_id}")
    patterns = [
        r"youtube\.com/channel/(UC[\w-]{21})",
        r"youtube\.com/@([\w.-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            handle = m.group(1)
            if re.match(r"^UC[\w-]{21}$", handle):
                return handle
            return _resolve_handle(handle)
    if re.match(r"^UC[\w-]{21}$", url_or_id.strip()):
        return url_or_id.strip()
    log.warning(f"Could not extract channel ID from: {url_or_id}")
    return None


def _resolve_handle(handle: str) -> Optional[str]:
    try:
        yt = _build_client()
        resp = yt.channels().list(part="id", forHandle=handle).execute()
        items = resp.get("items", [])
        if items:
            cid = items[0]["id"]
            log.debug(f"Resolved @{handle} → {cid}")
            return cid
        log.warning(f"Handle @{handle} not found")
        return None
    except Exception as e:
        log.error(f"_resolve_handle error: {e}")
        return None


def fetch_channel_info(channel_id: str) -> Optional[dict]:
    log.debug(f"fetch_channel_info: {channel_id}")
    try:
        yt = _build_client()
        resp = yt.channels().list(
            part="snippet,statistics", id=channel_id
        ).execute()
        items = resp.get("items", [])
        if not items:
            log.warning(f"No channel found for id={channel_id}")
            return None
        item = items[0]
        info = {
            "id": channel_id,
            "name": item["snippet"]["title"],
            "url": f"https://www.youtube.com/channel/{channel_id}",
            "subscribers": int(item["statistics"].get("subscriberCount", 0)),
        }
        log.info(f"Channel fetched: {info['name']} ({info['subscribers']:,} subs)")
        return info
    except Exception as e:
        log.error(f"fetch_channel_info error: {e}")
        return None


def fetch_recent_videos(
    channel_id: str,
    days: int = 30,
    max_results: int = 50,
) -> list[dict]:
    """Fetch recent videos using playlistItems API (1 unit) instead of search (100 units)."""
    log.debug(f"fetch_recent_videos: channel={channel_id} days={days}")
    try:
        yt = _build_client()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Uploads playlist = "UU" + channel_id[2:]  (costs 1 unit, not 100)
        uploads_playlist_id = "UU" + channel_id[2:]

        playlist_resp = yt.playlistItems().list(
            part="contentDetails,snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results,
        ).execute()

        # Filter by date client-side
        video_ids = []
        for item in playlist_resp.get("items", []):
            published_at = item["snippet"].get("publishedAt", "")
            if published_at:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if pub_dt >= cutoff:
                    vid_id = item["contentDetails"].get("videoId")
                    if vid_id:
                        video_ids.append(vid_id)

        log.debug(f"Found {len(video_ids)} video IDs in playlist (within {days} days)")

        if not video_ids:
            return []

        stats_resp = yt.videos().list(
            part="statistics,contentDetails,snippet",
            id=",".join(video_ids),
        ).execute()

        results = []
        for item in stats_resp.get("items", []):
            vid_id = item["id"]
            stats   = item.get("statistics", {})
            snippet = item.get("snippet", {})
            duration = _parse_duration(
                item.get("contentDetails", {}).get("duration", "PT0S")
            )
            results.append({
                "id":            vid_id,
                "title":         snippet.get("title", ""),
                "upload_date":   snippet.get("publishedAt", "")[:10],
                "thumbnail_url": snippet.get("thumbnails", {})
                                        .get("medium", {}).get("url", ""),
                "duration_sec":  duration,
                "view_count":    int(stats.get("viewCount", 0)),
                "youtube_url":   f"https://www.youtube.com/watch?v={vid_id}",
            })
        log.info(f"channel={channel_id} → {len(results)} videos with stats")
        return results

    except Exception as e:
        log.error(f"fetch_recent_videos error channel={channel_id}: {e}")
        return []


def _parse_duration(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mins, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mins * 60 + s
