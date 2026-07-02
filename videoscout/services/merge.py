"""ffmpeg merge service for concatenating source clips."""
from pathlib import Path
import logging
import os
import subprocess
import tempfile
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class MergeService:
    """Wrapper around ffmpeg concat for two local video files."""

    def __init__(self, runner: Optional[Callable[..., subprocess.CompletedProcess]] = None):
        self._runner = runner or subprocess.run

    @staticmethod
    def resolve_data_dir() -> Path:
        return Path(os.getenv("VIDEOSCOUT_DATA_DIR", "data")).expanduser()

    @staticmethod
    def finals_dir() -> Path:
        return MergeService.resolve_data_dir() / "finals"

    def merge(self, input_paths: list[Path], output_path: Path) -> bool:
        """Concatenate input videos into output_path. Returns True on success."""
        if len(input_paths) < 2:
            logger.warning("Merge requires at least two input files")
            return False

        for path in input_paths:
            if not path.exists():
                logger.warning("Missing merge input: %s", path)
                return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as list_file:
            for path in input_paths:
                list_file.write(f"file '{path.resolve()}'\n")
            list_path = list_file.name

        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-c",
            "copy",
            str(output_path),
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
                    "ffmpeg merge failed: %s",
                    (completed.stderr or "").strip(),
                )
                return False
            return output_path.exists()
        except Exception as exc:  # pragma: no cover
            logger.exception("Merge failed: %s", exc)
            return False
        finally:
            Path(list_path).unlink(missing_ok=True)
