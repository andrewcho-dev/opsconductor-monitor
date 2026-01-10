-- Migration 020: MVP Alert Aggregation Tables
-- Date: 2026-01-06
-- Description: Create tables for MVP alert aggregation platform

BEGIN;

-- ============================================
-- 1. Create updated_at trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- 2. Create alerts table
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system VARCHAR(50) NOT NULL,
    source_alert_id VARCHAR(255) NOT NULL,
    device_ip VARCHAR(45),
    device_name VARCHAR(255),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'major', 'minor', 'warning', 'info', 'clear')),
    category VARCHAR(50) NOT NULL CHECK (category IN ('network', 'power', 'video', 'wireless', 'security', 'environment', 'compute', 'storage', 'application', 'unknown')),
    alert_type VARCHAR(100) NOT NULL,
    impact VARCHAR(20) CHECK (impact IN ('high', 'medium', 'low')),
    urgency VARCHAR(20) CHECK (urgency IN ('high', 'medium', 'low')),
    priority VARCHAR(5) CHECK (priority IN ('P1', 'P2', 'P3', 'P4', 'P5')),
    title VARCHAR(255) NOT NULL,
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'suppressed', 'resolved', 'expired')),
    is_clear BOOLEAN DEFAULT FALSE,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    correlated_to_id UUID REFERENCES alerts(id),
    correlation_rule VARCHAR(255),
    tags TEXT[],
    custom_fields JSONB DEFAULT '{}',
    raw_data JSONB NOT NULL DEFAULT '{}',
    fingerprint VARCHAR(64),
    occurrence_count INTEGER DEFAULT 1,
    last_occurrence_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT alerts_device_required CHECK (device_ip IS NOT NULL OR device_name IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON alerts(category);
CREATE INDEX IF NOT EXISTS idx_alerts_device_ip ON alerts(device_ip);
CREATE INDEX IF NOT EXISTS idx_alerts_occurred_at ON alerts(occurred_at);
CREATE INDEX IF NOT EXISTS idx_alerts_source_system ON alerts(source_system);
CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(status) WHERE status = 'active';

DROP TRIGGER IF EXISTS alerts_updated_at ON alerts;
CREATE TRIGGER alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. Create alert_history table
-- ============================================
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    user_id VARCHAR(100),
    user_name VARCHAR(255),
    notes TEXT,
    changes JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_created_at ON alert_history(created_at);

-- ============================================
-- 4. Create dependencies table
-- ============================================
CREATE TABLE IF NOT EXISTS dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_ip VARCHAR(45) NOT NULL,
    depends_on_ip VARCHAR(45) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'network' CHECK (dependency_type IN ('network', 'power', 'service')),
    description TEXT,
    auto_discovered BOOLEAN DEFAULT FALSE,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT dependencies_no_self_reference CHECK (device_ip != depends_on_ip),
    CONSTRAINT dependencies_unique UNIQUE (device_ip, depends_on_ip, dependency_type)
);

CREATE INDEX IF NOT EXISTS idx_dependencies_device_ip ON dependencies(device_ip);
CREATE INDEX IF NOT EXISTS idx_dependencies_depends_on_ip ON dependencies(depends_on_ip);

DROP TRIGGER IF EXISTS dependencies_updated_at ON dependencies;
CREATE TRIGGER dependencies_updated_at
    BEFORE UPDATE ON dependencies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. Create connectors table
-- ============================================
CREATE TABLE IF NOT EXISTS connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'unknown' CHECK (status IN ('connected', 'disconnected', 'error', 'unknown')),
    error_message TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    last_poll_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    alerts_received INTEGER DEFAULT 0,
    alerts_today INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_connectors_type ON connectors(type);
CREATE INDEX IF NOT EXISTS idx_connectors_enabled ON connectors(enabled);

DROP TRIGGER IF EXISTS connectors_updated_at ON connectors;
CREATE TRIGGER connectors_updated_at
    BEFORE UPDATE ON connectors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 6. Create oid_mappings table
-- ============================================
CREATE TABLE IF NOT EXISTS oid_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oid_pattern VARCHAR(255) NOT NULL,
    vendor VARCHAR(50),
    alert_type VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('network', 'power', 'video', 'wireless', 'security', 'environment', 'compute', 'storage', 'application', 'unknown')),
    default_severity VARCHAR(20) NOT NULL CHECK (default_severity IN ('critical', 'major', 'minor', 'warning', 'info', 'clear')),
    title_template VARCHAR(255),
    description TEXT,
    is_clear_event BOOLEAN DEFAULT FALSE,
    clear_oid_pattern VARCHAR(255),
    mib_name VARCHAR(100),
    mib_object VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT oid_mappings_unique UNIQUE (oid_pattern, vendor)
);

CREATE INDEX IF NOT EXISTS idx_oid_mappings_oid_pattern ON oid_mappings(oid_pattern);
CREATE INDEX IF NOT EXISTS idx_oid_mappings_vendor ON oid_mappings(vendor);

