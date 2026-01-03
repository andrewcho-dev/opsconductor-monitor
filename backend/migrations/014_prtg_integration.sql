-- PRTG Integration Tables
-- Migration: 014_prtg_integration.sql

-- Table for storing PRTG alerts received via webhook
CREATE TABLE IF NOT EXISTS prtg_alerts (
    id SERIAL PRIMARY KEY,
    prtg_object_id VARCHAR(50),
    device_id VARCHAR(50),
    device_name VARCHAR(255),
    sensor_id VARCHAR(50),
    sensor_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',  -- active, acknowledged, resolved
    severity VARCHAR(50),  -- down, warning, unusual, up
    message TEXT,
    last_message TEXT,
    duration VARCHAR(100),
    probe VARCHAR(255),
    device_group VARCHAR(255),
    priority VARCHAR(50),
    tags TEXT,
    host VARCHAR(255),
    last_value TEXT,
    raw_data JSONB,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(255),
    resolved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_prtg_alerts_status ON prtg_alerts(status);
CREATE INDEX IF NOT EXISTS idx_prtg_alerts_severity ON prtg_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_prtg_alerts_sensor_id ON prtg_alerts(sensor_id);
CREATE INDEX IF NOT EXISTS idx_prtg_alerts_device_name ON prtg_alerts(device_name);
CREATE INDEX IF NOT EXISTS idx_prtg_alerts_created_at ON prtg_alerts(created_at);

-- Table for PRTG device cache (for faster lookups and NetBox sync)
CREATE TABLE IF NOT EXISTS prtg_devices (
    id SERIAL PRIMARY KEY,
    prtg_id VARCHAR(50) UNIQUE NOT NULL,
    device_name VARCHAR(255),
    host VARCHAR(255),
    device_group VARCHAR(255),
    probe VARCHAR(255),
    status VARCHAR(50),
    device_type VARCHAR(255),
    tags TEXT,
    location TEXT,
    comments TEXT,
    netbox_device_id INTEGER,  -- Link to NetBox device if synced
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prtg_devices_prtg_id ON prtg_devices(prtg_id);
CREATE INDEX IF NOT EXISTS idx_prtg_devices_host ON prtg_devices(host);
CREATE INDEX IF NOT EXISTS idx_prtg_devices_netbox_id ON prtg_devices(netbox_device_id);

-- Table for PRTG sync history
CREATE TABLE IF NOT EXISTS prtg_sync_history (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50),  -- devices, netbox
    status VARCHAR(50),  -- running, completed, failed
    total_processed INTEGER DEFAULT 0,
    created INTEGER DEFAULT 0,
    updated INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    error_details JSONB,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    initiated_by VARCHAR(255)
);

-- Add PRTG settings to settings table if not exists
INSERT INTO settings (key, value, updated_at) 
VALUES 
    ('prtg_url', '', CURRENT_TIMESTAMP),
    ('prtg_api_token', '', CURRENT_TIMESTAMP),
    ('prtg_username', '', CURRENT_TIMESTAMP),
    ('prtg_passhash', '', CURRENT_TIMESTAMP),
    ('prtg_verify_ssl', 'true', CURRENT_TIMESTAMP),
    ('prtg_enabled', 'false', CURRENT_TIMESTAMP),
    ('prtg_sync_interval', '300', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;
