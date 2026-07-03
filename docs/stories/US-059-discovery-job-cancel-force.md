# US-059 — Discovery job cancel + force restart

**Lane:** tiny  
**Epic:** E09 Dual-Track Discovery  
**Status:** in_progress

## Goal

Let operators cancel a stuck discovery job or force-start a new run when
`POST /discovery/run` would return 409.

## Acceptance

- `POST /discovery/jobs/{id}/cancel` marks active job failed
- `POST /discovery/run` with `force: true` cancels active job then starts new
- Web auto-restarts stale zombie jobs on 409; shows Start over while tracking

## Verify

```bash
python -m pytest videoscout/tests_api/test_discovery.py -v -k "cancel or force or stale"
cd web && npm run lint
```
