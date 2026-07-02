# US-003 Validation Plan

## Automated Proof

| Check | Command | Status |
| --- | --- | --- |
| TypeScript compile | `cd web && npm run build` | Required |
| Lint | `cd web && npm run lint` | Required |

No unit or Playwright tests exist yet.

## Manual E2E Checklist

- [ ] `/today` — load pending suggestions from API
- [ ] Bulk approve + reject with reason modal
- [ ] Report dialog saves outcome metrics
- [ ] `/sources` — add channel, trigger scan
- [ ] `/settings` — save weight changes
- [ ] `/insights` — trigger learning cycle, display patterns

## Status

| Layer | Status | Evidence |
| --- | --- | --- |
| Unit | ❌ | No test files |
| Integration | ⏳ | Types only; no contract test |
| E2E | ⏳ | Manual checklist above |
| Platform | ✅ | `npm run build` + `npm run lint` (2026-07-02) |
