# Sample-Shape Saturation Undo (US-080) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When enriched search-sample evidence shows a reliable viral outlier (`sample_size >= 5`), set validation `adjustments["saturation"] = +0.05` so component breakdown does not read as market saturation — audit/display only.

**Architecture:** Single change in `_heuristic_validation()` reading the same `derived.search_sample.{youtube,tiktok}` blocks already used for `viral_outlier`. Do not touch `compute_saturation`, haircuts, or `final_score` recompute.

**Tech Stack:** Python, pytest, existing `validation_pass.py` / US-065 fixtures.

## Global Constraints

- Approach **X** only: no ranking claim; no `final_score` recompute; no haircut change.
- `sample_size` from search_sample platform dict only — never `tiktok_stats.video_count_7d`.
- Keep VP −0.12 and confidence −0.12 when outlier fires.
- Undo once at +0.05 (do not stack YT+TT).
- Story: US-080. Spec: `docs/superpowers/specs/2026-07-15-sample-shape-saturation-undo-design.md`.

## File map

| File | Role |
| --- | --- |
| `videoscout/core_engine/validation_pass.py` | Add saturation undo after existing outlier VP/confidence block; extend rationale |
| `videoscout/tests_api/test_validation_pass.py` | New unit cases + assert existing outlier fixture still weakened |
| `docs/stories/US-080-sample-shape-saturation-undo.md` | Mark criteria done + validation evidence after tests pass |

---

### Task 1: Failing tests for saturation undo

**Files:**
- Modify: `videoscout/tests_api/test_validation_pass.py`
- Test: same file

**Interfaces:**
- Consumes: `_heuristic_validation(scored: dict) -> dict`, `_scored_with_evidence(youtube_stats, rq)`
- Produces: tests covering n≥5 / n=4 / no-outlier / apply path for component display

- [ ] **Step 1: Extend helper to accept optional tiktok_stats**

```python
def _scored_with_evidence(
    youtube_stats: dict,
    rq: dict,
    *,
    tiktok_stats: dict | None = None,
) -> dict:
    return {
        "keyword": "test keyword phrase",
        "final_score": 0.82,
        "component_scores": {
            "trend": 0.84,
            "relevance": 0.80,
            "specificity": 0.75,
            "saturation": 0.70,
            "video_performance": 0.65,
        },
        "platform_signals": {
            "tiktok": {"unverified": False, "gate_score": 0.7, "stats": {}},
            "agent": {
                "scored_with": "test",
                "confidence": 0.75,
                "component_reasons": {},
                "risk_flags": [],
            },
        },
        "trend_evidence": {
            "schema_version": "2",
            "derived": {
                "search_sample": {
                    "youtube": youtube_stats,
                    "tiktok": tiktok_stats if tiktok_stats is not None else {},
                },
                "representation_quality": rq,
            },
        },
        "tiktok_stats": {},
    }
```

- [ ] **Step 2: Add failing tests**

