-- Migration: Add SNMP Trap Mappings for Siklu and standard traps
-- This ensures SNMP traps use the same database-driven mapping system as all other connectors

-- Siklu SNMP Trap Severity Mappings
-- Format: trap OID -> severity
-- Raise traps end in .1, Clear traps end in .2

-- RF Link State
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.1.2.1.1', 'trap_oid', 'critical', 100, 'Siklu RF Link Down (raise)'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.1.2.1.2', 'trap_oid', 'clear', 100, 'Siklu RF Link Up (clear)')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- RSSI Threshold
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.1.3.1', 'trap_oid', 'major', 100, 'Siklu RSSI Low (raise)'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.1.3.2', 'trap_oid', 'clear', 100, 'Siklu RSSI Normal (clear)')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- Modulation Degraded
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.2.4.1', 'trap_oid', 'warning', 100, 'Siklu Modulation Degraded (raise)'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.2.4.2', 'trap_oid', 'clear', 100, 'Siklu Modulation Restored (clear)')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- Temperature
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.1.1.1', 'trap_oid', 'major', 100, 'Siklu Temperature High (raise)'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.1.1.2', 'trap_oid', 'clear', 100, 'Siklu Temperature Normal (clear)')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- Power Fault
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.2.2.1', 'trap_oid', 'critical', 100, 'Siklu Power Fault (raise)'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.2.2.2', 'trap_oid', 'clear', 100, 'Siklu Power Normal (clear)')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- Sync Lost
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.4.1.1.1', 'trap_oid', 'major', 100, 'Siklu Sync Lost (raise)'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.4.1.1.2', 'trap_oid', 'clear', 100, 'Siklu Sync Restored (clear)')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- One-shot events (no clear)
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.5.1.0', 'trap_oid', 'warning', 100, 'Siklu Device Reboot'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.5.2.0', 'trap_oid', 'info', 100, 'Siklu Config Change')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- Standard IF-MIB traps
INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.6.3.1.1.5.3', 'trap_oid', 'warning', 50, 'Standard Link Down'),
    ('snmp_trap', '1.3.6.1.6.3.1.1.5.4', 'trap_oid', 'clear', 50, 'Standard Link Up')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;


-- Siklu SNMP Trap Category Mappings
-- RF Link State
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.1.2.1.1', 'trap_oid', 'wireless', 100, 'Siklu RF Link Down'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.1.2.1.2', 'trap_oid', 'wireless', 100, 'Siklu RF Link Up')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- RSSI Threshold
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.1.3.1', 'trap_oid', 'wireless', 100, 'Siklu RSSI Low'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.1.3.2', 'trap_oid', 'wireless', 100, 'Siklu RSSI Normal')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- Modulation Degraded
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.2.4.1', 'trap_oid', 'wireless', 100, 'Siklu Modulation Degraded'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.2.2.4.2', 'trap_oid', 'wireless', 100, 'Siklu Modulation Restored')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- Temperature
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.1.1.1', 'trap_oid', 'environment', 100, 'Siklu Temperature High'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.1.1.2', 'trap_oid', 'environment', 100, 'Siklu Temperature Normal')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- Power Fault
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.2.2.1', 'trap_oid', 'power', 100, 'Siklu Power Fault'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.3.2.2.2', 'trap_oid', 'power', 100, 'Siklu Power Normal')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- Sync Lost
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.4.1.1.1', 'trap_oid', 'network', 100, 'Siklu Sync Lost'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.4.1.1.2', 'trap_oid', 'network', 100, 'Siklu Sync Restored')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- One-shot events
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.4.1.31926.1.5.1.0', 'trap_oid', 'wireless', 100, 'Siklu Device Reboot'),
    ('snmp_trap', '1.3.6.1.4.1.31926.1.5.2.0', 'trap_oid', 'wireless', 100, 'Siklu Config Change')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- Standard IF-MIB traps
INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, priority, description)
VALUES 
    ('snmp_trap', '1.3.6.1.6.3.1.1.5.3', 'trap_oid', 'network', 50, 'Standard Link Down'),
    ('snmp_trap', '1.3.6.1.6.3.1.1.5.4', 'trap_oid', 'network', 50, 'Standard Link Up')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;


