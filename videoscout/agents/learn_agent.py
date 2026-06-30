"""
Learn Agent — analyzes outcomes and suggests strategy improvements.
"""
import json
from datetime import datetime
from pathlib import Path
try:
    from agents.skills.youtube_skills import get_outcomes
    from agents.skills.llm_skills import suggest_keywords, summarize_outcomes
    from utils.logger import get_logger
except ModuleNotFoundError:
    from videoscout.agents.skills.youtube_skills import get_outcomes
    from videoscout.agents.skills.llm_skills import suggest_keywords, summarize_outcomes
    from videoscout.utils.logger import get_logger

log = get_logger("learn")

MEMORY_DIR = Path(__file__).parent / "memory"


def _load_strategy() -> dict:
    path = MEMORY_DIR / "strategy.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_strategy(strategy: dict):
    path = MEMORY_DIR / "strategy.json"
    strategy["last_updated"] = datetime.now().isoformat()
    path.write_text(json.dumps(strategy, indent=2))


def _load_learnings() -> dict:
    path = MEMORY_DIR / "learnings.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"patterns": [], "keyword_suggestions": []}


def _save_learnings(learnings: dict):
    path = MEMORY_DIR / "learnings.json"
    learnings["last_updated"] = datetime.now().isoformat()
    (MEMORY_DIR / "learnings.json").write_text(json.dumps(learnings, indent=2))


def analyze_outcomes() -> dict:
    """
    Analyze historical channel outcomes to identify patterns.
    Returns: {patterns: str, successful_channels: list, failed_channels: list}
    """
    outcomes = get_outcomes()
    if not outcomes:
        log.info("No outcomes to analyze yet")
        return {"patterns": "No data yet", "successful_channels": [], "failed_channels": []}

    successful = [o for o in outcomes if o.get("outcome") == "follow" and o.get("videos_found", 0) > 5]
    failed = [o for o in outcomes if o.get("outcome") == "skip" or o.get("videos_found", 0) == 0]

    log.info(f"Analyzing {len(outcomes)} outcomes: {len(successful)} success, {len(failed)} failed")

    # LLM pattern analysis
    patterns = summarize_outcomes(outcomes[:30])

    return {
        "patterns": patterns,
        "successful_channels": successful,
        "failed_channels": failed,
    }


def suggest_strategy_updates(analysis: dict | None = None) -> dict:
    """
    Suggest updates to strategy based on learnings.
    Returns: {keyword_suggestions: list, filter_adjustments: dict, reasoning: str}
    """
    strategy = _load_strategy()
    if analysis is None:
        analysis = analyze_outcomes()

    if not analysis["successful_channels"]:
        log.info("Not enough successful channels to suggest updates")
        return {"keyword_suggestions": [], "filter_adjustments": {}, "reasoning": "Need more data"}

    # LLM keyword suggestions
    current_kw = strategy.get("keywords", [])
    new_keywords = suggest_keywords(analysis["successful_channels"], current_kw)

    # simple filter adjustment logic
    successful = analysis["successful_channels"]
    avg_subs = sum(ch.get("subscribers", 0) for ch in successful) / len(successful) if successful else 0
    avg_videos = sum(ch.get("videos_found", 0) for ch in successful) / len(successful) if successful else 0

    filter_adjustments = {}
    current_max = strategy.get("filters", {}).get("max_subs", 50000)

    if avg_subs < current_max * 0.3:
        filter_adjustments["max_subs"] = int(current_max * 0.7)
        reasoning = f"Successful channels have avg {avg_subs:.0f} subs — reducing max_subs to {filter_adjustments['max_subs']}"
    else:
        reasoning = "No filter adjustments needed"

    log.info(f"Suggestions: {len(new_keywords)} new keywords, {reasoning}")

    return {
        "keyword_suggestions": new_keywords,
        "filter_adjustments": filter_adjustments,
        "reasoning": reasoning,
    }


