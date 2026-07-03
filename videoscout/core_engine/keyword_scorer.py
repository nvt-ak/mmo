"""Beta keyword LLM scoring with rules guardrails (ADR 0012 / US-055 / US-057)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from sqlalchemy.orm import Session

from videoscout.core_engine.keyword_classifier import (
    BETA_MIN_SCORE,
    classify_keyword_type,
)
from videoscout.core_engine.keyword_context import KeywordContextBuilder
from videoscout.core_engine.platform_signals import build_platform_signals
from videoscout.core_engine.scoring_rubric import resolve_scoring_rubric
from videoscout.core_engine.llm_config import create_llm_client, get_llm_config
from videoscout.db.models import PerformanceReportModel, SettingsModel, SuggestionModel

logger = logging.getLogger(__name__)

BETA_MIN_WORDS = 3
SATURATION_CAP = 0.3
BLEND_LLM_WEIGHT = 0.6
BLEND_HEURISTIC_WEIGHT = 0.4
CALIBRATION_REPORT_THRESHOLD = 20
LLM_TEMPERATURE = 0.25
BATCH_MAX_SIZE = 10

COMPONENT_KEYS = (
    "relevance",
    "specificity",
    "saturation",
    "trend",
    "video_performance",
)


class BetaScoringError(Exception):
    """Raised when beta LLM scoring fails."""


def _default_weights() -> Dict[str, float]:
    return {
        "relevance": 0.30,
        "specificity": 0.25,
        "saturation": 0.25,
        "trend": 0.10,
        "video_performance": 0.10,
    }


def get_scoring_weights(settings: Optional[SettingsModel]) -> Dict[str, float]:
    if not settings:
        return _default_weights()
    return {
        "relevance": settings.weight_relevance,
        "specificity": settings.weight_specificity,
        "saturation": settings.weight_saturation,
        "trend": settings.weight_trend,
        "video_performance": settings.weight_video_performance,
    }


def _heuristic_components(keyword: str, tiktok_gate: Dict[str, Any]) -> Dict[str, float]:
    specificity = min(1.0, len(keyword.split()) / 5.0)
    saturation_score = float(tiktok_gate.get("score", 0.5))
    return {
        "relevance": 0.5,
        "specificity": round(specificity, 3),
        "saturation": round(saturation_score, 3),
        "trend": 0.7,
        "video_performance": 0.5,
    }


def heuristic_final_score(keyword: str, tiktok_gate: Dict[str, Any]) -> float:
    components = _heuristic_components(keyword, tiktok_gate)
    return round(0.5 * components["specificity"] + 0.5 * components["saturation"], 3)


def weighted_final_score(
    components: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    total = sum(
        float(components.get(key, 0.0)) * float(weights.get(key, 0.0))
        for key in COMPONENT_KEYS
    )
    return round(total, 3)


def clamp_components(components: Dict[str, Any]) -> Dict[str, float]:
    clamped: Dict[str, float] = {}
    for key in COMPONENT_KEYS:
        raw = float(components.get(key, 0.0))
        clamped[key] = round(max(0.0, min(1.0, raw)), 3)
    return clamped


def count_linked_beta_reports(db: Session) -> int:
    return (
        db.query(PerformanceReportModel)
        .join(
            SuggestionModel,
            PerformanceReportModel.suggestion_id == SuggestionModel.id,
        )
        .filter(SuggestionModel.keyword_type == "beta")
        .count()
    )


def _apply_saturation_cap(
    components: Dict[str, float],
    saturation_tier: str,
) -> Dict[str, float]:
    if saturation_tier == "saturated":
        capped = dict(components)
        capped["saturation"] = min(capped.get("saturation", 0.0), SATURATION_CAP)
        return capped
    return components


def passes_beta_pre_rules(keyword: str, tiktok_gate: Dict[str, Any]) -> bool:
    if not tiktok_gate.get("surface", True):
        return False
    if len(keyword.split()) < BETA_MIN_WORDS:
        return False
    return True


def _build_batch_prompt(
    batch_items: List[Dict[str, Any]],
    weights: Dict[str, float],
    settings: Optional[SettingsModel] = None,
) -> str:
    payload = {
        "candidates": batch_items,
        "weights": weights,
        "scoring_mode": "relative_batch",
        "rubric": resolve_scoring_rubric("beta", settings),
    }
    return f"""Score ALL beta keyword candidates in this batch.

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
      "rationale": "1-2 sentences",
      "risk_flags": [],
      "confidence": 0.0
    }}
  ]
}}

