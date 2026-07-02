# US-054: Keyword Context Builder (Beta Knowledge Graph v1)

## Status

implemented

## Lane

normal

## Product Contract

Build `KeywordContextBuilder` to assemble evidence-backed context for beta LLM scoring.
Extends flat `KnowledgeBase.get_context()` with patterns, niche, and similarity signals.

**Epic:** E09  
**ADR:** `docs/decisions/0012-beta-llm-scoring-knowledge-graph.md`  
**Depends on:** US-012 (performance reports), US-051 (dual-track)  
**Blocks:** US-055

## Acceptance Criteria

- New module `videoscout/core_engine/keyword_context.py` with `KeywordContextBuilder`
- `build(keyword, *, keyword_type="beta", limit=5) -> dict` returns structured JSON:
  - `similar_reports`: recent `performance_reports` (keyword fuzzy match)
  - `aggregates`: avg views, success/failure counts
  - `patterns`: matching `keyword_patterns` (trait overlap, beta-relevant outcomes)
  - `niche`: topics + target_audience from settings
  - `tiktok_hint`: optional pre-fetched stats passthrough slot
- Token budget: serialized context ≤ ~2000 chars (configurable constant)
- `KnowledgeBase.get_context()` delegates to builder for backward compat (text format preserved for scan path)
- Unit tests with fixture reports + patterns; no live LLM

## Out of Scope

- LLM scoring call (US-055)
- Neo4j / embedding index
- Nurture context (beta-only retrieval filter)

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/test_keyword_context.py -v
```
