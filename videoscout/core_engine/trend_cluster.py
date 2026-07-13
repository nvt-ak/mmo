"""Heuristic trend clustering for near-duplicate keywords (US-066 / ADR 0014 Phase 2)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple

from videoscout.core_engine.nurture_scorer import _GENERIC_TOKENS


def cluster_jaccard_low() -> float:
    raw = os.getenv("CLUSTER_JACCARD_LOW", "0.35").strip()
    try:
        return max(0.0, min(float(raw), 1.0))
    except ValueError:
        return 0.35


def cluster_jaccard_high() -> float:
    raw = os.getenv("CLUSTER_JACCARD_HIGH", "0.65").strip()
    try:
        return max(0.0, min(float(raw), 1.0))
    except ValueError:
        return 0.65


def normalize_keyword_tokens(keyword: str) -> Set[str]:
    """Strip generic nurture tokens before overlap comparison."""
    return {
        token
        for token in keyword.lower().split()
        if len(token) > 1 and token not in _GENERIC_TOKENS
    }


def keyword_token_jaccard(keyword_a: str, keyword_b: str) -> float:
    tokens_a = normalize_keyword_tokens(keyword_a)
    tokens_b = normalize_keyword_tokens(keyword_b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def overlap_band(jaccard: float) -> str:
    """Classify pair overlap: distinct | same | ambiguous."""
    if jaccard >= cluster_jaccard_high():
        return "same"
    if jaccard < cluster_jaccard_low():
        return "distinct"
    return "ambiguous"


def pair_key(keyword_a: str, keyword_b: str) -> str:
    left, right = keyword_a.lower(), keyword_b.lower()
    return f"{left}|||{right}" if left <= right else f"{right}|||{left}"


class _UnionFind:
    def __init__(self, keys: List[str]) -> None:
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        parent = self.parent[key]
        if parent != key:
            self.parent[key] = self.find(parent)
        return self.parent[key]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def find_pair_candidates(
    scored_items: List[Dict[str, Any]],
) -> Tuple[List[Tuple[str, str, float]], List[Tuple[str, str, float]]]:
    """Return (auto_same_pairs, ambiguous_pairs) as (keyword_a, keyword_b, jaccard)."""
    keywords = [row["keyword"] for row in scored_items]
    same_pairs: List[Tuple[str, str, float]] = []
    ambiguous_pairs: List[Tuple[str, str, float]] = []

    for index in range(len(keywords)):
        for other in range(index + 1, len(keywords)):
            jaccard = keyword_token_jaccard(keywords[index], keywords[other])
            band = overlap_band(jaccard)
            if band == "same":
                same_pairs.append((keywords[index], keywords[other], jaccard))
            elif band == "ambiguous":
                ambiguous_pairs.append((keywords[index], keywords[other], jaccard))

    return same_pairs, ambiguous_pairs


def filter_escalated_ambiguous_pairs(
    ambiguous_pairs: List[Tuple[str, str, float]],
    *,
    escalate_keywords: Set[str],
) -> List[Tuple[str, str, float]]:
    """Only escalate ambiguous pairs touching at least one Top-N keyword."""
    lowered = {keyword.lower() for keyword in escalate_keywords}
    return [
        pair
        for pair in ambiguous_pairs
        if pair[0].lower() in lowered or pair[1].lower() in lowered
    ]


def parse_pair_groupings(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Map normalized pair key -> same | distinct."""
    decisions: Dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        keyword_a = str(row.get("keyword_a") or "").strip()
        keyword_b = str(row.get("keyword_b") or "").strip()
        if not keyword_a or not keyword_b:
            continue
        decision = "same" if bool(row.get("same_pattern")) else "distinct"
        decisions[pair_key(keyword_a, keyword_b)] = decision
    return decisions


def build_clusters(
    scored_items: List[Dict[str, Any]],
    *,
    llm_pair_decisions: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Assign cluster metadata to scored rows.

    Canonical keyword = highest final_score member (stable across runs).
    history_prior remains per-keyword at scoring time (no cluster penalty).
    """
    if not scored_items:
        return []

    decisions = llm_pair_decisions or {}
    same_pairs, ambiguous_pairs = find_pair_candidates(scored_items)
    union_find = _UnionFind([row["keyword"] for row in scored_items])

    for keyword_a, keyword_b, _ in same_pairs:
        union_find.union(keyword_a, keyword_b)

    for keyword_a, keyword_b, _ in ambiguous_pairs:
        decision = decisions.get(pair_key(keyword_a, keyword_b))
        if decision == "same":
            union_find.union(keyword_a, keyword_b)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in scored_items:
        root = union_find.find(row["keyword"])
        grouped.setdefault(root, []).append(row)

    clusters: List[Dict[str, Any]] = []
    for members in grouped.values():
        if len(members) < 2:
            for member in members:
                member["cluster_assignment"] = None
            continue

        canonical = max(members, key=lambda item: float(item.get("final_score") or 0.0))
        canonical_keyword = canonical["keyword"]
        member_keywords = [member["keyword"] for member in members]
        cluster_meta = {
            "canonical_keyword": canonical_keyword,
            "member_keywords": member_keywords,
        }
        for member in members:
            member["cluster_assignment"] = {
                **cluster_meta,
                "is_canonical": member["keyword"] == canonical_keyword,
            }
        clusters.append({**cluster_meta, "members": members})

    return clusters
