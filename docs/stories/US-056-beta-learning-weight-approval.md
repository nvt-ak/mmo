# US-056: Beta Learning Weight Approval (R7c)

## Status

implemented

## Lane

normal

## Product Contract

Close beta self-improvement loop: learning cycle proposes weight adjustments from
beta performance patterns; operator approves before settings update.

**Epic:** E09  
**ADR:** `docs/decisions/0012-beta-llm-scoring-knowledge-graph.md`  
**Depends on:** US-055, US-050 (performance reports)

## Acceptance Criteria

- Learning cycle filters `keyword_type=beta` reports and patterns
- Proposals stored with `suggested_adjustment` on `keyword_patterns` or learning report
- API: list pending weight proposals; approve/reject endpoint
- Approved changes update `SettingsModel.weight_relevance|specificity|saturation` only
- Remove blind auto-apply in `api/learning.py` for weight factors
- Settings or feedback UI shows pending proposals (minimal list + approve button)

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/test_learning_api.py -v
```