Return one entry per input keyword. Do not compute final_score.

Batch payload:
{json.dumps(payload, ensure_ascii=False)}
"""


def _is_timeout_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "timeout" in msg or "timed out" in msg


def _call_llm_json(*, llm: OpenAI, model: str, prompt: str) -> Dict[str, Any]:
    response = llm.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=LLM_TEMPERATURE,
    )
    content = response.choices[0].message.content
    if not content:
        raise BetaScoringError("LLM returned empty content")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise BetaScoringError("LLM response was not a JSON object")
    return parsed


def _finalize_beta_score(
    candidate: Dict[str, Any],
    *,
    tiktok_gate: Dict[str, Any],
    llm_payload: Dict[str, Any],
    weights: Dict[str, float],
    min_score: float,
    keyword_type_filter: str,
    linked_reports: int,
) -> Optional[Dict[str, Any]]:
    keyword = candidate["keyword"]
    discovery_source = candidate.get("discovery_source", "youtube_trend")
    tiktok_stats = tiktok_gate.get("tiktok_stats") or {}
    saturation_tier = tiktok_stats.get("saturation_tier", "moderate")
    heuristic_final = heuristic_final_score(keyword, tiktok_gate)

    llm_components = clamp_components(llm_payload.get("component_scores") or {})
    llm_components = _apply_saturation_cap(llm_components, saturation_tier)
    llm_final = weighted_final_score(llm_components, weights)

    if linked_reports < CALIBRATION_REPORT_THRESHOLD:
        final_score = round(
            BLEND_LLM_WEIGHT * llm_final + BLEND_HEURISTIC_WEIGHT * heuristic_final,
            3,
        )
        blend_meta = {
            "llm_weight": BLEND_LLM_WEIGHT,
            "heuristic_weight": BLEND_HEURISTIC_WEIGHT,
            "llm_final": llm_final,
            "heuristic_final": heuristic_final,
            "linked_beta_reports": linked_reports,
        }
    else:
        final_score = llm_final
        blend_meta = None

    keyword_type = classify_keyword_type(
        keyword,
        trend_source=discovery_source,
        saturation_tier=saturation_tier,
        agent_score=final_score,
    )

    if keyword_type_filter in ("nurture", "beta") and keyword_type != keyword_type_filter:
        return None
    if keyword_type != "beta":
        return None
    if final_score < min_score:
        return None

    tier_to_status = {"fresh": "low", "moderate": "moderate", "saturated": "saturated"}
    rationale = str(llm_payload.get("rationale") or "")
    component_reasons = {
        key: f"LLM scored {llm_components[key]:.0%} for {key.replace('_', ' ')}."
        for key in COMPONENT_KEYS
    }
    trend_signals = dict(candidate.get("trend_signals") or {})
    trend_signals["scoring"] = {
        "rationale": rationale,
        "confidence": round(float(llm_payload.get("confidence") or 0.0), 3),
        "risk_flags": list(llm_payload.get("risk_flags") or []),
        "scored_with": "llm_beta_batch",
        "blend": blend_meta,
    }

    return {
        "keyword": keyword,
        "keyword_type": keyword_type,
        "discovery_source": discovery_source,
        "trend_signals": trend_signals,
        "gate_profile": "full",
        "final_score": final_score,
        "component_scores": llm_components,
        "platform_signals": build_platform_signals(
            candidate=candidate,
            tiktok_gate=tiktok_gate,
            component_scores=llm_components,
            component_reasons=component_reasons,
            scored_with="llm_beta_batch",
            rationale=rationale,
            confidence=float(llm_payload.get("confidence") or 0.0),
            risk_flags=list(llm_payload.get("risk_flags") or []),
        ),
        "tiktok_status": tier_to_status.get(saturation_tier, "moderate"),
        "tiktok_count": tiktok_stats.get("video_count_7d", 0),
        "tiktok_stats": tiktok_stats,
        "tiktok_unverified": bool(tiktok_gate.get("tiktok_unverified", False)),
    }


def _prepare_batch_items(
    items: List[Dict[str, Any]],
    db: Session,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Return LLM batch rows + lookup map keyword -> {candidate, tiktok_gate}."""
    builder = KeywordContextBuilder(db)
    batch_rows: List[Dict[str, Any]] = []
    lookup: Dict[str, Dict[str, Any]] = {}

    for item in items:
        candidate = item["candidate"]
        tiktok_gate = item["tiktok_gate"]
        keyword = candidate["keyword"]
        if not passes_beta_pre_rules(keyword, tiktok_gate):
            continue

        tiktok_stats = tiktok_gate.get("tiktok_stats") or {}
        kb_context = builder.build(
            keyword,
            keyword_type="beta",
            tiktok_hint=tiktok_stats or None,
        )
        batch_rows.append(
            {
                "keyword": keyword,
                "discovery_source": candidate.get("discovery_source", "youtube_trend"),
                "trend_signals": candidate.get("trend_signals"),
                "tiktok_stats": tiktok_stats,
                "kb_context": kb_context,
            }
        )
        lookup[keyword.lower()] = item

    return batch_rows, lookup


