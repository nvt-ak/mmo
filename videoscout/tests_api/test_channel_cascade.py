"""Tests for keyword approve cascade (R2 M2)."""
from unittest.mock import MagicMock, patch

from videoscout.db.models import (
    SuggestionModel,
    ChannelModel,
    ChannelKeywordLinkModel,
    KeywordCascadeJobModel,
)


def _mock_youtube_discovery(mock_get_yt):
    mock_service = MagicMock()
    mock_client = MagicMock()
    mock_service.client = mock_client
    mock_get_yt.return_value = mock_service

    mock_search_execute = {
        "items": [
            {"snippet": {"channelId": "UC_ALPHA"}},
            {"snippet": {"channelId": "UC_BETA"}},
        ]
    }
    mock_details_execute = {
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

    mock_client.search.return_value.list.return_value.execute.return_value = (
        mock_search_execute
    )
    mock_client.channels.return_value.list.return_value.execute.return_value = (
        mock_details_execute
    )


@patch("videoscout.core_engine.channel_discovery.get_youtube_service")
def test_bulk_approve_triggers_cascade_and_links_channels(
    mock_get_yt,
    client,
    db_session,
):
    _mock_youtube_discovery(mock_get_yt)

    suggestion = SuggestionModel(
        keyword="ai marketing niche",
        final_score=0.8,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.8,
            "saturation": 0.7,
            "trend": 0.6,
            "video_performance": 0.7,
        },
        suggested_by=[{"source": "test", "score": 0.8, "timestamp": "2026-07-02"}],
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
    payload = resp.json()
    assert payload["approved_count"] == 1
    assert len(payload["cascade_job_ids"]) == 1
    job_id = payload["cascade_job_ids"][0]

    db_session.refresh(suggestion)
    assert suggestion.status == "approved"

    channels = db_session.query(ChannelModel).all()
    assert len(channels) == 2
    assert all(ch.scan_enabled for ch in channels)

    links = db_session.query(ChannelKeywordLinkModel).filter(
        ChannelKeywordLinkModel.suggestion_id == suggestion.id
    ).all()
    assert len(links) == 2

    job = next(
        (
            candidate
            for candidate in db_session.query(KeywordCascadeJobModel).all()
            if str(candidate.id) == job_id
        ),
        None,
    )
    assert job is not None
    assert job.status == "completed"
    assert job.channels_discovered == 2
    assert job.channels_subscribed == 2

    job_resp = client.get(f"/api/v1/cascade/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "completed"

    channels_resp = client.get(f"/api/v1/suggestions/{suggestion.id}/channels")
    assert channels_resp.status_code == 200
    assert channels_resp.json()["total"] == 2
    assert channels_resp.json()["items"][0]["youtube_channel_id"] in {"UC_ALPHA", "UC_BETA"}


@patch("videoscout.core_engine.channel_discovery.get_youtube_service")
def test_bulk_approve_filters_channels_below_min_score(
    mock_get_yt,
    client,
    db_session,
):
    """Channels with discovery_score < MIN_DISCOVERY_SCORE must not be subscribed."""
    mock_service = MagicMock()
    mock_client = MagicMock()
    mock_service.client = mock_client
    mock_get_yt.return_value = mock_service

    # UC_LOW has weak stats → discovery_score below default threshold of 40.
    mock_client.search.return_value.list.return_value.execute.return_value = {
        "items": [
            {"snippet": {"channelId": "UC_LOW"}},
        ]
    }
    mock_client.channels.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "UC_LOW",
                "snippet": {
                    "title": "Low Quality Channel",
                    "description": "Low desc",
                    "thumbnails": {"medium": {"url": "https://img/low.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "100000",
                    "videoCount": "5",
                    "viewCount": "10000",
                },
            },
        ]
    }

    suggestion = SuggestionModel(
        keyword="low quality keyword",
        final_score=0.8,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.8,
            "saturation": 0.7,
            "trend": 0.6,
            "video_performance": 0.7,
        },
        suggested_by=[{"source": "test", "score": 0.8, "timestamp": "2026-07-02"}],
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
    job_id = resp.json()["cascade_job_ids"][0]

    channels = db_session.query(ChannelModel).all()
    assert len(channels) == 0

    links = db_session.query(ChannelKeywordLinkModel).filter(
        ChannelKeywordLinkModel.suggestion_id == suggestion.id
    ).all()
    assert len(links) == 0

    job = next(
        (
            candidate
            for candidate in db_session.query(KeywordCascadeJobModel).all()
            if str(candidate.id) == job_id
        ),
        None,
    )
    assert job is not None
    assert job.status == "completed_no_source"
    assert job.channels_discovered == 1
    assert job.channels_subscribed == 0

    job_resp = client.get(f"/api/v1/cascade/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "completed_no_source"


def test_bulk_approve_skips_already_approved_suggestion(client, db_session):
    suggestion = SuggestionModel(
        keyword="already approved",
        final_score=0.8,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.8,
            "saturation": 0.7,
            "trend": 0.6,
            "video_performance": 0.7,
        },
        suggested_by=[{"source": "test", "score": 0.8, "timestamp": "2026-07-02"}],
        status="approved",
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    resp = client.post(
        "/api/v1/suggestions/bulk-approve",
        json={"keyword_ids": [str(suggestion.id)]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved_count"] == 0
    assert data["cascade_job_ids"] == []
