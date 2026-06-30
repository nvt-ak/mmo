"""
Integration test for keyword learning cycle.
US-001 Phase 4 validation.
Tests full flow: insert experiments → analyze → suggest → approve → verify strategy.
"""
import pytest
import json
import sys
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.db import get_connection
from agents.orchestrator import run_keyword_learning_cycle
from agents.learn_agent import apply_approved_adjustments, _load_strategy
import agents.learn_agent as learn_agent_module

@pytest.fixture(autouse=True)
def isolated_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(learn_agent_module, "MEMORY_DIR", tmp_path)

@pytest.fixture
def db_conn():
    """Test database connection with sample experiments."""
    conn = get_connection()
    
    # Create test channel
    conn.execute("""
        INSERT OR IGNORE INTO channels 
        (id, name, url, subscribers, avg_views)
        VALUES ('CH_TEST', 'Test Channel', 'https://youtube.com/test', 10000, 5000)
    """)
    conn.commit()
    
    yield conn
    
    # Cleanup
    conn.execute("DELETE FROM keyword_experiments WHERE channel_id = 'CH_TEST'")
    conn.execute("DELETE FROM keyword_patterns")
    conn.execute("DELETE FROM agent_loops WHERE loop_type = 'keyword_learning'")
    conn.execute("DELETE FROM channels WHERE id = 'CH_TEST'")
    conn.commit()
    conn.close()

def test_full_keyword_learning_cycle(db_conn):
    """
    Test complete keyword learning cycle:
    1. Insert 5+ experiments with patterns
    2. Run orchestrator cycle
    3. Verify analysis and suggestions
    4. Apply approved adjustments
    5. Verify strategy updated
    """
    from pathlib import Path
    
    # Ensure memory directory exists
    memory_dir = Path(__file__).parent.parent / "agents" / "memory"
    memory_dir.mkdir(exist_ok=True)
    
    # Step 1: Insert experiments with clear pattern
    # Pattern: "viral" keywords consistently overestimated (false positives)
    for i in range(5):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, channel_subscribers, creator_avg_views,
             suggestion_source, predicted_score, test_status, outcome_type, 
             accuracy, actual_views, actual_engagement, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            exp_id, f"viral trend {i}", "CH_TEST", 10000, 5000,
            "agent_suggested", 75, "failed", "false_positive", 
            0.7, 3000, 8.0  # Underperformed vs prediction
        ))
    
    db_conn.commit()
    
    # Step 2: Run orchestrator cycle
    result = run_keyword_learning_cycle()
    
    # Verify result structure
    assert result['status'] == 'completed'
    assert 'analysis' in result
    assert 'suggestions' in result
    assert 'loop_id' in result
    
    analysis = result['analysis']
    suggestions = result['suggestions']
    
    # Step 3: Verify analysis
    assert analysis['status'] == 'completed'
    assert len(analysis['patterns']) > 0
    assert analysis['stats']['total'] == 5
    
    # Check if pattern detected
    viral_pattern = next(
        (p for p in analysis['patterns'] if p['trait'] == 'contains_viral'),
        None
    )
    assert viral_pattern is not None
    assert viral_pattern['outcome_type'] == 'false_positive'
    assert viral_pattern['count'] >= 3
    
    # Verify suggestions structure
    assert 'weight_adjustments' in suggestions
    assert 'reasoning' in suggestions
    assert isinstance(suggestions['reasoning'], list)
    
    # Step 4: Verify loop saved to database
    loop_record = db_conn.execute("""
        SELECT * FROM agent_loops 
        WHERE id = ? AND loop_type = 'keyword_learning'
    """, (result['loop_id'],)).fetchone()
    
    assert loop_record is not None
    assert loop_record['learning_status'] in ['pending_approval', 'no_adjustments']
    
    result_json = json.loads(loop_record['result_json'])
    assert 'analysis' in result_json
    assert 'suggestions' in result_json
    
    # Step 5: Apply approved adjustments (if any suggested)
    if suggestions['weight_adjustments']:
        apply_approved_adjustments(suggestions['weight_adjustments'])
        
        # Step 6: Verify strategy updated
        strategy = _load_strategy()
        
        assert 'keyword_scoring_weights' in strategy
        for key, value in suggestions['weight_adjustments'].items():
            assert strategy['keyword_scoring_weights'][key] == value
        
        # Verify update history
        assert 'update_history' in strategy
        assert len(strategy['update_history']) > 0
        last_update = strategy['update_history'][-1]
        assert last_update['type'] == 'keyword_scoring_weights'
    
    print(f"✓ Full cycle completed: {result['status']}")
    print(f"✓ Patterns found: {len(analysis['patterns'])}")
    print(f"✓ Suggestions: {len(suggestions['weight_adjustments'])} weight adjustments")

def test_insufficient_data_cycle(db_conn):
    """Test cycle with insufficient data (<5 experiments)."""
    # Insert only 2 experiments
    for i in range(2):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, suggestion_source, predicted_score, 
             test_status, outcome_type, accuracy, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            exp_id, f"keyword {i}", "CH_TEST", "user_manual", 
            70, "success", "true_positive", 0.85
        ))
    
    db_conn.commit()
    
    result = run_keyword_learning_cycle()
    
    assert result['status'] == 'insufficient_data'
    assert 'message' in result
    assert 'Need at least 5' in result['message']

def test_action_required_flag(db_conn):
    """Test action_required flag set correctly."""
    # Insert experiments that will trigger suggestions
    for i in range(5):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, suggestion_source, predicted_score, 
             test_status, outcome_type, accuracy, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            exp_id, f"viral keyword {i}", "CH_TEST", "agent_suggested", 
            80, "failed", "false_positive", 0.6
        ))
    
    db_conn.commit()
    
    result = run_keyword_learning_cycle()
    
    if result['suggestions']['weight_adjustments']:
        assert result['action_required'] == 'human_approval'
    else:
        assert result['action_required'] == 'none'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
