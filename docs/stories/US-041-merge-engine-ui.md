# US-041: Merge Engine + `/merge` UI

## Status

implemented

## Lane

normal

## Product Contract

Implement Module **M4 (Production)** — merge two `in_pool` videos via ffmpeg into
`data/finals/` with manual and random (same-keyword) modes.

**Epic:** E07 Batch & Merge  
**Roadmap:** R5 — M4 merge (`docs/superpowers/plans/2026-07-02-r5-merge.md`)

## Acceptance Criteria

- Schema adds `merge_jobs`, `final_videos`; `review_status` includes `merged`
- `services/merge.py` wraps ffmpeg concat with test injection
- Manual merge accepts exactly two pool videos
- Random merge picks two videos sharing a keyword
- Output written to `{VIDEOSCOUT_DATA_DIR}/finals/{job_id}.mp4`
- API: pool, enqueue, job status, list finals
- Web route `/merge` with pool selection + random action + finals list

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
```

## Harness Delta

- Story registered in Harness matrix
- Matrix evidence updated after full API suite run
