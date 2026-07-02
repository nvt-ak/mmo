"""
Suggestion Engine - Core keyword extraction and scoring logic.
Implements Section 2: Multi-factor scoring with 5 criteria.
"""
import re
import json
import inspect
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict

from openai import OpenAI
import logging

from videoscout.services.youtube import get_youtube_service
from videoscout.services.tiktok import get_tiktok_service
from videoscout.db.models import SuggestionModel
from videoscout.db import get_session
from videoscout.core_engine.knowledge_base import KnowledgeBase
from videoscout.schemas import ComponentScores, SuggestedByEntry


logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Suggestion engine that extracts keywords from YouTube videos
    and scores them using multi-factor analysis.
    """
    
    def __init__(
        self,
        llm_client: Optional[OpenAI] = None,
        db_session = None,
        llm_model: str = "gpt-4o"
    ):
        self.llm = llm_client or OpenAI()
        self.llm_model = llm_model
        self.youtube = get_youtube_service()
        self.tiktok = get_tiktok_service()
        self.db = db_session or get_session()
    
    async def extract_keywords(
        self,
        video_context: Dict
    ) -> List[Dict]:
        """
        Extract keyword candidates from video content using LLM.
        
        Args:
            video_context: {
                "video_id": str,
                "channel_id": str,
                "title": str,
                "description": str,
                "tags": List[str],
                "transcript": List[{"text": str, "start": float}],
                "view_count": int,
                "like_count": int,
                "comment_count": int
            }
        
        Returns:
            List of keyword candidates with confidence scores
        """
        # Combine all text sources
        full_text = "\n".join([
            f"Title: {video_context['title']}",
            f"Description: {video_context['description']}",
            *[
                f"[{seg.get('start', 0):.0f}s] {seg['text']}"
                for seg in video_context.get('transcript', [])[:50]  # Limit to first 50 segments
            ]
        ])

        # Reuse recent report outcomes for nearby terms to bias generation.
        kb = KnowledgeBase(self.db)
        niche_context = video_context.get("niche") or ", ".join(video_context.get("tags", [])[:5])
        kb_context_chunks = []
        for term in [niche_context, *video_context.get("tags", [])[:3]]:
            if not term:
                continue
            context_snippet = kb.get_context(term, limit=3)
            if context_snippet:
                kb_context_chunks.append(context_snippet)
        kb_context = "\n\n".join(dict.fromkeys(kb_context_chunks))
        kb_section = ""
        if kb_context:
            kb_section = f"""
Knowledge base context (recent TikTok outcomes):
{kb_context}
"""
        
        prompt = f"""
Analyze this Vietnamese/English content from a YouTube video and extract 10-20 potential TikTok keyword ideas.

Video context:
- Title: {video_context['title']}
- Channel ID: {video_context['channel_id']}
- Tags: {', '.join(video_context.get('tags', []))}
- Views: {video_context.get('view_count', 0):,}
- Likes: {video_context.get('like_count', 0):,}
- Comments: {video_context.get('comment_count', 0):,}

Transcript (last 5000 chars):
{full_text[-5000:]}
{kb_section}

Requirements:
1. Focus on specific, actionable phrases (2-5 words)
2. Prefer long-tail keywords over broad terms
3. Mix of: transcript quotes, conceptual themes, how-to phrases, problem-solution
4. Avoid: single words, generic terms like "tips"/"tutorial"/"guide", brand names
5. Prioritize phrases that would work well on TikTok for short-form content

Output format (JSON object):
{{"keywords": [
  {{"keyword": "phrase in Vietnamese or English", "rationale": "why this could work", "source": "transcript|title|description|tags|theme", "confidence": 0.0-1.0}}
]}}

