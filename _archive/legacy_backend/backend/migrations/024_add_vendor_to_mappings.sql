-- Migration: Add vendor column to severity_mappings and category_mappings
-- This allows filtering SNMP trap mappings by vendor (siklu, ciena, eaton, etc.)

-- Add vendor column to severity_mappings
ALTER TABLE severity_mappings ADD COLUMN IF NOT EXISTS vendor VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_severity_mappings_vendor ON severity_mappings(vendor);

-- Add vendor column to category_mappings
ALTER TABLE category_mappings ADD COLUMN IF NOT EXISTS vendor VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_category_mappings_vendor ON category_mappings(vendor);

-- Update existing SNMP trap mappings with vendor based on OID prefix
-- Siklu enterprise OID: 1.3.6.1.4.1.31926
UPDATE severity_mappings 
SET vendor = 'siklu' 
WHERE connector_type = 'snmp_trap' 
AND source_value LIKE '1.3.6.1.4.1.31926%';

UPDATE category_mappings 
SET vendor = 'siklu' 
WHERE connector_type = 'snmp_trap' 
AND source_value LIKE '1.3.6.1.4.1.31926%';

-- Standard IF-MIB traps
UPDATE severity_mappings 
SET vendor = 'standard' 
WHERE connector_type = 'snmp_trap' 
AND source_value LIKE '1.3.6.1.6.3.1.1.5%';

UPDATE category_mappings 
SET vendor = 'standard' 
WHERE connector_type = 'snmp_trap' 
AND source_value LIKE '1.3.6.1.6.3.1.1.5%';
