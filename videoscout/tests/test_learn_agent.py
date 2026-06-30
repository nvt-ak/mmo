"""
Unit tests for learn_agent keyword experiment functions.
US-001 keyword learning validation.
"""
import pytest
import sys
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.learn_agent import (
    analyze_keyword_experiments,
    suggest_scoring_adjustments,
    apply_approved_adjustments,
    _extract_patterns
)
from database.db import get_connection
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
        VALUES ('CH_TEST', 'Test Channel', 'https://youtube.com/test', 5000, 2000)
    """)
    conn.commit()
    
    yield conn
    
    # Cleanup
    conn.execute("DELETE FROM keyword_experiments WHERE channel_id = 'CH_TEST'")
    conn.execute("DELETE FROM keyword_patterns")
    conn.execute("DELETE FROM channels WHERE id = 'CH_TEST'")
    conn.commit()
    conn.close()

def test_analyze_insufficient_data(db_conn):
    """Test insufficient data returns correct status."""
    result = analyze_keyword_experiments()
    
    assert result['status'] == 'insufficient_data'
    assert result['patterns'] == []
    assert 'total' in result['stats']

def test_extract_patterns_min_occurrences(db_conn):
    """Test pattern extraction requires min 3 occurrences."""
    # Insert 2 experiments with same trait (below threshold)
    for i in range(2):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, channel_subscribers, creator_avg_views,
             suggestion_source, predicted_score, test_status, outcome_type, accuracy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id, "viral dance tutorial", "CH_TEST", 5000, 2000,
            "user_manual", 75, "success", "true_positive", 0.9
        ))
    
    db_conn.commit()
    
    experiments = [dict(e) for e in db_conn.execute(
        "SELECT * FROM keyword_experiments WHERE channel_id = 'CH_TEST'"
    ).fetchall()]
    
    patterns = _extract_patterns(experiments)
    
    # Should be empty (need 3+ occurrences)
    assert len(patterns) == 0

def test_extract_patterns_with_sufficient_data(db_conn):
    """Test pattern extraction with 3+ occurrences."""
    # Insert 3 experiments with "viral" keyword
    for i in range(3):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, channel_subscribers, creator_avg_views,
             suggestion_source, predicted_score, test_status, outcome_type, 
             accuracy, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            exp_id, f"viral keyword {i}", "CH_TEST", 5000, 2000,
            "user_manual", 75, "failed", "false_positive", 0.8
        ))
    
    db_conn.commit()
    
    experiments = [dict(e) for e in db_conn.execute(
        "SELECT * FROM keyword_experiments WHERE channel_id = 'CH_TEST'"
    ).fetchall()]
    
    patterns = _extract_patterns(experiments)
    
    # Should find "contains_viral" + "false_positive" pattern
    assert len(patterns) > 0
    viral_pattern = next((p for p in patterns if p['trait'] == 'contains_viral'), None)
    assert viral_pattern is not None
    assert viral_pattern['count'] >= 3
    assert viral_pattern['outcome_type'] == 'false_positive'

def test_suggest_scoring_adjustments_format(db_conn):
    """Test suggestion format structure."""
    patterns = [
        {
            "trait": "contains_viral",
            "outcome_type": "false_positive",
            "count": 5,
            "confidence": 0.85,
            "avg_predicted": 75,
            "avg_actual": 45
        }
    ]
    
    suggestions = suggest_scoring_adjustments(patterns)
    
    assert 'weight_adjustments' in suggestions
    assert 'reasoning' in suggestions
    assert 'affected_patterns' in suggestions
    assert isinstance(suggestions['reasoning'], list)

def test_weight_adjustment_caps(db_conn):
    """Test weight adjustments capped to 0.5x - 2.0x range."""
    patterns = [
        {
            "trait": "contains_viral",
            "outcome_type": "false_positive",
            "count": 10,
            "confidence": 0.95,
            "avg_predicted": 90,
            "avg_actual": 20
        }
    ]
    
    suggestions = suggest_scoring_adjustments(patterns)
    
    for key, value in suggestions['weight_adjustments'].items():
        assert 0.5 <= value <= 2.0, f"Weight {key}={value} outside allowed range"

def test_insufficient_confidence_no_suggestion(db_conn):
    """Test low confidence patterns don't trigger suggestions."""
    patterns = [
        {
            "trait": "contains_viral",
            "outcome_type": "false_positive",
            "count": 3,
            "confidence": 0.4,  # Below 0.6 threshold
            "avg_predicted": 75,
            "avg_actual": 45
        }
    ]
    
    suggestions = suggest_scoring_adjustments(patterns)
    
    # Should not suggest adjustments for low confidence
    assert len(suggestions['weight_adjustments']) == 0

def test_agent_tracking_separate_accuracy(db_conn):
    """Test agent-suggested experiments tracked separately."""
    # Insert agent-suggested experiments
    for i in range(3):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, suggestion_source, predicted_score, 
             test_status, outcome_type, accuracy, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            exp_id, f"agent keyword {i}", "CH_TEST", "agent_suggested", 
            75, "success", "true_positive", 0.9
        ))
    
    # Insert manual experiments
    for i in range(2):
        exp_id = str(uuid4())
        db_conn.execute("""
            INSERT INTO keyword_experiments 
            (id, keyword, channel_id, suggestion_source, predicted_score, 
             test_status, outcome_type, accuracy, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            exp_id, f"manual keyword {i}", "CH_TEST", "user_manual", 
            70, "failed", "false_positive", 0.5
        ))
    
    db_conn.commit()
    
    result = analyze_keyword_experiments()
    
    assert result['status'] == 'completed'
    assert result['stats']['agent_suggested_count'] == 3
    assert result['stats']['agent_accuracy'] is not None
    # Agent accuracy should be high (0.9)
    assert result['stats']['agent_accuracy'] > 0.8

def test_apply_approved_adjustments(db_conn):
    """Test applying approved weight adjustments."""
    adjustments = {
        "search_volume": 0.9,
        "trend_velocity": 1.1
    }
    
    apply_approved_adjustments(adjustments)
    
    # Load strategy and verify
    from agents.learn_agent import _load_strategy
    strategy = _load_strategy()
    
    assert strategy['keyword_scoring_weights']['search_volume'] == 0.9
    assert strategy['keyword_scoring_weights']['trend_velocity'] == 1.1
    assert len(strategy['update_history']) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
