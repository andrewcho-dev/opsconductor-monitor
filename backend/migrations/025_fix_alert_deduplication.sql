-- Migration: Fix alert deduplication race condition
-- Add partial unique index on fingerprint for non-resolved alerts

-- First, clean up existing duplicates by keeping only the oldest one
WITH duplicates AS (
    SELECT id, fingerprint, created_at,
           ROW_NUMBER() OVER (PARTITION BY fingerprint ORDER BY created_at ASC) as rn
    FROM alerts
    WHERE status != 'resolved'
),
to_delete AS (
    SELECT id FROM duplicates WHERE rn > 1
)
DELETE FROM alerts WHERE id IN (SELECT id FROM to_delete);

-- Add partial unique index to prevent future duplicates
-- Only enforces uniqueness for non-resolved alerts
DROP INDEX IF EXISTS idx_alerts_fingerprint_unique_active;
CREATE UNIQUE INDEX idx_alerts_fingerprint_unique_active 
ON alerts (fingerprint) 
WHERE status != 'resolved';

-- Log the cleanup
DO $$
DECLARE
    deleted_count INTEGER;
BEGIN
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Cleaned up duplicate alerts and added unique constraint';
END $$;
