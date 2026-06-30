# Fix LLM Error - Step by Step

## 🐛 Lỗi Hiện Tại

```
Client.__init__() got an unexpected keyword argument 'proxies'
```

**Tại sao có lỗi?**
- OpenAI Python SDK version 1.54.3 không chấp nhận `proxies` argument
- Code có thể đang pass thừa parameters hoặc có cấu hình cũ

---

## 🔧 Solution 1: Fix Code (Recommended)

### Kiểm tra version hiện tại:
```bash
cd videoscout
source venv/bin/activate
python -c "import openai; print(openai.__version__)"
```

### Backup file trước khi sửa:
```bash
cp videoscout/agents/skills/llm_skills.py videoscout/agents/skills/llm_skills.py.backup
```

### Sửa file llm_skills.py:

**Option A: Đơn giản hóa client initialization**

```python
# videoscout/agents/skills/llm_skills.py
# Line 16-17

# BEFORE (có thể có lỗi)
def _client() -> OpenAI:
    return OpenAI(base_url=_BASE_URL, api_key=_API_KEY)

# AFTER (thêm error handling)
def _client() -> OpenAI:
    try:
        return OpenAI(
            base_url=_BASE_URL,
            api_key=_API_KEY,
            timeout=30.0
        )
    except Exception as e:
        log.error(f"Failed to create OpenAI client: {e}")
        raise
```

**Option B: Downgrade OpenAI SDK**

```bash
cd videoscout
source venv/bin/activate
pip uninstall openai -y
pip install openai==1.12.0
```

---

## 🔧 Solution 2: Check 9router

### Kiểm tra 9router có chạy không:

```bash
# Check port 20128
curl http://localhost:20128/v1/models

# Nếu không có response, start 9router:
npm install -g 9router
9router
```

### Test kết nối trực tiếp:

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

**Kỳ vọng response:**
```json
{
  "id": "chatcmpl-xxx",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      }
    }
  ]
}
```

---

## 🔧 Solution 3: Update llm_skills.py (Full Rewrite)

Tạo version mới với error handling tốt hơn:

```python
"""
LLM Skills — 9router OpenAI-compatible client.
Uses local 9router proxy for channel evaluation + keyword suggestions.
"""
import json
import os
from typing import Optional
from openai import OpenAI
from utils.logger import get_logger

log = get_logger("llm")

_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:20128/v1")
_API_KEY = os.getenv("LLM_API_KEY", "sk-local")
_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

def _client() -> OpenAI:
    """Create OpenAI client with proper error handling."""
    try:
        client = OpenAI(
            base_url=_BASE_URL,
            api_key=_API_KEY,
            timeout=30.0,
            max_retries=2
        )
        log.debug(f"LLM client created: base_url={_BASE_URL}, model={_MODEL}")
        return client
    except Exception as e:
        log.error(f"Failed to create LLM client: {e}")
        raise

def _call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 300) -> Optional[str]:
    """
    Generic LLM call wrapper with error handling.
    Returns None on error instead of crashing.
    """
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        return None

def evaluate_channel(channel: dict, videos: list[dict]) -> dict:
    """
    Ask LLM to evaluate a channel for TikTok repost suitability.
    Returns: {score: 0-10, niche_fit: bool, risk: str, recommendation: str, reasoning: str}
    """
    if not videos:
        return {
            "niche_fit": None,
            "risk": "unknown",
            "score": None,
            "recommendation": "skip",
            "reasoning": "No videos to evaluate"
        }
    
    titles = "\n".join(f"- {v['title']} ({v['view_count']:,} views)" for v in videos[:10])
    prompt = f"""You are a TikTok content scout evaluating YouTube channels.

Channel: {channel.get('name', 'Unknown')}
Subscribers: {channel.get('subscribers', 0):,}
Niche tag: {channel.get('niche_tag', 'unknown')}

Recent video titles:
{titles}

Evaluate this channel for TikTok repost suitability:
1. niche_fit (bool): Is content idol/kpop/dance focused?
2. risk (low/medium/high): Copyright risk level?
3. score (0-10): Repost potential?
4. recommendation (follow/skip): Overall recommendation?
5. reasoning (1-2 sentences): Why?

Respond in strict JSON:
{{"niche_fit": true, "risk": "low", "score": 8, "recommendation": "follow", "reasoning": "..."}}"""

    response = _call_llm(prompt, temperature=0.3, max_tokens=300)
    
    if response is None:
        return {
            "niche_fit": None,
            "risk": "unknown",
            "score": None,
            "recommendation": "skip",
            "reasoning": "LLM evaluation failed"
        }
    
    try:
        # Extract JSON from response
        text = response
        if "{" in text:
            text = text[text.index("{"):text.rindex("}") + 1]
        result = json.loads(text)
        log.info(f"LLM evaluate: {channel.get('name')} → score={result.get('score')} rec={result.get('recommendation')}")
        return result
    except Exception as e:
        log.error(f"Failed to parse LLM response: {e}")
        log.debug(f"Raw response: {response}")
        return {
            "niche_fit": None,
            "risk": "unknown",
            "score": None,
            "recommendation": "skip",
            "reasoning": f"Parse error: {str(e)}"
        }

def suggest_keywords(successful_channels: list[dict], current_keywords: list[str]) -> list[str]:
    """
    Ask LLM to suggest new keywords based on what's working.
    """
    if not successful_channels:
        log.warning("No successful channels to analyze")
        return []
    
    channel_summary = "\n".join(
        f"- {ch['name']} ({ch.get('subscribers', 0):,} subs, score={ch.get('score', 0)})"
        for ch in successful_channels[:15]
    )
    current = ", ".join(current_keywords) if current_keywords else "None"
    
    prompt = f"""You are a YouTube/TikTok content strategist.

Current keywords: {current}

Channels performing well:
{channel_summary}

Suggest 3-5 NEW keywords (not duplicates) that could find similar or better channels.
Focus on specific idol names, dance styles, or content types.

Respond as JSON array of strings: ["keyword1", "keyword2", "keyword3"]"""

    response = _call_llm(prompt, temperature=0.7, max_tokens=200)
    
    if response is None:
        return []
    
    try:
        text = response
        if "[" in text:
            text = text[text.index("["):text.rindex("]") + 1]
        suggestions = json.loads(text)
        log.info(f"LLM keyword suggestions: {suggestions}")
        return suggestions
    except Exception as e:
        log.error(f"Failed to parse keyword suggestions: {e}")
        return []

def summarize_outcomes(outcomes: list[dict]) -> str:
    """
    Ask LLM to summarize channel outcomes and identify patterns.
    """
    if not outcomes:
        return "No outcomes to analyze"
    
    summary = "\n".join(
        f"- {o.get('name', '?')}: subs={o.get('subscribers', 0):,}, "
        f"videos_found={o.get('videos_found', 0)}, "
        f"avg_score={o.get('avg_video_score', 0):.1f}, "
        f"outcome={o.get('outcome', 'unknown')}"
        for o in outcomes[:20]
    )
    
    prompt = f"""Analyze these YouTube channel outcomes for TikTok repost strategy:

{summary}

Identify patterns:
1. What channel characteristics correlate with good results?
2. What should we look for more of?
3. What should we avoid?

Respond in 3-5 bullet points, be specific and actionable."""

    response = _call_llm(prompt, temperature=0.4, max_tokens=500)
    
    if response is None:
        return "Pattern analysis failed - LLM unavailable"
    
    return response
```

