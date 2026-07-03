"""Nurture keyword scoring — multi-signal heuristic + optional LLM batch (US-060)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from videoscout.core_engine.keyword_classifier import classify_keyword_type
from videoscout.core_engine.trend_evidence import velocity_percentile_from_evidence
from videoscout.core_engine.keyword_scorer import (
    BLEND_HEURISTIC_WEIGHT,
    BLEND_LLM_WEIGHT,
    COMPONENT_KEYS,
    get_scoring_weights,
    weighted_final_score,
)
from videoscout.core_engine.llm_config import create_llm_client, get_llm_config
from videoscout.core_engine.platform_signals import build_platform_signals
from videoscout.core_engine.scoring_rubric import (
    enforce_batch_relevance_tiebreak,
    enforce_batch_spread,
    resolve_scoring_rubric,
)
from videoscout.db.models import SettingsModel

logger = logging.getLogger(__name__)

NURTURE_MIN_SCORE = 0.25
NURTURE_BATCH_MAX_SIZE = 25
LLM_TEMPERATURE = 0.25
COMPONENT_MAX = 0.98

_GENERIC_TOKENS = frozenset({
    "viral", "trend", "trends", "video", "videos", "new", "funny", "best", "top",
    "clip", "clips", "challenge", "shorts", "tiktok", "youtube", "watch", "latest",
})
_GENERIC_PHRASES = frozenset({
    "viral trend", "new video", "funny video", "viral video", "trending now",
})


class NurtureScoringError(Exception):
    """Raised when nurture LLM scoring fails without fallback."""


def _clip_component(score: float) -> float:
    return round(max(0.0, min(COMPONENT_MAX, score)), 3)


def _normalize_title_text(title: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", (title or "").lower())
    return " ".join(t for t in cleaned.split() if len(t) > 1)


def _normalize_title(title: str) -> set[str]:
    return set(_normalize_title_text(title).split())


def _title_tokens_ordered(title: str) -> list[str]:
    return _normalize_title_text(title).split()


def _contiguous_match(
    kw_lower: str,
    ordered: list[str],
) -> tuple[bool, bool, float]:
    """Return (contiguous, early_position, keyword_title_coverage)."""
    kw_words = kw_lower.split()
    if not kw_words or not ordered:
        return False, False, 0.0

    for idx in range(len(ordered) - len(kw_words) + 1):
        if ordered[idx : idx + len(kw_words)] == kw_words:
            early = idx <= max(0, int(len(ordered) * 0.4))
            return True, early, len(kw_words) / len(ordered)

    norm_title = " ".join(ordered)
    if kw_lower in norm_title:
        early = norm_title.startswith(kw_lower)
        matched = len(set(kw_words) & set(ordered))
        return True, early, matched / len(ordered)

    matched = len(set(kw_words) & set(ordered))
    return False, False, matched / len(ordered) if ordered else 0.0


def compute_title_relevance(keyword: str, source_title: str) -> tuple[float, str]:
    kw_lower = keyword.lower().strip()
    kw_tokens = set(kw_lower.split())
    if not kw_tokens:
        return 0.5, "No keyword tokens to compare with source title."

    if kw_lower in _GENERIC_PHRASES:
        return 0.55, "Generic phrase only; relevance capped."

    title_tokens = _normalize_title(source_title)
    if not title_tokens:
        return 0.45, "Source title missing; neutral relevance."

    matched = kw_tokens & title_tokens
    overlap = len(matched) / len(kw_tokens)
    ordered = _title_tokens_ordered(source_title)
    contiguous, early, kw_coverage = _contiguous_match(kw_lower, ordered)

    generic_only = kw_tokens.issubset(_GENERIC_TOKENS)
    if generic_only:
        return 0.55, f"{len(matched)}/{len(kw_tokens)} keyword tokens in title — generic tail only."

    if overlap == 1.0 and contiguous and (kw_coverage >= 0.40 or early):
        score = 0.98
        label = "exact contiguous phrase representing the video's primary subject"
    elif overlap == 1.0 and contiguous:
        score = 0.96
        label = "high overlap; contiguous phrase with minor title context gap"
    elif overlap == 1.0:
        score = 0.95
        label = "high overlap with minor normalization"
    elif overlap >= 0.67:
        score = round(0.90 + (overlap - 0.67) * 0.12, 3)
        label = "strong overlap but partially incomplete"
    elif overlap >= 0.50:
        score = round(0.75 + (overlap - 0.50) * 0.60, 3)
        label = "moderate title overlap"
    else:
        score = round(0.35 + 0.55 * overlap, 3)
        label = "weak title overlap"

    return _clip_component(score), (
        f"{len(matched)}/{len(kw_tokens)} keyword tokens in title — {label}."
    )


def _title_proper_nouns(source_title: str) -> set[str]:
    nouns: set[str] = set()
    for match in re.finditer(r"\b([A-ZÀ-Ý][a-zA-ZÀ-ÿß]{1,})\b", source_title or ""):
        nouns.add(match.group(1).lower())
    for match in re.finditer(r"\b([A-ZÀ-Ý]{2,})\b", source_title or ""):
        nouns.add(match.group(1).lower())
    return nouns


def _has_proper_noun(keyword: str, source_title: str = "") -> bool:
    kw_tokens = {t.lower() for t in keyword.split()}
    if source_title and kw_tokens & _title_proper_nouns(source_title):
        return True
    for token in keyword.split():
        if token[:1].isupper() and token.lower() not in _GENERIC_TOKENS:
            return True
    return False


def _has_numeric_identifier(keyword: str) -> bool:
    return any(re.search(r"\d", token) for token in keyword.split())


def compute_specificity(keyword: str, source_title: str = "") -> tuple[float, str]:
    words = keyword.split()
    count = len(words)
    if count <= 1:
        base = 0.30
    elif count == 2:
        base = 0.44
    elif count == 3:
        base = 0.625
    else:
        base = 0.775

    score = base
    modifiers: list[str] = []
    if _has_proper_noun(keyword, source_title):
        score += 0.08
        modifiers.append("named entity")
    if _has_numeric_identifier(keyword):
        score += 0.07
        modifiers.append("distinctive numeric identifier")

    generic_hits = sum(1 for t in keyword.lower().split() if t in _GENERIC_TOKENS)
    score -= min(0.16, generic_hits * 0.08)

    if keyword.lower().strip() in _GENERIC_PHRASES:
        score = min(score, 0.50)

    reason = f"{count}-word phrase"
    if modifiers:
        reason += f" containing {' and '.join(modifiers)}"
    reason += "."
    return _clip_component(score), reason


def compute_saturation(tiktok_gate: Dict[str, Any]) -> tuple[float, str]:
    stats = tiktok_gate.get("tiktok_stats") or {}
    tier = stats.get("saturation_tier", "moderate")
    count = int(stats.get("video_count_7d", 0) or 0)
    avg_views = float(stats.get("avg_views", 0.0) or 0.0)

    if tiktok_gate.get("tiktok_unverified"):
        return _clip_component(0.5), "TikTok gate unverified — neutral saturation applied."

    if tier == "fresh":
        score = 0.95 - min(count, 10) * 0.012
        score = max(0.75, score)
    elif tier == "saturated":
        score = max(0.15, 0.40 - max(0, count - 30) * 0.005)
    else:
        score = 0.75 - min(max(count - 10, 0), 20) * 0.0125
        score = max(0.50, score)

    if count >= 3:
        if avg_views >= 100_000:
            penalty = min(0.06, 0.02 + (avg_views / 1_000_000) * 0.02)
            score -= penalty
        elif avg_views < 1_000 and tier == "fresh":
            score += 0.03

    reason = f"TikTok tier={tier} with {count} videos published in the last 7 days."
    return _clip_component(score), reason


def compute_video_performance(tiktok_stats: Dict[str, Any]) -> tuple[float, str]:
    avg_views = float(tiktok_stats.get("avg_views", 0.0) or 0.0)
    avg_likes = float(tiktok_stats.get("avg_likes", 0.0) or 0.0)
    avg_comments = float(tiktok_stats.get("avg_comments", 0.0) or 0.0)

    if avg_views <= 0:
        return 0.35, "No TikTok view data — low performance signal."

    if avg_views >= 1_000_000:
        view_score = 0.93
    elif avg_views >= 100_000:
        view_score = 0.825
    elif avg_views >= 10_000:
        view_score = 0.675
    elif avg_views >= 1_000:
        view_score = 0.525
    else:
        view_score = 0.375

    engagement = (avg_likes + avg_comments) / avg_views
    engagement_boost = min(0.10, engagement * 25.0)
    score = _clip_component(view_score + engagement_boost)
    return score, (
        f"Avg views {avg_views:,.0f}; likes/comments engagement adds {engagement_boost:.2f}."
    )


def compute_trend_signal(
    keyword: str,
    discovery_source: str,
    source_title: str,
    *,
    trend_evidence: Optional[Dict[str, Any]] = None,
) -> tuple[float, str]:
    percentile = velocity_percentile_from_evidence(trend_evidence)
    if percentile is not None:
        score = _clip_component(float(percentile))
        return score, (
            f"Velocity percentile {percentile:.0%} within region/category batch."
        )

    if discovery_source != "youtube_trend" or not source_title:
        return 0.5, "No strong trending-source signal."

    kw_lower = keyword.lower().strip()
    norm_title = _normalize_title_text(source_title)
    ordered = _title_tokens_ordered(source_title)

    if not ordered:
        return 0.5, "Source title empty; neutral trend signal."

    if kw_lower in _GENERIC_TOKENS or len(kw_lower.split()) == 1:
        generic = kw_lower in _GENERIC_TOKENS
        return (0.48 if generic else 0.52), (
            "Single generic token from title." if generic else "Single-word tail from title."
        )

    kw_words = kw_lower.split()
    position: Optional[int] = None
    for idx in range(len(ordered) - len(kw_words) + 1):
        if ordered[idx : idx + len(kw_words)] == kw_words:
            position = idx
            break

    if position is not None:
        title_len = len(ordered)
        coverage = len(kw_words) / title_len
        frac = position / max(title_len, 1)
        is_primary = (
            coverage >= 0.50
            or frac < 0.40
            or (title_len <= 4 and coverage >= 0.40)
        )
        if is_primary:
            return _clip_component(0.84), (
                "Primary hook appearing prominently in the trending title."
            )
        if frac < 0.70:
            return _clip_component(0.72), (
                "Secondary hook — contiguous phrase in trending title."
            )
        return _clip_component(0.60), "Supporting phrase from trending title."

    if kw_lower in norm_title:
        return _clip_component(0.58), "Partial phrase match in trending title."

    overlap = len(set(kw_words) & set(ordered)) / len(kw_words)
    if overlap >= 0.5:
        return _clip_component(0.55), "Partial token overlap with trending title."

    return 0.50, "Weak trending-source signal."


def compute_confidence(
    *,
    source_title: str,
    tiktok_gate: Dict[str, Any],
    discovery_source: str,
) -> float:
    score = 0.0
    if source_title:
        score += 0.20
    if not tiktok_gate.get("tiktok_unverified"):
        score += 0.25
    stats = tiktok_gate.get("tiktok_stats") or {}
    count = int(stats.get("video_count_7d", 0) or 0)
    avg_views = float(stats.get("avg_views", 0.0) or 0.0)
    if count >= 3:
        score += 0.15
    if avg_views > 0:
        score += 0.10
    if discovery_source == "youtube_trend" and count > 0:
        score += 0.10
    return round(min(1.0, score), 2)


def _token_jaccard(a: str, b: str) -> float:
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _levenshtein_ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    rows = len(a) + 1
    cols = len(b) + 1
    dist = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        dist[i][0] = i
    for j in range(cols):
        dist[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dist[i][j] = min(dist[i - 1][j] + 1, dist[i][j - 1] + 1, dist[i - 1][j - 1] + cost)
    max_len = max(len(a), len(b))
    return 1.0 - dist[rows - 1][cols - 1] / max_len


def detect_batch_risk_flags(keywords: List[str]) -> Dict[str, List[str]]:
    flags: Dict[str, List[str]] = {kw: [] for kw in keywords}
    for i, a in enumerate(keywords):
        for b in keywords[i + 1 :]:
            jaccard = _token_jaccard(a, b)
            lev = _levenshtein_ratio(a.lower(), b.lower())
            if jaccard > 0.80 or lev > 0.90:
                flags[a].append("duplicate_of_batch_peer")
                flags[b].append("duplicate_of_batch_peer")
    return flags


def _collect_risk_flags(
    keyword: str,
    *,
    source_title: str,
    tiktok_stats: Dict[str, Any],
    batch_flags: Optional[List[str]] = None,
) -> List[str]:
    flags: List[str] = list(batch_flags or [])
    kw_lower = keyword.lower().strip()
    if kw_lower in _GENERIC_PHRASES or set(kw_lower.split()).issubset(_GENERIC_TOKENS):
        flags.append("generic_phrase")
    tier = tiktok_stats.get("saturation_tier", "moderate")
    count = int(tiktok_stats.get("video_count_7d", 0) or 0)
    if tier == "saturated" or count > 30:
        flags.append("saturated")
    kw_tokens = set(kw_lower.split())
    title_tokens = _normalize_title(source_title)
    if kw_tokens and title_tokens:
        overlap = len(kw_tokens & title_tokens) / len(kw_tokens)
        if overlap < 0.5:
            flags.append("weak_title_overlap")
    avg_views = float(tiktok_stats.get("avg_views", 0.0) or 0.0)
    if 0 < avg_views < 1_000:
        flags.append("low_views")
    return sorted(set(flags))


def compute_nurture_components(
    candidate: Dict[str, Any],
    *,
    tiktok_gate: Dict[str, Any],
    batch_peer_flags: Optional[List[str]] = None,
) -> tuple[Dict[str, float], Dict[str, str]]:
    trend_signals = candidate.get("trend_signals") or {}
    source_title = str(trend_signals.get("source_title") or "")
    keyword = candidate["keyword"]
    tiktok_stats = tiktok_gate.get("tiktok_stats") or {}

    relevance, rel_reason = compute_title_relevance(keyword, source_title)
    specificity, spec_reason = compute_specificity(keyword, source_title)
    if batch_peer_flags and "duplicate_of_batch_peer" in batch_peer_flags:
        specificity = _clip_component(specificity - 0.05)
        spec_reason = f"{spec_reason} Duplicate of batch peer (−0.05)."
    saturation, sat_reason = compute_saturation(tiktok_gate)
    trend, trend_reason = compute_trend_signal(
        keyword,
        candidate.get("discovery_source", "youtube_trend"),
        source_title,
        trend_evidence=candidate.get("trend_evidence"),
    )
    video_performance, perf_reason = compute_video_performance(tiktok_stats)

    components = {
        "relevance": relevance,
        "specificity": specificity,
        "saturation": saturation,
        "trend": trend,
        "video_performance": video_performance,
    }
    reasons = {
        "relevance": rel_reason,
        "specificity": spec_reason,
        "saturation": sat_reason,
        "trend": trend_reason,
        "video_performance": perf_reason,
    }
    return components, reasons


def _heuristic_rationale(
    keyword: str,
    components: Dict[str, float],
    final_score: float,
) -> str:
    top = sorted(components.items(), key=lambda item: item[1], reverse=True)[:2]
    drivers = ", ".join(f"{name} {value:.0%}" for name, value in top)
    return (
        f"Nurture heuristic score {final_score:.0%} for '{keyword}' "
        f"driven mainly by {drivers}."
    )


def score_nurture_heuristic(
    candidate: Dict[str, Any],
    *,
    tiktok_gate: Dict[str, Any],
    weights: Dict[str, float],
    keyword_type_filter: str = "both",
    batch_peer_flags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    keyword = candidate["keyword"]
    if not tiktok_gate.get("surface", True):
        return None

    components, reasons = compute_nurture_components(
        candidate,
        tiktok_gate=tiktok_gate,
        batch_peer_flags=batch_peer_flags,
    )
    final_score = weighted_final_score(components, weights)

    tiktok_stats = tiktok_gate.get("tiktok_stats") or {}
    saturation_tier = tiktok_stats.get("saturation_tier", "moderate")
    discovery_source = candidate.get("discovery_source", "youtube_trend")
    trend_signals = candidate.get("trend_signals") or {}
    source_title = str(trend_signals.get("source_title") or "")

    keyword_type = classify_keyword_type(
        keyword,
        trend_source=discovery_source,
        saturation_tier=saturation_tier,
        agent_score=final_score,
    )
    if keyword_type_filter in ("nurture", "beta") and keyword_type != keyword_type_filter:
        return None
    if keyword_type != "nurture":
        return None
    if final_score < NURTURE_MIN_SCORE:
        return None

    rationale = _heuristic_rationale(keyword, components, final_score)
    tier_to_status = {"fresh": "low", "moderate": "moderate", "saturated": "saturated"}
    risk_flags = _collect_risk_flags(
        keyword,
        source_title=source_title,
        tiktok_stats=tiktok_stats,
        batch_flags=batch_peer_flags,
    )

    return {
        "keyword": keyword,
        "keyword_type": keyword_type,
        "discovery_source": discovery_source,
        "trend_signals": candidate.get("trend_signals"),
        "trend_evidence": candidate.get("trend_evidence"),
        "gate_profile": "light",
        "final_score": final_score,
        "component_scores": components,
        "platform_signals": build_platform_signals(
            candidate=candidate,
            tiktok_gate=tiktok_gate,
            component_scores=components,
            component_reasons=reasons,
            scored_with="heuristic_nurture",
            rationale=rationale,
            confidence=compute_confidence(
                source_title=source_title,
                tiktok_gate=tiktok_gate,
                discovery_source=discovery_source,
            ),
            risk_flags=risk_flags,
        ),
        "tiktok_status": tier_to_status.get(saturation_tier, "moderate"),
        "tiktok_count": tiktok_stats.get("video_count_7d", 0),
        "tiktok_stats": tiktok_stats,
        "tiktok_unverified": bool(tiktok_gate.get("tiktok_unverified", False)),
    }


def _build_nurture_llm_prompt(
    batch_rows: List[Dict[str, Any]],
    weights: Dict[str, float],
    settings: Optional[SettingsModel] = None,
) -> str:
    payload = {
        "candidates": batch_rows,
        "weights": weights,
        "scoring_mode": "relative_batch",
        "rubric": resolve_scoring_rubric("nurture", settings),
    }
    return f"""Score ALL nurture keyword candidates.

