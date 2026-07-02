# US-051: Dual-Track Trend Discovery Foundation (R7a)

## Status

implemented

## Lane

normal

## Product Contract

R7a foundation per dual-track spec — trend-first keyword discovery, nurture/beta
classification, dual inbox, light vs full TikTok gate. Channel-first scan deprecated
as primary.

**Epic:** E09 Dual-Track Discovery  
**Roadmap:** R7a (`docs/superpowers/plans/2026-07-02-r7a-dual-track-foundation.md`)  
**Spec:** `docs/superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md`  
**ADR:** `docs/decisions/0011-dual-track-nurture-beta.md`

## Intake

| Field | Value |
| --- | --- |
| Type | spec-slice |
| Lane | normal |
| Risk | Bounded — extends M1; no auth/data-ownership change |

## Acceptance Criteria

- `suggestions.keyword_type` (`nurture` \| `beta`) with discovery metadata columns
- `discovery_jobs` table + `POST /api/v1/discovery/run` (YouTube trending v1)
- `keyword_classifier.py` implements §6.2 heuristics (unit tested)
- Light TikTok gate (nurture): surfaces with `tiktok_unverified` on failure
- Full TikTok gate (beta): blocks from inbox on TikTok failure
- Web routes `/today/nurture` and `/today/beta` with filtered inbox
- Fresh install: first discovery run yields nurture + beta candidates (no manual channel)
- Classifier experiment: Appendix B started; ship mode per agreement threshold
- `POST /scan/run` retained but documented deprecated

## Out of Scope (R7b–d)

- `tiktok_profiles`, typed media pools, profile bulk post
- Social/web trend sources (R7d)
- Learning loop split by `keyword_type` (R7c)

## Validation

```bash
python -m pytest videoscout/tests_api/test_discovery.py \
  videoscout/tests_api/test_keyword_classifier.py -v
cd web && npm run build && npm run lint
```

Bootstrap check (manual):

```bash
# Fresh DB or empty suggestions
curl -X POST http://localhost:8000/api/v1/discovery/run -d '{"keyword_type_filter":"both"}'
# Expect ≥5 nurture + ≥3 beta pending after job completes
```

Classifier experiment:

```bash
python scripts/run_classifier_experiment.py --day 1 --region DE
# Operator fills operator_tag column; re-run with --score after 7 days
```

## Harness Delta

```bash
scripts/bin/harness-cli intake --type spec-slice \
  --summary "R7a dual-track discovery foundation" --lane normal --story US-051

scripts/bin/harness-cli story add --id US-051 \
  --title "Dual-track trend discovery foundation" --lane normal \
  --verify "python -m pytest videoscout/tests_api/test_discovery.py videoscout/tests_api/test_keyword_classifier.py -v"
```
