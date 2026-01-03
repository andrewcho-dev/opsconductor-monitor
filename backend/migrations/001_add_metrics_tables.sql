-- ============================================================================
-- OpsConductor Database Migration 001: Add Metrics Tables
-- ============================================================================
-- This migration adds new tables for time-series metrics, baselines, anomalies,
-- and health scores. It does NOT modify existing tables.
--
-- Run with: PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan -f 001_add_metrics_tables.sql
--
-- Rollback: Run 001_rollback.sql
-- ============================================================================

BEGIN;

-- Record migration
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Check if already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '001') THEN
        RAISE EXCEPTION 'Migration 001 already applied';
    END IF;
END $$;

-- ============================================================================
-- 1. CORE PERFORMANCE METRICS (Time-Series, Partitioned)
-- ============================================================================

-- Optical power readings - critical for fiber network health
CREATE TABLE IF NOT EXISTS optical_metrics (
    id BIGSERIAL,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100) NOT NULL,
    interface_index INTEGER,
    
    -- Optical metrics
    tx_power NUMERIC(8,3),              -- dBm
    rx_power NUMERIC(8,3),              -- dBm
    tx_power_high_warn NUMERIC(8,3),
    tx_power_low_warn NUMERIC(8,3),
    rx_power_high_warn NUMERIC(8,3),
    rx_power_low_warn NUMERIC(8,3),
    temperature NUMERIC(6,2),           -- Celsius
    voltage NUMERIC(6,3),               -- Volts
    bias_current NUMERIC(8,3),          -- mA
    
    -- Quality indicators
    signal_quality_pct NUMERIC(5,2),
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Create initial partitions (current month + next 3 months)
CREATE TABLE IF NOT EXISTS optical_metrics_2026_01 PARTITION OF optical_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS optical_metrics_2026_02 PARTITION OF optical_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS optical_metrics_2026_03 PARTITION OF optical_metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS optical_metrics_2026_04 PARTITION OF optical_metrics
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX IF NOT EXISTS idx_optical_device_time ON optical_metrics (device_ip, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_optical_interface_time ON optical_metrics (device_ip, interface_name, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_optical_site_time ON optical_metrics (site_id, recorded_at DESC);


-- Interface traffic and error statistics
CREATE TABLE IF NOT EXISTS interface_metrics (
    id BIGSERIAL,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100) NOT NULL,
    interface_index INTEGER,
    
    -- Traffic counters (cumulative)
    rx_bytes BIGINT,
    tx_bytes BIGINT,
    rx_packets BIGINT,
    tx_packets BIGINT,
    
    -- Calculated rates (per second)
    rx_bps BIGINT,
    tx_bps BIGINT,
    rx_pps INTEGER,
    tx_pps INTEGER,
    
    -- Utilization
    rx_utilization_pct NUMERIC(5,2),
    tx_utilization_pct NUMERIC(5,2),
    
    -- Errors and discards
    rx_errors BIGINT,
    tx_errors BIGINT,
    rx_discards BIGINT,
    tx_discards BIGINT,
    rx_crc_errors BIGINT,
    collisions BIGINT,
    
    -- Error rates
    error_rate_ppm NUMERIC(8,2),
    
    -- Status
    oper_status INTEGER,
    admin_status INTEGER,
    speed_mbps INTEGER,
    duplex VARCHAR(10),
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE TABLE IF NOT EXISTS interface_metrics_2026_01 PARTITION OF interface_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS interface_metrics_2026_02 PARTITION OF interface_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS interface_metrics_2026_03 PARTITION OF interface_metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS interface_metrics_2026_04 PARTITION OF interface_metrics
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX IF NOT EXISTS idx_iface_device_time ON interface_metrics (device_ip, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_iface_site_time ON interface_metrics (site_id, recorded_at DESC);


-- Network path performance
CREATE TABLE IF NOT EXISTS path_metrics (
    id BIGSERIAL,
    source_ip INET NOT NULL,
    destination_ip INET NOT NULL,
    source_device_id INTEGER,
    destination_device_id INTEGER,
    source_site_id INTEGER,
    destination_site_id INTEGER,
    
    -- Latency metrics (milliseconds)
    latency_ms NUMERIC(10,3),
    latency_min_ms NUMERIC(10,3),
    latency_max_ms NUMERIC(10,3),
    latency_stddev_ms NUMERIC(10,3),
    
    -- Jitter
    jitter_ms NUMERIC(10,3),
    
    -- Packet loss
    packets_sent INTEGER,
    packets_received INTEGER,
    packet_loss_pct NUMERIC(5,2),
    
    -- Hop count
    hop_count INTEGER,
    
    -- Test metadata
    test_type VARCHAR(20),
    test_duration_ms INTEGER,
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE TABLE IF NOT EXISTS path_metrics_2026_01 PARTITION OF path_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS path_metrics_2026_02 PARTITION OF path_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS path_metrics_2026_03 PARTITION OF path_metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS path_metrics_2026_04 PARTITION OF path_metrics
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX IF NOT EXISTS idx_path_source_time ON path_metrics (source_ip, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_path_dest_time ON path_metrics (destination_ip, recorded_at DESC);


-- Device availability and reachability
CREATE TABLE IF NOT EXISTS availability_metrics (
    id BIGSERIAL,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    device_role VARCHAR(50),
    
    -- Reachability status
    ping_status VARCHAR(20),
    snmp_status VARCHAR(20),
    ssh_status VARCHAR(20),
    https_status VARCHAR(20),
    
    -- Response times (milliseconds)
    ping_latency_ms NUMERIC(8,3),
    snmp_response_ms NUMERIC(8,3),
    ssh_response_ms NUMERIC(8,3),
    
    -- Device health indicators
    cpu_utilization_pct NUMERIC(5,2),
    memory_utilization_pct NUMERIC(5,2),
    uptime_seconds BIGINT,
    temperature_celsius NUMERIC(6,2),
    
    -- Power
    poe_power_watts NUMERIC(8,2),
    poe_power_available_watts NUMERIC(8,2),
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE TABLE IF NOT EXISTS availability_metrics_2026_01 PARTITION OF availability_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS availability_metrics_2026_02 PARTITION OF availability_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS availability_metrics_2026_03 PARTITION OF availability_metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS availability_metrics_2026_04 PARTITION OF availability_metrics
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX IF NOT EXISTS idx_avail_device_time ON availability_metrics (device_ip, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_avail_site_time ON availability_metrics (site_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_avail_role_time ON availability_metrics (device_role, recorded_at DESC);


-- ============================================================================
-- 2. BASELINE & ANOMALY DETECTION TABLES
-- ============================================================================

-- Baseline profiles - statistical model of "normal" for each metric
CREATE TABLE IF NOT EXISTS metric_baselines (
    id SERIAL PRIMARY KEY,
    
    -- Scope
    scope_type VARCHAR(30) NOT NULL,
    device_ip INET,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    device_role VARCHAR(50),
    
    -- Metric being baselined
    metric_name VARCHAR(50) NOT NULL,
    metric_unit VARCHAR(20),
    
    -- Time context
    time_period VARCHAR(20) NOT NULL,
    hour_of_day INTEGER,
    day_of_week INTEGER,
    
    -- Statistical baseline
    sample_count INTEGER NOT NULL,
    baseline_mean NUMERIC(12,4),
    baseline_median NUMERIC(12,4),
    baseline_stddev NUMERIC(12,4),
    baseline_min NUMERIC(12,4),
    baseline_max NUMERIC(12,4),
    baseline_p5 NUMERIC(12,4),
    baseline_p95 NUMERIC(12,4),
    baseline_p99 NUMERIC(12,4),
    
    -- Thresholds
    warn_threshold_low NUMERIC(12,4),
    warn_threshold_high NUMERIC(12,4),
    crit_threshold_low NUMERIC(12,4),
    crit_threshold_high NUMERIC(12,4),
    
    -- Metadata
    baseline_start_date DATE NOT NULL,
    baseline_end_date DATE NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    confidence_score NUMERIC(5,2),
    
    UNIQUE (scope_type, device_ip, interface_name, metric_name, time_period, hour_of_day, day_of_week)
);

CREATE INDEX IF NOT EXISTS idx_baseline_device ON metric_baselines (device_ip, metric_name) WHERE device_ip IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_baseline_site ON metric_baselines (site_id, metric_name) WHERE site_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_baseline_scope ON metric_baselines (scope_type, metric_name);


-- Detected anomalies
CREATE TABLE IF NOT EXISTS anomaly_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- What was anomalous
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    
    -- The anomaly
    metric_name VARCHAR(50) NOT NULL,
    metric_value NUMERIC(12,4) NOT NULL,
    baseline_id INTEGER REFERENCES metric_baselines(id),
    
    -- Comparison to baseline
    baseline_mean NUMERIC(12,4),
    baseline_stddev NUMERIC(12,4),
    deviation_sigma NUMERIC(6,2),
    deviation_pct NUMERIC(8,2),
    
    -- Severity
    severity VARCHAR(20) NOT NULL,
    anomaly_type VARCHAR(30),
    
    -- Context
    description TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Resolution tracking
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    is_false_positive BOOLEAN DEFAULT FALSE,
    
    -- Correlation
    correlation_group_id UUID,
    root_cause_event_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_anomaly_device_time ON anomaly_events (device_ip, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_site_time ON anomaly_events (site_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_severity ON anomaly_events (severity, detected_at DESC) WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_anomaly_correlation ON anomaly_events (correlation_group_id) WHERE correlation_group_id IS NOT NULL;


-- Network health scores
CREATE TABLE IF NOT EXISTS health_scores (
    id BIGSERIAL,
    
    -- Scope
    scope_type VARCHAR(30) NOT NULL,
    device_ip INET,
    netbox_device_id INTEGER,
    site_id INTEGER,
    path_id VARCHAR(100),
    
    -- Health scores (0-100)
    overall_score NUMERIC(5,2),
    availability_score NUMERIC(5,2),
    performance_score NUMERIC(5,2),
    error_score NUMERIC(5,2),
    capacity_score NUMERIC(5,2),
    
    -- Component scores
    optical_health NUMERIC(5,2),
    latency_health NUMERIC(5,2),
    throughput_health NUMERIC(5,2),
    
    -- Trend indicators
    trend_1h NUMERIC(6,2),
    trend_24h NUMERIC(6,2),
    trend_7d NUMERIC(6,2),
    
    -- Active issues
    active_anomaly_count INTEGER DEFAULT 0,
    active_warning_count INTEGER DEFAULT 0,
    active_critical_count INTEGER DEFAULT 0,
    
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, calculated_at)
) PARTITION BY RANGE (calculated_at);

CREATE TABLE IF NOT EXISTS health_scores_2026_01 PARTITION OF health_scores
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS health_scores_2026_02 PARTITION OF health_scores
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS health_scores_2026_03 PARTITION OF health_scores
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS health_scores_2026_04 PARTITION OF health_scores
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX IF NOT EXISTS idx_health_device ON health_scores (device_ip, calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_site ON health_scores (site_id, calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_scope ON health_scores (scope_type, calculated_at DESC);


-- ============================================================================
-- 3. CONFIGURATION & STATE SNAPSHOTS
-- ============================================================================

-- CLI configuration snapshots
CREATE TABLE IF NOT EXISTS config_snapshots (
    id SERIAL PRIMARY KEY,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    
    config_type VARCHAR(50) NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    config_content TEXT NOT NULL,
    
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_from_previous BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_config_device_type ON config_snapshots (device_ip, config_type, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_config_hash ON config_snapshots (config_hash);


-- Interface state snapshots
CREATE TABLE IF NOT EXISTS interface_snapshots (
    id SERIAL PRIMARY KEY,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    interface_name VARCHAR(100) NOT NULL,
    interface_index INTEGER,
    
    -- Physical details
    is_optical BOOLEAN,
    medium VARCHAR(50),
    connector VARCHAR(50),
    speed VARCHAR(50),
    
    -- LLDP neighbor info
    lldp_remote_system VARCHAR(255),
    lldp_remote_port VARCHAR(100),
    lldp_remote_mgmt_ip INET,
    lldp_remote_chassis_id VARCHAR(100),
    
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_iface_snap_device ON interface_snapshots (device_ip, captured_at DESC);


-- ============================================================================
-- 4. EVENT & CHANGE TRACKING
-- ============================================================================

-- Network events
CREATE TABLE IF NOT EXISTS network_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- What
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30),
    severity VARCHAR(20),
    
    -- Where
    device_ip INET,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    
    -- Details
    description TEXT,
    details JSONB,
    
    -- Timing
    event_time TIMESTAMPTZ NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER,
    
    -- Correlation
    correlation_group_id UUID,
    caused_by_event_id BIGINT,
    
    -- Source
    source_system VARCHAR(50),
    source_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_device_time ON network_events (device_ip, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_events_site_time ON network_events (site_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON network_events (event_type, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_events_correlation ON network_events (correlation_group_id);


-- ============================================================================
-- 5. POLLING HISTORY
-- ============================================================================

CREATE TABLE IF NOT EXISTS poll_history (
    id BIGSERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    device_ip INET,
    netbox_device_id INTEGER,
    
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    records_collected INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_poll_history_type_time ON poll_history (job_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_poll_history_device ON poll_history (device_ip, started_at DESC);


-- ============================================================================
-- 6. AGGREGATION TABLES
-- ============================================================================

-- Hourly aggregates
CREATE TABLE IF NOT EXISTS metrics_hourly (
    id BIGSERIAL,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    metric_name VARCHAR(50) NOT NULL,
    stat_hour TIMESTAMPTZ NOT NULL,
    
    -- Statistical aggregates
    sample_count INTEGER,
    val_min NUMERIC(12,4),
    val_max NUMERIC(12,4),
    val_avg NUMERIC(12,4),
    val_sum NUMERIC(16,4),
    val_stddev NUMERIC(12,4),
    val_p50 NUMERIC(12,4),
    val_p95 NUMERIC(12,4),
    val_p99 NUMERIC(12,4),
    
    PRIMARY KEY (id, stat_hour)
) PARTITION BY RANGE (stat_hour);

CREATE TABLE IF NOT EXISTS metrics_hourly_2026_01 PARTITION OF metrics_hourly
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS metrics_hourly_2026_02 PARTITION OF metrics_hourly
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS metrics_hourly_2026_03 PARTITION OF metrics_hourly
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS metrics_hourly_2026_04 PARTITION OF metrics_hourly
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX IF NOT EXISTS idx_hourly_device_metric ON metrics_hourly (device_ip, metric_name, stat_hour DESC);
CREATE INDEX IF NOT EXISTS idx_hourly_site_metric ON metrics_hourly (site_id, metric_name, stat_hour DESC);


-- Daily aggregates
CREATE TABLE IF NOT EXISTS metrics_daily (
    id SERIAL PRIMARY KEY,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    metric_name VARCHAR(50) NOT NULL,
    stat_date DATE NOT NULL,
    
    -- Statistical aggregates
    sample_count INTEGER,
    val_min NUMERIC(12,4),
    val_max NUMERIC(12,4),
    val_avg NUMERIC(12,4),
    val_stddev NUMERIC(12,4),
    val_p50 NUMERIC(12,4),
    val_p95 NUMERIC(12,4),
    val_p99 NUMERIC(12,4),
    
    -- Availability
    uptime_pct NUMERIC(5,2),
    downtime_seconds INTEGER,
    
    -- Anomaly summary
    anomaly_count INTEGER DEFAULT 0,
    
    UNIQUE (device_ip, interface_name, metric_name, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_device_metric ON metrics_daily (device_ip, metric_name, stat_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_site_metric ON metrics_daily (site_id, metric_name, stat_date DESC);


-- Site daily summaries
CREATE TABLE IF NOT EXISTS site_daily_summary (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL,
    site_name VARCHAR(100),
    stat_date DATE NOT NULL,
    
    -- Device counts
    total_devices INTEGER,
    devices_up INTEGER,
    devices_down INTEGER,
    
    -- Availability
    avg_availability_pct NUMERIC(5,2),
    
    -- Performance
    avg_latency_ms NUMERIC(8,3),
    avg_optical_rx_power NUMERIC(8,3),
    
    -- Health
    health_score NUMERIC(5,2),
    
    -- Issues
    anomaly_count INTEGER,
    event_count INTEGER,
    critical_event_count INTEGER,
    
    UNIQUE (site_id, stat_date)
);


-- ============================================================================
-- 7. NETBOX CACHE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS netbox_device_cache (
    netbox_device_id INTEGER PRIMARY KEY,
    device_ip INET,
    device_name VARCHAR(255),
    device_type VARCHAR(255),
    manufacturer VARCHAR(100),
    site_id INTEGER,
    site_name VARCHAR(255),
    role_name VARCHAR(100),
    
    tags TEXT[],
    
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_netbox_cache_ip ON netbox_device_cache (device_ip);
CREATE INDEX IF NOT EXISTS idx_netbox_cache_site ON netbox_device_cache (site_id);
CREATE INDEX IF NOT EXISTS idx_netbox_cache_role ON netbox_device_cache (role_name);


-- ============================================================================
-- 8. AI/ML SUPPORT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS ml_training_snapshots (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    snapshot_type VARCHAR(30),
    
    scope_type VARCHAR(30),
    device_ip INET,
    site_id INTEGER,
    
    feature_vector JSONB,
    label JSONB,
    
    data_start_time TIMESTAMPTZ,
    data_end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    
    accuracy NUMERIC(5,4),
    precision_score NUMERIC(5,4),
    recall_score NUMERIC(5,4),
    f1_score NUMERIC(5,4),
    false_positive_rate NUMERIC(5,4),
    
    predictions_made INTEGER,
    true_positives INTEGER,
    false_positives INTEGER,
    
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================================
-- Record successful migration
-- ============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('001', 'Add metrics tables for time-series data, baselines, anomalies, and health scores');

COMMIT;

-- ============================================================================
-- Post-migration: Create function for automatic partition creation
-- ============================================================================

CREATE OR REPLACE FUNCTION create_monthly_partitions(
    table_name TEXT,
    start_date DATE,
    num_months INTEGER
) RETURNS VOID AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_range TEXT;
    end_range TEXT;
BEGIN
    FOR i IN 0..num_months-1 LOOP
        partition_date := start_date + (i || ' months')::INTERVAL;
        partition_name := table_name || '_' || TO_CHAR(partition_date, 'YYYY_MM');
        start_range := TO_CHAR(partition_date, 'YYYY-MM-01');
        end_range := TO_CHAR(partition_date + '1 month'::INTERVAL, 'YYYY-MM-01');
        
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
            partition_name, table_name, start_range, end_range
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create partitions for the next 12 months
SELECT create_monthly_partitions('optical_metrics', '2026-05-01', 12);
SELECT create_monthly_partitions('interface_metrics', '2026-05-01', 12);
SELECT create_monthly_partitions('path_metrics', '2026-05-01', 12);
SELECT create_monthly_partitions('availability_metrics', '2026-05-01', 12);
SELECT create_monthly_partitions('health_scores', '2026-05-01', 12);
SELECT create_monthly_partitions('metrics_hourly', '2026-05-01', 12);
