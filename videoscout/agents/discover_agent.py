"""
Discover Agent — finds YouTube channels matching strategy keywords.
Wraps existing YouTube services + strategy-driven keyword expansion.
"""
import json
from pathlib import Path
from agents.skills.youtube_skills import (
    discover_channels,
    get_existing_channels,
    get_top_channels_for_evaluation,
)
from utils.logger import get_logger

log = get_logger("discover")

MEMORY_DIR = Path(__file__).parent / "memory"


def _load_strategy() -> dict:
    path = MEMORY_DIR / "strategy.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"keywords": [], "filters": {}}


def run() -> list[dict]:
    """
    Discover candidate channels based on current strategy.
    Returns list of new channels not already tracked.
    """
    strategy = _load_strategy()
    keywords = strategy.get("keywords", [])
    filters = strategy.get("filters", {})

    if not keywords:
        log.warning("No keywords in strategy — nothing to discover")
        return []

    existing = get_existing_channels()
    all_candidates = []

    for kw in keywords:
        log.info(f"Discovering channels for: '{kw}'")
        channels = discover_channels(kw, filters)
        for ch in channels:
            if ch["id"] not in existing and ch["id"] not in {c["id"] for c in all_candidates}:
                all_candidates.append(ch)
                existing.add(ch["id"])
        log.info(f"  → {len(channels)} found, {len(all_candidates)} new total")

    # sort by score
    all_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    log.info(f"Discover complete: {len(all_candidates)} new candidate channels")
    return all_candidates
