# 0009 Keyword-Led Content Factory

Date: 2026-07-02

## Status

Accepted

## Context

Brainstorming (2026-07-02) confirmed operator workflow differs from PRD v0.1
(video Daily Digest + export URLs) and from initial web implementation focus.

Actual workflow: approve **keywords** → auto cascade (channels, download) →
daily batch Keep/Skip → merge → final videos → upload handoff (v1).

## Decision

Adopt **keyword-led content factory** as canonical product model.

| Topic | Decision |
| --- | --- |
| Primary unit | Approved keyword |
| Approve gate | Keyword only; triggers auto cascade |
| Pre-merge | Daily batch Keep \| Skip |
| Merge | Random same-keyword; manual cross-keyword OK |
| Architecture | Monolith: download + merge in-repo |
| Upload | v1: `data/finals/` handoff; v2: in-app module |
| Roadmap | Pipeline stages R0–R7 |

PRD v0.1 marked superseded. Canonical contract: `docs/product/workflows.md`.

Full spec: `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`.

## Alternatives Considered

1. **Keep PRD v0.1 video-centric model** — rejected; mismatch operator workflow
2. **Orchestrate external download/merge tools** — rejected; operator chose monolith
3. **Vertical slice happy path first** — rejected; pipeline stages preferred for harness alignment

## Consequences

Positive:

- Single product narrative for agents and operators
- Clear module boundaries M1–M5
- Existing US-002/003 map to M1 foundation

Tradeoffs:

- PRD v0.1 and parts of web UI need realignment over R1–R5
- US-001 SQLite experiments must port to PostgreSQL
- ~10 week v1 timeline before full keyword→final pipeline

## Follow-Up

- R0: product docs + backlog (this ADR)
- R1: M1 complete — see `docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md`
- Record new ADRs before R2+ stack changes