-- ============================================
-- 7. Create notification_rules table
-- ============================================
CREATE TABLE IF NOT EXISTS notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    conditions JSONB NOT NULL DEFAULT '{}',
    channels JSONB NOT NULL DEFAULT '[]',
    throttle_minutes INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_enabled ON notification_rules(enabled);

-- ============================================
-- 8. Create notification_log table
-- ============================================
CREATE TABLE IF NOT EXISTS notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES alerts(id),
    rule_id UUID REFERENCES notification_rules(id),
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('sent', 'failed', 'pending')),
    error_message TEXT,
    payload JSONB,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_notification_log_alert_id ON notification_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log(status);

-- ============================================
-- 9. Seed standard OID mappings
-- ============================================
INSERT INTO oid_mappings (oid_pattern, vendor, alert_type, category, default_severity, title_template, description, is_clear_event) VALUES
-- Standard RFC 3418 traps
('1.3.6.1.6.3.1.1.5.1', NULL, 'cold_start', 'network', 'warning', 'Device Cold Start - {device_name}', 'Device has rebooted (cold start)', false),
('1.3.6.1.6.3.1.1.5.2', NULL, 'warm_start', 'network', 'info', 'Device Warm Start - {device_name}', 'Device has rebooted (warm start)', false),
('1.3.6.1.6.3.1.1.5.3', NULL, 'link_down', 'network', 'major', 'Interface Down - {device_name}', 'Network interface has gone down', false),
('1.3.6.1.6.3.1.1.5.4', NULL, 'link_up', 'network', 'clear', 'Interface Up - {device_name}', 'Network interface has come up', true),
('1.3.6.1.6.3.1.1.5.5', NULL, 'auth_failure', 'security', 'warning', 'Auth Failure - {device_name}', 'SNMP authentication failure', false),

-- Ciena WWP-LEOS alarms (enterprise 6141)
('1.3.6.1.4.1.6141.2.60.5.1.2.1.*', 'ciena', 'optical_power_alarm', 'network', 'major', 'Optical Power Alarm - {device_name}', 'Optical transceiver power outside thresholds', false),
('1.3.6.1.4.1.6141.2.60.5.1.1.*', 'ciena', 'equipment_alarm', 'network', 'critical', 'Equipment Alarm - {device_name}', 'Hardware component failure', false),

-- Eaton UPS alarms (enterprise 534)
('1.3.6.1.4.1.534.1.7.3.*', 'eaton', 'on_battery', 'power', 'warning', 'UPS On Battery - {device_name}', 'UPS running on battery power', false),
('1.3.6.1.4.1.534.1.7.4.*', 'eaton', 'low_battery', 'power', 'critical', 'UPS Low Battery - {device_name}', 'UPS battery critically low', false),
('1.3.6.1.4.1.534.1.7.5.*', 'eaton', 'utility_restored', 'power', 'clear', 'UPS Utility Restored - {device_name}', 'AC power restored to UPS', true),
('1.3.6.1.4.1.534.1.7.7.*', 'eaton', 'battery_bad', 'power', 'major', 'UPS Battery Bad - {device_name}', 'UPS battery needs replacement', false),
('1.3.6.1.4.1.534.1.7.8.*', 'eaton', 'output_overload', 'power', 'critical', 'UPS Output Overload - {device_name}', 'UPS load exceeds capacity', false)

ON CONFLICT DO NOTHING;

-- ============================================
-- 10. Seed default connectors
-- ============================================
INSERT INTO connectors (name, type, enabled, status, config) VALUES
('PRTG', 'prtg', false, 'unknown', '{"url": "", "api_token": "", "poll_interval": 60, "verify_ssl": true}'),
('MCP', 'mcp', false, 'unknown', '{"url": "", "username": "", "password": "", "poll_interval": 60, "verify_ssl": false}'),
('SNMP Traps', 'snmp_trap', false, 'unknown', '{"port": 162, "community": "public"}'),
('SNMP Polling', 'snmp_poll', false, 'unknown', '{"targets": [], "poll_interval": 300}'),
('Eaton UPS', 'eaton', false, 'unknown', '{"targets": [], "poll_interval": 60}'),
('Axis Cameras', 'axis', false, 'unknown', '{"targets": [], "poll_interval": 60}'),
('Milestone VMS', 'milestone', false, 'unknown', '{"url": "", "username": "", "password": ""}'),
('Cradlepoint', 'cradlepoint', false, 'unknown', '{"targets": [], "poll_interval": 60}'),
('Siklu', 'siklu', false, 'unknown', '{"targets": [], "poll_interval": 60}'),
('Ubiquiti UISP', 'ubiquiti', false, 'unknown', '{"url": "", "api_token": ""}')
ON CONFLICT (name) DO NOTHING;

COMMIT;
