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


def evaluate_keyword(keyword: str, channel_id: str = None) -> dict:
    """
    Evaluate a keyword for TikTok repost potential.
    
    MVP Implementation (Formula 3, locked 2026-06-30):
    - Uses TikTok saturation check + keyword heuristics
    - No LLM required for Phase 1-2
    
    Args:
        keyword: Keyword to evaluate
        channel_id: Optional channel context (unused in MVP)
    
    Returns:
        {
            "keyword": str,
            "channel_id": str | None,
            "score": int (0-100),
            "reasoning": str
        }
    """
    from services.tiktok_service import check_saturation
    
    # Check TikTok saturation
    try:
        sat = check_saturation(keyword)
        status = sat.get("status", "unknown")
        video_count = sat.get("video_count_7d", 0)
    except Exception as e:
        # Fallback if saturation check fails
        status = "unknown"
        video_count = 0
    
    weights = _load_strategy().get("keyword_scoring_weights", {})
    search_volume_weight = weights.get("search_volume", 1.0)
    trend_velocity_weight = weights.get("trend_velocity", 1.0)
    competition_weight = weights.get("competition", 1.0)
    seasonality_weight = weights.get("seasonality", 1.0)

    # Saturation base score
    if status == "fresh":
        base = 50 + (30 * search_volume_weight)
    elif status == "medium":
        base = 50 + (5 * search_volume_weight)
    elif status == "saturated":
        base = 50 - (25 * search_volume_weight)
    else:
        base = 50  # unknown/error
    
    # Keyword trait adjustments
    word_count = len(keyword.split())
    
    if word_count >= 3:
        delta = 8 * trend_velocity_weight
        base += delta  # long_tail bonus
        trait_note = f"long-tail keyword (+{delta:.1f})"
    elif word_count == 1:
        delta = 10 * competition_weight
        base -= delta  # too broad penalty
        trait_note = f"single word (-{delta:.1f})"
    else:
        trait_note = "2-word keyword (neutral)"
    
    # Additional heuristics
    if "viral" in keyword.lower() or "trending" in keyword.lower():
        delta = 5 * search_volume_weight
        base -= delta  # overused terms penalty
        trait_note += f", contains viral/trending (-{delta:.1f})"
    
    if "tutorial" in keyword.lower() or "how to" in keyword.lower():
        delta = 5 * seasonality_weight
        base += delta  # educational bonus
        trait_note += f", educational (+{delta:.1f})"
    
    # Cap score
    score = round(min(100, max(0, base)))
    
    # Build reasoning
    reasoning = f"saturation={status} (base={base}), {trait_note}, words={word_count}"
    
    log.info(f"Evaluated keyword '{keyword}': score={score}, {reasoning}")
    
    return {
        "keyword": keyword,
        "channel_id": channel_id,
        "score": score,
        "reasoning": reasoning
    }
