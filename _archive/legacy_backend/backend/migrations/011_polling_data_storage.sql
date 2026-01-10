-- Generic polling data storage for custom poll types
-- This allows storing any SNMP polling results with flexible schema

-- Main polling data table - stores all custom poll results
CREATE TABLE IF NOT EXISTS polling_data (
    id BIGSERIAL PRIMARY KEY,
    poll_type VARCHAR(100) NOT NULL,      -- e.g., 'ciena_optical', 'cisco_traffic'
    device_ip VARCHAR(45) NOT NULL,        -- Device IP address
    device_name VARCHAR(255),              -- Device hostname
    site_name VARCHAR(255),                -- Site name
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Flexible data storage using JSONB
    data JSONB NOT NULL,                   -- All polled OID values as key-value pairs
    
    -- Metadata
    poll_config_id INTEGER,                -- Reference to polling_configs if applicable
    poll_execution_id INTEGER,             -- Reference to polling_executions
    
    -- Indexes for common queries
    CONSTRAINT polling_data_device_time UNIQUE (poll_type, device_ip, collected_at)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_polling_data_poll_type ON polling_data(poll_type);
CREATE INDEX IF NOT EXISTS idx_polling_data_device_ip ON polling_data(device_ip);
CREATE INDEX IF NOT EXISTS idx_polling_data_collected_at ON polling_data(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_polling_data_site ON polling_data(site_name);
CREATE INDEX IF NOT EXISTS idx_polling_data_jsonb ON polling_data USING GIN (data);

-- Partitioning hint: For high-volume deployments, consider partitioning by collected_at
-- This table can grow large, so retention policies should be implemented

-- View for easy querying of recent data
CREATE OR REPLACE VIEW polling_data_recent AS
SELECT 
    pd.*,
    pt.display_name as poll_type_name,
    p.vendor
FROM polling_data pd
LEFT JOIN snmp_poll_types pt ON pt.name = pd.poll_type
LEFT JOIN snmp_profiles p ON p.id = pt.profile_id
WHERE pd.collected_at > NOW() - INTERVAL '24 hours'
ORDER BY pd.collected_at DESC;

-- Function to clean up old polling data (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_polling_data(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM polling_data 
    WHERE collected_at < NOW() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add comment explaining the table
COMMENT ON TABLE polling_data IS 'Stores all custom SNMP polling results. The data column contains JSONB with OID name -> value mappings.';
COMMENT ON COLUMN polling_data.data IS 'JSONB object with OID names as keys and polled values. Example: {"rx_power_dbm": -5.2, "tx_power_dbm": -3.1, "temperature": 45}';
