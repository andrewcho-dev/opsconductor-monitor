-- MIB OID Mapping System
-- Allows defining SNMP OID mappings for different vendors/devices

-- Vendor/Device profiles (e.g., Ciena 3942, Cisco Catalyst, etc.)
CREATE TABLE IF NOT EXISTS snmp_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    vendor VARCHAR(100) NOT NULL,
    description TEXT,
    enterprise_oid VARCHAR(100),  -- e.g., '1.3.6.1.4.1.6141' for Ciena WWP
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- OID Groups within a profile (e.g., 'xcvr', 'port_stats', 'raps')
CREATE TABLE IF NOT EXISTS snmp_oid_groups (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES snmp_profiles(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    base_oid VARCHAR(200),  -- Base OID for this group
    mib_name VARCHAR(100),  -- e.g., 'WWP-LEOS-PORT-XCVR-MIB'
    is_table BOOLEAN DEFAULT false,  -- Is this a SNMP table (walk) or scalar
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(profile_id, name)
);

-- Individual OID mappings within a group
CREATE TABLE IF NOT EXISTS snmp_oid_mappings (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES snmp_oid_groups(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- Field name (e.g., 'rx_power_dbm')
    oid VARCHAR(200) NOT NULL,   -- Full OID
    description TEXT,            -- Human description
    mib_object_name VARCHAR(100), -- MIB object name (e.g., 'wwpLeosPortXcvrRxDbmPower')
    data_type VARCHAR(50) DEFAULT 'string',  -- string, integer, counter, gauge, timeticks, octetstring
    transform VARCHAR(100),      -- Transformation to apply (e.g., 'divide:10000' for dBm)
    unit VARCHAR(50),            -- Unit of measurement (e.g., 'dBm', 'bytes', 'ms')
    is_index BOOLEAN DEFAULT false,  -- Is this the table index
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, name)
);

-- Enum value mappings (for integer->string translations)
CREATE TABLE IF NOT EXISTS snmp_enum_mappings (
    id SERIAL PRIMARY KEY,
    mapping_id INTEGER NOT NULL REFERENCES snmp_oid_mappings(id) ON DELETE CASCADE,
    int_value INTEGER NOT NULL,
    string_value VARCHAR(100) NOT NULL,
    severity VARCHAR(20),  -- For alarm-type enums: 'critical', 'major', 'minor', 'warning', 'info'
    UNIQUE(mapping_id, int_value)
);

-- Poll types that use these mappings
CREATE TABLE IF NOT EXISTS snmp_poll_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,  -- e.g., 'ciena_optical', 'ciena_raps'
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    profile_id INTEGER NOT NULL REFERENCES snmp_profiles(id) ON DELETE CASCADE,
    target_table VARCHAR(100),  -- Database table to store results (e.g., 'optical_metrics')
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Which OID groups are included in a poll type
CREATE TABLE IF NOT EXISTS snmp_poll_type_groups (
    id SERIAL PRIMARY KEY,
    poll_type_id INTEGER NOT NULL REFERENCES snmp_poll_types(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES snmp_oid_groups(id) ON DELETE CASCADE,
    poll_order INTEGER DEFAULT 0,  -- Order to poll groups
    UNIQUE(poll_type_id, group_id)
);

-- Insert Ciena profile
INSERT INTO snmp_profiles (name, vendor, description, enterprise_oid)
VALUES ('ciena_saos6', 'Ciena', 'Ciena 3942/5160 switches running SAOS 6', '1.3.6.1.4.1.6141')
ON CONFLICT (name) DO NOTHING;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_snmp_oid_groups_profile ON snmp_oid_groups(profile_id);
CREATE INDEX IF NOT EXISTS idx_snmp_oid_mappings_group ON snmp_oid_mappings(group_id);
CREATE INDEX IF NOT EXISTS idx_snmp_enum_mappings_mapping ON snmp_enum_mappings(mapping_id);
CREATE INDEX IF NOT EXISTS idx_snmp_poll_types_profile ON snmp_poll_types(profile_id);
CREATE INDEX IF NOT EXISTS idx_snmp_poll_type_groups_poll_type ON snmp_poll_type_groups(poll_type_id);
