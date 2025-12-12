-- Migration: 004_system_alerts
-- Description: Create system_alerts table for persistent alert management
-- Created: 2025-12-12

-- Alert rules configuration table
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, critical
    category VARCHAR(50) NOT NULL,  -- logs, jobs, infrastructure, custom
    
    -- Rule configuration (JSON)
    condition_type VARCHAR(50) NOT NULL,  -- error_rate, error_count, job_failures, worker_count, custom_query
    condition_config JSONB NOT NULL,  -- threshold, time_window, source filter, etc.
    
    -- Cooldown to prevent alert spam
    cooldown_minutes INTEGER DEFAULT 60,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System alerts table
CREATE TABLE IF NOT EXISTS system_alerts (
    id SERIAL PRIMARY KEY,
    
    -- Alert identification
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE SET NULL,
    alert_key VARCHAR(255) NOT NULL,  -- Unique key for deduplication (rule_name + context)
    
    -- Alert details
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, critical
    category VARCHAR(50) NOT NULL,  -- logs, jobs, infrastructure, custom
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,  -- Additional context (affected jobs, error samples, etc.)
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, acknowledged, resolved, expired
    
    -- Timestamps
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,  -- Auto-expire old alerts
    
    -- Prevent duplicate active alerts
    CONSTRAINT unique_active_alert UNIQUE (alert_key, status) 
        DEFERRABLE INITIALLY DEFERRED
);

-- Alert history for resolved/expired alerts (for reporting)
CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    original_alert_id INTEGER,
    rule_id INTEGER,
    alert_key VARCHAR(255),
    severity VARCHAR(20),
    category VARCHAR(50),
    title VARCHAR(255),
    message TEXT,
    details JSONB,
    status VARCHAR(20),
    triggered_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_system_alerts_status ON system_alerts(status);
CREATE INDEX IF NOT EXISTS idx_system_alerts_severity ON system_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_system_alerts_category ON system_alerts(category);
CREATE INDEX IF NOT EXISTS idx_system_alerts_triggered_at ON system_alerts(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_alerts_alert_key ON system_alerts(alert_key);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at ON alert_history(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled);

-- Insert default alert rules
INSERT INTO alert_rules (name, description, severity, category, condition_type, condition_config, cooldown_minutes)
VALUES 
    ('high_error_rate', 'High error rate in system logs', 'warning', 'logs', 'error_rate', 
     '{"threshold": 10, "time_window_minutes": 60, "levels": ["ERROR", "CRITICAL"]}', 60),
    
    ('critical_errors', 'Critical errors detected', 'critical', 'logs', 'error_count',
     '{"threshold": 1, "time_window_minutes": 60, "levels": ["CRITICAL"]}', 30),
    
    ('job_failures', 'Multiple job failures', 'warning', 'jobs', 'job_failure_count',
     '{"threshold": 3, "time_window_minutes": 60}', 60),
    
    ('worker_offline', 'Celery workers offline', 'critical', 'infrastructure', 'worker_count',
     '{"min_workers": 1}', 5),
    
    ('long_running_job', 'Job running longer than expected', 'warning', 'jobs', 'long_running_job',
     '{"max_duration_minutes": 30}', 15)
ON CONFLICT (name) DO NOTHING;

-- Record this migration
INSERT INTO schema_versions (version, description, applied_at)
VALUES ('004', 'Add system_alerts tables for persistent alert management', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;
