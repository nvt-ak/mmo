"""TikTok profile registry API (R7b)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import TikTokProfileModel
from videoscout.schemas import (
    TikTokProfile,
    TikTokProfileCreate,
    TikTokProfileListResponse,
    TikTokProfileUpdate,
)

router = APIRouter()


def _to_profile(row: TikTokProfileModel) -> TikTokProfile:
    return TikTokProfile(
        id=str(row.id),
        label=row.label,
        handle=row.handle,
        stage=row.stage,
        beta_eligible=bool(row.beta_eligible),
        promoted_at=row.promoted_at,
        notes=row.notes,
        created_at=row.created_at,
    )


@router.get("/profiles", response_model=TikTokProfileListResponse)
async def list_profiles(
    stage: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(TikTokProfileModel)
    if stage:
        if stage not in ("nurture", "beta"):
            raise HTTPException(400, "stage must be nurture or beta")
        query = query.filter(TikTokProfileModel.stage == stage)
    rows = query.order_by(TikTokProfileModel.created_at.desc()).all()
    return TikTokProfileListResponse(items=[_to_profile(r) for r in rows], total=len(rows))


@router.post("/profiles", response_model=TikTokProfile, status_code=201)
async def create_profile(payload: TikTokProfileCreate, db: Session = Depends(get_db)):
    if payload.stage not in ("nurture", "beta"):
        raise HTTPException(400, "stage must be nurture or beta")
    handle = payload.handle.lstrip("@")
    row = TikTokProfileModel(
        label=payload.label.strip(),
        handle=handle,
        stage=payload.stage,
        notes=payload.notes,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Handle already exists") from exc
    db.refresh(row)
    return _to_profile(row)


@router.put("/profiles/{profile_id}", response_model=TikTokProfile)
async def update_profile(
    profile_id: str,
    payload: TikTokProfileUpdate,
    db: Session = Depends(get_db),
):
    try:
        pid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(404, "Profile not found") from exc

    row = db.query(TikTokProfileModel).filter(TikTokProfileModel.id == pid).first()
    if not row:
        raise HTTPException(404, "Profile not found")

    if payload.label is not None:
        row.label = payload.label.strip()
    if payload.handle is not None:
        row.handle = payload.handle.lstrip("@")
    if payload.beta_eligible is not None:
        row.beta_eligible = payload.beta_eligible
    if payload.notes is not None:
        row.notes = payload.notes

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Handle already exists") from exc
    db.refresh(row)
    return _to_profile(row)


@router.post("/profiles/{profile_id}/promote", response_model=TikTokProfile)
async def promote_profile(profile_id: str, db: Session = Depends(get_db)):
    """Move nurture profile to beta list (manual operator action)."""
    try:
        pid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(404, "Profile not found") from exc

    row = db.query(TikTokProfileModel).filter(TikTokProfileModel.id == pid).first()
    if not row:
        raise HTTPException(404, "Profile not found")
    if row.stage != "nurture":
        raise HTTPException(409, "Only nurture profiles can be promoted")

    row.stage = "beta"
    row.beta_eligible = False
    row.promoted_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_profile(row)


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(404, "Profile not found") from exc

    row = db.query(TikTokProfileModel).filter(TikTokProfileModel.id == pid).first()
    if not row:
        raise HTTPException(404, "Profile not found")
    db.delete(row)
    db.commit()
