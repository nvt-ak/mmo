# LLM 9router Connection Fix — Design Spec

**Date:** 2026-06-30  
**Status:** Approved  
**Problem:** Learn agent fails with `Connection refused` to `localhost:20218`

## Root Cause

- `.env` pointed to Codex local API (`localhost:20218`) which is not running
- 9router is running on `localhost:20128` and responds to `/v1/models`
- `main.py` did not load `.env` at startup — agents could miss config
- Default URLs inconsistent across files (`/v1` vs `/api/v1` vs port 20218)

## Solution

Config-only fix + startup hardening + better error messages.

### 1. Config & Startup

- `.env`: `LLM_BASE_URL=http://localhost:20128/v1`, keep existing 9router API key
- `LLM_MODEL` must be a provider configured in 9router (e.g. `gemini/gemini-3.1-flash-lite-preview` — `gpt-4o-mini` fails without OpenAI credentials)
- `main.py`: call `load_dotenv()` before any agent imports
- Unify defaults in `llm_skills.py` and `settings.py` to port 20128

### 2. LLM Client (`llm_skills.py`)

- Add `_check_llm_available()` — GET `/v1/models` with 3s timeout
- On connection error: log actionable message ("Start 9router: `9router`")
- `summarize_outcomes`: fallback to basic stats when LLM unavailable

### 3. Learn Agent

No logic changes. Requires re-running Discovery after LLM fix to populate `follow` outcomes.

## Files Changed

| File | Change |
|------|--------|
| `.env` | Point to 9router port 20128 |
| `main.py` | Add `load_dotenv()` |
| `agents/skills/llm_skills.py` | Defaults, health check, fallback summary, better errors |
| `ui/settings.py` | Default URL to 20128 |
| `test_llm_client.py` | Update test URL to 20128 |

## Success Criteria

1. Learn agent completes without connection error when 9router running
2. `summarize_outcomes` returns LLM analysis or stats fallback
3. `.env` loaded at app startup without opening Settings first
4. Clear log message when 9router not running

## Out of Scope

- Auto-detect fallback across ports
- Settings UI "Test Connection" button
- Changing learn agent success threshold
