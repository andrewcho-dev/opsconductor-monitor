-- SNMP Trap Receiver Tables
-- Migration: 012_snmp_trap_tables.sql

-- Table to store all received SNMP traps (raw log)
CREATE TABLE IF NOT EXISTS trap_log (
    id BIGSERIAL PRIMARY KEY,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    source_ip INET NOT NULL,
    source_port INTEGER,
    snmp_version VARCHAR(10),
    community VARCHAR(100),
    enterprise_oid VARCHAR(255),
    trap_oid VARCHAR(255) NOT NULL,
    trap_type VARCHAR(100),
    vendor VARCHAR(50),
    uptime BIGINT,
    varbinds JSONB,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    handler VARCHAR(50),
    event_id BIGINT,
    raw_hex TEXT
);

-- Indexes for trap_log
CREATE INDEX IF NOT EXISTS idx_trap_log_source ON trap_log(source_ip);
CREATE INDEX IF NOT EXISTS idx_trap_log_received ON trap_log(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_trap_log_oid ON trap_log(trap_oid);
CREATE INDEX IF NOT EXISTS idx_trap_log_vendor ON trap_log(vendor);
CREATE INDEX IF NOT EXISTS idx_trap_log_unprocessed ON trap_log(processed) WHERE processed = FALSE;

-- Table for normalized trap events
CREATE TABLE IF NOT EXISTS trap_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    source_ip INET NOT NULL,
    device_name VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    object_type VARCHAR(50),
    object_id VARCHAR(100),
    description TEXT,
    details JSONB,
    trap_log_id BIGINT REFERENCES trap_log(id),
    alarm_id VARCHAR(255),
    is_clear BOOLEAN DEFAULT FALSE,
    cleared_event_id BIGINT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100)
);

-- Indexes for trap_events
CREATE INDEX IF NOT EXISTS idx_trap_events_source ON trap_events(source_ip);
CREATE INDEX IF NOT EXISTS idx_trap_events_type ON trap_events(event_type);
CREATE INDEX IF NOT EXISTS idx_trap_events_severity ON trap_events(severity);
CREATE INDEX IF NOT EXISTS idx_trap_events_created ON trap_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trap_events_alarm_id ON trap_events(alarm_id);
CREATE INDEX IF NOT EXISTS idx_trap_events_active ON trap_events(is_clear) WHERE is_clear = FALSE;

-- Active alarms view (from traps) - correlates raised/cleared
CREATE OR REPLACE VIEW active_trap_alarms AS
SELECT 
    e.id,
    e.created_at,
    e.source_ip,
    e.device_name,
    e.event_type,
    e.severity,
    e.object_type,
    e.object_id,
    e.description,
    e.details,
    e.alarm_id,
    e.acknowledged,
    e.acknowledged_at,
    e.acknowledged_by
FROM trap_events e
WHERE e.is_clear = FALSE
  AND e.alarm_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM trap_events c 
      WHERE c.alarm_id = e.alarm_id 
        AND c.is_clear = TRUE 
        AND c.created_at > e.created_at
  );

-- Trap receiver status table
CREATE TABLE IF NOT EXISTS trap_receiver_status (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE,
    last_trap_at TIMESTAMP WITH TIME ZONE,
    traps_received BIGINT DEFAULT 0,
    traps_processed BIGINT DEFAULT 0,
    traps_errors BIGINT DEFAULT 0,
    queue_depth INTEGER DEFAULT 0,
    is_running BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial status row
INSERT INTO trap_receiver_status (id, is_running) VALUES (1, FALSE)
ON CONFLICT (id) DO NOTHING;

-- Function to update trap receiver stats
CREATE OR REPLACE FUNCTION update_trap_receiver_stats(
    p_traps_received BIGINT DEFAULT NULL,
    p_traps_processed BIGINT DEFAULT NULL,
    p_traps_errors BIGINT DEFAULT NULL,
    p_queue_depth INTEGER DEFAULT NULL,
    p_is_running BOOLEAN DEFAULT NULL,
    p_last_trap_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE trap_receiver_status SET
        traps_received = COALESCE(p_traps_received, traps_received),
        traps_processed = COALESCE(p_traps_processed, traps_processed),
        traps_errors = COALESCE(p_traps_errors, traps_errors),
        queue_depth = COALESCE(p_queue_depth, queue_depth),
        is_running = COALESCE(p_is_running, is_running),
        last_trap_at = COALESCE(p_last_trap_at, last_trap_at),
        updated_at = NOW()
    WHERE id = 1;
END;
$$ LANGUAGE plpgsql;
