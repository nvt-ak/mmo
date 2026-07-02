# US-058 — Discovery SSE + reload persistence

**Lane:** normal  
**Epic:** E09 Dual-Track Discovery  
**Status:** implemented

## Goal

Replace discovery job polling with SSE. Block Discover while a job is
in-progress, including after page reload.

## Acceptance

- `GET /api/v1/discovery/jobs/{id}/stream` emits job status until terminal
- `POST /discovery/run` returns 409 when a job is already active
- Web uses EventSource instead of 2s poll loop
- Active job id persisted in localStorage; reload resumes stream + disables button
- Completed/failed clears storage and re-enables button

## Verify

```bash
python -m pytest videoscout/tests_api/test_discovery.py -v
cd web && npm run lint && npm run build
```
