"""Discovery job progress — shared worker + API computation."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from videoscout.db.models import DiscoveryJobModel

TRENDING_VIDEO_LIMIT = 10
VELOCITY_VIDEO_LIMIT = 10
MAX_KEYWORDS_PER_JOB = 10
MAX_CANDIDATES_ESTIMATE = (TRENDING_VIDEO_LIMIT + VELOCITY_VIDEO_LIMIT) * 4

PHASE_LABELS = {
    "starting": "Starting discovery…",
    "fetch_trends": "Fetching YouTube trends…",
    "fetch_velocity": "Fetching emergence videos…",
    "scan_videos": "Checking TikTok gates…",
    "score_nurture": "Scoring nurture keywords…",
    "score_beta": "Scoring beta keywords…",
    "enrich_top": "Enriching top keywords…",
    "validate": "Validating keyword evidence…",
    "rank_final": "Final ranking…",
    "complete": "Discovery complete",
    "failed": "Discovery failed",
}


class DiscoveryProgress(TypedDict):
    progress_percent: int
    progress_phase: str
    progress_label: str


def _phase_base(phase: str) -> str:
    """Strip optional `:REGION` suffix from progress phases (US-079)."""
    if ":" in phase:
        return phase.split(":", 1)[0]
    return phase


def _running_percent(
    phase: str,
    videos: int,
    candidates: int,
    keywords: int,
) -> int:
    base = _phase_base(phase)
    if base in ("starting", "fetch_trends", "fetch_velocity") and videos == 0:
        return 5 if base in ("fetch_trends", "fetch_velocity") else 2

    video_cap = TRENDING_VIDEO_LIMIT + VELOCITY_VIDEO_LIMIT
    video_pct = 10 + int(30 * min(videos, video_cap) / video_cap)
    candidate_pct = int(
        35 * min(candidates, MAX_CANDIDATES_ESTIMATE) / MAX_CANDIDATES_ESTIMATE,
    )
    keyword_pct = int(15 * min(keywords, MAX_KEYWORDS_PER_JOB) / MAX_KEYWORDS_PER_JOB)

    if base in ("score_beta", "score_nurture", "enrich_top", "validate", "rank_final"):
        return min(75 + int(20 * keywords / MAX_KEYWORDS_PER_JOB), 95)

    return min(max(video_pct + candidate_pct + keyword_pct, 5), 94)


def _running_label(
    phase: str,
    videos: int,
    candidates: int,
    keywords: int,
) -> str:
    base = _phase_base(phase)
    region = phase.split(":", 1)[1] if ":" in phase else None
    if base == "fetch_trends":
        if region:
            return f"Fetching YouTube trends ({region})…"
        return PHASE_LABELS["fetch_trends"]
    if base == "fetch_velocity":
        return PHASE_LABELS["fetch_velocity"]
    if base == "scan_videos":
        if region:
            return f"Checking TikTok gates ({region})…"
        return PHASE_LABELS["scan_videos"]
    if base == "rank_final":
        return PHASE_LABELS["rank_final"]
    if base == "validate":
        return PHASE_LABELS["validate"]
    if base == "score_beta":
        return PHASE_LABELS["score_beta"]
    if base == "score_nurture":
        return PHASE_LABELS["score_nurture"]
    if base == "enrich_top":
        return PHASE_LABELS["enrich_top"]
    if keywords > 0:
        return f"Saving keywords ({keywords}/{MAX_KEYWORDS_PER_JOB})"
    if candidates > 0:
        return PHASE_LABELS["scan_videos"]
    if videos > 0:
        return f"Scanning trends ({videos}/{TRENDING_VIDEO_LIMIT + VELOCITY_VIDEO_LIMIT})"
    return PHASE_LABELS.get(base, "Discovering…")


def compute_discovery_progress(job: DiscoveryJobModel) -> DiscoveryProgress:
    phase = job.progress_phase or "starting"
    videos = job.videos_scanned or 0
    candidates = job.candidates_checked or 0
    keywords = job.keywords_generated or 0

    if job.status == "completed":
        return {
            "progress_percent": 100,
            "progress_phase": "complete",
            "progress_label": PHASE_LABELS["complete"],
        }

    if job.status == "failed":
        return {
            "progress_percent": _running_percent(phase, videos, candidates, keywords),
            "progress_phase": "failed",
            "progress_label": job.error_message or PHASE_LABELS["failed"],
        }

    return {
        "progress_percent": _running_percent(phase, videos, candidates, keywords),
        "progress_phase": phase,
        "progress_label": _running_label(phase, videos, candidates, keywords),
    }