```python
def test_heuristic_saturation_undo_when_outlier_n_ge_5():
    validation = _heuristic_validation(
        _scored_with_evidence(
            {
                "viral_outlier": True,
                "top_contribution_pct": 96,
                "median_views": 7000,
                "sample_size": 5,
            },
            {"representation_confidence": "high"},
        )
    )
    assert validation["adjustments"]["saturation"] == pytest.approx(0.05)
    assert validation["adjustments"]["video_performance"] == pytest.approx(-0.12)
    assert validation["adjustments"]["confidence"] == pytest.approx(-0.12)
    assert "saturation undo" in validation["validation_rationale"].lower()


def test_heuristic_no_saturation_undo_when_outlier_n_lt_5():
    validation = _heuristic_validation(
        _scored_with_evidence(
            {
                "viral_outlier": True,
                "top_contribution_pct": 90,
                "median_views": 5000,
                "sample_size": 4,
            },
            {"representation_confidence": "high"},
        )
    )
    assert validation["adjustments"]["saturation"] == pytest.approx(0.0)
    assert validation["adjustments"]["video_performance"] == pytest.approx(-0.12)


def test_heuristic_no_saturation_undo_without_outlier():
    validation = _heuristic_validation(
        _scored_with_evidence(
            {"viral_outlier": False, "sample_size": 10, "median_views": 8000},
            {"representation_confidence": "mixed"},
        )
    )
    assert validation["adjustments"]["saturation"] == pytest.approx(0.0)


def test_heuristic_saturation_undo_from_tiktok_sample_only():
    validation = _heuristic_validation(
        _scored_with_evidence(
            {"viral_outlier": False, "sample_size": 10, "median_views": 8000},
            {"representation_confidence": "mixed"},
            tiktok_stats={
                "viral_outlier": True,
                "top_contribution_pct": 80,
                "median_views": 4000,
                "sample_size": 6,
            },
        )
    )
    assert validation["adjustments"]["saturation"] == pytest.approx(0.05)
    assert validation["adjustments"]["video_performance"] == pytest.approx(-0.12)


def test_apply_validation_saturation_adj_updates_component_not_final_via_adj():
    scored = _scored_with_evidence(
        {
            "viral_outlier": True,
            "top_contribution_pct": 96,
            "median_views": 7000,
            "sample_size": 5,
        },
        {"representation_confidence": "high"},
    )
    validation = _heuristic_validation(scored)
    updated = apply_validation_result(scored, validation)
    assert updated["component_scores"]["saturation"] == pytest.approx(0.75)  # 0.70 + 0.05
    # Haircut from weakened still applies; final is not rebuilt from sat adj alone
    assert updated["final_score"] == pytest.approx(0.82 * 0.95)
```

- [ ] **Step 3: Run tests — expect FAIL on saturation asserts**

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_validation_pass.py -v
```

Expected: new saturation tests FAIL (`adjustments["saturation"]` is 0.0).

---

### Task 2: Implement undo in `_heuristic_validation`

**Files:**
- Modify: `videoscout/core_engine/validation_pass.py` (`_heuristic_validation`)
- Test: `videoscout/tests_api/test_validation_pass.py`

**Interfaces:**
- Consumes: `yt` / `tt` dicts from `derived.search_sample`
- Produces: `adjustments["saturation"]` set to `0.05` when reliable outlier; rationale clause

- [ ] **Step 1: After VP/confidence outlier block, add**

```python
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
```

(Use `if`/`elif` so YT+TT both qualifying still apply once at +0.05.)

- [ ] **Step 2: Append rationale when `sat_undo`**

```python
    if sat_undo:
        rationale_parts.append(
            f"Sample-shape saturation undo (+0.05) applied (n={undo_n})."
        )
```

- [ ] **Step 3: Run full validation_pass suite — expect PASS**

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_validation_pass.py -v
```

- [ ] **Step 4: Update story US-080 checkboxes + validation evidence; harness story update**

- [ ] **Step 5: Commit** (when user requests)

```bash
git add videoscout/core_engine/validation_pass.py \
  videoscout/tests_api/test_validation_pass.py \
  docs/stories/US-080-sample-shape-saturation-undo.md
git commit -m "feat(validation): sample-shape saturation undo for audit (US-080)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
| --- | --- |
| +0.05 when outlier + n≥5 from search_sample | Task 2 |
| Never use video_count_7d | Task 2 (only sample_size) |
| n&lt;5 → no undo | Task 1 test |
| VP/confidence unchanged | Task 1 asserts |
| Status/haircut unchanged | Existing + apply test |
| Rationale mentions undo | Task 1 + 2 |
| No compute_saturation / recompute final / Z | Out of plan |

## Self-review

- No placeholders; exact paths and code.
- Types match existing dict-based validation API.
- Single subsystem (validation heuristic) — no split needed.
