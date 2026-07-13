# US-063: Top-N Evidence Enrichment (Sprint 2)

## Status

implemented

> Doc sync 2026-07-13: status was stale (in_progress) though all acceptance
> boxes were already checked and downstream US-065 shipped on top of it.

## Lane

normal

## Product Contract

Sprint 2 per ADR 0013 — enrich Top-N scored candidates with Tier-1 channel cache,
YouTube video search round-trip, TikTok deep stats, and supply pressure + creator
diversity.

**ADR:** `docs/decisions/0013-trend-evidence-discovery-pipeline.md`  
**Depends:** US-062

## Acceptance Criteria

- [x] Top 10 scored candidates get tier-2 enrichment before save
- [x] Tier-1: `raw.channel` from `ChannelModel` when source channel in DB
- [x] `raw.youtube_search` — recent video search by keyword
- [x] `raw.tiktok` — deep search stats (reuse gate or fresh search)
- [x] `derived.supply_pressure` — video count, unique creators, creator diversity (YT + TT)
- [x] Discovery phase `enrich_top` in progress UI
- [x] `platform_signals` exposes supply pressure summary

## Validation

```bash
python -m pytest videoscout/tests_api/test_evidence_enrichment.py \
  videoscout/tests_api/test_discovery.py -v
```
