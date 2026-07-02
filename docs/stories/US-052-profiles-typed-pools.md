# US-052: TikTok Profiles + Typed Media Pools (R7b)

## Status

implemented

## Lane

normal

## Product Contract

R7b per dual-track spec — profile registry, typed pools, pool/profile routes. No bulk assign (R7c).

**Epic:** E09  
**Plan:** `docs/superpowers/plans/2026-07-02-r7b-profiles-pools.md`

## Acceptance Criteria

- `tiktok_profiles` table + CRUD API filtered by `stage`
- Promote nurture → beta sets `stage`, `promoted_at`, clears `beta_eligible` tick
- `video_assets` + `final_videos` have `pool_type`, `pool_status`
- Batch Keep sets `pool_type` from suggestion `keyword_type`, `pool_status=ready`
- Merge registers final with inherited `pool_type`, `pool_status=ready`
- `GET /api/v1/pools?pool_type=nurture|beta` lists ready assets + finals
- Web routes `/pool/nurture`, `/pool/beta`, `/profiles/nurture`, `/profiles/beta`

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/test_profiles.py videoscout/tests_api/test_pools.py -v
cd web && npm run build && npm run lint
```
