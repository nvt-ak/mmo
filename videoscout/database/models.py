from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Channel:
    id: str
    name: str
    url: str
    niche_tag: str = ""
    subscribers: int = 0
    avg_views: int = 0
    is_active: bool = True
    last_scanned: Optional[str] = None
    added_at: Optional[str] = None


@dataclass
class Video:
    id: str
    channel_id: str
    title: str
    view_count: int
    upload_date: str
    youtube_url: str
    duration_sec: int = 0
    thumbnail_url: str = ""
    opportunity_score: int = 0
    tiktok_status: str = "unknown"
    is_used: bool = False
    found_at: Optional[str] = None
    channel_name: Optional[str] = None
    channel_subscribers: Optional[int] = None


@dataclass
class ScanResult:
    channels_scanned: int
    videos_found: int
    top_score: int
    videos: list = field(default_factory=list)
