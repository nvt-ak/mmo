import csv
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication


def to_clipboard(videos: list[dict]):
    """Copy YouTube URLs to clipboard, one per line."""
    urls = "\n".join(v["youtube_url"] for v in videos)
    QApplication.clipboard().setText(urls)


def to_txt(videos: list[dict], path: Path):
    path.write_text(
        "\n".join(v["youtube_url"] for v in videos), encoding="utf-8"
    )


def to_csv(videos: list[dict], path: Path):
    if not videos:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "channel_name", "view_count",
                        "upload_date", "opportunity_score",
                        "tiktok_status", "youtube_url"],
        )
        writer.writeheader()
        for v in videos:
            writer.writerow({k: v.get(k, "") for k in writer.fieldnames})


def to_json(videos: list[dict], path: Path):
    path.write_text(
        json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
