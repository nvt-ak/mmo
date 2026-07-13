# US-068 — Discovery job cancel + force restart

> Renumbered from US-059 (2026-07-13 doc sync, then US-066→US-068 to avoid clashing with ADR 0014 reserved IDs) — collided with
> `US-059-discovery-progress-bar.md`. Acceptance verified against code
> (`videoscout/api/discovery.py::cancel_discovery_job`, `_cancel_discovery_job`).

**Lane:** tiny  
**Epic:** E09 Dual-Track Discovery  
**Status:** implemented

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
