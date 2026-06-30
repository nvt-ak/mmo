import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "videoscout.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS channels (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            url         TEXT NOT NULL,
            niche_tag   TEXT DEFAULT '',
            subscribers INTEGER DEFAULT 0,
            avg_views   INTEGER DEFAULT 0,
            is_active   INTEGER DEFAULT 1,
            last_scanned TEXT,
            added_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS videos (
            id              TEXT PRIMARY KEY,
            channel_id      TEXT REFERENCES channels(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            view_count      INTEGER DEFAULT 0,
            upload_date     TEXT,
            duration_sec    INTEGER DEFAULT 0,
            thumbnail_url   TEXT DEFAULT '',
            youtube_url     TEXT NOT NULL,
            opportunity_score INTEGER DEFAULT 0,
            tiktok_status   TEXT DEFAULT 'unknown',
            is_used         INTEGER DEFAULT 0,
            found_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scan_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            scanned_at       TEXT DEFAULT (datetime('now')),
            channels_scanned INTEGER DEFAULT 0,
            videos_found     INTEGER DEFAULT 0,
            top_score        INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tiktok_cache (
            keyword         TEXT PRIMARY KEY,
            video_count_7d  INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'unknown',
            checked_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
        CREATE INDEX IF NOT EXISTS idx_videos_score ON videos(opportunity_score DESC);
        CREATE INDEX IF NOT EXISTS idx_videos_used ON videos(is_used);
        CREATE INDEX IF NOT EXISTS idx_videos_found ON videos(found_at DESC);
    """)
    conn.commit()
    conn.close()
