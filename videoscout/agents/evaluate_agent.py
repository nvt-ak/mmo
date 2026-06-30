"""
Evaluate Agent — uses LLM to assess channel quality + niche fit.
"""
import json
from pathlib import Path
from agents.skills.llm_skills import evaluate_channel
from agents.skills.youtube_skills import (
    get_channel_videos,
    get_channel_stats,
    record_channel_outcome,
    get_top_channels_for_evaluation,
)
from utils.logger import get_logger

log = get_logger("evaluate")

MEMORY_DIR = Path(__file__).parent / "memory"


def _load_strategy() -> dict:
    path = MEMORY_DIR / "strategy.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"llm": {"enabled": True}}


def evaluate_candidate(channel: dict) -> dict:
    """
    Evaluate a single candidate channel using LLM.
    Returns enriched channel dict with LLM assessment.
    """
    strategy = _load_strategy()
    if not strategy.get("llm", {}).get("enabled", True):
        log.info("LLM evaluation disabled — skipping")
        return channel

    ch_id = channel["id"]
    log.info(f"Evaluating channel: {channel.get('name', ch_id)}")

    # fetch videos + stats
    videos = get_channel_videos(ch_id, days=30)
    stats = get_channel_stats(ch_id)

    if not videos:
        log.warning(f"No videos found for {channel.get('name')} — marking as skip")
        return {**channel, "llm": {"recommendation": "skip", "reasoning": "No recent videos"}}

    # LLM evaluation
    llm_result = evaluate_channel(channel, videos)

    # record outcome
    avg_score = sum(v.get("view_count", 0) for v in videos) / len(videos) if videos else 0
    record_channel_outcome(
        channel_id=ch_id,
        name=channel.get("name", "Unknown"),
        subscribers=channel.get("subscribers", 0),
        videos_found=len(videos),
        avg_video_score=avg_score,
        llm_evaluation=llm_result,
        outcome=llm_result.get("recommendation", "skip"),
    )

    enriched = {**channel, "llm": llm_result, "videos": videos}
    log.info(
        f"  → score={llm_result.get('score')} "
        f"rec={llm_result.get('recommendation')} "
        f"risk={llm_result.get('risk')}"
    )
    return enriched


def run(candidates: list[dict]) -> list[dict]:
    """
    Evaluate all candidate channels.
    Returns list with LLM assessments added.
    """
    log.info(f"Evaluating {len(candidates)} candidates")
    evaluated = []
    for ch in candidates:
        result = evaluate_candidate(ch)
        evaluated.append(result)

    # sort by LLM score
    evaluated.sort(
        key=lambda x: x.get("llm", {}).get("score", 0) or 0,
        reverse=True,
    )
    follows = [e for e in evaluated if e.get("llm", {}).get("recommendation") == "follow"]
    log.info(f"Evaluate complete: {len(follows)}/{len(evaluated)} recommended to follow")
    return evaluated
