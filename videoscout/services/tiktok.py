"""
TikTok API service for checking keyword saturation.
Based on videoscout/services/tiktok_service.py
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()
TIKTOK_API_KEY = os.getenv("TIKTOK_API_KEY", "")

# Cache for TikTok results (6 hours TTL)
_tiktok_cache: Dict[str, Dict] = {}


class TikTokService:
    """
    TikTok video search service.
    
    Uses TikTok API to check keyword saturation (number of videos in last 7 days).
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize TikTok service with API key."""
        self.api_key = api_key or TIKTOK_API_KEY
        self.base_url = "https://tiktok-api.p.rapidapi.com"
        self._client = None
    
    @property
    def client(self):
        """Lazy-load HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.Client(
                headers={
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "tiktok-api.p.rapidapi.com"
                }
            )
        return self._client
    
    def search_videos(
        self,
        keyword: str,
        period: str = "7d",
        limit: int = 50
    ) -> Dict:
        """
        Search TikTok videos by keyword.
        
        Args:
            keyword: Search term
            period: Time period ('1d', '7d', '30d')
            limit: Max results (max 50)
            
        Returns:
            {
                "videos": List[dict],
                "total_count": int,
                "avg_views": float,
                "avg_likes": float,
                "avg_comments": float,
                "avg_engagement_rate": float
            }
        """
        # Check cache first
        cache_key = f"{keyword}:{period}:{limit}"
        cached = _tiktok_cache.get(cache_key)
        if cached:
            expires_at = cached.get("expires_at", 0)
            if expires_at > time.time():
                return cached["data"]
        
        # Convert period to days
        days = {"1d": 1, "7d": 7, "30d": 30}.get(period, 7)
        
        # Build API request
        # Using RapidAPI TikTok API as placeholder
        # Replace with official TikTok Research API when available
        
        try:
            # Example: Use a generic API call structure
            # In production, replace with actual TikTok API endpoint
            response = self._client.get(
                f"{self.base_url}/search/video",
                params={
                    "keywords": keyword,
                    "count": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._process_response(data, days)
            else:
                # Fallback for testing without API
                return {
                    "videos": [],
                    "total_count": 0,
                    "avg_views": 0.0,
                    "avg_likes": 0.0,
                    "avg_comments": 0.0,
                    "avg_engagement_rate": 0.0,
                    "rate_limited": True
                }
                
        except Exception as e:
            print(f"Error searching TikTok: {e}")
            return {
                "videos": [],
                "total_count": 0,
                "avg_views": 0.0,
                "avg_likes": 0.0,
                "avg_comments": 0.0,
                "avg_engagement_rate": 0.0,
                "error": str(e)
            }
    
    def _process_response(self, data: Dict, days: int) -> Dict:
        """Process API response and calculate metrics."""
        videos = data.get("videos", [])
        
        if not videos:
            return {
                "videos": [],
                "total_count": 0,
                "avg_views": 0.0,
                "avg_likes": 0.0,
                "avg_comments": 0.0,
                "avg_engagement_rate": 0.0
            }
        
        # Filter by period
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_videos = []
        total_views = 0
        total_likes = 0
        total_comments = 0
        total_engagement = 0

        def _include_video_stats(video_item: Dict) -> None:
            nonlocal total_views, total_likes, total_comments, total_engagement
            filtered_videos.append(video_item)
            views = video_item.get("view_count", 0) or 0
            likes = video_item.get("like_count", 0) or 0
            comments = video_item.get("comment_count", 0) or 0
            shares = video_item.get("share_count", 0) or 0
            total_views += views
            total_likes += likes
            total_comments += comments
            total_engagement += (likes + comments + shares)
        
        for video in videos:
            created_at = video.get("created_at", "")
            if created_at:
                try:
                    video_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if video_date >= cutoff_date:
                        _include_video_stats(video)
                except Exception:
                    _include_video_stats(video)
            else:
                _include_video_stats(video)
        
        total_count = len(filtered_videos)
        avg_views = total_views / total_count if total_count > 0 else 0
        avg_likes = total_likes / total_count if total_count > 0 else 0
        avg_comments = total_comments / total_count if total_count > 0 else 0
        avg_engagement_rate = (
            total_engagement / total_views
            if total_views > 0 else 0
        )
        
        # Cache result (6 hours)
        _tiktok_cache[video.get("keyword", "")] = {
            "data": {
                "videos": filtered_videos,
                "total_count": total_count,
                "avg_views": avg_views,
                "avg_likes": avg_likes,
                "avg_comments": avg_comments,
                "avg_engagement_rate": avg_engagement_rate
            },
            "expires_at": time.time() + 6 * 3600
        }
        
        return {
            "videos": filtered_videos,
            "total_count": total_count,
            "avg_views": avg_views,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "avg_engagement_rate": avg_engagement_rate
        }
    
    def get_keyword_saturation(
        self,
        keyword: str,
        period: str = "7d"
    ) -> Dict:
        """
        Get saturation score for a keyword.
        
        Returns:
            {
                "keyword": str,
                "video_count": int,
                "status": "low" | "moderate" | "saturated",
                "avg_views": float,
                "engagement_rate": float
            }
        """
        result = self.search_videos(keyword, period=period, limit=50)
        
        count = result.get("total_count", 0)
        
        # Determine saturation level
        if count <= 10:
            status = "low"
        elif count <= 50:
            status = "moderate"
        else:
            status = "saturated"
        
        return {
            "keyword": keyword,
            "video_count": count,
            "status": status,
            "avg_views": result.get("avg_views", 0),
            "engagement_rate": result.get("avg_engagement_rate", 0)
        }


# Singleton instance
_tiktok_service: Optional[TikTokService] = None


def get_tiktok_service() -> TikTokService:
    """Get or create singleton TikTok service instance."""
    global _tiktok_service
    if _tiktok_service is None:
        _tiktok_service = TikTokService()
    return _tiktok_service
