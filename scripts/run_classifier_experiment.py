#!/usr/bin/env python3
"""
Appendix B — classifier agreement experiment runner.

Day run: fetch YouTube trending → extract keyword candidates → proposed_tag.
Operator fills operator_tag in CSV; score with --score.

Usage:
  python scripts/run_classifier_experiment.py --day 1 --region DE
  python scripts/run_classifier_experiment.py --score docs/superpowers/validation/classifier-day1.csv
  python scripts/run_classifier_experiment.py --db-calibrate
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from videoscout.core_engine.keyword_classifier import classify_keyword_type

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "shall", "can", "need", "dare", "ought", "used",
    "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
    "when", "where", "why", "how", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "don", "now", "new", "official",
    "video", "full", "hd", "4k", "ft", "feat", "vs", "ep", "part", "trailer",
    "reaction", "live", "stream", "shorts",
}


def _load_env() -> None:
    env_path = REPO_ROOT / "videoscout" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def extract_keyword_candidates(title: str, max_phrases: int = 3) -> list[str]:
    """Extract 2–5 word phrases from a trending video title."""
    cleaned = re.sub(r"[^\w\s-]", " ", title.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOPWORDS and len(t) > 1]
    if len(tokens) < 2:
        return []

    phrases: list[str] = []
    for width in (3, 2, 4, 5):
        for i in range(len(tokens) - width + 1):
            phrase = " ".join(tokens[i : i + width])
            if 2 <= width <= 5 and phrase not in phrases:
                phrases.append(phrase)
            if len(phrases) >= max_phrases:
                return phrases[:max_phrases]
    return phrases[:max_phrases]


def fetch_trending_candidates(region: str, max_videos: int) -> list[dict]:
    _load_env()
    from videoscout.services.youtube import get_youtube_service

    yt = get_youtube_service()
    response = yt.client.videos().list(
        part="snippet",
        chart="mostPopular",
        regionCode=region,
        maxResults=max_videos,
    ).execute()

    rows: list[dict] = []
    seen: set[str] = set()
    for item in response.get("items", []):
        title = item.get("snippet", {}).get("title", "")
        for kw in extract_keyword_candidates(title):
            key = kw.lower()
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "keyword": kw,
                    "phrase_words": len(kw.split()),
                    "trend_source": "youtube_trend",
                    "tiktok_7d": "",
                    "saturation": "moderate",
                    "source_title": title[:80],
                }
            )
    return rows


def run_day(day: int, region: str, max_videos: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_path = out_dir / f"classifier-day{day}-{today}.csv"

    candidates = fetch_trending_candidates(region, max_videos)
    if len(candidates) < 10:
        print(f"WARN: only {len(candidates)} candidates (target 20/day)")

    fieldnames = [
        "date",
        "keyword",
        "phrase_words",
        "trend_source",
        "tiktok_7d",
        "saturation",
        "operator_tag",
        "proposed_tag",
        "agree",
        "reason",
        "source_title",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in candidates[:20]:
            proposed = classify_keyword_type(
                row["keyword"],
                trend_source=row["trend_source"],
                saturation_tier=row["saturation"],
            )
            writer.writerow(
                {
                    "date": today,
                    "keyword": row["keyword"],
                    "phrase_words": row["phrase_words"],
                    "trend_source": row["trend_source"],
                    "tiktok_7d": row["tiktok_7d"],
                    "saturation": row["saturation"],
                    "operator_tag": "",
                    "proposed_tag": proposed,
                    "agree": "",
                    "reason": "",
                    "source_title": row["source_title"],
                }
            )

    print(f"Wrote {min(len(candidates), 20)} rows → {out_path}")
    print("Next: operator fills operator_tag (nurture|beta), then:")
    print(f"  python scripts/run_classifier_experiment.py --score {out_path}")
    return out_path


def score_csv(path: Path) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    tagged = [r for r in rows if r.get("operator_tag", "").strip() in ("nurture", "beta")]
    if not tagged:
        print("No operator_tag rows — fill CSV first")
        return {}

    agree = 0
    nurture_agree = nurture_total = beta_agree = beta_total = 0
    for r in tagged:
        op = r["operator_tag"].strip()
        prop = r.get("proposed_tag", "").strip()
        match = op == prop
        if match:
            agree += 1
        r["agree"] = "yes" if match else "no"
        if op == "nurture":
            nurture_total += 1
            if match:
                nurture_agree += 1
        else:
            beta_total += 1
            if match:
                beta_agree += 1

    # Rewrite with agree column
    if tagged:
        fieldnames = list(rows[0].keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    total = len(tagged)
    pct = 100.0 * agree / total if total else 0.0
    nurture_pct = 100.0 * nurture_agree / nurture_total if nurture_total else 0.0
    beta_pct = 100.0 * beta_agree / beta_total if beta_total else 0.0

    result = {
        "total_tagged": total,
        "agreement_pct": round(pct, 1),
        "nurture_agreement_pct": round(nurture_pct, 1),
        "beta_agreement_pct": round(beta_pct, 1),
        "gate_pass": pct >= 80.0,
    }
    print(f"Agreement: {pct:.1f}% ({agree}/{total})")
    print(f"  Nurture: {nurture_pct:.1f}% ({nurture_agree}/{nurture_total})")
    print(f"  Beta:    {beta_pct:.1f}% ({beta_agree}/{beta_total})")
    print(f"Gate ≥80%: {'PASS' if result['gate_pass'] else 'FAIL'}")
    return result


def db_calibrate() -> None:
    _load_env()
    from videoscout.db import get_session
    from videoscout.core_engine.classifier_calibration import (
        build_classifier_calibration,
        summarize_calibration,
    )

    db = get_session()
    try:
        calibration = build_classifier_calibration(db)
        print(summarize_calibration(calibration))
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Classifier agreement experiment")
    parser.add_argument("--day", type=int, help="Experiment day number (1–7)")
    parser.add_argument("--region", default="DE", help="YouTube trending region")
    parser.add_argument("--max-videos", type=int, default=25)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "superpowers" / "validation",
    )
    parser.add_argument("--score", type=Path, help="Score existing CSV after operator tags")
    parser.add_argument(
        "--db-calibrate",
        action="store_true",
        help="Print performance-report calibration summary from database",
    )
    args = parser.parse_args()

    if args.db_calibrate:
        db_calibrate()
        return

    if args.score:
        score_csv(args.score)
        return

    if not args.day:
        parser.error("--day required unless --score")
    run_day(args.day, args.region, args.max_videos, args.out_dir)


if __name__ == "__main__":
    main()
