"""LLM validation pass after search-sample enrichment (ADR 0014 / US-065)."""
from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from sqlalchemy.orm import Session

from videoscout.core_engine.llm_config import create_llm_client, get_llm_config
from videoscout.core_engine.platform_signals import build_platform_signals
from videoscout.core_engine.search_sample import discovery_validation_enabled
from videoscout.core_engine.trend_cluster import parse_pair_groupings

logger = logging.getLogger(__name__)

LLM_TEMPERATURE = 0.2
VALIDATION_BATCH_MAX = 10

_RUBRIC_PATH = Path(__file__).resolve().parent / "rubrics" / "validation_v1.md"


class ValidationError(Exception):
    """Validation LLM call failed."""


def load_validation_rubric() -> str:
    if _RUBRIC_PATH.is_file():
        return _RUBRIC_PATH.read_text(encoding="utf-8").strip()
    return ""


def _heuristic_validation(scored: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback validation from search-sample + representation quality."""
    evidence = scored.get("trend_evidence") or {}
    derived = evidence.get("derived") or {}
    yt = (derived.get("search_sample") or {}).get("youtube") or {}
    tt = (derived.get("search_sample") or {}).get("tiktok") or {}
    rq = derived.get("representation_quality") or {}

    rep_conf = str(rq.get("representation_confidence") or "mixed")
    if rep_conf == "high":
        pattern = "single_pattern"
    elif rep_conf == "low":
        pattern = "fragmented"
    else:
        pattern = "mixed"

    risk_flags: List[str] = []
    adjustments = {
        "generalizability": 0.0,
        "video_performance": 0.0,
        "confidence": 0.0,
        "saturation": 0.0,
    }

    if yt.get("viral_outlier") or tt.get("viral_outlier"):
        risk_flags.append("single_viral_source")
        adjustments["video_performance"] = -0.12
        adjustments["confidence"] = -0.12
        pattern = "mixed" if pattern == "single_pattern" else pattern

    # US-080: audit/display undo only — does not recompute final_score / haircut.
    sat_undo = False
    undo_n = 0
    if yt.get("viral_outlier") and int(yt.get("sample_size") or 0) >= 5:
        sat_undo = True
        undo_n = int(yt.get("sample_size") or 0)
    elif tt.get("viral_outlier") and int(tt.get("sample_size") or 0) >= 5:
        sat_undo = True
        undo_n = int(tt.get("sample_size") or 0)
    if sat_undo:
        adjustments["saturation"] = 0.05

    if rep_conf == "low":
        risk_flags.append("low_representation_quality")
        risk_flags.append("pattern_fragmented")
        adjustments["confidence"] = min(adjustments["confidence"] - 0.10, -0.10)
        pattern = "fragmented"

    if pattern == "fragmented":
        risk_flags.append("pattern_fragmented")
        adjustments["confidence"] = min(adjustments["confidence"] - 0.08, -0.18)

    risk_flags.append("search_sample_bias")
    risk_flags = sorted(set(risk_flags))

    if adjustments["confidence"] <= -0.15 or pattern == "fragmented":
        status = "weakened"
    elif yt.get("viral_outlier"):
        status = "weakened"
    else:
        status = "confirmed"

    rationale_parts = [
        f"Pattern={pattern}; representation={rep_conf}.",
    ]
    if yt.get("viral_outlier"):
        rationale_parts.append(
            f"YouTube sample outlier: top video {yt.get('top_contribution_pct', 0)}% of views."
        )
    if yt.get("sample_size"):
        rationale_parts.append(
            f"YouTube median views {yt.get('median_views', 0):,.0f} (n={yt.get('sample_size')})."
        )
    if sat_undo:
        rationale_parts.append(
            f"Sample-shape saturation undo (+0.05) applied (n={undo_n})."
        )

    return {
        "validation_status": status,
        "pattern_assessment": pattern,
        "adjustments": adjustments,
        "risk_flags": risk_flags,
        "validation_rationale": " ".join(rationale_parts),
    }


def _build_validation_prompt(
    batch_rows: List[Dict[str, Any]],
    ambiguous_pairs: Optional[List[Tuple[str, str, float]]] = None,
) -> str:
    payload: Dict[str, Any] = {
        "candidates": batch_rows,
        "rubric": load_validation_rubric(),
    }
    if ambiguous_pairs:
        payload["ambiguous_pairs"] = [
            {
                "keyword_a": keyword_a,
                "keyword_b": keyword_b,
                "token_jaccard": round(jaccard, 3),
            }
            for keyword_a, keyword_b, jaccard in ambiguous_pairs
        ]

    pair_groupings_hint = ""
    if ambiguous_pairs:
        pair_groupings_hint = """
  "pair_groupings": [
    {
      "keyword_a": "exact keyword",
      "keyword_b": "exact keyword",
      "same_pattern": true,
      "rationale": "1 sentence"
    }
  ],
"""

    return f"""Validate keyword evidence for each candidate (delta-only pass).

Return JSON only:
{{
  "validations": [
    {{
      "keyword": "exact keyword",
      "validation_status": "confirmed | weakened | contradicted",
      "pattern_assessment": "single_pattern | mixed | fragmented",
      "adjustments": {{
        "generalizability": 0.0,
        "video_performance": 0.0,
        "confidence": 0.0,
        "saturation": 0.0
      }},
      "risk_flags": [],
      "validation_rationale": "1-2 sentences citing sample stats"
    }}
  ],{pair_groupings_hint}
}}

For each ambiguous_pair, decide whether both keywords represent the same underlying
content pattern (same_pattern=true) or distinct opportunities (same_pattern=false).
Do not change trend, relevance, or specificity. Do not compute final_score.

Batch:
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
        raise ValidationError("LLM returned empty content")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValidationError("LLM response was not a JSON object")
    return parsed


def _clamp_adjustment(value: Any, *, low: float, high: float) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(low, min(high, num)), 3)


