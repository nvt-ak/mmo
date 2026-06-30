# 🚨 Playwright Browser Issue - macOS Sandbox

## Problem

```
TargetClosedError: BrowserType.launch: Target page, context or browser has been closed
```

## Root Cause

macOS sandbox is blocking Playwright Chromium browser from running properly.
The browser launches but is immediately closed by the system security.

## Evidence

Browser launch log shows:
- Browser started: `pid=85658`
- Browser closed immediately: `TargetClosedError`
- This is a macOS sandbox/security restriction

## What Works

✅ OpenAI SDK fix - `proxies` error is fixed  
✅ Playwright browser is installed (chromium-1208)  
✅ tiktok_service.py - updated with executable_path fix  
✅ LLM client - working correctly  

## What Doesn't Work

❌ TikTok checker - Playwright browser blocked by macOS sandbox  
❌ Chrome/Chromium automation in headless mode  

## Solution Options

### Option 1: Disable TikTok Check (Current)
Since Playwright is blocked by macOS sandbox, disable the TikTok checker feature.

### Option 2: Use System Browser
Use a non-headless browser that's already installed on the system:
- Google Chrome (if installed)
- Safari
- Firefox

### Option 3: Run Outside Sandbox
Run the app without macOS sandbox restrictions (not recommended for production).

### Option 4: Use Remote Browser
Use a remote Playwright browser service instead of local.

## Recommended: Disable Feature

For now, disable the TikTok checker and document that it requires:
1. Running outside macOS sandbox
2. OR using a non-Apple Silicon Mac
3. OR using a remote browser service

## Testing Status

| Feature | Status | Notes |
|---------|--------|-------|
| LLM client | ✅ FIXED | No more 'proxies' error |
| OpenAI SDK | ✅ Working | Test passes |
| Settings UI | ✅ UPDATED | LLM config added |
| Daily Digest | ✅ Working | No Playwright needed |
| Discovery Agent | ⚠️ PENDING | Needs OpenAI SDK |
| Evaluate Agent | ⚠️ PENDING | Needs OpenAI SDK |
| Learn Agent | ⚠️ PENDING | Needs OpenAI SDK |
| TikTok Checker | ❌ BLOCKED | macOS sandbox issue |

## To Test (When Sandbox Issue Resolved)

```bash
cd videoscout
source venv/bin/activate

# Test LLM (should work)
python test_llm_client.py

# Test TikTok (should fail until sandbox fixed)
python -c "from services.tiktok_service import check_saturation; print(check_saturation('test'))"
```

## Files Modified

1. `videoscout/agents/skills/llm_skills.py` - Fixed OpenAI client
2. `videoscout/ui/settings.py` - Added LLM config
3. `videoscout/.env` - Updated configuration
4. `videoscout/services/tiktok_service.py` - Updated browser path
5. `videoscout/test_llm_client.py` - Test file created

