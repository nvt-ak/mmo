"""Sources API endpoints - Channel management with DB persistence."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import logging

from videoscout.db import get_db
from videoscout.db.models import ChannelModel
from videoscout.schemas import ChannelListResponse, AddChannelRequest, AddChannelResponse
from videoscout.services.youtube import get_youtube_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sources/channels", response_model=ChannelListResponse)
async def list_channels(db: Session = Depends(get_db)):
    """List all YouTube channels."""
    channels = db.query(ChannelModel).order_by(
        ChannelModel.created_at.desc()
    ).all()
    
    items = []
    for ch in channels:
        items.append({
            'id': str(ch.id),
            'channel_id': ch.channel_id,
            'name': ch.name,
            'scan_enabled': ch.scan_enabled,
            'last_scan_at': ch.last_scan_at,
            'video_count': ch.last_video_count or 0,
            'suggestion_count': 0,
            'created_at': ch.created_at
        })
    
    return ChannelListResponse(items=items, total=len(items))


@router.post("/sources/channels", response_model=AddChannelResponse)
async def add_channel(
    payload: AddChannelRequest,
    db: Session = Depends(get_db)
):
    """Add a YouTube channel by ID or handle."""
    yt = get_youtube_service()
    
    # Extract channel ID from handle/URL/raw ID
    channel_id = yt.extract_channel_id(payload.channel_id)
    if not channel_id:
        raise HTTPException(400, f"Could not resolve channel: {payload.channel_id}")
    
    # Check if already exists
    existing = db.query(ChannelModel).filter(
        ChannelModel.channel_id == channel_id
    ).first()
    if existing:
        raise HTTPException(409, f"Channel already exists: {existing.name}")
    
    # Fetch channel info from YouTube
    info = yt.get_channel_info(channel_id)
    
    channel = ChannelModel(
        id=uuid.uuid4(),
        channel_id=channel_id,
        name=info.get('name', '') if info else '',
        description=info.get('description', '') if info else '',
        thumbnail_url=info.get('thumbnail_url', '') if info else '',
        subscriber_count=info.get('subscribers', 0) if info else 0,
        scan_enabled=payload.scan_enabled
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    logger.info(f"Added channel: {channel.name} ({channel_id})")
    
    return AddChannelResponse(
        id=str(channel.id),
        channel_id=channel.channel_id,
        name=channel.name,
        thumbnail_url=channel.thumbnail_url,
        subscriber_count=channel.subscriber_count
    )


@router.delete("/sources/channels/{channel_id}")
async def remove_channel(
    channel_id: str,
    db: Session = Depends(get_db)
):
    """Remove a YouTube channel."""
    channel = db.query(ChannelModel).filter(
        ChannelModel.channel_id == channel_id
    ).first()
    
    if not channel:
        raise HTTPException(404, "Channel not found")
    
    db.delete(channel)
    db.commit()
    return {"message": f"Channel {channel_id} removed"}


@router.put("/sources/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    scan_enabled: bool = True,
    db: Session = Depends(get_db)
):
    """Update channel scan status."""
    channel = db.query(ChannelModel).filter(
        ChannelModel.channel_id == channel_id
    ).first()
    
    if not channel:
        raise HTTPException(404, "Channel not found")
    
    channel.scan_enabled = scan_enabled
    db.commit()
    return {"message": f"Channel {channel_id} updated", "scan_enabled": scan_enabled}
