-- OpsConductor Execution User Tracking
-- Migration: 015_execution_triggered_by
-- Created: 2025-12-17
-- Description: Adds triggered_by column to track who initiated job/workflow executions

-- ============================================================================
-- ADD TRIGGERED_BY TO SCHEDULER_JOB_EXECUTIONS
-- ============================================================================
ALTER TABLE scheduler_job_executions 
ADD COLUMN IF NOT EXISTS triggered_by JSONB DEFAULT NULL;

COMMENT ON COLUMN scheduler_job_executions.triggered_by IS 'JSON object containing user info: {user_id, username, display_name, is_enterprise}';

-- Create index for querying by user
CREATE INDEX IF NOT EXISTS idx_sje_triggered_by_username 
ON scheduler_job_executions ((triggered_by->>'username'));

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO schema_versions (version, description) 
VALUES ('015', 'Add triggered_by column to scheduler_job_executions')
ON CONFLICT (version) DO NOTHING;
