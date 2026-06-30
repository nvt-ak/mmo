"""
DB Migrations for Agent System
"""
from database.db import get_connection
from utils.logger import get_logger

log = get_logger("migrations")


def migrate_agent_tables():
    """Add tables for agent outcomes and loop history."""
    conn = get_connection()
    
    # Channel outcomes table (for learning)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channel_outcomes (
            channel_id      TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            subscribers     INTEGER DEFAULT 0,
            videos_found    INTEGER DEFAULT 0,
            avg_video_score REAL DEFAULT 0,
            llm_score       INTEGER,
            llm_recommendation TEXT,
            llm_reasoning   TEXT,
            outcome         TEXT DEFAULT 'unknown',
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Agent loop history
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_loops (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            loop_type       TEXT NOT NULL,
            discovered      INTEGER DEFAULT 0,
            evaluated       INTEGER DEFAULT 0,
            recommended     INTEGER DEFAULT 0,
            auto_followed   INTEGER DEFAULT 0,
            learning_status TEXT,
            result_json     TEXT,
            started_at      TEXT DEFAULT (datetime('now')),
            completed_at    TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    log.info("Agent tables migrated successfully")


if __name__ == "__main__":
    migrate_agent_tables()