def run() -> dict:
    """
    Main learn agent entry point.
    Returns suggestions for human approval.
    """
    log.info("Learn agent starting")

    analysis = analyze_outcomes()
    suggestions = suggest_strategy_updates(analysis)  # reuse, avoid double LLM call

    # save to learnings memory
    learnings = _load_learnings()
    learnings["patterns"].append({
        "timestamp": datetime.now().isoformat(),
        "summary": analysis["patterns"],
        "successful_count": len(analysis["successful_channels"]),
        "failed_count": len(analysis["failed_channels"]),
    })
    learnings["keyword_suggestions"] = suggestions["keyword_suggestions"]
    _save_learnings(learnings)

    log.info("Learn agent complete — suggestions ready for approval")

    return {
        "analysis": analysis,
        "suggestions": suggestions,
        "status": "pending_approval",
    }


def apply_approved_suggestions(approved: dict):
    """
    Apply human-approved strategy updates.
    """
    strategy = _load_strategy()

    if "keywords" in approved:
        new_kw = approved["keywords"]
        existing = set(strategy.get("keywords", []))
        strategy["keywords"] = list(existing | set(new_kw))
        log.info(f"Added keywords: {new_kw}")

    if "filters" in approved:
        strategy["filters"].update(approved["filters"])
        log.info(f"Updated filters: {approved['filters']}")

    if "update_history" not in strategy:
        strategy["update_history"] = []

    strategy["update_history"].append({
        "timestamp": datetime.now().isoformat(),
        "changes": approved,
    })

    _save_strategy(strategy)
    log.info("Strategy updated and saved")


# ============================================================================
# US-001: Keyword Experiment Learning Functions
# ============================================================================

def analyze_keyword_experiments() -> dict:
    """
    Analyze keyword experiment outcomes.
    Returns patterns found from user experiments.
    
    Returns:
        {
            "status": "completed" | "insufficient_data",
            "patterns": list[dict],
            "llm_insights": str | None,
            "stats": dict
        }
    """
    from database.db import get_connection
    
    conn = get_connection()
    
    # Get completed experiments
    experiments = conn.execute("""
        SELECT * FROM keyword_experiments
        WHERE test_status IN ('success', 'failed', 'partial')
        AND reported_at IS NOT NULL
        ORDER BY reported_at DESC
        LIMIT 100
    """).fetchall()
    
    # Convert Row objects to dicts
    experiments = [dict(e) for e in experiments]
    
    if len(experiments) < 5:
        log.info("Not enough experiment data yet")
        return {
            "status": "insufficient_data",
            "patterns": [],
            "stats": {"total": len(experiments)}
        }
    
    # Extract patterns
    patterns = _extract_patterns(experiments)
    
    # Group by outcome type for stats
    true_positives = [e for e in experiments if e['outcome_type'] == 'true_positive']
    false_positives = [e for e in experiments if e['outcome_type'] == 'false_positive']
    false_negatives = [e for e in experiments if e['outcome_type'] == 'false_negative']
    
    # Agent-suggested vs manual tracking
    agent_suggested = [e for e in experiments if e['suggestion_source'] == 'agent_suggested']
    agent_accuracy = (
        sum(e['accuracy'] for e in agent_suggested if e['accuracy']) / len(agent_suggested)
        if agent_suggested else None
    )
    
    log.info(f"Analyzing {len(experiments)} experiments: "
             f"TP={len(true_positives)}, FP={len(false_positives)}, FN={len(false_negatives)}")
    
    # LLM analysis (optional, only if patterns found)
    llm_insights = None
    if patterns:
        try:
            llm_insights = _analyze_experiments_with_llm(experiments[:30])
        except Exception as e:
            log.warning(f"LLM analysis failed: {e}")
    
    return {
        "status": "completed",
        "patterns": patterns,
        "llm_insights": llm_insights,
        "stats": {
            "total": len(experiments),
            "true_positives": len(true_positives),
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives),
            "avg_accuracy": sum(e['accuracy'] for e in experiments if e['accuracy']) / len(experiments),
            "agent_suggested_count": len(agent_suggested),
            "agent_accuracy": agent_accuracy
        }
    }


