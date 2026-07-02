"""Tests for YouTube transcript fetching."""
from datetime import datetime, timedelta
import uuid
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled
from youtube_transcript_api._transcripts import (
    FetchedTranscript,
    FetchedTranscriptSnippet,
)

from videoscout.db.models import ChannelModel
from videoscout.services.youtube import YouTubeService


def _make_fetched(language_code="vi"):
    snippets = [
        FetchedTranscriptSnippet(text="Xin chao", start=0.0, duration=2.5),
        FetchedTranscriptSnippet(text="AI marketing tips", start=2.5, duration=3.0),
    ]
    return FetchedTranscript(
        snippets=snippets,
        video_id="vid123",
        language="Vietnamese" if language_code == "vi" else "English",
        language_code=language_code,
        is_generated=False,
    )


@pytest.fixture
def youtube_service():
    return YouTubeService(api_key="test-key")


@patch("youtube_transcript_api.YouTubeTranscriptApi")
def test_get_transcript_success(mock_api_cls, youtube_service):
    mock_api = mock_api_cls.return_value
    mock_api.fetch.return_value = _make_fetched("vi")

    result = youtube_service.get_transcript("vid123")

    assert len(result) == 2
    assert result[0] == {"text": "Xin chao", "start": 0.0, "duration": 2.5}
    assert result[1]["text"] == "AI marketing tips"
    mock_api.fetch.assert_called_once_with("vid123", languages=["vi", "en"])


@patch("youtube_transcript_api.YouTubeTranscriptApi")
def test_get_transcript_custom_languages(mock_api_cls, youtube_service):
    mock_api = mock_api_cls.return_value
    mock_api.fetch.return_value = _make_fetched("en")

    youtube_service.get_transcript("vid123", languages=["en"])

    mock_api.fetch.assert_called_once_with("vid123", languages=["en"])


@patch("youtube_transcript_api.YouTubeTranscriptApi")
def test_get_transcript_disabled(mock_api_cls, youtube_service):
    mock_api = mock_api_cls.return_value
    mock_api.fetch.side_effect = TranscriptsDisabled("vid123")

    assert youtube_service.get_transcript("vid123") == []


@patch("youtube_transcript_api.YouTubeTranscriptApi")
def test_get_transcript_fallback_to_any_track(mock_api_cls, youtube_service):
    mock_api = mock_api_cls.return_value
    mock_api.fetch.side_effect = NoTranscriptFound("vid123", ["vi", "en"], "none")

    fallback_transcript = MagicMock()
    fallback_transcript.fetch.return_value = _make_fetched("ja")
    mock_api.list.return_value = [fallback_transcript]

    result = youtube_service.get_transcript("vid123")

    assert len(result) == 2
    mock_api.list.assert_called_once_with("vid123")
    fallback_transcript.fetch.assert_called_once()


@patch("youtube_transcript_api.YouTubeTranscriptApi")
def test_get_transcript_no_tracks_available(mock_api_cls, youtube_service):
    mock_api = mock_api_cls.return_value
    mock_api.fetch.side_effect = NoTranscriptFound("vid123", ["vi", "en"], "none")
    mock_api.list.return_value = []

    assert youtube_service.get_transcript("vid123") == []


@patch("videoscout.api.scan.get_youtube_service")
@patch("videoscout.api.scan.SuggestionEngine")
def test_scan_uses_transcript_in_video_context(
    mock_engine_cls, mock_yt_service, client, db_session
):
    """Integration: scan pipeline passes fetched transcript to engine."""
    from datetime import datetime, timedelta
    import uuid

    ch = ChannelModel(
        id=uuid.uuid4(),
        channel_id="UC_test001",
        name="Test Channel",
        scan_enabled=True,
        last_scan_at=datetime.utcnow() - timedelta(days=2),
    )
    db_session.add(ch)
    db_session.commit()

    captured_context = {}

    async def capture_extract(video_context):
        captured_context.update(video_context)
        return []

    mock_yt = MagicMock()
    mock_yt.get_recent_videos.return_value = [{
        "id": "vid_abc",
        "title": "How AI is changing marketing",
        "description": "AI marketing for small business",
        "view_count": 15000,
        "like_count": 800,
        "comment_count": 45,
    }]
    mock_yt.get_transcript.return_value = [
        {"text": "AI marketing tips", "start": 0.0, "duration": 2.0}
    ]
    mock_yt_service.return_value = mock_yt

    mock_engine = MagicMock()
    from unittest.mock import AsyncMock
    mock_engine.extract_keywords = AsyncMock(side_effect=capture_extract)
    mock_engine.score_keywords = AsyncMock(return_value=[])
    mock_engine_cls.return_value = mock_engine

    resp = client.post("/api/v1/scan/run", json={"channel_ids": [], "force": True})
    assert resp.status_code == 200

    mock_yt.get_transcript.assert_called_once_with("vid_abc")
    assert captured_context["transcript"] == [
        {"text": "AI marketing tips", "start": 0.0, "duration": 2.0}
    ]
