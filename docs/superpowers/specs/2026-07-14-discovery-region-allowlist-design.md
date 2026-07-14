# VideoScout — Discovery Region Allowlist (Creator Rewards Markets)

**Date:** 2026-07-14  
**Status:** Approved (brainstorm 2026-07-14)  
**Lane:** normal (settings + discovery worker behavior; no auth/stack change)  
**Amends:** Dual-track discovery (`docs/decisions/0011-dual-track-nurture-beta.md`) — region no longer DE-only  
**Related:** Discovery run API, Settings persistence, `run_trend_discovery`

---

## 1. Problem

Discovery hardcodes a single YouTube `region_code` (default / client `"DE"`). Creator Rewards Beta is available in multiple markets; operators need to discover trends from an allowed subset of those markets without inventing free-form region strings.

## 2. Goal

Operator selects one or more **allowlisted** Creator Rewards markets in Settings. Every Discover run (nurture / beta / both) fans out across the selected regions in **one job**, merges candidates, then ranks and saves once.

## 3. Decisions (locked)

| Topic | Decision |
| --- | --- |
| Scope | Discovery only (not profile `beta_eligible`, not classifier language) |
| Selection UX | Settings multi-select (checkboxes) |
| Applies to | All Discover filters: nurture, beta, both |
| Default | `["US"]` (new installs and missing field on existing installs) |
| Job model | One Discover click → one job → sequential region fan-out |
| Dedup | Cross-region keyword first-win (order = Settings list order) |
| Google Trends | Unchanged (`GOOGLE_TRENDS_GEO`); no per-region Trends fan-out in this work |
| Rejected | N jobs per click; single-region-only select; empty selection |

## 4. Allowlist

Fixed ISO-3166-1 alpha-2 codes (Creator Rewards beta registration markets):

```text
US  United States
DE  Germany
GB  United Kingdom
JP  Japan
KR  South Korea
ES  Spain
FR  France
MX  Mexico
```

Constant name (suggested): `DISCOVERY_REGION_ALLOWLIST`.

Validation rules:

- Non-empty list required for Settings save and for Discover run resolution.
- Every code must be in the allowlist (case-normalized to uppercase).
- Duplicates stripped while preserving first occurrence order.

## 5. Settings + API

### 5.1 Settings field

- Name: `discovery_region_codes: list[str]`
- Default when absent: `["US"]`
- Web Settings: section **Discovery regions** — checkboxes for the eight markets (human labels as in §4)
- PATCH/save rejects empty or non-allowlisted codes with `400`

### 5.2 Discovery run

- Prefer Settings as source of truth.
- Optional request override: `region_codes: list[str]` with the same validation (useful for tests).
- Deprecate reliance on single `region_code`:
  - If only legacy `region_code` is sent, treat as `[region_code]` after allowlist check.
  - Web client stops hardcoding `"DE"`; omits body regions and uses Settings, or sends the list loaded from Settings.
- Default cascade if Settings missing: `["US"]` (not `DE`).

Applies equally when `keyword_type_filter` is `nurture`, `beta`, or `both`.

## 6. Worker behavior

`run_trend_discovery` receives `region_codes: list[str]` (resolved before enqueue).

For each region in order:

1. Update job progress phase to include the region (e.g. `fetch_trends:US`).
2. Fetch discovery sources with that YouTube `regionCode`.
3. Build candidates / evidence tagged with that `region`.
4. Merge into job-level queues with keyword `seen` set — **first-win** across regions.

After all regions:

- Existing rank → TikTok gate → qualification → save path runs **once**.
- Inbox cap (e.g. top 10) is **not** multiplied by region count.

Error handling:

- If one region’s YouTube fetch fails, log and continue with remaining regions when at least one region already contributed sources; if **all** regions fail, fail the job as today.
- Invalid/empty resolved list at job start → fail fast (`400` at API or job `failed` with clear message).

## 7. Data / product notes

- Evidence already carries `region`; preserve it so operators can later see which market a keyword came from (inbox column optional, **out of scope**).
- Product copy that says “Creator Rewards DE” should be updated to “Creator Rewards markets (allowlisted regions)” in `docs/product/workflows.md` as part of implementation.
- No ADR required unless durable default/`DE`→`US` migration is disputed later; this spec is sufficient for the story packet.

## 8. Out of scope

- Profile country / `beta_eligible` by market
- Classifier or scoring by language/country
- Parallel multi-job Discover
- Google Trends per-geo fan-out
- Inbox UI “Region” column (follow-up OK)

## 9. Acceptance criteria

1. Settings exposes checkboxes for exactly the eight allowlisted markets; default selection is US only.
2. Saving empty selection or a non-allowlisted code returns `400`.
3. Discover with Settings `["US","DE"]` fetches YouTube trends for US then DE in one job and does not call other regions.
4. Duplicate keyword across US and DE appears once (first region wins).
5. Nurture-only and beta-only Discover both honor the same Settings list.
6. Existing installs without the field behave as `["US"]` without requiring a manual migration step.
7. Tests cover allowlist validation, default resolution, and multi-region fan-out merge/dedup.

## 10. Testing plan

- Unit: allowlist normalize/validate helper.
- API: settings PATCH valid/invalid; discovery/run resolves Settings and optional override.
- Worker (mocked YouTube): two regions → sources called twice; shared keyword deduped; progress phase mentions each region.
- Regression: single-region `["US"]` path matches prior single-`region_code` behavior aside from default code change.

## 11. Implementation note (harness)

- Intake: **normal** change request.
- Create story packet under `docs/stories/` (suggested id US-079) before code.
- Update matrix proof after validation.
