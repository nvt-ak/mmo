#!/usr/bin/env python3
"""Quick test script for Agentic Loop"""
import sys
sys.path.insert(0, '.')

from agents import discover_agent, evaluate_agent, learn_agent, orchestrator
from database.db import get_connection
import json

print("=== Testing Agentic Loop ===\n")

# 1. Check memory files
print("1. Memory files:")
from pathlib import Path
mem = Path("agents/memory")
for f in ["strategy.json", "channel_outcomes.json", "learnings.json"]:
    exists = (mem / f).exists()
    print(f"   {f}: {'✓' if exists else '✗'}")

# 2. Check DB tables
print("\n2. Database tables:")
conn = get_connection()
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()
required = ["channels", "videos", "channel_outcomes", "agent_loops"]
for t in required:
    exists = any(row[0] == t for row in tables)
    print(f"   {t}: {'✓' if exists else '✗'}")
conn.close()

# 3. Load strategy
print("\n3. Strategy loaded:")
with open("agents/memory/strategy.json") as f:
    strategy = json.load(f)
print(f"   Keywords: {strategy['keywords']}")
print(f"   LLM enabled: {strategy['llm']['enabled']}")

# 4. Test LLM connection (optional - only if 9router running)
print("\n4. Testing LLM connection (9router):")
try:
    from agents.skills.llm_skills import _client
    client = _client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10,
    )
    print(f"   LLM response: ✓ ({resp.choices[0].message.content.strip()})")
except Exception as e:
    print(f"   LLM connection: ✗ ({e})")
    print("   (Start 9router first: npm install -g 9router && 9router)")

print("\n=== Setup Complete ===")
print("\nNext steps:")
print("1. Start 9router: 9router")
print("2. Run app: python main.py")
print("3. Go to 🤖 Agent Loop tab")
print("4. Click 🔍 Run Discovery")
