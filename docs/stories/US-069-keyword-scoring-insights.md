# US-069 — Keyword scoring diversity + platform insights

> Renumbered from US-060 (2026-07-13 doc sync, then US-067→US-069 to avoid clashing with ADR 0014 reserved IDs) — collided with
> `US-060-tiktok-token-proxy-rotation.md`.

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
