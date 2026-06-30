"""
Orchestrator Agent — coordinates Discover → Evaluate → Learn loop.
Main entry point for agentic workflow.
"""
import json
from datetime import datetime
from pathlib import Path
from agents import discover_agent, evaluate_agent, learn_agent
from services.channel_discovery import save_channel
from utils.logger import get_logger

log = get_logger("orchestrator")

MEMORY_DIR = Path(__file__).parent / "memory"


def _load_strategy() -> dict:
    path = MEMORY_DIR / "strategy.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def run_discovery_cycle(auto_follow_top_n: int = 10) -> dict:
    """
    Run full Discover → Evaluate cycle.
    auto_follow_top_n: automatically save top N recommended channels to DB.
    
    Returns: {
        discovered: int,
        evaluated: int,
        recommended: int,
        auto_followed: int,
        top_channels: list
    }
    """
    log.info("=== Orchestrator: Discovery Cycle Starting ===")
    
    # Step 1: Discover
    log.info("Step 1/3: Discover Agent")
    candidates = discover_agent.run()
    log.info(f"Discovered {len(candidates)} new candidates")
    
    if not candidates:
        log.info("No new candidates — cycle complete")
        return {
            "discovered": 0,
            "evaluated": 0,
            "recommended": 0,
            "auto_followed": 0,
            "top_channels": [],
        }
    
    # Step 2: Evaluate
    log.info("Step 2/3: Evaluate Agent")
    evaluated = evaluate_agent.run(candidates)
    recommended = [
        e for e in evaluated
        if e.get("llm", {}).get("recommendation") == "follow"
    ]
    log.info(f"Evaluated {len(evaluated)} channels, {len(recommended)} recommended")
    
    # Step 3: Auto-follow top N
    auto_followed = 0
    strategy = _load_strategy()
    niche_tag = strategy.get("filters", {}).get("niche_tag", "kpop")
    
    for ch in recommended[:auto_follow_top_n]:
        try:
            save_channel(ch, niche_tag=niche_tag)
            auto_followed += 1
            log.info(f"Auto-followed: {ch.get('name')} (score={ch.get('llm', {}).get('score')})")
        except Exception as e:
            log.error(f"Failed to save {ch.get('name')}: {e}")
    
    log.info(f"Auto-followed {auto_followed}/{len(recommended)} recommended channels")
    log.info("=== Discovery Cycle Complete ===")
    
    return {
        "discovered": len(candidates),
        "evaluated": len(evaluated),
        "recommended": len(recommended),
        "auto_followed": auto_followed,
        "top_channels": recommended[:10],
        "timestamp": datetime.now().isoformat(),
    }


def run_learning_cycle() -> dict:
    """
    Run Learn Agent to analyze outcomes and suggest improvements.
    Returns suggestions for human approval.
    """
    log.info("=== Orchestrator: Learning Cycle Starting ===")
    
    result = learn_agent.run()
    
    log.info("=== Learning Cycle Complete ===")
    return result


def run_full_loop(auto_follow_top_n: int = 10) -> dict:
    """
    Run complete loop: Discover → Evaluate → Learn.
    Returns combined results.
    """
    log.info("=== ORCHESTRATOR: FULL AGENTIC LOOP ===")
    
    # Discovery + Evaluation
    discovery_result = run_discovery_cycle(auto_follow_top_n=auto_follow_top_n)
    
    # Learning (every N cycles or on-demand)
    learning_result = None
    if discovery_result["auto_followed"] > 0:
        log.info("Running learning cycle after successful discoveries")
        learning_result = run_learning_cycle()
    
    log.info("=== FULL LOOP COMPLETE ===")
    
    return {
        "discovery": discovery_result,
        "learning": learning_result,
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
    }


def apply_learning_suggestions(approved_suggestions: dict):
    """
    Apply human-approved learning suggestions to strategy.
    Called from UI after user reviews suggestions.
    """
    log.info("Applying approved suggestions")
    learn_agent.apply_approved_suggestions(approved_suggestions)
    log.info("Strategy updated successfully")


def run_keyword_learning_cycle() -> dict:
    """
    Analyze keyword experiments and suggest weight adjustments.
    
    Returns:
        {
            "status": "completed" | "insufficient_data",
            "analysis": dict,
            "suggestions": dict,
            "action_required": "human_approval" | "none",
            "loop_id": int | None
        }
    """
    log.info("=== Orchestrator: Keyword Learning Cycle Starting ===")
    
    # Analyze keyword experiments
    analysis = learn_agent.analyze_keyword_experiments()
    
    if analysis["status"] == "insufficient_data":
        log.info("Insufficient experiment data")
        return {
            "status": "insufficient_data",
            "message": f"Need at least 5 completed experiments. Current: {analysis['stats']['total']}"
        }
    
    # Generate suggestions (don't auto-apply)
    suggestions = learn_agent.suggest_scoring_adjustments(analysis['patterns'])
    
    # Save to agent_loops table
    conn = get_connection()
    loop_id = conn.execute("""
        INSERT INTO agent_loops 
        (loop_type, discovered, evaluated, learning_status, result_json, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, (
        "keyword_learning",
        0,  # discovered (not applicable)
        len(analysis['stats']['total']),  # evaluated experiments
        "pending_approval" if suggestions['weight_adjustments'] else "no_adjustments",
        json.dumps({"analysis": analysis, "suggestions": suggestions}),
        datetime.now().isoformat(),
        datetime.now().isoformat()
    )).fetchone()['id']
    conn.commit()
    
    log.info(f"Keyword learning cycle complete (loop_id={loop_id})")
    
    return {
        "status": "completed",
        "analysis": analysis,
        "suggestions": suggestions,
        "action_required": "human_approval" if suggestions['weight_adjustments'] else "none",
        "loop_id": loop_id
    }


def get_connection():
    """Import database connection."""
    from database.db import get_connection as db_get_connection
    return db_get_connection()
