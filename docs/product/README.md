# Product Docs

Living product contract for VideoScout.

| File | Status |
| --- | --- |
| [`workflows.md`](workflows.md) | **Active** — operator workflow, modules, metrics |
| [`PRD.md`](PRD.md) | Superseded v0.1 — historical only |
| [`agent-learning-system.md`](agent-learning-system.md) | Draft — update in R1 |
| [`keyword-experiments.md`](keyword-experiments.md) | Draft — update in R1 |

Design spec: [`docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`](../superpowers/specs/2026-07-02-videoscout-workflow-design.md)

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
