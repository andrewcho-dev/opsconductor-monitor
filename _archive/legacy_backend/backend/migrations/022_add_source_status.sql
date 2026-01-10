-- Migration: Add source_status column to alerts table
-- Date: 2026-01-07
-- Description: Adds source_status column to store the raw status from the source system
--              This supports the new source-system-driven status model where OpsConductor
--              mirrors the originating system's state.

-- Add source_status column
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source_status VARCHAR(100);

-- Add comment
COMMENT ON COLUMN alerts.source_status IS 'Human-readable status from source system (e.g., "Down", "Warning", "Paused (User)")';

-- Update schema version
INSERT INTO schema_versions (version, description, applied_at)
VALUES ('022', 'Add source_status column to alerts', NOW())
ON CONFLICT (version) DO NOTHING;
