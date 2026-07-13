"""Tests for trend cluster heuristic dedup (US-066)."""
from videoscout.core_engine.trend_cluster import (
    build_clusters,
    cluster_jaccard_high,
    cluster_jaccard_low,
    filter_escalated_ambiguous_pairs,
    find_pair_candidates,
    keyword_token_jaccard,
    normalize_keyword_tokens,
    overlap_band,
    parse_pair_groupings,
)


def _scored(keyword: str, score: float) -> dict:
    return {"keyword": keyword, "final_score": score}


def test_normalize_keyword_tokens_strips_generic():
    tokens = normalize_keyword_tokens("viral dance trend challenge")
    assert "viral" not in tokens
    assert "trend" not in tokens
    assert "challenge" not in tokens
    assert "dance" in tokens


def test_keyword_token_jaccard_identical_after_generic_strip():
    assert keyword_token_jaccard(
        "viral dance trend",
        "dance trend viral",
    ) == 1.0


def test_overlap_band_boundaries():
    low = cluster_jaccard_low()
    high = cluster_jaccard_high()
    assert overlap_band(low - 0.01) == "distinct"
    assert overlap_band(high + 0.01) == "same"
    assert overlap_band((low + high) / 2) == "ambiguous"


def test_find_pair_candidates_classifies_same_and_ambiguous():
    items = [
        _scored("morning routine tips", 0.8),
        _scored("morning routine tip", 0.7),
        _scored("completely different topic", 0.6),
    ]
    same_pairs, ambiguous_pairs = find_pair_candidates(items)
    assert same_pairs or ambiguous_pairs
    assert not any(
        pair[0] == "completely different topic" and pair[1] == "morning routine tips"
        for pair in same_pairs + ambiguous_pairs
    )


def test_build_clusters_auto_groups_high_overlap():
    items = [
        _scored("morning coffee ritual", 0.82),
        _scored("coffee morning ritual", 0.71),
        _scored("unrelated finance tips", 0.55),
    ]
    clusters = build_clusters(items)
    assert len(clusters) == 1
    assert clusters[0]["canonical_keyword"] == "morning coffee ritual"
    assert items[0]["cluster_assignment"]["is_canonical"] is True
    assert items[1]["cluster_assignment"]["is_canonical"] is False
    assert items[2]["cluster_assignment"] is None


def test_build_clusters_respects_llm_pair_decisions():
    items = [
        _scored("alpha beta gamma", 0.7),
        _scored("alpha beta gammas", 0.69),
    ]
    _, ambiguous_pairs = find_pair_candidates(items)
    if not ambiguous_pairs:
        return
    keyword_a, keyword_b, _ = ambiguous_pairs[0]
    decisions = parse_pair_groupings(
        [{"keyword_a": keyword_a, "keyword_b": keyword_b, "same_pattern": True}]
    )
    clusters = build_clusters(items, llm_pair_decisions=decisions)
    assert len(clusters) == 1


def test_filter_escalated_ambiguous_pairs_requires_top_keyword():
    pairs = [("alpha beta", "alpha betas", 0.5)]
    assert filter_escalated_ambiguous_pairs(pairs, escalate_keywords={"alpha beta"}) == pairs
    assert filter_escalated_ambiguous_pairs(pairs, escalate_keywords={"other keyword"}) == []


def test_parse_pair_groupings_normalizes_order():
    decisions = parse_pair_groupings(
        [{"keyword_a": "Zulu Keyword", "keyword_b": "Alpha Keyword", "same_pattern": False}]
    )
    assert len(decisions) == 1
    assert decisions["alpha keyword|||zulu keyword"] == "distinct"
