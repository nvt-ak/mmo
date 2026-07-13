"""Runtime scoring rubrics loaded from markdown (US-061)."""
from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

from videoscout.db.models import SettingsModel

_RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"

BATCH_MIN_STD = 0.08
BATCH_STRETCH_MIN = 0.45
BATCH_STRETCH_MAX = 0.92
BATCH_MIN_TOP_BOTTOM_GAP = 0.15
RELEVANCE_TIEBREAK_EPS = 0.03

RUBRIC_KEYS = {
    "nurture": "nurture_v1",
    "beta": "beta_v1",
}


def load_rubric(name: str) -> str:
    path = _RUBRICS_DIR / f"{name}.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def default_rubric_text(track: str) -> str:
    file_key = RUBRIC_KEYS.get(track, track)
    return load_rubric(file_key)


def resolve_scoring_rubric(
    track: str,
    settings: Optional[SettingsModel] = None,
) -> str:
    """Effective rubric: settings override when set, else bundled markdown."""
    default = default_rubric_text(track)
    if not settings:
        return default

    attr = f"{track}_scoring_rubric" if track in RUBRIC_KEYS else None
    if not attr:
        return default

    override = getattr(settings, attr, None)
    if override and str(override).strip():
        return str(override).strip()
    return default


def normalize_rubric_override(custom: Optional[str], default: str) -> Optional[str]:
    """Persist None when blank or identical to ship default."""
    stripped = (custom or "").strip()
    if not stripped:
        return None
    if stripped == default.strip():
        return None
    return stripped


def build_rubric_field(
    track: str,
    settings: Optional[SettingsModel],
) -> Dict[str, Any]:
    default = default_rubric_text(track)
    override = None
    if settings:
        override = getattr(settings, f"{track}_scoring_rubric", None)
    custom = (override or "").strip()
    is_custom = bool(custom)
    return {
        "text": custom or default,
        "custom_text": custom or None,
        "default_text": default,
        "is_custom": is_custom,
    }


def batch_score_std(results: List[Dict[str, Any]]) -> float:
    if len(results) < 2:
        return 0.0
    scores = [float(r["final_score"]) for r in results]
    return statistics.pstdev(scores)


def batch_relevance_std(results: List[Dict[str, Any]]) -> float:
    if len(results) < 2:
        return 0.0
    relevances = [
        float((r.get("component_scores") or {}).get("relevance", 0.0))
        for r in results
    ]
    return statistics.pstdev(relevances)


def _heuristic_rank_score(rank: int, total: int) -> float:
    if total <= 1:
        return round((BATCH_STRETCH_MIN + BATCH_STRETCH_MAX) / 2, 3)
    frac = rank / (total - 1)
    return round(BATCH_STRETCH_MIN + frac * (BATCH_STRETCH_MAX - BATCH_STRETCH_MIN), 3)


def _tiebreak_rank(row: Dict[str, Any]) -> float:
    components = row.get("component_scores") or {}
    return (
        float(components.get("trend", 0.0)) * 0.40
        + float(components.get("specificity", 0.0)) * 0.35
        + float(components.get("saturation", 0.0)) * 0.25
    )


def enforce_batch_relevance_tiebreak(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Spread near-identical relevance scores using trend/specificity/saturation."""
    if len(results) < 2:
        return results

    updated: List[Dict[str, Any]] = []
    for row in results:
        copy = dict(row)
        copy["component_scores"] = dict(row.get("component_scores") or {})
        updated.append(copy)

    order = sorted(range(len(updated)), key=lambda i: _tiebreak_rank(updated[i]), reverse=True)
    relevances = [
        float(updated[i]["component_scores"].get("relevance", 0.0)) for i in order
    ]

    if max(relevances) - min(relevances) < RELEVANCE_TIEBREAK_EPS:
        base = max(relevances)
        for rank, idx in enumerate(order):
            updated[idx]["component_scores"]["relevance"] = round(
                max(0.0, base - rank * 0.01), 3
            )
    else:
        seen: Dict[float, int] = {}
        for idx in order:
            rel = round(float(updated[idx]["component_scores"].get("relevance", 0.0)), 3)
            dup = seen.get(rel, 0)
            if dup:
                updated[idx]["component_scores"]["relevance"] = round(
                    max(0.0, rel - dup * 0.01), 3
                )
            seen[rel] = seen.get(rel, 0) + 1

    return updated


def enforce_batch_spread(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rescale flat batches when final scores AND relevance both look lazy-clustered."""
    if len(results) < 2:
        return results
    if batch_score_std(results) >= BATCH_MIN_STD:
        return results
    if batch_relevance_std(results) >= RELEVANCE_TIEBREAK_EPS:
        return results

    ranked: List[tuple[Dict[str, Any], float]] = []
    for row in results:
        blend = (row.get("platform_signals") or {}).get("agent", {}).get("blend") or {}
        heuristic_final = float(blend.get("heuristic_final", row["final_score"]))
        ranked.append((row, heuristic_final))

    ranked.sort(key=lambda item: item[1])
    total = len(ranked)
    updated: List[Dict[str, Any]] = []
    for rank, (row, _) in enumerate(ranked):
        stretched = dict(row)
        new_score = _heuristic_rank_score(rank, total)
        stretched["final_score"] = new_score
        signals = dict(stretched.get("platform_signals") or {})
        agent = dict(signals.get("agent") or {})
        blend = dict(agent.get("blend") or {})
        blend["spread_enforced"] = True
        blend["spread_std_before"] = round(batch_score_std(results), 4)
        blend["pre_stretch_final"] = row["final_score"]
        agent["blend"] = blend
        signals["agent"] = agent
        stretched["platform_signals"] = signals
        updated.append(stretched)

    return updated
