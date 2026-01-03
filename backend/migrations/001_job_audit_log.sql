-- Job Audit Log Schema
-- Migration: 001_job_audit_log
-- Created: 2025-12-11
-- Purpose: Track every event in job execution with links to affected database records

-- Job execution audit events
CREATE TABLE IF NOT EXISTS job_audit_events (
    id SERIAL PRIMARY KEY,
    
    -- Link to execution
    execution_id INTEGER REFERENCES scheduler_job_executions(id) ON DELETE CASCADE,
    task_id VARCHAR(255),  -- Celery task ID for correlation
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,  -- 'job_started', 'action_started', 'db_insert', 'db_update', 'db_delete', 'action_completed', 'job_completed', 'error'
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Context
    action_name VARCHAR(255),  -- Which action within the job
    action_index INTEGER,      -- Position in action list
    target_ip VARCHAR(45),     -- Target device if applicable
    
    -- Database operation details (for db_insert, db_update, db_delete events)
    table_name VARCHAR(255),   -- Which table was affected
    record_id INTEGER,         -- Primary key of affected record
    record_ids INTEGER[],      -- For bulk operations
    operation_type VARCHAR(20), -- 'insert', 'update', 'delete', 'upsert'
    
    -- Data snapshot (optional - for critical audits)
    old_values JSONB,          -- Previous values (for updates/deletes)
    new_values JSONB,          -- New values (for inserts/updates)
    
    -- Result/Error info
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    details JSONB,             -- Additional context
    
    -- Indexes for efficient querying
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_job_audit_execution_id ON job_audit_events(execution_id);
CREATE INDEX IF NOT EXISTS idx_job_audit_task_id ON job_audit_events(task_id);
CREATE INDEX IF NOT EXISTS idx_job_audit_event_type ON job_audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_job_audit_table_name ON job_audit_events(table_name);
CREATE INDEX IF NOT EXISTS idx_job_audit_timestamp ON job_audit_events(event_timestamp);

-- Record migration
INSERT INTO schema_versions (version, description) 
VALUES ('001', 'Job audit log for tracking all job events and database operations')
ON CONFLICT (version) DO NOTHING;
