-- Migration: 027_addon_registry.sql
-- Description: Create tables for addon/plugin management system

-- ============================================================================
-- INSTALLED ADDONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS installed_addons (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(32) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('nms', 'device')),
    description TEXT,
    author VARCHAR(255),
    enabled BOOLEAN DEFAULT true,
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    manifest JSONB NOT NULL,
    config JSONB DEFAULT '{}',
    storage_path VARCHAR(512) NOT NULL,
    is_builtin BOOLEAN DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_installed_addons_category ON installed_addons(category);
CREATE INDEX IF NOT EXISTS idx_installed_addons_enabled ON installed_addons(enabled);
CREATE INDEX IF NOT EXISTS idx_installed_addons_builtin ON installed_addons(is_builtin);

-- ============================================================================
-- ADDON MIGRATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS addon_migrations (
    id SERIAL PRIMARY KEY,
    addon_id VARCHAR(64) REFERENCES installed_addons(id) ON DELETE CASCADE,
    migration_name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(addon_id, migration_name)
);

-- ============================================================================
-- UPDATED_AT TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_addon_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS addon_updated_at ON installed_addons;
CREATE TRIGGER addon_updated_at
    BEFORE UPDATE ON installed_addons
    FOR EACH ROW
    EXECUTE FUNCTION update_addon_timestamp();

-- ============================================================================
-- SEED BUILT-IN ADDONS
-- ============================================================================

INSERT INTO installed_addons (id, name, version, category, description, author, enabled, is_builtin, storage_path, manifest) VALUES
('prtg', 'PRTG Network Monitor', '1.0.0', 'nms', 'Connect to PRTG Network Monitor for centralized alerting', 'OpsConductor', true, true, 'builtin/prtg', '{"id": "prtg", "connector_class": "PRTGConnector", "normalizer_class": "PRTGDatabaseNormalizer", "capabilities": ["polling", "webhooks"]}'),
('mcp', 'MCP (Ciena)', '1.0.0', 'nms', 'Connect to Ciena MCP for optical network monitoring', 'OpsConductor', true, true, 'builtin/mcp', '{"id": "mcp", "connector_class": "MCPConnector", "normalizer_class": "MCPNormalizer", "capabilities": ["polling"]}'),
('axis', 'Axis Cameras', '1.0.0', 'device', 'Monitor Axis network cameras via VAPIX', 'OpsConductor', true, true, 'builtin/axis', '{"id": "axis", "connector_class": "AxisConnector", "normalizer_class": "AxisNormalizer", "capabilities": ["polling"]}'),
('milestone', 'Milestone VMS', '1.0.0', 'device', 'Monitor Milestone XProtect video management system', 'OpsConductor', true, true, 'builtin/milestone', '{"id": "milestone", "connector_class": "MilestoneConnector", "normalizer_class": "MilestoneNormalizer", "capabilities": ["polling"]}'),
('cradlepoint', 'Cradlepoint', '1.0.0', 'device', 'Monitor Cradlepoint cellular routers via NetCloud API', 'OpsConductor', true, true, 'builtin/cradlepoint', '{"id": "cradlepoint", "connector_class": "CradlepointConnector", "normalizer_class": "CradlepointNormalizer", "capabilities": ["polling"]}'),
('siklu', 'Siklu Radios', '1.0.0', 'device', 'Monitor Siklu EtherHaul wireless radios', 'OpsConductor', true, true, 'builtin/siklu', '{"id": "siklu", "connector_class": "SikluConnector", "normalizer_class": "SikluNormalizer", "capabilities": ["polling", "snmp_traps"]}'),
('ubiquiti', 'Ubiquiti', '1.0.0', 'device', 'Monitor Ubiquiti wireless devices', 'OpsConductor', true, true, 'builtin/ubiquiti', '{"id": "ubiquiti", "connector_class": "UbiquitiConnector", "normalizer_class": "UbiquitiNormalizer", "capabilities": ["polling"]}'),
('cisco_asa', 'Cisco ASA', '1.0.0', 'device', 'Monitor Cisco ASA firewalls', 'OpsConductor', true, true, 'builtin/cisco_asa', '{"id": "cisco_asa", "connector_class": "CiscoASAConnector", "normalizer_class": "CiscoASANormalizer", "capabilities": ["polling"]}'),
('eaton', 'Eaton UPS', '1.0.0', 'device', 'Monitor Eaton UPS systems via SNMP', 'OpsConductor', true, true, 'builtin/eaton', '{"id": "eaton", "connector_class": "EatonConnector", "normalizer_class": "EatonNormalizer", "capabilities": ["polling"]}'),
('snmp_trap', 'SNMP Traps', '1.0.0', 'nms', 'Receive SNMP traps from any device', 'OpsConductor', true, true, 'builtin/snmp_trap', '{"id": "snmp_trap", "connector_class": "SNMPTrapConnector", "normalizer_class": "SNMPTrapNormalizer", "capabilities": ["traps"]}')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    version = EXCLUDED.version,
    description = EXCLUDED.description,
    manifest = EXCLUDED.manifest;

-- Record migration
INSERT INTO schema_migrations (version, name, applied_at)
VALUES ('027', '027_addon_registry', NOW())
ON CONFLICT (version) DO NOTHING;
