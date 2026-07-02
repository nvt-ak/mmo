# Test Matrix

Maps product behavior to proof. Query live status:

```bash
scripts/bin/harness-cli query matrix
```

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted, not implemented |
| in_progress | Actively being built |
| implemented | Proof exists |
| changed | Contract changed after implementation |
| retired | No longer in product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | Keyword experiment feedback loop | yes | yes | no | no | implemented | `videoscout/tests/test_keyword_learning_integration.py` |
| US-002 | FastAPI backend + PostgreSQL | yes | yes | no | no | implemented | `python -m pytest videoscout/tests_api/ -v` |
| US-003 | Next.js web inbox UI | no | no | no | yes | implemented | `cd web && npm run build && npm run lint` |
| US-004 | Browser E2E tests | — | — | — | — | planned | — |
| US-010 | Keyword experiments on PostgreSQL + API | yes | yes | no | no | implemented | `python -m pytest videoscout/tests_api/test_experiments_api.py videoscout/tests_api/test_experiments_engine.py -v` |
| US-011 | TikTok search stats in agent scoring | yes | yes | no | no | implemented | `python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v` |
| US-012 | Performance report → knowledge base | yes | yes | no | no | implemented | `python -m pytest videoscout/tests_api/test_performance_api.py -v` |
| US-013 | Web experiments & report UI (`/insights`) | no | no | no | yes | implemented | `cd web && npm run build && npm run lint` |

## Evidence Rules

- Unit: pure domain and application rules
- Integration: API enforcement, data integrity, service contracts
- E2E: user-visible browser flows
- Platform: build/deploy/runtime proof when lower layers insufficient
