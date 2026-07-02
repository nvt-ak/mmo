"""
Learning Agent - Analyzes outcomes and updates strategy.
Ported from videoscout/agents/learn_agent.py with async support.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import numpy as np

from videoscout.db.models import SuggestionModel, LearningEventModel
from videoscout.db import get_session


class LearningAgent:
    """Learning agent that analyzes rejection/report patterns and updates strategy."""
    
    def __init__(self, db_session=None):
        self.db = db_session or get_session()
    
    def analyze_rejection_patterns(self, days: int = 30) -> List[Dict]:
        """
        Analyze rejection events to identify patterns.
        
        Returns list of patterns sorted by frequency.
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        # Query rejections
        rejections = self.db.query(LearningEventModel).filter(
            LearningEventModel.type == 'rejection',
            LearningEventModel.timestamp >= cutoff
        ).all()
        
        if not rejections:
            return []
        
        # Group by reason
        patterns = defaultdict(lambda: {
            'reason': None,
            'frequency': 0,
            'keywords': [],
            'avg_specificity': 0,
            'avg_saturation': 0,
            'avg_relevance': 0
        })
        
        for event in rejections:
            reason = event.reason or 'unknown'
            patterns[reason]['reason'] = reason
            patterns[reason]['frequency'] += 1
            
            if event.scores:
                scores = event.scores
                patterns[reason]['keywords'].append(event.keyword)
                patterns[reason]['avg_specificity'] += scores.get('specificity', 0)
                patterns[reason]['avg_saturation'] += scores.get('saturation', 0)
                patterns[reason]['avg_relevance'] += scores.get('relevance', 0)
        
        # Calculate averages
        result = []
        for reason, data in patterns.items():
            count = data['frequency']
            result.append({
                'reason': reason,
                'frequency': count,
                'common_characteristics': {
                    'avg_specificity': data['avg_specificity'] / count if count > 0 else 0,
                    'avg_saturation': data['avg_saturation'] / count if count > 0 else 0,
                    'avg_relevance': data['avg_relevance'] / count if count > 0 else 0,
                    'typical_word_count': np.mean([len(k.split()) for k in data['keywords']]) if data['keywords'] else 0,
                    'common_terms': self._extract_common_terms(data['keywords'])
                },
                'suggested_action': self._infer_action(reason, data)
            })
        
        # Sort by frequency
        return sorted(result, key=lambda x: x['frequency'], reverse=True)
    
    def _extract_common_terms(self, keywords: List[str]) -> List[str]:
        """Extract common words from a list of keywords."""
        from collections import Counter
        words = []
        stop_words = {'for', 'with', 'and', 'in', 'on', 'at', 'to', 'a', 'the'}
        
        for keyword in keywords:
            words.extend([w.lower() for w in keyword.split() if w.lower() not in stop_words])
        
        common = Counter(words).most_common(5)
        return [word for word, count in common if count >= 2]
    
    def _infer_action(self, reason: str, data: Dict) -> str:
        """Infer action based on rejection pattern."""
        avg_specificity = data['avg_specificity'] / data['frequency'] if data['frequency'] > 0 else 0
        avg_saturation = data['avg_saturation'] / data['frequency'] if data['frequency'] > 0 else 0
        
        if reason == 'too_broad' and avg_specificity < 0.5:
            return "Increase specificity weight by 10%"
        elif reason == 'too_competitive' and avg_saturation < 0.4:
            return "Increase saturation threshold to 0.5"
        elif reason == 'off_topic':
            return "Review niche definition - keywords may be out of scope"
        else:
            return "No automatic action - manual review recommended"
    
    def analyze_success_patterns(
        self,
        days: int = 30,
        *,
        keyword_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Analyze successful keyword reports to identify patterns.
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        query = self.db.query(LearningEventModel).filter(
            LearningEventModel.type == 'report',
            LearningEventModel.outcome == 'success',
            LearningEventModel.timestamp >= cutoff
        )
        if keyword_type:
            query = query.join(
                SuggestionModel,
                LearningEventModel.suggestion_id == SuggestionModel.id,
            ).filter(SuggestionModel.keyword_type == keyword_type)

        reports = query.order_by(LearningEventModel.actual_views.desc()).limit(50).all()
        
        if len(reports) < 3:
            return []  # Not enough data
        
        # Cluster by characteristics
        clusters = defaultdict(list)
        for event in reports:
            scores = event.scores or {}
            key = (
                round(scores.get('specificity', 0), 1),
                round(scores.get('saturation', 0), 1)
            )
            clusters[key].append(event)
        
        result = []
        for key, cluster in clusters.items():
            avg_views = np.mean([e.actual_views or 0 for e in cluster])
            avg_engagement = np.mean([
                e.actual_engagement_rate or 0 for e in cluster
            ])
            avg_specificity = np.mean([
                (e.scores or {}).get('specificity', 0) for e in cluster
            ])
            avg_saturation = np.mean([
                (e.scores or {}).get('saturation', 0) for e in cluster
            ])
            
            result.append({
                'keyword_example': cluster[0].keyword,
                'avg_views': int(avg_views),
                'avg_engagement_rate': avg_engagement,
                'common_characteristics': {
                    'word_count': int(np.mean([len(e.keyword.split()) for e in cluster])),
                    'avg_specificity': avg_specificity,
                    'avg_saturation': avg_saturation,
                    'tiktok_status': 'low' if avg_saturation > 0.6 else 'moderate'
                },
                'replication_strategy': (
                    f"Generate more {'long-tail' if avg_specificity > 0.7 else 'mid-tail'} "
                    f"keywords with {'low' if avg_saturation > 0.6 else 'moderate'} competition"
                )
            })
        
        return sorted(result, key=lambda x: x['avg_views'], reverse=True)
    
    def calibrate_weights(self, report_event: Dict) -> List[Dict]:
        """
        Adjust scoring weights based on prediction error.
        
        Returns list of weight adjustments made.
        """
        from videoscout.schemas import ComponentScores
        
        # Get current weights from settings
        weights = ComponentScores(
            relevance=0.30,
            specificity=0.25,
            saturation=0.25,
            trend=0.10,
            video_performance=0.10
        ).model_dump()
        
        # Calculate prediction error
        predicted = report_event.get('predicted_score', 0)
        actual = report_event.get('actual_engagement_rate', 0)
        
        # Calculate error per component (simplified)
        component_errors = {
            'relevance': abs(weights['relevance'] - actual),
            'specificity': abs(weights['specificity'] - actual),
            'saturation': abs(weights['saturation'] - actual),
            'video_performance': abs(weights['video_performance'] - actual)
        }
        
        # Find worst predictor
        worst_factor = max(component_errors, key=component_errors.get)
        
        # Reduce weight of worst predictor
        new_weight = max(0.05, weights[worst_factor] - 0.05)
        adjustment = weights[worst_factor] - new_weight
        
        adjustments = [{
            'factor': worst_factor,
            'old_value': weights[worst_factor],
            'new_value': new_weight,
            'reason': f"Highest prediction error ({component_errors[worst_factor]:.2f})",
            'confidence': 0.7
        }]
        
        # Redistribute to better predictors
        better_factors = sorted(component_errors.items(), key=lambda x: x[1])[:2]
        increase_per = adjustment / len(better_factors)
        
        for factor, _ in better_factors:
            adjustments.append({
                'factor': factor,
                'old_value': weights[factor],
                'new_value': weights[factor] + increase_per,
                'reason': "Better predictor - redistributing weight",
                'confidence': 0.7
            })
        
        return adjustments
    
    def generate_similar_keywords(
        self,
        success_keyword: str,
        scores: Dict[str, float]
    ) -> List[str]:
        """
        Generate variations of a successful keyword using LLM.
        
        Returns list of new keyword suggestions.
        """
        # For Phase 1: Generate simple variations
        # In production, this would call an LLM
        
        variations = [
            f"{success_keyword} tips",
            f"{success_keyword} tutorial",
            f"how to {success_keyword}",
            f"{success_keyword} for beginners",
            f"advanced {success_keyword}"
        ]
        
        return variations
