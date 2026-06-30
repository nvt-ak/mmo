"""
Scoring Skills — enhanced scoring with strategy weights.
"""
from services.scanner_service import score_video
from services.channel_discovery import _score_channel
from utils.logger import get_logger

log = get_logger("scoring")


def score_channel_with_strategy(channel: dict, strategy: dict) -> int:
    """Score a channel using strategy weights."""
    weights = strategy.get("weights", {})
    filters = strategy.get("filters", {})

    subs = channel.get("subscribers", 0)
    avg_views = channel.get("avg_views", 0)
    video_count = channel.get("video_count", 0)

    # sub score
    max_subs = filters.get("max_subs", 50000)
    if subs <= 5000:
        sub_score = 30
    elif subs <= 15000:
        sub_score = 24
    elif subs <= 30000:
        sub_score = 16
    elif subs <= max_subs:
        sub_score = 8
    else:
        sub_score = 0

    # view score
    min_v = filters.get("min_views", 50000)
    max_v = filters.get("max_views", 300000)
    midpoint = (min_v + max_v) / 2
    view_range = (max_v - min_v) / 2
    distance = abs(avg_views - midpoint)
    view_score = max(0, int(30 * (1 - distance / view_range))) if view_range > 0 else 0

    # upload consistency
    if video_count >= 100:
        upload_score = 20
    elif video_count >= 50:
        upload_score = 14
    elif video_count >= 20:
        upload_score = 8
    else:
        upload_score = 2

    # engagement
    ratio = avg_views / subs if subs > 0 else 0
    ratio_score = 20 if ratio >= 5 else 14 if ratio >= 2 else 8 if ratio >= 1 else 2

    total = sub_score + view_score + upload_score + ratio_score
    log.debug(f"Channel score: {channel.get('name')} = {total}")
    return min(100, total)


def score_video_with_strategy(video: dict, channel_subs: int, strategy: dict) -> int:
    """Score a video using strategy weights."""
    tiktok_status = video.get("tiktok_status", "unknown")
    return score_video(
        video["view_count"],
        video["upload_date"],
        channel_subs,
        tiktok_status,
    )
