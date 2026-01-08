-- Migration 021: Normalization Rules Tables
-- Date: 2026-01-07
-- Description: Create tables for configurable alert normalization rules

BEGIN;

-- ============================================
-- 1. Severity Mapping Rules
-- ============================================
CREATE TABLE IF NOT EXISTS severity_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_type VARCHAR(50) NOT NULL,
    source_value VARCHAR(100) NOT NULL,
    source_field VARCHAR(50) NOT NULL DEFAULT 'status',
    target_severity VARCHAR(20) NOT NULL CHECK (target_severity IN ('critical', 'major', 'minor', 'warning', 'info', 'clear')),
    priority INTEGER DEFAULT 100,
    enabled BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (connector_type, source_value, source_field)
);

CREATE INDEX IF NOT EXISTS idx_severity_mappings_connector ON severity_mappings(connector_type);
CREATE INDEX IF NOT EXISTS idx_severity_mappings_enabled ON severity_mappings(enabled);

-- ============================================
-- 2. Category Mapping Rules
-- ============================================
CREATE TABLE IF NOT EXISTS category_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_type VARCHAR(50) NOT NULL,
    source_value VARCHAR(100) NOT NULL,
    source_field VARCHAR(50) NOT NULL DEFAULT 'type',
    target_category VARCHAR(50) NOT NULL CHECK (target_category IN ('network', 'power', 'video', 'wireless', 'security', 'environment', 'compute', 'storage', 'application', 'unknown')),
    priority INTEGER DEFAULT 100,
    enabled BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (connector_type, source_value, source_field)
);

CREATE INDEX IF NOT EXISTS idx_category_mappings_connector ON category_mappings(connector_type);
CREATE INDEX IF NOT EXISTS idx_category_mappings_enabled ON category_mappings(enabled);

-- ============================================
-- 3. Impact/Urgency Rules (for priority calculation)
-- ============================================
CREATE TABLE IF NOT EXISTS priority_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    impact VARCHAR(20) CHECK (impact IN ('high', 'medium', 'low')),
    urgency VARCHAR(20) CHECK (urgency IN ('high', 'medium', 'low')),
    priority VARCHAR(5) CHECK (priority IN ('P1', 'P2', 'P3', 'P4', 'P5')),
    enabled BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (connector_type, category, severity)
);

CREATE INDEX IF NOT EXISTS idx_priority_rules_connector ON priority_rules(connector_type);
CREATE INDEX IF NOT EXISTS idx_priority_rules_enabled ON priority_rules(enabled);

-- ============================================
-- 4. Alert Type Templates
-- ============================================
CREATE TABLE IF NOT EXISTS alert_type_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_type VARCHAR(50) NOT NULL,
    pattern VARCHAR(100) NOT NULL,
    template VARCHAR(255) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (connector_type, pattern)
);

-- ============================================
-- 5. Deduplication Rules
-- ============================================
CREATE TABLE IF NOT EXISTS deduplication_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_type VARCHAR(50) NOT NULL,
    fingerprint_fields TEXT[] NOT NULL, -- Array of field names to use for fingerprint
    dedup_window_minutes INTEGER DEFAULT 300, -- 5 hours default
    enabled BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 6. Trigger for updated_at
-- ============================================
DROP TRIGGER IF EXISTS severity_mappings_updated_at ON severity_mappings;
CREATE TRIGGER severity_mappings_updated_at
    BEFORE UPDATE ON severity_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS category_mappings_updated_at ON category_mappings;
CREATE TRIGGER category_mappings_updated_at
    BEFORE UPDATE ON category_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS priority_rules_updated_at ON priority_rules;
CREATE TRIGGER priority_rules_updated_at
    BEFORE UPDATE ON priority_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS alert_type_templates_updated_at ON alert_type_templates;
CREATE TRIGGER alert_type_templates_updated_at
    BEFORE UPDATE ON alert_type_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS deduplication_rules_updated_at ON deduplication_rules;
CREATE TRIGGER deduplication_rules_updated_at
    BEFORE UPDATE ON deduplication_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 7. Seed Default Mappings
-- ============================================

-- PRTG Severity Mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, priority, description) VALUES
('prtg', '1', 'warning', 100, 'Unknown status'),
('prtg', '2', 'info', 100, 'Scanning'),
('prtg', '3', 'clear', 100, 'Up/OK'),
('prtg', '4', 'warning', 100, 'Warning'),
('prtg', '5', 'critical', 100, 'Down'),
('prtg', '6', 'major', 100, 'No Probe'),
('prtg', '7', 'info', 100, 'Paused by User'),
('prtg', '8', 'info', 100, 'Paused by Dependency'),
('prtg', '9', 'info', 100, 'Paused by Schedule'),
('prtg', '10', 'warning', 100, 'Unusual'),
('prtg', '11', 'warning', 100, 'Not Licensed'),
('prtg', '12', 'info', 100, 'Paused Until'),
('prtg', '13', 'major', 100, 'Down (Acknowledged)'),
('prtg', '14', 'major', 100, 'Down (Partial)')
ON CONFLICT DO NOTHING;

