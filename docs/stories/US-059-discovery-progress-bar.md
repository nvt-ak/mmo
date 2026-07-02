# US-059 — Discovery progress bar

**Lane:** tiny  
**Epic:** E09  
**Status:** implemented

## Goal

Accurate discovery progress bar driven by worker metrics over SSE.

## Verify

```bash
python -m pytest videoscout/tests_api/test_discovery.py -v
cd web && npm run lint && npm run build
```
