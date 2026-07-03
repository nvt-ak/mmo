# US-060 — Keyword scoring diversity + platform insights

**Lane:** normal  
**Epic:** E09 Dual-Track Discovery  
**Status:** implemented

## Goal

Differentiate nurture scores using real signals; persist per-platform metrics and
agent rationale; expose breakdown in inbox.

## Acceptance

1. Nurture `final_score` uses weighted real components (not flat 75%)
2. `platform_signals` JSONB on suggestions (tiktok, youtube, agent)
3. Nurture LLM batch scoring with heuristic fallback
4. Inbox expandable insight panel (components + rationale + platform stats)

## Verify

```bash
python -m pytest videoscout/tests_api/test_nurture_scorer.py videoscout/tests_api/test_discovery.py -v
cd web && npm run lint && npm run build
```
