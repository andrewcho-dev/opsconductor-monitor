-- ============================================================================
-- OpsConductor Database Migration 002: Add Polling Configuration Tables
-- ============================================================================
-- This migration adds tables for managing SNMP polling configurations,
-- allowing granular control over polling schedules, targets, and parameters.
--
-- Run with: PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan -f 002_add_polling_configs.sql
-- ============================================================================

BEGIN;

-- Check if already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '002') THEN
        RAISE EXCEPTION 'Migration 002 already applied';
    END IF;
END $$;

-- ============================================================================
-- 1. POLLING CONFIGURATIONS
-- ============================================================================

-- Main polling configuration table
CREATE TABLE IF NOT EXISTS polling_configs (
    id SERIAL PRIMARY KEY,
    
    -- Identity
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    
    -- Polling type
    poll_type VARCHAR(50) NOT NULL,  -- 'snmp_optical', 'snmp_interfaces', 'snmp_availability', 'snmp_ciena_full'
    
    -- Schedule
    enabled BOOLEAN DEFAULT TRUE,
    interval_seconds INTEGER NOT NULL DEFAULT 300,  -- 5 minutes default
    cron_expression VARCHAR(100),  -- Alternative to interval
    
    -- Target selection (one of these should be set)
    target_type VARCHAR(30) NOT NULL,  -- 'all', 'device', 'device_group', 'site', 'role', 'manufacturer', 'custom_query'
    target_device_ip INET,
    target_device_ids INTEGER[],
    target_site_id INTEGER,
    target_site_name VARCHAR(255),
    target_role VARCHAR(100),
    target_manufacturer VARCHAR(100),
    target_custom_filter JSONB,  -- For complex filters
    
    -- SNMP Parameters
    snmp_community VARCHAR(100) DEFAULT 'public',
    snmp_version VARCHAR(10) DEFAULT '2c',  -- '1', '2c', '3'
    snmp_port INTEGER DEFAULT 161,
    snmp_timeout INTEGER DEFAULT 5,  -- seconds
    snmp_retries INTEGER DEFAULT 2,
    
    -- SNMPv3 parameters (if version = '3')
    snmpv3_username VARCHAR(100),
    snmpv3_auth_protocol VARCHAR(20),  -- 'MD5', 'SHA'
    snmpv3_auth_password VARCHAR(255),
    snmpv3_priv_protocol VARCHAR(20),  -- 'DES', 'AES'
    snmpv3_priv_password VARCHAR(255),
    
    -- Performance tuning
    max_concurrent INTEGER DEFAULT 50,
    batch_size INTEGER DEFAULT 25,
    
    -- Metadata
    tags TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    
    -- Last execution info
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(20),
    last_run_duration_ms INTEGER,
    last_run_devices_polled INTEGER,
    last_run_devices_success INTEGER,
    last_run_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_polling_configs_type ON polling_configs (poll_type);
CREATE INDEX IF NOT EXISTS idx_polling_configs_enabled ON polling_configs (enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_polling_configs_target ON polling_configs (target_type);

-- ============================================================================
-- 2. POLLING EXECUTION HISTORY
-- ============================================================================

-- Detailed execution history for each polling run
CREATE TABLE IF NOT EXISTS polling_executions (
    id BIGSERIAL PRIMARY KEY,
    config_id INTEGER REFERENCES polling_configs(id) ON DELETE CASCADE,
    config_name VARCHAR(100),
    
    -- Execution details
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Results
    status VARCHAR(20) NOT NULL,  -- 'running', 'success', 'partial', 'failed'
    devices_targeted INTEGER,
    devices_polled INTEGER,
    devices_success INTEGER,
    devices_failed INTEGER,
    records_collected INTEGER,
    
    -- Errors
    error_message TEXT,
    error_details JSONB,
    
    -- Trigger info
    triggered_by VARCHAR(50),  -- 'schedule', 'manual', 'api'
    celery_task_id VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_polling_exec_config ON polling_executions (config_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_polling_exec_status ON polling_executions (status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_polling_exec_time ON polling_executions (started_at DESC);

-- ============================================================================
-- 3. DEVICE-LEVEL POLLING RESULTS
-- ============================================================================

-- Per-device results for each polling execution
CREATE TABLE IF NOT EXISTS polling_device_results (
    id BIGSERIAL PRIMARY KEY,
    execution_id BIGINT REFERENCES polling_executions(id) ON DELETE CASCADE,
    
    device_ip INET NOT NULL,
    device_name VARCHAR(255),
    
    -- Result
    status VARCHAR(20) NOT NULL,  -- 'success', 'timeout', 'auth_error', 'unreachable', 'error'
    duration_ms INTEGER,
    records_collected INTEGER,
    
    -- Error info
    error_message TEXT,
    
    polled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_polling_device_exec ON polling_device_results (execution_id);
CREATE INDEX IF NOT EXISTS idx_polling_device_ip ON polling_device_results (device_ip, polled_at DESC);

-- ============================================================================
-- 4. DEFAULT POLLING CONFIGURATIONS
-- ============================================================================

-- Insert default polling configurations
INSERT INTO polling_configs (name, description, poll_type, target_type, interval_seconds, snmp_community, tags)
VALUES 
    ('Ciena Optical Power', 'Poll optical TX/RX power from Ciena switches using WWP-LEOS MIB', 
     'snmp_ciena_optical', 'manufacturer', 300, 'public', ARRAY['ciena', 'optical']),
    
    ('Ciena Full Poll', 'Full SNMP poll of Ciena switches (optical, traffic, alarms, rings)', 
     'snmp_ciena_full', 'manufacturer', 300, 'public', ARRAY['ciena', 'full']),
    
    ('Network Availability', 'Check SNMP reachability for all devices', 
     'snmp_availability', 'all', 60, 'public', ARRAY['availability']),
    
    ('Interface Statistics', 'Collect interface traffic counters from switches', 
     'snmp_interfaces', 'role', 300, 'public', ARRAY['interfaces', 'traffic'])
ON CONFLICT (name) DO NOTHING;

-- Set manufacturer filter for Ciena configs
UPDATE polling_configs SET target_manufacturer = 'Ciena' WHERE name LIKE 'Ciena%';
UPDATE polling_configs SET target_role = 'Backbone Switch' WHERE name = 'Interface Statistics';

-- ============================================================================
-- 5. HELPER VIEWS
-- ============================================================================

-- View for active polling schedules with next run time
CREATE OR REPLACE VIEW v_polling_schedules AS
SELECT 
    pc.id,
    pc.name,
    pc.description,
    pc.poll_type,
    pc.enabled,
    pc.interval_seconds,
    pc.target_type,
    pc.target_manufacturer,
    pc.target_role,
    pc.target_site_name,
    pc.snmp_community,
    pc.last_run_at,
    pc.last_run_status,
    pc.last_run_duration_ms,
    pc.last_run_devices_polled,
    pc.tags,
    CASE 
        WHEN pc.last_run_at IS NULL THEN NOW()
        ELSE pc.last_run_at + (pc.interval_seconds || ' seconds')::INTERVAL
    END AS next_run_at
FROM polling_configs pc
WHERE pc.enabled = TRUE;

-- View for recent polling execution summary
CREATE OR REPLACE VIEW v_polling_summary AS
SELECT 
    pc.id AS config_id,
    pc.name AS config_name,
    pc.poll_type,
    pc.enabled,
    COUNT(pe.id) AS total_executions,
    COUNT(CASE WHEN pe.status = 'success' THEN 1 END) AS successful_executions,
    COUNT(CASE WHEN pe.status = 'failed' THEN 1 END) AS failed_executions,
    AVG(pe.duration_ms) AS avg_duration_ms,
    MAX(pe.started_at) AS last_execution,
    SUM(pe.records_collected) AS total_records_collected
FROM polling_configs pc
LEFT JOIN polling_executions pe ON pc.id = pe.config_id 
    AND pe.started_at > NOW() - INTERVAL '24 hours'
GROUP BY pc.id, pc.name, pc.poll_type, pc.enabled;

-- ============================================================================
-- Record successful migration
-- ============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('002', 'Add polling configuration tables for granular SNMP polling management');

COMMIT;
