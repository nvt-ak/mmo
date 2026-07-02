# US-053: TikTok msToken Search for Web API

## Status

implemented

## Lane

normal

## Product Contract

Wire TikTok internal search (TikTokApi + `TIKTOK_MS_TOKEN`) into `videoscout/services/tiktok.py` so TrendDiscovery gate and agent scoring work without RapidAPI placeholder.

**Epic:** E09  
**Depends on:** US-051 (TrendDiscovery gate)

## Acceptance Criteria

- `TikTokService.search_videos()` uses TikTokApi + msToken (not RapidAPI)
- Missing token returns `error: no_ms_token` (same gate behavior as before)
- Response shape unchanged: `videos`, `total_count`, `avg_*` metrics
- In-memory 6h cache retained
- `.env.example` documents `TIKTOK_MS_TOKEN`
- Tests mock TikTokApi; no live network in CI

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v
```
