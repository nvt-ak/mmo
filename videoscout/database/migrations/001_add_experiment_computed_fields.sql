-- Migration 001: Add computed fields and cleanup for US-001
-- Author: Phase 1 cleanup
-- Date: 2026-06-30

-- Add actual_score column (computed from views+engagement)
ALTER TABLE keyword_experiments ADD COLUMN actual_score REAL;

-- Add keyword_traits column (JSON array of traits)
ALTER TABLE keyword_experiments ADD COLUMN keyword_traits TEXT;

-- Add account_label (free-text TikTok account, decouple from YouTube FK)
ALTER TABLE keyword_experiments ADD COLUMN account_label TEXT;

-- Make channel_id truly optional (already nullable in schema)
-- No FK enforcement change needed - already has ON DELETE CASCADE

-- Add suggested_adjustment to patterns
ALTER TABLE keyword_patterns ADD COLUMN suggested_adjustment TEXT;

-- Add experiment_ids to patterns (JSON array linking evidence)
ALTER TABLE keyword_patterns ADD COLUMN experiment_ids TEXT;

-- Add index on actual_score for pattern analysis queries
CREATE INDEX IF NOT EXISTS idx_experiments_actual_score ON keyword_experiments(actual_score DESC);
