"""
Data models for VideoScout.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class KeywordExperiment:
    """
    Keyword experiment tracking model.
    Maps to keyword_experiments table.
    """
    id: str
    keyword: str
    channel_id: Optional[str]
    
    # Baseline context
    channel_subscribers: Optional[int]
    creator_avg_views: Optional[int]
    views_vs_baseline: Optional[float]
    
    # Suggestion tracking
    suggestion_source: str  # 'agent_suggested' | 'user_manual'
    agent_suggested_score: Optional[int]
    
    # Prediction
    predicted_score: int
    prediction_reasoning: Optional[str]
    predicted_at: str
    
    # Actual results
    actual_views: Optional[int]
    actual_engagement: Optional[float]
    actual_retention: Optional[float]
    actual_score: Optional[float]  # Computed field
    test_status: str  # 'in_progress' | 'success' | 'failed' | 'partial'
    
    # User feedback
    user_rating: Optional[int]
    user_comments: Optional[str]
    
    # Computed metrics
    accuracy: Optional[float]
    outcome_type: Optional[str]  # 'true_positive' | 'false_positive' | 'true_negative' | 'false_negative'
    
    # Metadata
    keyword_traits: Optional[str]  # JSON array
    account_label: Optional[str]
    reported_at: Optional[str]
    created_at: str
    
    @staticmethod
    def from_db_row(row) -> 'KeywordExperiment':
        """Create from sqlite Row object."""
        return KeywordExperiment(
            id=row['id'],
            keyword=row['keyword'],
            channel_id=row['channel_id'],
            channel_subscribers=row['channel_subscribers'],
            creator_avg_views=row['creator_avg_views'],
            views_vs_baseline=row['views_vs_baseline'],
            suggestion_source=row['suggestion_source'],
            agent_suggested_score=row['agent_suggested_score'],
            predicted_score=row['predicted_score'],
            prediction_reasoning=row['prediction_reasoning'],
            predicted_at=row['predicted_at'],
            actual_views=row['actual_views'],
            actual_engagement=row['actual_engagement'],
            actual_retention=row['actual_retention'],
            actual_score=row['actual_score'],
            test_status=row['test_status'],
            user_rating=row['user_rating'],
            user_comments=row['user_comments'],
            accuracy=row['accuracy'],
            outcome_type=row['outcome_type'],
            keyword_traits=row['keyword_traits'],
            account_label=row['account_label'],
            reported_at=row['reported_at'],
            created_at=row['created_at']
        )


@dataclass
class KeywordPattern:
    """
    Learned keyword pattern model.
    Maps to keyword_patterns table.
    """
    id: str
    pattern_type: str  # 'overestimate' | 'underestimate' | 'surprise'
    keyword_trait: str  # 'contains_viral' | 'long_tail' | 'single_word' | etc.
    outcome_type: str  # 'true_positive' | 'false_positive' | etc.
    
    insight: str
    reasoning: Optional[str]
    
    # Evidence
    example_keywords: Optional[str]  # JSON array
    occurrence_count: int
    avg_predicted: Optional[float]
    avg_actual: Optional[float]
    
    # Adjustment
    suggested_adjustment: Optional[str]  # JSON: {"search_volume": 0.9}
    experiment_ids: Optional[str]  # JSON array of experiment IDs
    
    confidence: float
    discovered_at: str
    last_seen_at: str
    
    @staticmethod
    def from_db_row(row) -> 'KeywordPattern':
        """Create from sqlite Row object."""
        return KeywordPattern(
            id=row['id'],
            pattern_type=row['pattern_type'],
            keyword_trait=row['keyword_trait'],
            outcome_type=row['outcome_type'],
            insight=row['insight'],
            reasoning=row['reasoning'],
            example_keywords=row['example_keywords'],
            occurrence_count=row['occurrence_count'],
            avg_predicted=row['avg_predicted'],
            avg_actual=row['avg_actual'],
            suggested_adjustment=row['suggested_adjustment'],
            experiment_ids=row['experiment_ids'],
            confidence=row['confidence'],
            discovered_at=row['discovered_at'],
            last_seen_at=row['last_seen_at']
        )


# Formula constants
PREDICTED_SUCCESS_THRESHOLD = 60


def compute_actual_score(
    actual_views: int,
    creator_avg_views: int,
    actual_engagement: float,
    actual_retention: Optional[float] = None
) -> float:
    """
    Compute 0-100 score from actual performance.
    
    Formula (locked 2026-06-30):
    - views_component = min(75, views_vs_baseline * 35)
    - engagement_component = min(25, engagement% * 1.2)
    - retention_component = min(10, retention% * 0.2) if provided
    - actual_score = sum, capped [0, 100]
    
    Example:
        actual_views=4500, creator_avg=2000, engagement=12%
        → views_vs_baseline=2.25
        → views_component = min(75, 2.25*35) = 75
        → engagement_component = min(25, 12*1.2) = 14.4
        → actual_score = 89.4 (rounds to 89.4)
    """
    views_vs_baseline = actual_views / creator_avg_views if creator_avg_views > 0 else 0.0
    
    views_component = min(75.0, views_vs_baseline * 35.0)
    engagement_component = min(25.0, actual_engagement * 1.2)
    
    score = views_component + engagement_component
    
    if actual_retention is not None:
        score += min(10.0, actual_retention * 0.2)
    
    return round(min(100.0, max(0.0, score)), 1)


def classify_outcome(predicted_score: int, test_status: str) -> Optional[str]:
    """
    Classify experiment outcome type.
    
    Logic (locked 2026-06-30):
    - predicted_success = predicted_score >= 60
    - actual_success = test_status == 'success'
    - partial counts as fail (conservative)
    - in_progress returns None
    
    Returns:
        'true_positive' | 'false_positive' | 'true_negative' | 'false_negative' | None
    """
    if test_status == 'in_progress':
        return None
    
    predicted_success = predicted_score >= PREDICTED_SUCCESS_THRESHOLD
    actual_success = test_status == 'success'
    
    if test_status == 'partial':
        actual_success = False  # Conservative
    
    if predicted_success and actual_success:
        return 'true_positive'
    if predicted_success and not actual_success:
        return 'false_positive'
    if not predicted_success and actual_success:
        return 'false_negative'
    return 'true_negative'


def compute_accuracy(predicted_score: int, actual_score: float) -> float:
    """
    Compute accuracy as: 1 - |predicted - actual| / 100
    
    Returns value in [0, 1].
    """
    return max(0.0, 1.0 - abs(predicted_score - actual_score) / 100.0)
