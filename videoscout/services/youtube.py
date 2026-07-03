"""
YouTube API service for fetching channel and video data.
Ported from videoscout/services/youtube_service.py with async support.
"""
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube Data API v3 wrapper with async support."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize YouTube service with API key."""
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY not set in environment")
        self._client = None
    
    @property
    def client(self):
        """Lazy-load YouTube API client."""
        if self._client is None:
            self._client = build(
                "youtube", 
                "v3", 
                developerKey=self.api_key,
                cache_discovery=False
            )
        return self._client
    
    def extract_channel_id(self, url_or_id: str) -> Optional[str]:
        """
        Extract YouTube channel ID from URL or handle.
        
        Supports:
        - youtube.com/channel/UC...
        - youtube.com/@username
        - UC... (direct channel ID)
        """
        logger.debug(f"Extracting channel ID from: {url_or_id}")
        
        # Patterns for channel URLs
        patterns = [
            r"youtube\.com/channel/(UC[\w-]{22})",
            r"youtube\.com/@([\w.-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                handle = match.group(1)
                # If already a channel ID, return it
                if re.match(r"^UC[\w-]{22}$", handle):
                    return handle
                # Otherwise resolve handle
                return self._resolve_handle(handle)
        
        # Check if input is already a channel ID
        if re.match(r"^UC[\w-]{22}$", url_or_id.strip()):
            return url_or_id.strip()
        
        logger.warning(f"Could not extract channel ID from: {url_or_id}")
        return None
    
    def _resolve_handle(self, handle: str) -> Optional[str]:
        """Resolve @username to channel ID."""
        try:
            response = self.client.channels().list(
                part="id",
                forHandle=handle
            ).execute()
            
            items = response.get("items", [])
            if items:
                channel_id = items[0]["id"]
                logger.debug(f"Resolved @{handle} → {channel_id}")
                return channel_id
            
            logger.warning(f"Handle @{handle} not found")
            return None
        except Exception as e:
            logger.error(f"Error resolving handle @{handle}: {e}")
            return None
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """
        Fetch channel information.
        
        Returns:
            {
                "id": str,
                "name": str,
                "url": str,
                "subscribers": int,
                "description": str,
                "thumbnail_url": str
            }
        """
        logger.debug(f"Fetching channel info: {channel_id}")
        
        try:
            response = self.client.channels().list(
                part="snippet,statistics",
                id=channel_id
            ).execute()
            
            items = response.get("items", [])
            if not items:
                logger.warning(f"No channel found for id={channel_id}")
                return None
            
            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            
            info = {
                "id": channel_id,
                "name": snippet.get("title", ""),
                "url": f"https://www.youtube.com/channel/{channel_id}",
                "subscribers": int(stats.get("subscriberCount", 0)),
                "description": snippet.get("description", ""),
                "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
            }
            
            logger.info(
                f"Channel fetched: {info['name']} "
                f"({info['subscribers']:,} subscribers)"
            )
            return info
            
        except Exception as e:
            logger.error(f"Error fetching channel info: {e}")
            return None
    
    def get_recent_videos(
        self,
        channel_id: str,
        days: int = 30,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Fetch recent videos from a channel using playlistItems API (1 quota unit).
        More efficient than search API (100 quota units).
        
        Returns:
            List of dicts with keys:
            - id: str
            - title: str
            - upload_date: str (YYYY-MM-DD)
            - thumbnail_url: str
            - duration_sec: int
            - view_count: int
            - youtube_url: str
        """
        logger.debug(f"Fetching recent videos: channel={channel_id}, days={days}")
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Convert channel ID to uploads playlist ID
            # Channel ID: UC... → Uploads playlist: UU...
            uploads_playlist_id = "UU" + channel_id[2:]
            
            # Fetch playlist items (1 quota unit)
            playlist_response = self.client.playlistItems().list(
                part="contentDetails,snippet",
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            
            # Filter by date client-side
            video_ids = []
            for item in playlist_response.get("items", []):
                published_at = item["snippet"].get("publishedAt", "")
                if published_at:
                    pub_dt = datetime.fromisoformat(
                        published_at.replace("Z", "+00:00")
                    )
                    if pub_dt >= cutoff:
                        vid_id = item["contentDetails"].get("videoId")
                        if vid_id:
                            video_ids.append(vid_id)
            
            logger.debug(
                f"Found {len(video_ids)} videos within {days} days"
            )
            
            if not video_ids:
                return []
            
            # Fetch video statistics (1 quota unit per 50 videos)
            stats_response = self.client.videos().list(
                part="statistics,contentDetails,snippet",
                id=",".join(video_ids)
            ).execute()
            
            results = []
            for item in stats_response.get("items", []):
                vid_id = item["id"]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                
                duration = self._parse_duration(
                    content_details.get("duration", "PT0S")
                )
                
                results.append({
                    "id": vid_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "upload_date": snippet.get("publishedAt", "")[:10],
                    "thumbnail_url": (
                        snippet.get("thumbnails", {})
                        .get("medium", {})
                        .get("url", "")
                    ),
                    "duration_sec": duration,
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "youtube_url": f"https://www.youtube.com/watch?v={vid_id}",
                    "channel_id": channel_id
                })
            
            logger.info(
                f"Fetched {len(results)} videos with stats for {channel_id}"
            )
            return results
            
        except Exception as e:
            logger.error(
                f"Error fetching recent videos for {channel_id}: {e}"
            )
            return []
    
    def _parse_duration(self, iso_duration: str) -> int:
        """
        Parse ISO 8601 duration to seconds.
        
        Examples:
            PT1H2M30S → 3750
            PT15M → 900
            PT45S → 45
        """
        match = re.match(
            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
            iso_duration
        )
        if not match:
            return 0
        
        hours, minutes, seconds = (int(x or 0) for x in match.groups())
        return hours * 3600 + minutes * 60 + seconds
    
    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Fetch detailed information for a single video.
        
        Returns same structure as get_recent_videos items.
        """
        try:
            response = self.client.videos().list(
                part="statistics,contentDetails,snippet",
                id=video_id
            ).execute()
            
            items = response.get("items", [])
            if not items:
                logger.warning(f"No video found for id={video_id}")
                return None
            
            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
            
            return {
                "id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "upload_date": snippet.get("publishedAt", "")[:10],
                "thumbnail_url": (
                    snippet.get("thumbnails", {})
                    .get("medium", {})
                    .get("url", "")
                ),
                "duration_sec": self._parse_duration(
                    content_details.get("duration", "PT0S")
                ),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "channel_id": snippet.get("channelId", "")
            }
            
        except Exception as e:
            logger.error(f"Error fetching video details: {e}")
            return None

    def search_videos_by_keyword(
        self,
        keyword: str,
        *,
        max_results: int = 25,
        days: int = 7,
    ) -> List[Dict]:
        """Search recent YouTube videos by keyword (supply-pressure round-trip)."""
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        published_after = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat().replace("+00:00", "Z")
        logger.debug(
            "YouTube video search keyword=%r max=%d days=%d",
            keyword,
            max_results,
            days,
        )
        try:
            search_resp = self.client.search().list(
                part="snippet",
                q=keyword,
                type="video",
                maxResults=max_results,
                order="date",
                publishedAfter=published_after,
                relevanceLanguage="en",
            ).execute()
            video_ids: List[str] = []
            snippets: Dict[str, Dict] = {}
            for item in search_resp.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id or video_id in snippets:
                    continue
                snippet = item.get("snippet", {})
                video_ids.append(video_id)
                snippets[video_id] = {
                    "title": snippet.get("title", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "published_at": snippet.get("publishedAt"),
                }

            if not video_ids:
                return []

            stats_resp = self.client.videos().list(
                part="statistics",
                id=",".join(video_ids),
            ).execute()
            stats_by_id = {
                row["id"]: row.get("statistics", {})
                for row in stats_resp.get("items", [])
            }

            results: List[Dict] = []
            for video_id in video_ids:
                snippet = snippets[video_id]
                stats = stats_by_id.get(video_id, {})
                results.append({
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "channel_id": snippet.get("channel_id", ""),
                    "published_at": snippet.get("published_at"),
                    "view_count": int(stats.get("viewCount") or 0),
                })
            logger.info(
                "YouTube search returned %d videos for keyword %r",
                len(results),
                keyword,
            )
            return results
        except Exception as e:
            logger.error("YouTube video search failed for %r: %s", keyword, e)
            return []

    def get_trending_videos(
        self,
        region_code: str = "DE",
        max_results: int = 25,
    ) -> List[Dict]:
        """
        Fetch YouTube trending videos for a region.

        Returns list of dicts with id, title, channel_id, published_at,
        view_count, category_id.
        """
        logger.debug("Fetching trending videos region=%s limit=%d", region_code, max_results)
        try:
            response = self.client.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=region_code,
                maxResults=max_results,
            ).execute()
            results = []
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                view_count = int(statistics.get("viewCount") or 0)
                results.append({
                    "id": item["id"],
                    "title": snippet.get("title", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "published_at": snippet.get("publishedAt"),
                    "view_count": view_count,
                    "category_id": snippet.get("categoryId"),
                })
            logger.info("Fetched %d trending videos for %s", len(results), region_code)
            return results
        except Exception as e:
            logger.error("Error fetching trending videos: %s", e)
            return []

    @staticmethod
    def _normalize_transcript(fetched) -> List[Dict]:
        """Convert youtube-transcript-api result to engine segment format."""
        return [
            {
                "text": segment.text,
                "start": segment.start,
                "duration": segment.duration,
            }
            for segment in fetched
        ]

    def get_transcript(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Fetch video transcript/captions.

        Uses youtube-transcript-api (no YouTube Data API quota).
        Tries preferred languages first, then any available track.

        Returns:
            List[{"text": str, "start": float, "duration": float}]
        """
        preferred = list(languages or ["vi", "en"])
        logger.debug("Fetching transcript: video=%s langs=%s", video_id, preferred)

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api import (
                NoTranscriptFound,
                TranscriptsDisabled,
            )
        except ImportError:
            logger.warning("youtube-transcript-api not installed")
            return []

        api = YouTubeTranscriptApi()

        try:
            fetched = api.fetch(video_id, languages=preferred)
            segments = self._normalize_transcript(fetched)
            logger.info(
                "Transcript fetched: video=%s lang=%s segments=%d",
                video_id,
                fetched.language_code,
                len(segments),
            )
            return segments
        except TranscriptsDisabled:
            logger.warning("Transcripts disabled for video=%s", video_id)
            return []
        except NoTranscriptFound:
            logger.debug(
                "No transcript in preferred langs for video=%s, trying fallback",
                video_id,
            )
        except Exception as e:
            logger.warning("Transcript fetch failed for video=%s: %s", video_id, e)
            return []

        try:
            for transcript in api.list(video_id):
                fetched = transcript.fetch()
                segments = self._normalize_transcript(fetched)
                logger.info(
                    "Transcript fetched (fallback): video=%s lang=%s segments=%d",
                    video_id,
                    fetched.language_code,
                    len(segments),
                )
                return segments
        except Exception as e:
            logger.warning("No transcript available for video=%s: %s", video_id, e)

        return []


# Singleton instance
_youtube_service: Optional[YouTubeService] = None


def get_youtube_service() -> YouTubeService:
    """Get or create singleton YouTube service instance."""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service