### Apply fix:

```bash
# Backup original
cp videoscout/agents/skills/llm_skills.py videoscout/agents/skills/llm_skills.py.backup

# Copy new version (paste code above vào file)
nano videoscout/agents/skills/llm_skills.py
# Paste code, save (Ctrl+O, Enter, Ctrl+X)
```

---

## ✅ Verification Steps

### 1. Test Python Import
```bash
cd videoscout
source venv/bin/activate
python3 << 'PYEOF'
from agents.skills import llm_skills
print("✅ Import successful")

# Test client creation
try:
    client = llm_skills._client()
    print(f"✅ Client created: {client}")
except Exception as e:
    print(f"❌ Client creation failed: {e}")
PYEOF
```

### 2. Test LLM Call
```bash
python3 << 'PYEOF'
from agents.skills.llm_skills import _call_llm

response = _call_llm("Say hello in one word", temperature=0.5, max_tokens=10)
if response:
    print(f"✅ LLM response: {response}")
else:
    print("❌ LLM call failed")
PYEOF
```

### 3. Test Full Agent Flow
```bash
python3 << 'PYEOF'
from agents.skills.llm_skills import evaluate_channel

test_channel = {
    "id": "UCtest",
    "name": "Test Channel",
    "subscribers": 5000,
    "niche_tag": "kpop"
}

test_videos = [
    {"title": "NewJeans Hype Boy fancam", "view_count": 100000},
    {"title": "IVE Kitsch dance cover", "view_count": 150000}
]

result = evaluate_channel(test_channel, test_videos)
print(f"✅ Evaluation result: {result}")
PYEOF
```

### 4. Run Agent Loop Again
```bash
# Start app
python main.py

# Go to Agent Loop tab → Click "Run Discovery"
# Check logs for errors
```

---

## 📊 Expected Logs (Success)

```
2026-06-30 22:40:00 [DEBUG] llm: LLM client created: base_url=http://localhost:20128/v1, model=gpt-4o-mini
2026-06-30 22:40:01 [INFO] llm: LLM evaluate: KpopDancer123 → score=8 rec=follow
2026-06-30 22:40:02 [INFO] evaluate:   → score=8 rec=follow risk=low
```

---

## 🆘 Troubleshooting

### Error: "Connection refused"
```bash
# 9router không chạy
9router
```

### Error: "Timeout"
```bash
# Tăng timeout trong .env
echo "LLM_TIMEOUT=60" >> .env
```

### Error: "Invalid JSON response"
```bash
# Check model có hỗ trợ JSON mode không
# Hoặc parse response linh hoạt hơn (đã có trong code mới)
```

### Error: Still getting 'proxies' error
```bash
# Reinstall OpenAI SDK
pip uninstall openai -y
pip install openai==1.12.0

# Or try latest
pip install --upgrade openai
```

---

## 📝 Summary

**3 bước fix chính:**

1. **Update llm_skills.py** với error handling tốt hơn
2. **Verify 9router đang chạy** (`curl localhost:20128/v1/models`)
3. **Test từng bước** trước khi chạy full agent loop

**File cần sửa:**
- `videoscout/agents/skills/llm_skills.py`

**Cách verify:**
- Import test → Client creation test → LLM call test → Full agent test