def _extract_patterns(experiments: list) -> list:
    """
    Extract patterns from experiments using rule-based grouping.
    
    Algorithm:
    1. Group experiments by keyword traits + outcome_type
    2. Require min 3 occurrences to qualify as pattern
    3. Compute confidence based on consistency within group
    4. Return patterns sorted by occurrence_count DESC
    
    Returns:
        List of pattern dicts with trait, outcome_type, count, confidence
    """
    import statistics
    
    MIN_OCCURRENCES = 3
    patterns = []
    
    # Group by (trait, outcome_type)
    groups = {}
    
    for exp in experiments:
        keyword = exp['keyword']
        outcome = exp['outcome_type']
        
        if not outcome:  # Skip in_progress
            continue
        
        # Extract traits
        traits = []
        keyword_lower = keyword.lower()
        
        if 'viral' in keyword_lower:
            traits.append('contains_viral')
        if 'trending' in keyword_lower:
            traits.append('contains_trending')
        
        word_count = len(keyword.split())
        if word_count == 1:
            traits.append('single_word')
        if word_count >= 3:
            traits.append('long_tail')
        
        if 'tutorial' in keyword_lower:
            traits.append('contains_tutorial')
        if 'how to' in keyword_lower:
            traits.append('contains_how_to')
        
        # Group by each trait
        for trait in traits:
            key = (trait, outcome)
            if key not in groups:
                groups[key] = []
            groups[key].append(exp)
    
    # Filter groups with min occurrences and compute stats
    for (trait, outcome), group in groups.items():
        if len(group) < MIN_OCCURRENCES:
            continue
        
        # Compute averages using baseline-normalized scores
        avg_predicted = sum(e['predicted_score'] for e in group) / len(group)
        
        # Use actual_score if available, else compute from views_vs_baseline
        actual_scores = []
        for e in group:
            if e.get('actual_score') is not None:
                actual_scores.append(e['actual_score'])
            elif e.get('views_vs_baseline') is not None and e.get('actual_engagement') is not None:
                # Fallback computation
                from models import compute_actual_score
                score = compute_actual_score(
                    e.get('actual_views', 0),
                    e.get('creator_avg_views', 1),
                    e.get('actual_engagement', 0)
                )
                actual_scores.append(score)
        
        avg_actual = sum(actual_scores) / len(actual_scores) if actual_scores else 0
        
        # Confidence based on consistency (stddev of accuracy)
        accuracies = [e['accuracy'] for e in group if e['accuracy'] is not None]
        if accuracies and len(accuracies) > 1:
            stddev = statistics.stdev(accuracies)
            confidence = max(0.3, 1.0 - stddev)  # Higher consistency = higher confidence
        else:
            confidence = 0.5
        
        pattern = {
            "trait": trait,
            "outcome_type": outcome,
            "count": len(group),
            "examples": [e['keyword'] for e in group[:3]],
            "avg_predicted": round(avg_predicted, 1),
            "avg_actual": round(avg_actual, 1),
            "confidence": round(confidence, 2)
        }
        
        patterns.append(pattern)
    
    # Sort by count DESC, then confidence DESC
    patterns.sort(key=lambda p: (p['count'], p['confidence']), reverse=True)
    
    return patterns


