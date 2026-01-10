-- Migration: 003_system_logs
-- Description: Create system_logs table for comprehensive application logging
-- Created: 2025-12-12

-- System logs table for storing all application logs
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    level VARCHAR(10) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    source VARCHAR(50) NOT NULL,  -- Component: api, scheduler, worker, ssh, snmp, database, workflow, system
    category VARCHAR(50),  -- Sub-category for filtering
    message TEXT NOT NULL,
    details JSONB,  -- Structured additional data
    
    -- Context fields
    request_id VARCHAR(36),  -- UUID for request tracing
    user_id VARCHAR(50),  -- If authentication is added
    ip_address VARCHAR(45),  -- Client IP (supports IPv6)
    
    -- Related entity references
    job_id VARCHAR(100),
    workflow_id VARCHAR(100),
    execution_id VARCHAR(36),
    device_ip VARCHAR(45),
    
    -- Metadata
    duration_ms INTEGER,  -- For timed operations
    status_code INTEGER,  -- For HTTP requests
    
    -- Indexes for common queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_source ON system_logs(source);
CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);
CREATE INDEX IF NOT EXISTS idx_system_logs_request_id ON system_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_job_id ON system_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_workflow_id ON system_logs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_execution_id ON system_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_device_ip ON system_logs(device_ip);

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_system_logs_source_level_time 
    ON system_logs(source, level, timestamp DESC);

-- Record this migration
INSERT INTO schema_versions (version, description, applied_at)
VALUES ('003', 'Add system_logs table for comprehensive logging', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;
