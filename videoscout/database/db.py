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

        -- US-001: Keyword Experiment Tracking
        CREATE TABLE IF NOT EXISTS keyword_experiments (
            id                      TEXT PRIMARY KEY,
            keyword                 TEXT NOT NULL,
            channel_id              TEXT REFERENCES channels(id) ON DELETE CASCADE,
            
            -- Baseline context (for normalization)
            channel_subscribers     INTEGER,
            creator_avg_views       INTEGER,
            views_vs_baseline       REAL,
            
            -- Suggestion tracking
            suggestion_source       TEXT CHECK(suggestion_source IN ('agent_suggested', 'user_manual')),
            agent_suggested_score   INTEGER,
            
            -- Prediction
            predicted_score         INTEGER DEFAULT 0,
            prediction_reasoning    TEXT,
            predicted_at            TEXT DEFAULT (datetime('now')),
            
            -- Actual results
            actual_views            INTEGER,
            actual_engagement       REAL,
            actual_retention        REAL,
            test_status             TEXT DEFAULT 'in_progress' CHECK(test_status IN ('in_progress', 'success', 'failed', 'partial')),
            
            -- User feedback
            user_rating             INTEGER CHECK(user_rating BETWEEN 1 AND 5),
            user_comments           TEXT,
            
            -- Computed metrics
            accuracy                REAL,
            outcome_type            TEXT CHECK(outcome_type IN ('true_positive', 'false_positive', 'true_negative', 'false_negative')),
            
            reported_at             TEXT,
            created_at              TEXT DEFAULT (datetime('now'))
        );

        -- US-001: Pattern Storage
        CREATE TABLE IF NOT EXISTS keyword_patterns (
            id                  TEXT PRIMARY KEY,
            pattern_type        TEXT NOT NULL,
            keyword_trait       TEXT NOT NULL,
            outcome_type        TEXT NOT NULL,
            
            insight             TEXT NOT NULL,
            reasoning           TEXT,
            
            -- Evidence
            example_keywords    TEXT,
            occurrence_count    INTEGER DEFAULT 1,
            avg_predicted       REAL,
            avg_actual          REAL,
            
            confidence          REAL DEFAULT 0.5,
            discovered_at       TEXT DEFAULT (datetime('now')),
            last_seen_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
        CREATE INDEX IF NOT EXISTS idx_videos_score ON videos(opportunity_score DESC);
        CREATE INDEX IF NOT EXISTS idx_videos_used ON videos(is_used);
        CREATE INDEX IF NOT EXISTS idx_videos_found ON videos(found_at DESC);
        
        -- US-001: Indexes for experiment queries
        CREATE INDEX IF NOT EXISTS idx_experiments_keyword ON keyword_experiments(keyword);
        CREATE INDEX IF NOT EXISTS idx_experiments_status ON keyword_experiments(test_status);
        CREATE INDEX IF NOT EXISTS idx_experiments_source ON keyword_experiments(suggestion_source);
        CREATE INDEX IF NOT EXISTS idx_experiments_channel ON keyword_experiments(channel_id);
        CREATE INDEX IF NOT EXISTS idx_experiments_created ON keyword_experiments(created_at DESC);
        
        CREATE INDEX IF NOT EXISTS idx_patterns_trait ON keyword_patterns(keyword_trait);
        CREATE INDEX IF NOT EXISTS idx_patterns_outcome ON keyword_patterns(outcome_type);
        CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON keyword_patterns(confidence DESC);
    """)
    conn.commit()
    conn.close()