def _analyze_experiments_with_llm(experiments: list) -> str:
    """
    Use LLM to analyze experiment outcomes and suggest insights.
    """
    from agents.skills.llm_skills import get_llm_client
    import os
    
    # Prepare data for LLM
    experiment_summary = []
    for exp in experiments:
        experiment_summary.append({
            "keyword": exp['keyword'],
            "predicted_score": exp['predicted_score'],
            "actual_score": exp.get('actual_score'),
            "outcome": exp['test_status'],
            "reasoning": exp.get('prediction_reasoning')
        })
    
    prompt = f"""
Analyze these keyword experiment outcomes and identify patterns:

{json.dumps(experiment_summary, indent=2)}

Questions:
1. Which keyword patterns consistently overperform predictions?
2. Which keyword patterns consistently underperform?
3. What traits correlate with success/failure?
4. What should we adjust in our keyword evaluation strategy?

Provide actionable insights in 3-4 bullet points.
"""
    
    client = get_llm_client()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return response.choices[0].message.content


def suggest_scoring_adjustments(patterns: list) -> dict:
    """
    Return suggestions for human approval based on patterns.
    Does NOT auto-apply.
    
    Returns:
        {
            "weight_adjustments": dict,
            "reasoning": list[str],
            "affected_patterns": list[dict]
        }
    """
    suggestions = {
        "weight_adjustments": {},
        "reasoning": [],
        "affected_patterns": []
    }
    
    strategy = _load_strategy()
    if "keyword_scoring_weights" not in strategy:
        strategy["keyword_scoring_weights"] = {
            "search_volume": 1.0,
            "trend_velocity": 1.0,
            "competition": 1.0,
            "seasonality": 1.0
        }
    
    current_weights = strategy["keyword_scoring_weights"].copy()
    
    for pattern in patterns:
        trait = pattern["trait"]
        outcome = pattern["outcome_type"]
        count = pattern["count"]
        confidence = pattern["confidence"]
        
        # Only suggest adjustments for high-confidence patterns
        if confidence < 0.6 or count < 3:
            continue
        
        # Pattern: consistently overestimate "viral" keywords
        if trait == "contains_viral" and outcome == "false_positive":
            adjustment = 0.9  # Reduce by 10%
            if "search_volume" not in suggestions["weight_adjustments"]:
                suggestions["weight_adjustments"]["search_volume"] = current_weights["search_volume"] * adjustment
                suggestions["reasoning"].append(
                    f"Reduce search_volume weight: '{trait}' keywords consistently overestimated ({count} occurrences)"
                )
                suggestions["affected_patterns"].append(pattern)
        
        # Pattern: consistently underestimate long-tail keywords
        if trait == "long_tail" and outcome == "false_negative":
            adjustment = 1.1  # Increase by 10%
            if "trend_velocity" not in suggestions["weight_adjustments"]:
                suggestions["weight_adjustments"]["trend_velocity"] = current_weights["trend_velocity"] * adjustment
                suggestions["reasoning"].append(
                    f"Increase trend_velocity weight: '{trait}' keywords consistently underestimated ({count} occurrences)"
                )
                suggestions["affected_patterns"].append(pattern)
    
    # Cap all adjustments to 0.5x - 2.0x range
    for key in suggestions["weight_adjustments"]:
        suggestions["weight_adjustments"][key] = round(
            max(0.5, min(2.0, suggestions["weight_adjustments"][key])),
            2
        )
    
    return suggestions


def apply_approved_adjustments(adjustments: dict):
    """
    Apply human-approved weight adjustments.
    Only called after user clicks "Apply" in UI.
    """
    strategy = _load_strategy()
    
    if "keyword_scoring_weights" not in strategy:
        strategy["keyword_scoring_weights"] = {
            "search_volume": 1.0,
            "trend_velocity": 1.0,
            "competition": 1.0,
            "seasonality": 1.0
        }
    
    # Apply adjustments
    for key, value in adjustments.items():
        strategy["keyword_scoring_weights"][key] = value
        log.info(f"Applied weight adjustment: {key} = {value}")
    
    # Log to update history
    if "update_history" not in strategy:
        strategy["update_history"] = []
    
    strategy["update_history"].append({
        "timestamp": datetime.now().isoformat(),
        "type": "keyword_scoring_weights",
        "changes": adjustments
    })
    
    _save_strategy(strategy)
    log.info("Scoring weight adjustments applied")
