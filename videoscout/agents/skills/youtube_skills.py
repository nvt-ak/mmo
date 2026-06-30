"""
YouTube Skills — wrappers around existing services.
"""
from services.channel_discovery import search_channels, save_channel, _existing_channel_ids
from services.youtube_service import fetch_channel_info, fetch_recent_videos, _build_client
from services.scanner_service import score_video, apply_filters
from database.db import get_connection
from utils.logger import get_logger

log = get_logger("yt_skills")


def discover_channels(keyword: str, strategy_filters: dict) -> list[dict]:
    """Search YouTube channels matching keyword + strategy filters."""
    min_subs = strategy_filters.get("min_subs", 1000)
    max_subs = strategy_filters.get("max_subs", 50000)
    return search_channels(keyword, max_results=20, max_subs=max_subs, min_subs=min_subs)


def get_channel_videos(channel_id: str, days: int = 30) -> list[dict]:
    """Fetch recent videos for a channel."""
    return fetch_recent_videos(channel_id, days=days)


def get_channel_stats(channel_id: str) -> dict | None:
    """Fetch channel info/stats."""
    return fetch_channel_info(channel_id)


def get_existing_channels() -> set[str]:
    """Return set of already-tracked channel IDs."""
    return _existing_channel_ids()


def record_channel_outcome(channel_id: str, name: str, subscribers: int,
                           videos_found: int, avg_video_score: float,
                           llm_evaluation: dict, outcome: str = "followed"):
    """Save channel outcome for learning."""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO channel_outcomes
           (channel_id, name, subscribers, videos_found, avg_video_score,
            llm_score, llm_recommendation, llm_reasoning, outcome)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (channel_id, name, subscribers, videos_found, avg_video_score,
         llm_evaluation.get("score"), llm_evaluation.get("recommendation"),
         llm_evaluation.get("reasoning"), outcome),
    )
    conn.commit()
    conn.close()
    log.info(f"Recorded outcome: {name} → {outcome}")


def get_outcomes() -> list[dict]:
    """Get all channel outcomes for learning."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM channel_outcomes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_channels_for_evaluation(limit: int = 10) -> list[dict]:
    """Get top-scoring channels that haven't been LLM-evaluated yet."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, COUNT(v.id) as video_count,
                  AVG(v.opportunity_score) as avg_video_score
           FROM channels c
           LEFT JOIN videos v ON c.id = v.channel_id
           WHERE c.is_active = 1
             AND c.id NOT IN (SELECT channel_id FROM channel_outcomes)
           GROUP BY c.id
           ORDER BY avg_video_score DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
