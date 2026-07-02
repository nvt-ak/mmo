"""Tests for R3 ingestion flow (bulk download + video assets APIs)."""
from unittest.mock import MagicMock, patch

from videoscout.db.models import (
    DownloadJobModel,
    SuggestionModel,
    VideoAssetModel,
)


def _mock_channel_discovery(mock_get_yt):
    mock_service = MagicMock()
    mock_client = MagicMock()
    mock_service.client = mock_client
    mock_get_yt.return_value = mock_service

    mock_client.search.return_value.list.return_value.execute.return_value = {
        "items": [
            {"snippet": {"channelId": "UC_ALPHA"}},
            {"snippet": {"channelId": "UC_BETA"}},
        ]
    }
    mock_client.channels.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "UC_ALPHA",
                "snippet": {
                    "title": "Alpha Channel",
                    "description": "Alpha desc",
                    "thumbnails": {"medium": {"url": "https://img/alpha.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "12000",
                    "videoCount": "80",
                    "viewCount": "9600000",
                },
            },
            {
                "id": "UC_BETA",
                "snippet": {
                    "title": "Beta Channel",
                    "description": "Beta desc",
                    "thumbnails": {"medium": {"url": "https://img/beta.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "4000",
                    "videoCount": "120",
                    "viewCount": "2400000",
                },
            },
        ]
    }


def _mock_bulk_recent_videos(mock_get_youtube):
    mock_service = MagicMock()
    mock_service.get_recent_videos.side_effect = [
        [
            {
                "id": "vid_alpha_1",
                "title": "Alpha upload",
                "view_count": 1000,
                "duration_sec": 120,
                "youtube_url": "https://www.youtube.com/watch?v=vid_alpha_1",
                "upload_date": "2026-07-02",
            }
        ],
        [
            {
                "id": "vid_beta_1",
                "title": "Beta upload",
                "view_count": 2000,
                "duration_sec": 300,
                "youtube_url": "https://www.youtube.com/watch?v=vid_beta_1",
                "upload_date": "2026-07-02",
            }
        ],
    ]
    mock_get_youtube.return_value = mock_service


@patch("videoscout.workers.bulk_download.DownloadService.download", return_value=True)
@patch("videoscout.workers.bulk_download.get_youtube_service")
@patch("videoscout.core_engine.channel_discovery.get_youtube_service")
def test_cascade_triggers_bulk_download_and_persists_assets(
    mock_discovery_youtube,
    mock_bulk_youtube,
    mock_download,
    client,
    db_session,
):
    _mock_channel_discovery(mock_discovery_youtube)
    _mock_bulk_recent_videos(mock_bulk_youtube)

    suggestion = SuggestionModel(
        keyword="r3 ingestion keyword",
        final_score=0.82,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.8,
            "saturation": 0.7,
            "trend": 0.6,
            "video_performance": 0.7,
        },
        suggested_by=[{"source": "test", "score": 0.82, "timestamp": "2026-07-02"}],
        status="pending",
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    resp = client.post(
        "/api/v1/suggestions/bulk-approve",
        json={"keyword_ids": [str(suggestion.id)]},
    )
    assert resp.status_code == 200
    assert resp.json()["approved_count"] == 1

    assets = db_session.query(VideoAssetModel).all()
    assert len(assets) == 2
    assert {asset.youtube_video_id for asset in assets} == {"vid_alpha_1", "vid_beta_1"}
    assert all(asset.status == "downloaded" for asset in assets)
    assert all(asset.review_status == "pending" for asset in assets)

    jobs = db_session.query(DownloadJobModel).all()
    assert len(jobs) == 1
    assert jobs[0].job_type == "bulk"
    assert jobs[0].status == "completed"
    assert jobs[0].videos_downloaded == 2

    job_resp = client.get(f"/api/v1/downloads/jobs/{jobs[0].id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["videos_downloaded"] == 2

    list_resp = client.get(f"/api/v1/videos?suggestion_id={suggestion.id}&review_status=pending&limit=10")
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2
