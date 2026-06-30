"""
LLM Skills — OpenAI-compatible client for 9router local API.
Uses http_client directly to avoid 'proxies' argument issues.
"""
import json
import os
from typing import Optional
from openai import OpenAI
from utils.logger import get_logger

log = get_logger("llm")

DEFAULT_BASE_URL = "http://localhost:20128/v1"

def _get_config() -> dict:
    """Read LLM config from environment."""
    return {
        "base_url": os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL),
        "api_key": os.getenv("LLM_API_KEY", "sk-local"),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    }

def _check_llm_available() -> bool:
    """Quick health check against the configured LLM endpoint."""
    config = _get_config()
    try:
        import httpx
        url = config["base_url"].rstrip("/") + "/models"
        resp = httpx.get(url, timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False

def _client() -> OpenAI:
    """Create OpenAI client with explicit http_client to avoid proxies issue."""
    config = _get_config()
    try:
        import httpx
        # Create httpx client explicitly without proxies
        httpx_client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "VideoScout/1.0"}
        )

        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            http_client=httpx_client,
        )
        log.debug(f"LLM client created: base_url={config['base_url']}, model={config['model']}")
        return client
    except Exception as e:
        log.error(f"Failed to create LLM client: {e}")
        raise

def _call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 300) -> Optional[str]:
    """
    Generic LLM call wrapper with error handling.
    Returns None on error instead of crashing.
    """
    config = _get_config()
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        config = _get_config()
        log.error(
            f"LLM call failed: {e}. "
            f"Check 9router is running at {config['base_url']} (run: 9router)"
        )
        return None

def _load_recent_patterns(n: int = 3) -> str:
    """Load the most recent successful pattern summaries from learnings.json."""
    try:
        from pathlib import Path
        path = Path(__file__).parent.parent / "memory" / "learnings.json"
        if not path.exists():
            return ""
        data = json.loads(path.read_text())
        patterns = [
            p for p in data.get("patterns", [])
            if p.get("successful_count", 0) > 0 and "failed" not in p.get("summary", "").lower()
        ]
        if not patterns:
            return ""
        recent = patterns[-n:]
        summaries = "\n\n".join(f"[{p['timestamp'][:10]}] {p['summary']}" for p in recent)
        return f"\n\nPast learning insights (use to guide evaluation):\n{summaries}"
    except Exception:
        return ""


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
    past_insights = _load_recent_patterns(n=3)

    prompt = f"""You are a TikTok content scout evaluating YouTube channels.

Channel: {channel.get('name', 'Unknown')}
Subscribers: {channel.get('subscribers', 0):,}
Niche tag: {channel.get('niche_tag', 'unknown')}

Recent video titles:
{titles}{past_insights}

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

def _stats_fallback(outcomes: list[dict]) -> str:
    """Rule-based pattern summary when LLM is unavailable."""
    if not outcomes:
        return "No outcomes to analyze"

    total = len(outcomes)
    skips = sum(1 for o in outcomes if o.get("outcome") == "skip")
    follows = sum(1 for o in outcomes if o.get("outcome") == "follow")
    subs = [o.get("subscribers", 0) for o in outcomes if o.get("subscribers")]
    scores = [o.get("avg_video_score", 0) for o in outcomes if o.get("avg_video_score")]

    lines = [
        f"Analyzed {total} channels: {follows} follow, {skips} skip (LLM unavailable — stats only)",
    ]
    if subs:
        lines.append(f"Subscriber range: {min(subs):,} – {max(subs):,} (avg {sum(subs)//len(subs):,})")
    if scores:
        lines.append(f"Avg video score range: {min(scores):.0f} – {max(scores):.0f}")
    if follows == 0:
        lines.append("No successful channels yet — re-run Discovery with LLM enabled")
    return "\n".join(f"- {l}" for l in lines)

def summarize_outcomes(outcomes: list[dict]) -> str:
    """
    Ask LLM to summarize channel outcomes and identify patterns.
    """
    if not outcomes:
        return "No outcomes to analyze"

    if not _check_llm_available():
        config = _get_config()
        log.warning(f"LLM unavailable at {config['base_url']} — using stats fallback")
        return _stats_fallback(outcomes)

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
        return _stats_fallback(outcomes)

    return response