-- PRTG Text Severity Mappings
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description) VALUES
('prtg', 'up', 'status_text', 'clear', 200, 'Up status'),
('prtg', 'down', 'status_text', 'critical', 200, 'Down status'),
('prtg', 'warning', 'status_text', 'warning', 200, 'Warning status'),
('prtg', 'unusual', 'status_text', 'warning', 200, 'Unusual status'),
('prtg', 'paused', 'status_text', 'info', 200, 'Paused status'),
('prtg', 'unknown', 'status_text', 'warning', 200, 'Unknown status')
ON CONFLICT DO NOTHING;

-- PRTG Category Mappings
INSERT INTO category_mappings (connector_type, source_value, target_category, priority, description) VALUES
('prtg', 'ping', 'network', 100, 'Ping sensors'),
('prtg', 'snmp', 'network', 100, 'SNMP sensors'),
('prtg', 'bandwidth', 'network', 100, 'Bandwidth sensors'),
('prtg', 'traffic', 'network', 100, 'Traffic sensors'),
('prtg', 'port', 'network', 100, 'Port sensors'),
('prtg', 'cpu', 'compute', 100, 'CPU sensors'),
('prtg', 'memory', 'compute', 100, 'Memory sensors'),
('prtg', 'disk', 'storage', 100, 'Disk sensors'),
('prtg', 'http', 'application', 100, 'HTTP sensors'),
('prtg', 'ssl', 'security', 100, 'SSL sensors'),
('prtg', 'wmi', 'compute', 100, 'WMI sensors'),
('prtg', 'vmware', 'compute', 100, 'VMware sensors'),
('prtg', 'ups', 'power', 100, 'UPS sensors'),
('prtg', 'temperature', 'environment', 100, 'Temperature sensors'),
('prtg', 'humidity', 'environment', 100, 'Humidity sensors')
ON CONFLICT DO NOTHING;

-- MCP Severity Mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, priority, description) VALUES
('mcp', 'CRITICAL', 'critical', 100, 'Critical alarms'),
('mcp', 'MAJOR', 'major', 100, 'Major alarms'),
('mcp', 'MINOR', 'minor', 100, 'Minor alarms'),
('mcp', 'WARNING', 'warning', 100, 'Warning alarms'),
('mcp', 'INFO', 'info', 100, 'Info alarms'),
('mcp', 'CLEARED', 'clear', 100, 'Cleared alarms'),
('mcp', 'CLEAR', 'clear', 100, 'Clear alarms')
ON CONFLICT DO NOTHING;

-- MCP Category Mappings
INSERT INTO category_mappings (connector_type, source_value, target_category, priority, description) VALUES
('mcp', 'equipment', 'network', 100, 'Equipment alarms'),
('mcp', 'communication', 'network', 100, 'Communication alarms'),
('mcp', 'processing', 'compute', 100, 'Processing alarms'),
('mcp', 'environment', 'environment', 100, 'Environment alarms'),
('mcp', 'power', 'power', 100, 'Power alarms'),
('mcp', 'security', 'security', 100, 'Security alarms'),
('mcp', 'qos', 'network', 100, 'QoS alarms')
ON CONFLICT DO NOTHING;

-- Priority Rules (ITIL Matrix)
INSERT INTO priority_rules (connector_type, category, severity, impact, urgency, priority, description) VALUES
-- Critical severity
('prtg', 'network', 'critical', 'high', 'high', 'P1', 'Network critical'),
('prtg', 'compute', 'critical', 'high', 'high', 'P1', 'Compute critical'),
('prtg', 'power', 'critical', 'high', 'high', 'P1', 'Power critical'),
('prtg', 'storage', 'critical', 'high', 'high', 'P1', 'Storage critical'),
('prtg', 'application', 'critical', 'high', 'high', 'P1', 'Application critical'),
-- Major severity
('prtg', 'network', 'major', 'high', 'medium', 'P2', 'Network major'),
('prtg', 'compute', 'major', 'high', 'medium', 'P2', 'Compute major'),
('prtg', 'power', 'major', 'high', 'medium', 'P2', 'Power major'),
-- Minor severity
('prtg', 'network', 'minor', 'medium', 'low', 'P3', 'Network minor'),
('prtg', 'compute', 'minor', 'medium', 'low', 'P3', 'Compute minor'),
-- Warning severity
('prtg', 'network', 'warning', 'low', 'medium', 'P3', 'Network warning'),
('prtg', 'compute', 'warning', 'low', 'medium', 'P3', 'Compute warning'),
-- Info severity
('prtg', 'network', 'info', 'low', 'low', 'P4', 'Network info'),
('prtg', 'compute', 'info', 'low', 'low', 'P4', 'Compute info')
;

-- Alert Type Templates
INSERT INTO alert_type_templates (connector_type, pattern, template, description) VALUES
('prtg', 'default', 'prtg_{sensor_type}_{status}', 'Default PRTG alert type'),
('mcp', 'default', 'mcp_{alarm_type}', 'Default MCP alert type')
;

-- Deduplication Rules
INSERT INTO deduplication_rules (connector_type, fingerprint_fields, dedup_window_minutes, description) VALUES
('prtg', ARRAY['sensorid', 'device'], 300, 'PRTG dedup by sensor+device'),
('mcp', ARRAY['id', 'sourceName'], 300, 'MCP dedup by alarm+device')
ON CONFLICT (connector_type) DO NOTHING;

COMMIT;
