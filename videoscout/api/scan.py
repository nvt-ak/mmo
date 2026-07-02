"""Scan API endpoints - Full implementation with engine integration."""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta
import logging

from videoscout.db import get_db
from videoscout.db.models import SuggestionModel, ScanJobModel, ChannelModel
from videoscout.core_engine.engine import SuggestionEngine
from videoscout.schemas import ScanRunRequest, ScanRunResponse, ScanProgressResponse
from videoscout.services.youtube import get_youtube_service
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()


async def run_daily_digest(
    job_id: str,
    channel_ids: list,
    force: bool,
    engine: SuggestionEngine
):
    """Background task to scan channels and generate suggestions."""
    from videoscout.db import get_session
    db = get_session()
    
    job = db.query(ScanJobModel).filter(ScanJobModel.id == job_id).first()
    if job:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()
    
    channels_processed = 0
    videos_processed = 0
    suggestions_generated = 0
    
    # Get channels to scan
    channels_query = db.query(ChannelModel).filter(
        ChannelModel.scan_enabled == True
    )
    
    if channel_ids:
        channels_query = channels_query.filter(
            ChannelModel.channel_id.in_(channel_ids)
        )
    
    channels = channels_query.all()
    
    try:
        for channel in channels:
            channels_processed += 1
            
            # Skip recently scanned (unless force)
            if not force and channel.last_scan_at:
                hours_since = (datetime.utcnow() - channel.last_scan_at).total_seconds() / 3600
                if hours_since < 6:
                    logger.info(f"Skipping {channel.channel_id} - scanned {hours_since:.1f}h ago")
                    continue
            
            # Fetch recent videos (last 7 days)
            videos = get_youtube_service().get_recent_videos(
                channel.channel_id,
                days=7,
                max_results=10
            )
            
            for video in videos:
                videos_processed += 1
                yt = get_youtube_service()

                # Build video context
                video_context = {
                    'video_id': video['id'],
                    'channel_id': channel.channel_id,
                    'title': video['title'],
                    'description': video.get('description', ''),
                    'tags': [],  # TODO: Fetch tags
                    'transcript': yt.get_transcript(video['id']),
                    'view_count': video['view_count'],
                    'like_count': video.get('like_count', 0),
                    'comment_count': video.get('comment_count', 0)
                }
                
                # Extract and score keywords
                try:
                    candidates = await engine.extract_keywords(video_context)
                    scored = await engine.score_keywords(
                        candidates, video_context,
                        niche_topics=channel.description.split()[:10] if channel.description else []
                    )
                    
                    # Deduplicate and save
                    for kw in scored:
                        try:
                            # Check for existing keyword
                            existing = db.query(SuggestionModel).filter(
                                SuggestionModel.keyword == kw['keyword']
                            ).first()
                            
                            if existing:
                                # Update suggested_by with new source
                                updated_sources = list(existing.suggested_by or [])
                                updated_sources.append({
                                    'source': 'digest_scan',
                                    'video_id': video['id'],
                                    'channel_id': channel.channel_id,
                                    'score': kw['final_score'],
                                    'timestamp': datetime.utcnow().isoformat()
                                })
                                existing.suggested_by = updated_sources
                                flag_modified(existing, 'suggested_by')
                                # Update scores if new score is higher
                                if kw['final_score'] > existing.final_score:
                                    existing.final_score = kw['final_score']
                                    existing.component_scores = kw['component_scores']
                                    existing.tiktok_status = kw.get('tiktok_status')
                                    existing.tiktok_count_at_suggest = kw.get(
                                        'tiktok_count',
                                        (kw.get('tiktok_stats') or {}).get('video_count_7d')
                                    )
                                    existing.tiktok_stats = kw.get('tiktok_stats')
                                    existing.tiktok_checked_at = datetime.utcnow()
                                db.commit()
                            else:
                                # Create new suggestion
                                suggestion = SuggestionModel(
                                    keyword=kw['keyword'],
                                    final_score=kw['final_score'],
                                    component_scores=kw['component_scores'],
                                    tiktok_status=kw['tiktok_status'],
                                    tiktok_count_at_suggest=kw.get(
                                        'tiktok_count',
                                        (kw.get('tiktok_stats') or {}).get('video_count_7d', 0)
                                    ),
                                    tiktok_stats=kw.get('tiktok_stats'),
                                    tiktok_checked_at=datetime.utcnow(),
                                    suggested_by=[{
                                        'source': 'digest_scan',
                                        'video_id': video['id'],
                                        'channel_id': channel.channel_id,
                                        'score': kw['final_score'],
                                        'timestamp': datetime.utcnow().isoformat()
                                    }],
                                    status='pending',
                                    created_at=datetime.utcnow()
                                )
                                db.add(suggestion)
                                suggestions_generated += 1
                            
                            db.commit()
                            
                        except IntegrityError:
                            db.rollback()
                            # Keyword already exists from different source
                            logger.debug(f"Duplicate keyword skipped: {kw['keyword']}")
                            
                except Exception as e:
                    logger.error(f"Error processing video {video['id']}: {e}")
                    db.rollback()
            
            # Update channel scan timestamp
            channel.last_scan_at = datetime.utcnow()
            channel.last_video_count = len(videos)
            db.commit()
            
            logger.info(f"Processed channel {channel.channel_id}: {len(videos)} videos, {suggestions_generated} suggestions")
        
        # Update job status
        if job:
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.channels_processed = channels_processed
            job.videos_processed = videos_processed
            job.suggestions_generated = suggestions_generated
            db.commit()
        
        logger.info(f"Scan job {job_id} complete: {suggestions_generated} suggestions")
        
    except Exception as e:
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        logger.error(f"Scan job {job_id} failed: {e}")
        raise
    finally:
        db.close()


@router.post("/scan/run", response_model=ScanRunResponse)
async def run_scan(
    payload: ScanRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger daily digest scan.
    
    Scans enabled YouTube channels and generates keyword suggestions
    based on recent videos.
    """
    job_id = uuid.uuid4()
    
    # Create scan job record
    job = ScanJobModel(
        id=job_id,
        status='started',
        channels_total=len(payload.channel_ids) if payload.channel_ids else 0
    )
    db.add(job)
    db.commit()
    
    # Queue background task
    background_tasks.add_task(
        run_daily_digest,
        job_id=job_id,
        channel_ids=payload.channel_ids,
        force=payload.force,
        engine=SuggestionEngine()
    )
    
    return ScanRunResponse(
        job_id=str(job_id),
        status='started',
        estimated_duration_seconds=300  # 5 minutes estimate
    )


@router.get("/scan/status/{job_id}", response_model=ScanProgressResponse)
async def get_scan_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get status and progress of a scan job."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = db.query(ScanJobModel).filter(ScanJobModel.id == job_uuid).first()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    progress = {
        'channels_processed': job.channels_processed,
        'videos_processed': job.videos_processed,
        'suggestions_generated': job.suggestions_generated
    }
    
    return ScanProgressResponse(
        job_id=job_id,
        status=job.status,
        progress=progress,
        error=job.error_message
    )


@router.get("/scan/history", response_model=list)
async def get_scan_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recent scan history."""
    jobs = db.query(ScanJobModel).order_by(
        ScanJobModel.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            'id': job.id,
            'status': job.status,
            'channels_processed': job.channels_processed,
            'videos_processed': job.videos_processed,
            'suggestions_generated': job.suggestions_generated,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at
        }
        for job in jobs
    ]