Constraints:
- No markdown formatting in response
- Valid JSON only
- Confidence score based on relevance and specificity
"""
        
        try:
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            candidates_data = response.choices[0].message.content
            parsed = json.loads(candidates_data)
            candidates = parsed.get('keywords', parsed) if isinstance(parsed, dict) else parsed
            
            # Filter and validate
            filtered = []
            for c in candidates:
                keyword = c.get('keyword', '').lower().strip()
                
                if (
                    len(keyword) >= 2 and  # Min 2 chars
                    len(keyword.split()) >= 2 and  # Min 2 words
                    len(keyword) <= 50 and  # Max 50 chars
                    c.get('confidence', 0) > 0.4  # Min 40% confidence
                ):
                    filtered.append({
                        'keyword': keyword,
                        'source': c.get('source', 'theme'),
                        'llm_confidence': c.get('confidence', 0.5),
                        'rationale': c.get('rationale', ''),
                        'video_id': video_context['video_id'],
                        'channel_id': video_context['channel_id']
                    })
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def calculate_relevance(
        self,
        keyword: str,
        video_context: Dict,
        niche_topics: List[str]
    ) -> float:
        """
        Calculate relevance score using embedding similarity.
        
        Returns: 0.0-1.0
        """
        # Simple keyword matching for Phase 1
        # In production: use sentence-transformers
        
        keyword_lower = keyword.lower()
        text_to_check = (
            f"{video_context['title']} {video_context['description']} "
            f"{' '.join(video_context.get('tags', []))}"
        ).lower()
        
        # Score components
        title_match = 0.3 if keyword_lower in video_context['title'].lower() else 0
        tag_match = 0.2 if any(
            keyword_lower in tag.lower() for tag in video_context.get('tags', [])
        ) else 0
        text_match = 0.2 if keyword_lower in text_to_check else 0
        
        # Niche match (simplified)
        niche_match = 0.3 if any(
            niche.lower() in keyword_lower for niche in niche_topics
        ) else 0
        
        score = title_match + tag_match + text_match + niche_match
        
        # Bonus for keyword appearing in transcript
        transcript = ' '.join(
            seg.get('text', '') for seg in video_context.get('transcript', [])
        ).lower()
        if keyword_lower in transcript:
            score += 0.2
        
        return min(1.0, score)
    
    def calculate_specificity(self, keyword: str) -> float:
        """
        Calculate specificity score based on word count and generic terms.
        
        Returns: 0.0-1.0
        """
        words = keyword.split()
        length = len(words)
        
        # Base score by word count
        if length == 1:
            score = 0.1  # Too broad
        elif length == 2:
            score = 0.4
        elif length == 3:
            score = 0.7
        elif length == 4:
            score = 0.9
        else:  # 5+ words
            score = 1.0
        
        # Penalty for generic terms
        generic_terms = [
            'tips', 'tricks', 'tutorial', 'guide', 'how to',
            'best', 'top', 'ultimate', 'complete'
        ]
        if any(term in keyword.lower() for term in generic_terms):
            score *= 0.7
        
        return min(1.0, score)
    
    async def calculate_saturation(self, keyword: str) -> Dict[str, Any]:
        """
        Calculate TikTok saturation score.
        
        Returns:
            {
                "score": float,
                "tiktok_stats": {
                    "video_count_7d": int,
                    "avg_views": float,
                    "avg_likes": float,
                    "avg_comments": float,
                    "saturation_tier": "fresh" | "moderate" | "saturated"
                }
            }
        """
        try:
            result = self.tiktok.search_videos(keyword, period='7d', limit=50)
            if inspect.isawaitable(result):
                result = await result

            count = result.get('total_count', 0)

            avg_views = float(result.get('avg_views', 0.0) or 0.0)
            videos = result.get('videos') or []

            def _avg_metric(field: str) -> float:
                values = [
                    float(video.get(field, 0) or 0)
                    for video in videos
                    if video.get(field) is not None
                ]
                if not values:
                    return 0.0
                return sum(values) / len(values)

            avg_likes = float(result.get('avg_likes', _avg_metric('like_count')) or 0.0)
            avg_comments = float(result.get('avg_comments', _avg_metric('comment_count')) or 0.0)

            # Saturation tiers for operator-facing context.
            if count <= 10:
                score = 1.0
                tier = 'fresh'
            elif count <= 30:
                score = 0.7
                tier = 'moderate'
            else:
                score = 0.3
                tier = 'saturated'

            # Bonus: high views but low count = opportunity
            if count < 20 and avg_views > 10000:
                score = min(1.0, score + 0.2)

            return {
                'score': score,
                'tiktok_stats': {
                    'video_count_7d': int(count),
                    'avg_views': round(avg_views, 2),
                    'avg_likes': round(avg_likes, 2),
                    'avg_comments': round(avg_comments, 2),
                    'saturation_tier': tier
                }
            }

        except Exception as e:
            logger.error(f"Error checking TikTok saturation: {e}")
            return {
                'score': 0.5,  # Neutral fallback
                'tiktok_stats': {
                    'video_count_7d': 0,
                    'avg_views': 0.0,
                    'avg_likes': 0.0,
                    'avg_comments': 0.0,
                    'saturation_tier': 'moderate'
                }
            }
    
    def calculate_video_performance(self, video_context: Dict) -> float:
        """
        Calculate score based on source video's engagement.
        
        Returns: 0.0-1.0
        """
        views = video_context.get('view_count', 0)
        likes = video_context.get('like_count', 0)
        comments = video_context.get('comment_count', 0)
        
        if views == 0:
            return 0.5
        
        # Engagement rate (typical: 2-5%)
        engagement_rate = (likes + comments * 2) / views
        
        # Normalize to 0-1 range
        normalized = min(1.0, engagement_rate / 0.05)
        
        return normalized
    
    async def score_keywords(
        self,
        candidates: List[Dict],
        video_context: Dict,
        weights: Dict[str, float] = None,
        niche_topics: List[str] = None
    ) -> List[Dict]:
        """
        Score keyword candidates using multi-factor analysis.
        
        Args:
            candidates: List of keyword candidates from extract_keywords()
            video_context: Video metadata
            weights: Factor weights (defaults: relevance=0.30, specificity=0.25, 
                     saturation=0.25, trend=0.10, video_performance=0.10)
            niche_topics: User's niche topics for relevance scoring
        
        Returns:
            List of scored keywords sorted by final_score
        """
        if weights is None:
            weights = {
                'relevance': 0.30,
                'specificity': 0.25,
                'saturation': 0.25,
                'trend': 0.10,
                'video_performance': 0.10
            }
        
        if niche_topics is None:
            niche_topics = ['technology', 'business', 'self-improvement']
        
        # Calculate all scores
        scored = []
        for candidate in candidates:
            keyword = candidate['keyword']
            
            relevance = self.calculate_relevance(keyword, video_context, niche_topics)
            specificity = self.calculate_specificity(keyword)
            saturation_data = await self.calculate_saturation(keyword)
            saturation = saturation_data['score']
            tiktok_stats = saturation_data['tiktok_stats']
            trend = 0.5  # Placeholder for Phase 1
            video_perf = self.calculate_video_performance(video_context)
            
            # Weighted sum
            final_score = (
                relevance * weights['relevance'] +
                specificity * weights['specificity'] +
                saturation * weights['saturation'] +
                trend * weights['trend'] +
                video_perf * weights['video_performance']
            )
            
            # Determine TikTok status
            tier_to_status = {
                'fresh': 'low',
                'moderate': 'moderate',
                'saturated': 'saturated'
            }
            tiktok_status = tier_to_status.get(tiktok_stats['saturation_tier'], 'moderate')
            
            scored.append({
                'keyword': keyword,
                'final_score': final_score,
                'component_scores': {
                    'relevance': round(relevance, 3),
                    'specificity': round(specificity, 3),
                    'saturation': round(saturation, 3),
                    'trend': round(trend, 3),
                    'video_performance': round(video_perf, 3)
                },
                'tiktok_status': tiktok_status,
                'tiktok_count': tiktok_stats['video_count_7d'],
                'tiktok_stats': tiktok_stats,
                'video_id': candidate['video_id'],
                'channel_id': candidate['channel_id'],
                'source': candidate['source'],
                'llm_confidence': candidate['llm_confidence'],
                'rationale': candidate['rationale']
            })
        
        # Sort and filter
        scored.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Filter by minimum threshold
        min_threshold = 0.4
        filtered = [s for s in scored if s['final_score'] >= min_threshold]
        
        # Return top 20
        return filtered[:20]
    
    async def process_video(self, video_id: str) -> List[Dict]:
        """
        Complete pipeline: fetch video → extract → score → dedupe.
        
        Returns list of scored keywords ready to save.
        """
        # Fetch video details
        video_details = self.youtube.get_video_details(video_id)
        if not video_details:
            logger.warning(f"Video not found: {video_id}")
            return []
        
        # Get channel info
        channel_info = self.youtube.get_channel_info(
            video_details['channel_id']
        )
        
        # Build context
        video_context = {
            'video_id': video_id,
            'channel_id': video_details['channel_id'],
            'title': video_details['title'],
            'description': video_details['description'],
            'tags': [],  # TODO: Fetch tags from API
            'transcript': self.youtube.get_transcript(video_id),
            'view_count': video_details['view_count'],
            'like_count': video_details.get('like_count', 0),
            'comment_count': video_details.get('comment_count', 0)
        }
        
        # Extract keywords
        candidates = await self.extract_keywords(video_context)
        
        # Score keywords
        scored = await self.score_keywords(
            candidates, video_context, 
            niche_topics=channel_info.get('description', '').split()[:10]
            if channel_info else None
        )
        
        return scored
    
    def deduplicate(self, keywords: List[Dict]) -> List[Dict]:
        """
        Deduplicate keywords by keeping the best score for each unique keyword.
        Updates the suggested_by JSONB array with multiple sources.
        
        Returns list of unique keywords with best scores.
        """
        deduped = {}
        
        for kw in keywords:
            keyword = kw['keyword']
            
            if keyword in deduped:
                # Keep higher score
                if kw['final_score'] > deduped[keyword]['final_score']:
                    deduped[keyword] = kw
            else:
                deduped[keyword] = kw
        
        return list(deduped.values())
