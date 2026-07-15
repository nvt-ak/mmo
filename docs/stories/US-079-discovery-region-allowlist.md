# US-079 — Discovery region allowlist (Creator Rewards markets)

## Status

implemented

## Lane

normal

## Product Contract

Discovery runs only against operator-selected Creator Rewards markets from a fixed
allowlist (US, DE, GB, JP, KR, ES, FR, MX). Default is US. Multi-select in Settings;
one Discover job fans out regions sequentially, dedupes keywords first-win, then
ranks/saves once. Applies to nurture, beta, and both filters.

## Relevant Product Docs

- `docs/product/workflows.md`
- `docs/superpowers/specs/2026-07-14-discovery-region-allowlist-design.md`

## Acceptance Criteria

- Settings checkboxes for the eight allowlisted markets; default `["US"]`.
- Save/run rejects empty or non-allowlisted codes with 400.
- Multi-region Discover fetches each selected YouTube region in one job.
- Cross-region duplicate keywords appear once (first region wins).
- Nurture-only and beta-only honor the same Settings list.
- Missing field on existing installs resolves as `["US"]`.

## Design Notes

- API: `discovery_region_codes` on settings; optional `region_codes` / legacy `region_code` on `/discovery/run`
- Tables: `settings.discovery_region_codes` JSONB
- Domain: `DISCOVERY_REGION_ALLOWLIST` in `videoscout/core_engine/discovery_regions.py`
- UI: Settings → Discovery regions

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `videoscout/tests_api/test_discovery_regions.py` |
| Integration | settings + discovery API tests |
| E2E | — |
| Platform | `cd web && npm run lint` |

## Evidence

- `PYTHONPATH=. python -m pytest videoscout/tests_api/test_discovery_regions.py videoscout/tests_api/test_settings_api.py videoscout/tests_api/test_discovery.py -q` — 40 passed (2026-07-14)
- Spec: `docs/superpowers/specs/2026-07-14-discovery-region-allowlist-design.md`
- Plan: `docs/superpowers/plans/2026-07-14-discovery-region-allowlist.md`
