"""Typed media pool listing API (R7b)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import FinalVideoModel, SuggestionModel, VideoAssetModel
from videoscout.schemas import PoolListResponse, PoolMediaItem

router = APIRouter()


@router.get("/pools", response_model=PoolListResponse)
async def list_pool_media(
    pool_type: str = Query(..., description="nurture or beta"),
    pool_status: str = Query(default="ready"),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if pool_type not in ("nurture", "beta"):
        raise HTTPException(400, "pool_type must be nurture or beta")

    items: list[PoolMediaItem] = []

    video_rows = (
        db.query(VideoAssetModel, SuggestionModel)
        .outerjoin(SuggestionModel, VideoAssetModel.suggestion_id == SuggestionModel.id)
        .filter(
            VideoAssetModel.review_status == "in_pool",
            VideoAssetModel.pool_type == pool_type,
            VideoAssetModel.pool_status == pool_status,
        )
        .order_by(VideoAssetModel.downloaded_at.desc())
        .limit(limit)
        .all()
    )
    for row, suggestion in video_rows:
        items.append(
            PoolMediaItem(
                id=str(row.id),
                kind="video_asset",
                pool_type=row.pool_type,
                pool_status=row.pool_status,
                title=row.title,
                keyword=suggestion.keyword if suggestion else None,
                file_path=row.file_path,
                duration_sec=row.duration_sec,
                created_at=row.downloaded_at,
            )
        )

    remaining = max(0, limit - len(items))
    if remaining:
        final_rows = (
            db.query(FinalVideoModel)
            .filter(
                FinalVideoModel.pool_type == pool_type,
                FinalVideoModel.pool_status == pool_status,
            )
            .order_by(FinalVideoModel.created_at.desc())
            .limit(remaining)
            .all()
        )
        for row in final_rows:
            items.append(
                PoolMediaItem(
                    id=str(row.id),
                    kind="final_video",
                    pool_type=row.pool_type,
                    pool_status=row.pool_status,
                    title=row.keyword or row.file_path.split("/")[-1],
                    keyword=row.keyword,
                    file_path=row.file_path,
                    duration_sec=row.duration_sec,
                    created_at=row.created_at,
                )
            )

    return PoolListResponse(items=items, total=len(items), limit=limit)