def _finalize_batch_scores(
    scores: Any,
    lookup: Dict[str, Dict[str, Any]],
    *,
    weights: Dict[str, float],
    min_score: float,
    keyword_type_filter: str,
    linked_reports: int,
) -> List[Dict[str, Any]]:
    if not isinstance(scores, list):
        logger.warning("Beta batch LLM returned invalid scores payload")
        return []

    results: List[Dict[str, Any]] = []
    for row in scores:
        if not isinstance(row, dict):
            continue
        keyword = str(row.get("keyword") or "").strip()
        item = lookup.get(keyword.lower())
        if not item:
            continue
        finalized = _finalize_beta_score(
            item["candidate"],
            tiktok_gate=item["tiktok_gate"],
            llm_payload=row,
            weights=weights,
            min_score=min_score,
            keyword_type_filter=keyword_type_filter,
            linked_reports=linked_reports,
        )
        if finalized:
            results.append(finalized)
    return results


def _score_beta_chunk(
    chunk: List[Dict[str, Any]],
    *,
    db: Session,
    llm: OpenAI,
    model: str,
    weights: Dict[str, float],
    settings: Optional[SettingsModel],
    min_score: float,
    keyword_type_filter: str,
    linked_reports: int,
) -> List[Dict[str, Any]]:
    batch_rows, lookup = _prepare_batch_items(chunk, db)
    if not batch_rows:
        return []

    llm_response = _call_llm_json(
        llm=llm,
        model=model,
        prompt=_build_batch_prompt(batch_rows, weights, settings),
    )
    return _finalize_batch_scores(
        llm_response.get("scores") or [],
        lookup,
        weights=weights,
        min_score=min_score,
        keyword_type_filter=keyword_type_filter,
        linked_reports=linked_reports,
    )


