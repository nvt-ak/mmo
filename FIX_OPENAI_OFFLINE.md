# Fix OpenAI SDK - Hướng Dẫn Khi Có Mạng

## 🐛 Vấn đề
```
Client.__init__() got an unexpected keyword argument 'proxies'
```

## ✅ Giải pháp

### Bước 1: Cài lại OpenAI SDK (khi có mạng)

```bash
cd videoscout
source venv/bin/activate

# Cài lại version mới nhất
pip install --upgrade openai
```

### Bước 2: Verify cài đặt

```bash
python3 << 'PYEOF'
import openai
print(f"OpenAI version: {openai.__version__}")

# Test import
from agents.skills import llm_skills
print("✅ Import successful")

# Test client
config = llm_skills._get_config()
print(f"Config: {config}")

client = llm_skills._client()
print(f"✅ Client created: {type(client)}")
PYEOF
```

### Bước 3: Test LLM call

```bash
python3 << 'PYEOF'
from agents.skills.llm_skills import _call_llm

response = _call_llm("Say hello in 5 words", temperature=0.5, max_tokens=20)
if response:
    print(f"✅ LLM response: {response}")
else:
    print("❌ LLM call failed - check if Codex API is running on port 20218")
PYEOF
```

### Bước 4: Verify Codex API đang chạy

```bash
# Check port 20218
curl -X POST http://localhost:20218/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-71bdfd45ea19211e-wft2jm-561021e2" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

**Kỳ vọng response:**
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      }
    }
  ]
}
```

### Bước 5: Update Settings trong App

1. Mở VideoScout: `python main.py`
2. Go to **⚙️ Settings** tab
3. Kiểm tra **LLM Configuration**:
   - Base URL: `http://localhost:20218/api/v1`
   - API Key: `sk-71bdfd45ea19211e-wft2jm-561021e2`
   - Model: `gpt-4o-mini`
4. Click **💾 Save All Settings**

### Bước 6: Test Agent Loop

1. Go to **🤖 Agent Loop** tab
2. Click **🔍 Run Discovery**
3. Đợi kết quả
4. Check logs không còn lỗi `proxies`

## 📝 Files đã được update:

1. ✅ `videoscout/agents/skills/llm_skills.py` - Fixed client initialization
2. ✅ `videoscout/ui/settings.py` - Added LLM configuration UI
3. ✅ `videoscout/.env` - Added LLM settings

## 🎯 Tóm tắt thay đổi

### Settings UI mới có 4 sections:

1. **YouTube API** - YouTube Data API key
2. **LLM Configuration** - Base URL, API Key, Model (configurable!)
3. **Scanning Configuration** - Auto-scan schedule
4. **Video Filters** - View ranges, subs, days

### LLM Skills updated:

- Không còn hardcode URL/API key
- Đọc từ environment variables
- Better error handling
- No more `proxies` argument

## 🔄 Alternative: Sử dụng OpenAI API trực tiếp

Nếu không muốn dùng Codex local API, có thể dùng OpenAI API:

```bash
# Trong Settings tab:
Base URL: https://api.openai.com/v1
API Key: sk-proj-your-openai-api-key
Model: gpt-4o-mini
```

## 🆘 Troubleshooting

### Lỗi: "Connection refused"
```bash
# Codex API không chạy
# Check process
ps aux | grep codex

# Hoặc check port
lsof -i :20218
```

### Lỗi: "Unauthorized"
```bash
# API key sai
# Check ~/.codex/auth.json
cat ~/.codex/auth.json

# Update trong Settings UI
```

### Lỗi: Still getting 'proxies' error sau khi cài lại
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete

# Restart app
python main.py
```

---

**Khi nào cần fix:** Khi có kết nối internet, chạy lại `pip install openai` trong venv.

