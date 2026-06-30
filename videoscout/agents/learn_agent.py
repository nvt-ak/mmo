"""
Learn Agent — analyzes outcomes and suggests strategy improvements.
"""
import json
from datetime import datetime
from pathlib import Path
from agents.skills.youtube_skills import get_outcomes
from agents.skills.llm_skills import suggest_keywords, summarize_outcomes
from utils.logger import get_logger

log = get_logger("learn")

MEMORY_DIR = Path(__file__).parent / "memory"


def _load_strategy() -> dict:
    path = MEMORY_DIR / "strategy.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_strategy(strategy: dict):
    path = MEMORY_DIR / "strategy.json"
    strategy["last_updated"] = datetime.now().isoformat()
    path.write_text(json.dumps(strategy, indent=2))


def _load_learnings() -> dict:
    path = MEMORY_DIR / "learnings.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"patterns": [], "keyword_suggestions": []}


def _save_learnings(learnings: dict):
    path = MEMORY_DIR / "learnings.json"
    learnings["last_updated"] = datetime.now().isoformat()
    (MEMORY_DIR / "learnings.json").write_text(json.dumps(learnings, indent=2))


def analyze_outcomes() -> dict:
    """
    Analyze historical channel outcomes to identify patterns.
    Returns: {patterns: str, successful_channels: list, failed_channels: list}
    """
    outcomes = get_outcomes()
    if not outcomes:
        log.info("No outcomes to analyze yet")
        return {"patterns": "No data yet", "successful_channels": [], "failed_channels": []}

    successful = [o for o in outcomes if o.get("outcome") == "follow" and o.get("videos_found", 0) > 5]
    failed = [o for o in outcomes if o.get("outcome") == "skip" or o.get("videos_found", 0) == 0]

    log.info(f"Analyzing {len(outcomes)} outcomes: {len(successful)} success, {len(failed)} failed")

    # LLM pattern analysis
    patterns = summarize_outcomes(outcomes[:30])

    return {
        "patterns": patterns,
        "successful_channels": successful,
        "failed_channels": failed,
    }


def suggest_strategy_updates(analysis: dict | None = None) -> dict:
    """
    Suggest updates to strategy based on learnings.
    Returns: {keyword_suggestions: list, filter_adjustments: dict, reasoning: str}
    """
    strategy = _load_strategy()
    if analysis is None:
        analysis = analyze_outcomes()

    if not analysis["successful_channels"]:
        log.info("Not enough successful channels to suggest updates")
        return {"keyword_suggestions": [], "filter_adjustments": {}, "reasoning": "Need more data"}

    # LLM keyword suggestions
    current_kw = strategy.get("keywords", [])
    new_keywords = suggest_keywords(analysis["successful_channels"], current_kw)

    # simple filter adjustment logic
    successful = analysis["successful_channels"]
    avg_subs = sum(ch.get("subscribers", 0) for ch in successful) / len(successful) if successful else 0
    avg_videos = sum(ch.get("videos_found", 0) for ch in successful) / len(successful) if successful else 0

    filter_adjustments = {}
    current_max = strategy.get("filters", {}).get("max_subs", 50000)

    if avg_subs < current_max * 0.3:
        filter_adjustments["max_subs"] = int(current_max * 0.7)
        reasoning = f"Successful channels have avg {avg_subs:.0f} subs — reducing max_subs to {filter_adjustments['max_subs']}"
    else:
        reasoning = "No filter adjustments needed"

    log.info(f"Suggestions: {len(new_keywords)} new keywords, {reasoning}")

    return {
        "keyword_suggestions": new_keywords,
        "filter_adjustments": filter_adjustments,
        "reasoning": reasoning,
    }


def run() -> dict:
    """
    Main learn agent entry point.
    Returns suggestions for human approval.
    """
    log.info("Learn agent starting")

    analysis = analyze_outcomes()
    suggestions = suggest_strategy_updates(analysis)  # reuse, avoid double LLM call

    # save to learnings memory
    learnings = _load_learnings()
    learnings["patterns"].append({
        "timestamp": datetime.now().isoformat(),
        "summary": analysis["patterns"],
        "successful_count": len(analysis["successful_channels"]),
        "failed_count": len(analysis["failed_channels"]),
    })
    learnings["keyword_suggestions"] = suggestions["keyword_suggestions"]
    _save_learnings(learnings)

    log.info("Learn agent complete — suggestions ready for approval")

    return {
        "analysis": analysis,
        "suggestions": suggestions,
        "status": "pending_approval",
    }


def apply_approved_suggestions(approved: dict):
    """
    Apply human-approved strategy updates.
    """
    strategy = _load_strategy()

    if "keywords" in approved:
        new_kw = approved["keywords"]
        existing = set(strategy.get("keywords", []))
        strategy["keywords"] = list(existing | set(new_kw))
        log.info(f"Added keywords: {new_kw}")

    if "filters" in approved:
        strategy["filters"].update(approved["filters"])
        log.info(f"Updated filters: {approved['filters']}")

    if "update_history" not in strategy:
        strategy["update_history"] = []

    strategy["update_history"].append({
        "timestamp": datetime.now().isoformat(),
        "changes": approved,
    })

    _save_strategy(strategy)
    log.info("Strategy updated and saved")