def _score_beta_chunk_resilient(
    chunk: List[Dict[str, Any]],
    *,
    db: Session,
    llm: OpenAI,
    model: str,
    weights: Dict[str, float],
    settings: Optional[SettingsModel],
    min_score: float,
    keyword_type_filter: str,
    linked_reports: int,
) -> List[Dict[str, Any]]:
    try:
        return _score_beta_chunk(
            chunk,
            db=db,
            llm=llm,
            model=model,
            weights=weights,
            settings=settings,
            min_score=min_score,
            keyword_type_filter=keyword_type_filter,
            linked_reports=linked_reports,
        )
    except BetaScoringError as exc:
        if _is_timeout_error(exc) and len(chunk) > 1:
            mid = len(chunk) // 2
            return (
                _score_beta_chunk_resilient(
                    chunk[:mid],
                    db=db,
                    llm=llm,
                    model=model,
                    weights=weights,
                    settings=settings,
                    min_score=min_score,
                    keyword_type_filter=keyword_type_filter,
                    linked_reports=linked_reports,
                )
                + _score_beta_chunk_resilient(
                    chunk[mid:],
                    db=db,
                    llm=llm,
                    model=model,
                    weights=weights,
                    settings=settings,
                    min_score=min_score,
                    keyword_type_filter=keyword_type_filter,
                    linked_reports=linked_reports,
                )
            )
        logger.warning("Beta chunk scoring failed (%d items): %s", len(chunk), exc)
        return []
    except Exception as exc:
        logger.error("Beta batch LLM scoring failed: %s", exc)
        if _is_timeout_error(exc) and len(chunk) > 1:
            mid = len(chunk) // 2
            return (
                _score_beta_chunk_resilient(
                    chunk[:mid],
                    db=db,
                    llm=llm,
                    model=model,
                    weights=weights,
                    settings=settings,
                    min_score=min_score,
                    keyword_type_filter=keyword_type_filter,
                    linked_reports=linked_reports,
                )
                + _score_beta_chunk_resilient(
                    chunk[mid:],
                    db=db,
                    llm=llm,
                    model=model,
                    weights=weights,
                    settings=settings,
                    min_score=min_score,
                    keyword_type_filter=keyword_type_filter,
                    linked_reports=linked_reports,
                )
            )
        logger.warning("Beta chunk scoring failed (%d items): %s", len(chunk), exc)
        return []


async def score_beta_candidates_batch(
    items: List[Dict[str, Any]],
    *,
    db: Session,
    settings: Optional[SettingsModel] = None,
    keyword_type_filter: str = "both",
    llm_client: Optional[OpenAI] = None,
) -> List[Dict[str, Any]]:
    """
    Score multiple beta candidates in one LLM call (chunked by BATCH_MAX_SIZE).

    Each item: {"candidate": dict, "tiktok_gate": dict}
    Returns list of scored suggestion dicts (may be shorter than input).
    """
    if not items:
        return []

    if settings is None:
        settings = db.query(SettingsModel).first()

    weights = get_scoring_weights(settings)
    min_score = float(settings.min_score_threshold if settings else BETA_MIN_SCORE)
    linked_reports = count_linked_beta_reports(db)
    llm_config = get_llm_config(db)
    llm = llm_client or create_llm_client(db)

    results: List[Dict[str, Any]] = []

    for start in range(0, len(items), BATCH_MAX_SIZE):
        chunk = items[start : start + BATCH_MAX_SIZE]
        results.extend(
            _score_beta_chunk_resilient(
                chunk,
                db=db,
                llm=llm,
                model=llm_config["model"],
                weights=weights,
                settings=settings,
                min_score=min_score,
                keyword_type_filter=keyword_type_filter,
                linked_reports=linked_reports,
            )
        )

    return results


async def score_beta_candidate(
    candidate: Dict[str, Any],
    *,
    tiktok_gate: Dict[str, Any],
    db: Session,
    settings: Optional[SettingsModel] = None,
    keyword_type_filter: str = "both",
    llm_client: Optional[OpenAI] = None,
) -> Optional[Dict[str, Any]]:
    """Score one beta keyword (delegates to batch API)."""
    scored = await score_beta_candidates_batch(
        [{"candidate": candidate, "tiktok_gate": tiktok_gate}],
        db=db,
        settings=settings,
        keyword_type_filter=keyword_type_filter,
        llm_client=llm_client,
    )
    return scored[0] if scored else None
