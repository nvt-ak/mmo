# R7b — Profiles + Typed Pools Implementation Plan

**Goal:** `tiktok_profiles` CRUD + nurture→beta promote; `pool_type`/`pool_status` on assets; pool + profile UI routes.

**Story:** US-052  
**Spec:** `docs/superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md` §9.2–9.3, §8  
**Out of scope:** `profile_media_assignments`, bulk assign (R7c)

## Tasks

1. US-052 story + harness intake
2. Alembic 0010: `tiktok_profiles`, `pool_type`/`pool_status` on `video_assets` + `final_videos`
3. Batch keep → inherit `pool_type`, set `pool_status=ready`
4. Merge worker → set `pool_type`/`pool_status` on `final_videos`
5. API `profiles.py` — CRUD + promote
6. API `pools.py` — list ready media by `pool_type`
7. Web `/pool/nurture`, `/pool/beta`, `/profiles/nurture`, `/profiles/beta`
8. Tests + harness closeout