-- Add a new table for SNMP trap-specific metadata (alert_type, is_clear, correlation_key)
-- This extends the standard severity/category mappings with trap-specific fields
CREATE TABLE IF NOT EXISTS snmp_trap_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trap_oid VARCHAR(200) NOT NULL UNIQUE,
    alert_type VARCHAR(100) NOT NULL,
    is_clear BOOLEAN DEFAULT FALSE,
    correlation_key VARCHAR(100),  -- Used to match raise/clear pairs (e.g., 'siklu_rf_link')
    vendor VARCHAR(50),
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snmp_trap_mappings_oid ON snmp_trap_mappings(trap_oid);
CREATE INDEX IF NOT EXISTS idx_snmp_trap_mappings_vendor ON snmp_trap_mappings(vendor);
CREATE INDEX IF NOT EXISTS idx_snmp_trap_mappings_correlation ON snmp_trap_mappings(correlation_key);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS snmp_trap_mappings_updated_at ON snmp_trap_mappings;
CREATE TRIGGER snmp_trap_mappings_updated_at
    BEFORE UPDATE ON snmp_trap_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert Siklu trap mappings with correlation keys
INSERT INTO snmp_trap_mappings (trap_oid, alert_type, is_clear, correlation_key, vendor, description)
VALUES 
    -- RF Link State
    ('1.3.6.1.4.1.31926.1.1.2.1.1', 'siklu_rf_link_down', FALSE, 'siklu_rf_link', 'siklu', 'RF Link Down (raise)'),
    ('1.3.6.1.4.1.31926.1.1.2.1.2', 'siklu_rf_link_down', TRUE, 'siklu_rf_link', 'siklu', 'RF Link Up (clear)'),
    -- RSSI Threshold
    ('1.3.6.1.4.1.31926.1.2.1.3.1', 'siklu_rssi_low', FALSE, 'siklu_rssi', 'siklu', 'RSSI Low (raise)'),
    ('1.3.6.1.4.1.31926.1.2.1.3.2', 'siklu_rssi_low', TRUE, 'siklu_rssi', 'siklu', 'RSSI Normal (clear)'),
    -- Modulation Degraded
    ('1.3.6.1.4.1.31926.1.2.2.4.1', 'siklu_modulation_degraded', FALSE, 'siklu_modulation', 'siklu', 'Modulation Degraded (raise)'),
    ('1.3.6.1.4.1.31926.1.2.2.4.2', 'siklu_modulation_degraded', TRUE, 'siklu_modulation', 'siklu', 'Modulation Restored (clear)'),
    -- Temperature
    ('1.3.6.1.4.1.31926.1.3.1.1.1', 'siklu_temperature_high', FALSE, 'siklu_temperature', 'siklu', 'Temperature High (raise)'),
    ('1.3.6.1.4.1.31926.1.3.1.1.2', 'siklu_temperature_high', TRUE, 'siklu_temperature', 'siklu', 'Temperature Normal (clear)'),
    -- Power Fault
    ('1.3.6.1.4.1.31926.1.3.2.2.1', 'siklu_power_fault', FALSE, 'siklu_power', 'siklu', 'Power Fault (raise)'),
    ('1.3.6.1.4.1.31926.1.3.2.2.2', 'siklu_power_fault', TRUE, 'siklu_power', 'siklu', 'Power Normal (clear)'),
    -- Sync Lost
    ('1.3.6.1.4.1.31926.1.4.1.1.1', 'siklu_sync_lost', FALSE, 'siklu_sync', 'siklu', 'Sync Lost (raise)'),
    ('1.3.6.1.4.1.31926.1.4.1.1.2', 'siklu_sync_lost', TRUE, 'siklu_sync', 'siklu', 'Sync Restored (clear)'),
    -- One-shot events (no clear, no correlation)
    ('1.3.6.1.4.1.31926.1.5.1.0', 'siklu_device_reboot', FALSE, NULL, 'siklu', 'Device Reboot'),
    ('1.3.6.1.4.1.31926.1.5.2.0', 'siklu_config_change', FALSE, NULL, 'siklu', 'Config Change'),
    -- Standard IF-MIB traps
    ('1.3.6.1.6.3.1.1.5.3', 'link_down', FALSE, 'link_state', 'standard', 'Standard Link Down'),
    ('1.3.6.1.6.3.1.1.5.4', 'link_down', TRUE, 'link_state', 'standard', 'Standard Link Up')
ON CONFLICT (trap_oid) DO UPDATE SET
    alert_type = EXCLUDED.alert_type,
    is_clear = EXCLUDED.is_clear,
    correlation_key = EXCLUDED.correlation_key,
    vendor = EXCLUDED.vendor,
    description = EXCLUDED.description;