Return JSON only:
{{
  "scores": [
    {{
      "keyword": "exact keyword from input",
      "component_scores": {{
        "relevance": 0.0,
        "specificity": 0.0,
        "saturation": 0.0,
        "trend": 0.0,
        "video_performance": 0.0
      }},
      "component_reasons": {{
        "relevance": "short reason",
        "specificity": "short reason",
        "saturation": "short reason",
        "trend": "short reason",
        "video_performance": "short reason"
      }},
      "rationale": "1-2 sentences",
      "confidence": 0.0,
      "risk_flags": []
    }}
  ]
}}

Return one entry per input keyword. Do not compute final_score.
If relevance differs by less than 0.03 within the batch, separate candidates using
trend, specificity, and saturation — do not assign identical relevance scores.

Batch payload:
{json.dumps(payload, ensure_ascii=False)}
"""


def _call_llm_json(*, llm: OpenAI, model: str, prompt: str) -> Dict[str, Any]:
    response = llm.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=LLM_TEMPERATURE,
    )
    content = response.choices[0].message.content
    if not content:
        raise NurtureScoringError("LLM returned empty content")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise NurtureScoringError("LLM response was not a JSON object")
    return parsed


def _finalize_nurture_llm_row(
    item: Dict[str, Any],
    llm_row: Dict[str, Any],
    *,
    weights: Dict[str, float],
    keyword_type_filter: str,
    batch_peer_flags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    candidate = item["candidate"]
    tiktok_gate = item["tiktok_gate"]
    keyword = candidate["keyword"]

    components: Dict[str, float] = {}
    reasons: Dict[str, str] = {}
    heuristic_components, heuristic_reasons = compute_nurture_components(
        candidate,
        tiktok_gate=tiktok_gate,
        batch_peer_flags=batch_peer_flags,
    )

    raw_components = llm_row.get("component_scores") or {}
    raw_reasons = llm_row.get("component_reasons") or {}
    for key in COMPONENT_KEYS:
        try:
            components[key] = _clip_component(float(raw_components.get(key, 0.0)))
        except (TypeError, ValueError):
            components[key] = heuristic_components[key]
        reasons[key] = str(raw_reasons.get(key) or heuristic_reasons[key])

    heuristic_final = weighted_final_score(heuristic_components, weights)
    llm_final = weighted_final_score(components, weights)
    final_score = round(
        BLEND_LLM_WEIGHT * llm_final + BLEND_HEURISTIC_WEIGHT * heuristic_final,
        3,
    )
    blend_meta = {
        "llm_weight": BLEND_LLM_WEIGHT,
        "heuristic_weight": BLEND_HEURISTIC_WEIGHT,
        "llm_final": llm_final,
        "heuristic_final": heuristic_final,
    }

    tiktok_stats = tiktok_gate.get("tiktok_stats") or {}
    saturation_tier = tiktok_stats.get("saturation_tier", "moderate")
    discovery_source = candidate.get("discovery_source", "youtube_trend")
    trend_signals = candidate.get("trend_signals") or {}
    source_title = str(trend_signals.get("source_title") or "")

    keyword_type = classify_keyword_type(
        keyword,
        trend_source=discovery_source,
        saturation_tier=saturation_tier,
        agent_score=final_score,
    )
    if keyword_type_filter in ("nurture", "beta") and keyword_type != keyword_type_filter:
        return None
    if keyword_type != "nurture":
        return None
    if final_score < NURTURE_MIN_SCORE:
        return None
    if not tiktok_gate.get("surface", True):
        return None

    tier_to_status = {"fresh": "low", "moderate": "moderate", "saturated": "saturated"}
    rationale = str(llm_row.get("rationale") or _heuristic_rationale(keyword, components, final_score))
    llm_flags = list(llm_row.get("risk_flags") or [])
    heuristic_flags = _collect_risk_flags(
        keyword,
        source_title=source_title,
        tiktok_stats=tiktok_stats,
        batch_flags=batch_peer_flags,
    )
    risk_flags = sorted(set(llm_flags + heuristic_flags))

    return {
        "keyword": keyword,
        "keyword_type": keyword_type,
        "discovery_source": discovery_source,
        "trend_signals": candidate.get("trend_signals"),
        "trend_evidence": candidate.get("trend_evidence"),
        "gate_profile": "light",
        "final_score": final_score,
        "component_scores": components,
        "platform_signals": build_platform_signals(
            candidate=candidate,
            tiktok_gate=tiktok_gate,
            component_scores=components,
            component_reasons=reasons,
            scored_with="llm_nurture_batch",
            rationale=rationale,
            confidence=float(llm_row.get("confidence") or compute_confidence(
                source_title=source_title,
                tiktok_gate=tiktok_gate,
                discovery_source=discovery_source,
            )),
            risk_flags=risk_flags,
            blend=blend_meta,
        ),
        "tiktok_status": tier_to_status.get(saturation_tier, "moderate"),
        "tiktok_count": tiktok_stats.get("video_count_7d", 0),
        "tiktok_stats": tiktok_stats,
        "tiktok_unverified": bool(tiktok_gate.get("tiktok_unverified", False)),
    }


async def score_nurture_candidates_batch(
    items: List[Dict[str, Any]],
    *,
    db: Session,
    settings: Optional[SettingsModel] = None,
    keyword_type_filter: str = "both",
    llm_client: Optional[OpenAI] = None,
) -> List[Dict[str, Any]]:
    """Score nurture candidates via LLM batch; heuristic fallback per item on failure."""
    if not items:
        return []

    if settings is None:
        settings = db.query(SettingsModel).first()
    weights = get_scoring_weights(settings)

    llm_config = get_llm_config(db)
    llm = llm_client or create_llm_client(db)
    results: List[Dict[str, Any]] = []

    for start in range(0, len(items), NURTURE_BATCH_MAX_SIZE):
        chunk = items[start : start + NURTURE_BATCH_MAX_SIZE]
        batch_rows: List[Dict[str, Any]] = []
        lookup: Dict[str, Dict[str, Any]] = {}
        keywords = [item["candidate"]["keyword"] for item in chunk]
        batch_risk = detect_batch_risk_flags(keywords)

        for item in chunk:
            candidate = item["candidate"]
            tiktok_gate = item["tiktok_gate"]
            keyword = candidate["keyword"]
            peer_flags = batch_risk.get(keyword, [])
            components, reasons = compute_nurture_components(
                candidate,
                tiktok_gate=tiktok_gate,
                batch_peer_flags=peer_flags or None,
            )
            trend_signals = candidate.get("trend_signals") or {}
            batch_rows.append(
                {
                    "keyword": keyword,
                    "discovery_source": candidate.get("discovery_source"),
                    "source_title": trend_signals.get("source_title"),
                    "tiktok_stats": tiktok_gate.get("tiktok_stats") or {},
                    "heuristic_components": components,
                    "heuristic_reasons": reasons,
                    "risk_flags": peer_flags,
                }
            )
            lookup[keyword.lower()] = item

        llm_scores: List[Dict[str, Any]] = []
        try:
            llm_response = _call_llm_json(
                llm=llm,
                model=llm_config["model"],
                prompt=_build_nurture_llm_prompt(batch_rows, weights, settings),
            )
            raw_scores = llm_response.get("scores") or []
            if isinstance(raw_scores, list):
                llm_scores = [row for row in raw_scores if isinstance(row, dict)]
        except Exception as exc:
            logger.warning("Nurture LLM batch failed, using heuristic fallback: %s", exc)

        if not llm_scores:
            for item in chunk:
                kw = item["candidate"]["keyword"]
                scored = score_nurture_heuristic(
                    item["candidate"],
                    tiktok_gate=item["tiktok_gate"],
                    weights=weights,
                    keyword_type_filter=keyword_type_filter,
                    batch_peer_flags=batch_risk.get(kw) or None,
                )
                if scored:
                    results.append(scored)
            continue

        seen_keywords: set[str] = set()
        chunk_results: List[Dict[str, Any]] = []
        for row in llm_scores:
            keyword = str(row.get("keyword") or "").strip()
            item = lookup.get(keyword.lower())
            if not item:
                continue
            seen_keywords.add(keyword.lower())
            finalized = _finalize_nurture_llm_row(
                item,
                row,
                weights=weights,
                keyword_type_filter=keyword_type_filter,
                batch_peer_flags=batch_risk.get(keyword) or None,
            )
            if finalized:
                chunk_results.append(finalized)

        chunk_results = enforce_batch_relevance_tiebreak(chunk_results)
        chunk_results = enforce_batch_spread(chunk_results)
        results.extend(chunk_results)

        for item in chunk:
            keyword = item["candidate"]["keyword"].lower()
            if keyword in seen_keywords:
                continue
            scored = score_nurture_heuristic(
                item["candidate"],
                tiktok_gate=item["tiktok_gate"],
                weights=weights,
                keyword_type_filter=keyword_type_filter,
                batch_peer_flags=batch_risk.get(item["candidate"]["keyword"]) or None,
            )
            if scored:
                results.append(scored)

    return results
