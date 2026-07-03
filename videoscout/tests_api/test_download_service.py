"""Tests for yt-dlp download command construction."""
from pathlib import Path

from videoscout.services.download import DownloadService


def test_build_ytdlp_command_uses_mp4_template_and_js_runtime(monkeypatch):
    monkeypatch.delenv("YTDLP_JS_RUNTIMES", raising=False)
    monkeypatch.delenv("YTDLP_SOCKET_TIMEOUT", raising=False)

    command = DownloadService.build_ytdlp_command(
        "https://www.youtube.com/watch?v=abc123",
        Path("/tmp/abc123.mp4"),
    )

    assert command[:2] == ["yt-dlp", "-t"]
    assert "mp4" in command
    assert "--js-runtimes" in command
    assert command[command.index("--js-runtimes") + 1] == "node"
    assert "--remote-components" in command
    assert command[command.index("--remote-components") + 1] == "ejs:github"
    assert command[-1] == "https://www.youtube.com/watch?v=abc123"
