# US-050: TikTok Performance Report Form (M5 Feedback)

## Status

implemented

## Lane

normal

## Product Contract

Close Module **M5 (Feedback Loop)** — operator reports TikTok stats after upload,
linked to finals and keywords, feeding agent accuracy tracking.

**Epic:** E08 Feedback  
**Roadmap:** R6 — M5 feedback (`docs/superpowers/plans/2026-07-02-r6-feedback.md`)

## Acceptance Criteria

- Performance reports accept optional `final_video_id`
- Submitting with `suggestion_id` marks keyword as `reported`
- `GET /api/v1/feedback/accuracy` returns agent accuracy metrics
- `GET /api/v1/feedback/pending-finals` lists unreported finals
- Web route `/feedback` with report form, pending finals picker, history
- Shares + notes fields on report form

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
```

## Harness Delta

- Story registered in Harness matrix
- Matrix evidence updated after full API suite run