def _normalize_validation_row(row: Dict[str, Any]) -> Dict[str, Any]:
    raw_adj = row.get("adjustments") or {}
    return {
        "validation_status": str(row.get("validation_status") or "confirmed"),
        "pattern_assessment": str(row.get("pattern_assessment") or "mixed"),
        "adjustments": {
            "generalizability": _clamp_adjustment(
                raw_adj.get("generalizability"), low=-0.25, high=0.05,
            ),
            "video_performance": _clamp_adjustment(
                raw_adj.get("video_performance"), low=-0.20, high=0.05,
            ),
            "confidence": _clamp_adjustment(
                raw_adj.get("confidence"), low=-0.25, high=0.05,
            ),
            "saturation": _clamp_adjustment(
                raw_adj.get("saturation"), low=-0.10, high=0.05,
            ),
        },
        "risk_flags": list(row.get("risk_flags") or []),
        "validation_rationale": str(row.get("validation_rationale") or ""),
    }


def apply_validation_result(
    scored: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge validation deltas; lock trend/relevance/specificity."""
    updated = copy.deepcopy(scored)
    components = dict(updated.get("component_scores") or {})

    adj = validation.get("adjustments") or {}
    for key in ("video_performance", "saturation"):
        if key in components:
            components[key] = round(
                max(0.0, min(0.98, float(components[key]) + float(adj.get(key, 0.0)))),
                3,
            )

    updated["component_scores"] = components

    agent = dict((updated.get("platform_signals") or {}).get("agent") or {})
    base_conf = float(agent.get("confidence") or 0.0)
    new_conf = round(
        max(0.0, min(1.0, base_conf + float(adj.get("confidence", 0.0)))),
        3,
    )

    risk_flags = sorted(set(list(agent.get("risk_flags") or []) + list(validation.get("risk_flags") or [])))
    agent["validation"] = validation
    agent["confidence"] = new_conf
    agent["risk_flags"] = risk_flags

    if validation.get("validation_status") == "contradicted":
        updated["final_score"] = round(max(0.0, float(updated.get("final_score", 0)) * 0.85), 3)
    elif validation.get("validation_status") == "weakened":
        updated["final_score"] = round(max(0.0, float(updated.get("final_score", 0)) * 0.95), 3)

    if updated.get("platform_signals"):
        candidate = {
            "keyword": updated["keyword"],
            "discovery_source": updated.get("discovery_source"),
            "trend_signals": updated.get("trend_signals"),
            "trend_evidence": updated.get("trend_evidence"),
        }
        tiktok_block = updated["platform_signals"].get("tiktok") or {}
        tiktok_gate = {
            "tiktok_unverified": tiktok_block.get("unverified", False),
            "score": tiktok_block.get("gate_score", 0.0),
            "tiktok_stats": tiktok_block.get("stats") or updated.get("tiktok_stats") or {},
        }
        updated["platform_signals"] = build_platform_signals(
            candidate=candidate,
            tiktok_gate=tiktok_gate,
            component_scores=components,
            component_reasons=agent.get("component_reasons") or {},
            scored_with=agent.get("scored_with", "validated"),
            rationale=agent.get("rationale"),
            confidence=new_conf,
            risk_flags=risk_flags,
            blend=agent.get("blend"),
            lifecycle_stage=agent.get("lifecycle_stage"),
            validation=validation,
        )
    return updated


def _validation_payload_row(scored: Dict[str, Any]) -> Dict[str, Any]:
    evidence = scored.get("trend_evidence") or {}
    derived = evidence.get("derived") or {}
    agent = (scored.get("platform_signals") or {}).get("agent") or {}
    return {
        "keyword": scored["keyword"],
        "initial_component_scores": scored.get("component_scores") or {},
        "initial_confidence": agent.get("confidence"),
        "search_sample": derived.get("search_sample"),
        "population_context": derived.get("population_context"),
        "representation_quality": derived.get("representation_quality"),
        "source_evidence": (evidence.get("raw") or {}).get("youtube"),
    }


async def validate_scored_candidate(
    scored: Dict[str, Any],
    *,
    db: Session,
    llm_client: Optional[OpenAI] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    if not discovery_validation_enabled():
        return scored
    if not scored.get("trend_evidence", {}).get("derived", {}).get("search_sample"):
        return scored

    validation = _heuristic_validation(scored)
    if use_llm:
        try:
            llm = llm_client or create_llm_client(db)
            config = get_llm_config(db)
            response = _call_llm_json(
                llm=llm,
                model=config["model"],
                prompt=_build_validation_prompt([_validation_payload_row(scored)]),
            )
            rows = response.get("validations") or []
            if rows and isinstance(rows[0], dict):
                validation = _normalize_validation_row(rows[0])
        except Exception as exc:
            logger.warning("Validation LLM failed for %r: %s", scored.get("keyword"), exc)

    return apply_validation_result(scored, validation)


async def validate_top_scored(
    scored_items: List[Dict[str, Any]],
    *,
    db: Session,
    top_n: int,
    llm_client: Optional[OpenAI] = None,
    ambiguous_pairs: Optional[List[Tuple[str, str, float]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Validate enriched top-N rows; pass through others. Returns pair grouping decisions."""
    if not discovery_validation_enabled() or not scored_items:
        return scored_items, {}

    ranked = sorted(scored_items, key=lambda row: row.get("final_score", 0.0), reverse=True)
    top_keys = {row["keyword"].lower() for row in ranked[:top_n]}
    top_rows = [
        row
        for row in ranked
        if row["keyword"].lower() in top_keys
        and row.get("trend_evidence", {}).get("schema_version") == "2"
        and row.get("trend_evidence", {}).get("derived", {}).get("search_sample")
    ]

    validated_map: Dict[str, Dict[str, Any]] = {}
    pair_decisions: Dict[str, str] = {}

    if top_rows:
        validations_by_keyword: Dict[str, Dict[str, Any]] = {
            row["keyword"].lower(): _heuristic_validation(row) for row in top_rows
        }

        try:
            llm = llm_client or create_llm_client(db)
            config = get_llm_config(db)
            response = _call_llm_json(
                llm=llm,
                model=config["model"],
                prompt=_build_validation_prompt(
                    [_validation_payload_row(row) for row in top_rows],
                    ambiguous_pairs,
                ),
            )
            rows = response.get("validations") or []
            for index, row in enumerate(top_rows):
                if index < len(rows) and isinstance(rows[index], dict):
                    validations_by_keyword[row["keyword"].lower()] = _normalize_validation_row(
                        rows[index]
                    )
            pair_decisions = parse_pair_groupings(response.get("pair_groupings") or [])
        except Exception as exc:
            logger.warning("Validation LLM batch failed: %s", exc)

        for row in top_rows:
            validation = validations_by_keyword.get(row["keyword"].lower()) or _heuristic_validation(row)
            validated_map[row["keyword"].lower()] = apply_validation_result(row, validation)

    results: List[Dict[str, Any]] = []
    for row in ranked:
        key = row["keyword"].lower()
        results.append(validated_map.get(key, row))

    return results, pair_decisions
