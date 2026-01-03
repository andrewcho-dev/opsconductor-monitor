-- ============================================================================
-- Migration: 016_execution_progress
-- Description: Adds progress tracking for real-time execution visibility
-- ============================================================================

-- ADD PROGRESS COLUMN TO SCHEDULER_JOB_EXECUTIONS
ALTER TABLE scheduler_job_executions 
ADD COLUMN IF NOT EXISTS progress JSONB DEFAULT '{"steps": [], "current_step": null, "percent": 0}'::jsonb;

COMMENT ON COLUMN scheduler_job_executions.progress IS 'Real-time progress: {steps: [{name, status, started_at, finished_at, message}], current_step, percent, message}';

-- Create index for querying running executions with progress
CREATE INDEX IF NOT EXISTS idx_sje_status_progress 
ON scheduler_job_executions (status) WHERE status = 'running';

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO schema_versions (version, description) 
VALUES ('016', 'Add progress column to scheduler_job_executions for real-time tracking')
ON CONFLICT (version) DO NOTHING;
