# Discovery Region Allowlist Implementation Plan

> **For agentic workers:** Execute task-by-task. Spec: `docs/superpowers/specs/2026-07-14-discovery-region-allowlist-design.md`

**Goal:** Persist allowlisted multi-region Settings; Discover fans out sequentially in one job.

**Architecture:** Helper validates `US|DE|GB|JP|KR|ES|FR|MX`; Settings column `discovery_region_codes`; worker loops regions then ranks once.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Next.js settings UI, pytest

**Story:** US-079

---

### Task 1: Allowlist helper + unit tests
### Task 2: Migration + Settings model/API
### Task 3: Discovery resolve + worker fan-out
### Task 4: Web settings + client
### Task 5: Integration tests + workflows + harness
