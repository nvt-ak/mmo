"""Video download service wrapper around yt-dlp."""
from pathlib import Path
import logging
import os
import subprocess
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class DownloadService:
    """Wrapper service to download a single video URL to a target path."""

    def __init__(self, runner: Optional[Callable[..., subprocess.CompletedProcess]] = None):
        self._runner = runner or subprocess.run

    @staticmethod
    def resolve_data_dir() -> Path:
        """Resolve root data dir from env, default to ./data."""
        return Path(os.getenv("VIDEOSCOUT_DATA_DIR", "data")).expanduser()

    def download(self, url: str, output_path: Path) -> bool:
        """Download URL to output path with yt-dlp. Returns True on success."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "yt-dlp",
            "-f",
            "mp4",
            "-o",
            str(output_path),
            url,
        ]
        try:
            completed = self._runner(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                logger.warning(
                    "yt-dlp failed for %s: %s",
                    url,
                    (completed.stderr or "").strip(),
                )
                return False
            return output_path.exists()
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Download failed for %s: %s", url, exc)
            return False
