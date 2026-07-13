"""Cross-track reroute when post-score classification differs from scorer track."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REROUTE_MARKER = "_scoring_reroute"
MAX_REROUTE_DEPTH = 1


def make_reroute(
    *,
    to_track: str,
    from_track: str,
    keyword: str,
    item: Dict[str, Any],
    final_score: float,
) -> Dict[str, Any]:
    return {
        REROUTE_MARKER: True,
        "to_track": to_track,
        "from_track": from_track,
        "keyword": keyword,
        "item": item,
        "final_score": final_score,
    }


def is_reroute(result: Any) -> bool:
    return isinstance(result, dict) and result.get(REROUTE_MARKER) is True


def should_accept_reroute(to_track: str, keyword_type_filter: str) -> bool:
    if to_track == "beta":
        return keyword_type_filter in ("both", "beta")
    if to_track == "nurture":
        return keyword_type_filter in ("both", "nurture")
    return False


def log_reroute(reroute: Dict[str, Any]) -> None:
    logger.info(
        "Reclassify reroute %s→%s: keyword=%r score=%.3f",
        reroute["from_track"],
        reroute["to_track"],
        reroute["keyword"],
        float(reroute.get("final_score") or 0.0),
    )


def split_finalize_results(
    finalized: List[Any],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    scored: List[Dict[str, Any]] = []
    reroutes: List[Dict[str, Any]] = []
    for row in finalized:
        if row is None:
            continue
        if is_reroute(row):
            log_reroute(row)
            reroutes.append(row)
        else:
            scored.append(row)
    return scored, reroutes


def reroute_items(reroutes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [reroute["item"] for reroute in reroutes]
