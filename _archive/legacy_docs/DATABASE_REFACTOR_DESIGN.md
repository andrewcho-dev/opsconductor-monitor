# OpsConductor Database Refactor Design

## Vision

Build a **network intelligence platform** that:
1. Records comprehensive performance and status metrics
2. Establishes **baselines** for what "normal" looks like
3. Enables **AI/ML systems** to detect anomalies and predict issues
4. Provides historical context for troubleshooting and capacity planning

## Architecture Principle

**NetBox** = Single Source of Truth for Device Inventory
- What devices exist, their types, interfaces, sites, IPs
- Static/configuration data
- Network topology and connections

**OpsConductor** = Network Intelligence Data Store
- **Performance metrics** - optical power, latency, bandwidth, errors
- **Availability metrics** - uptime, reachability, response times
- **Baseline profiles** - statistical models of "normal" behavior
- **Anomaly records** - detected deviations from baseline
- **Historical trends** - long-term performance data
- **Configuration snapshots** - change tracking
- **Event correlation** - linking related events across devices

## Linking Strategy

All OpsConductor tables link to NetBox devices via:
- `device_ip` (INET) - Primary link, always available
- `netbox_device_id` (INTEGER, nullable) - Cached for faster joins
- `site_id` (INTEGER, nullable) - Cached site for geographic analysis

## Schema Design

### 1. Core Performance Metrics (Time-Series, Partitioned)

```sql
-- Optical power readings - critical for fiber network health
CREATE TABLE optical_metrics (
    id BIGSERIAL,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100) NOT NULL,
    interface_index INTEGER,
    
    -- Optical metrics
    tx_power NUMERIC(8,3),              -- dBm
    rx_power NUMERIC(8,3),              -- dBm
    tx_power_high_warn NUMERIC(8,3),    -- Threshold from transceiver
    tx_power_low_warn NUMERIC(8,3),
    rx_power_high_warn NUMERIC(8,3),
    rx_power_low_warn NUMERIC(8,3),
    temperature NUMERIC(6,2),           -- Celsius
    voltage NUMERIC(6,3),               -- Volts
    bias_current NUMERIC(8,3),          -- mA
    
    -- Quality indicators
    signal_quality_pct NUMERIC(5,2),    -- Calculated signal quality 0-100%
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Partitions created automatically via pg_partman or manual cron
-- Indexes for common query patterns
CREATE INDEX idx_optical_device_time ON optical_metrics (device_ip, recorded_at DESC);
CREATE INDEX idx_optical_interface_time ON optical_metrics (device_ip, interface_name, recorded_at DESC);
CREATE INDEX idx_optical_site_time ON optical_metrics (site_id, recorded_at DESC);
CREATE INDEX idx_optical_netbox_id ON optical_metrics (netbox_device_id) WHERE netbox_device_id IS NOT NULL;
```

```sql
-- Interface traffic and error statistics
CREATE TABLE interface_metrics (
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
    
    -- Calculated rates (per second, computed from delta)
    rx_bps BIGINT,                      -- Bits per second
    tx_bps BIGINT,
    rx_pps INTEGER,                     -- Packets per second
    tx_pps INTEGER,
    
    -- Utilization
    rx_utilization_pct NUMERIC(5,2),    -- % of interface capacity
    tx_utilization_pct NUMERIC(5,2),
    
    -- Errors and discards
    rx_errors BIGINT,
    tx_errors BIGINT,
    rx_discards BIGINT,
    tx_discards BIGINT,
    rx_crc_errors BIGINT,
    collisions BIGINT,
    
    -- Error rates (per million packets)
    error_rate_ppm NUMERIC(8,2),
    
    -- Status
    oper_status INTEGER,                -- 1=up, 2=down
    admin_status INTEGER,
    speed_mbps INTEGER,
    duplex VARCHAR(10),                 -- full, half
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE INDEX idx_iface_device_time ON interface_metrics (device_ip, recorded_at DESC);
CREATE INDEX idx_iface_site_time ON interface_metrics (site_id, recorded_at DESC);
```

```sql
-- Network path performance (latency, jitter, packet loss between points)
CREATE TABLE path_metrics (
    id BIGSERIAL,
    source_ip INET NOT NULL,
    destination_ip INET NOT NULL,
    source_device_id INTEGER,
    destination_device_id INTEGER,
    source_site_id INTEGER,
    destination_site_id INTEGER,
    
    -- Latency metrics (milliseconds)
    latency_ms NUMERIC(10,3),           -- Round-trip time
    latency_min_ms NUMERIC(10,3),
    latency_max_ms NUMERIC(10,3),
    latency_stddev_ms NUMERIC(10,3),
    
    -- Jitter (variation in latency)
    jitter_ms NUMERIC(10,3),
    
    -- Packet loss
    packets_sent INTEGER,
    packets_received INTEGER,
    packet_loss_pct NUMERIC(5,2),
    
    -- Hop count
    hop_count INTEGER,
    
    -- Test metadata
    test_type VARCHAR(20),              -- 'icmp', 'tcp', 'udp'
    test_duration_ms INTEGER,
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE INDEX idx_path_source_time ON path_metrics (source_ip, recorded_at DESC);
CREATE INDEX idx_path_dest_time ON path_metrics (destination_ip, recorded_at DESC);
CREATE INDEX idx_path_sites ON path_metrics (source_site_id, destination_site_id, recorded_at DESC);
```

```sql
-- Device availability and reachability
CREATE TABLE availability_metrics (
    id BIGSERIAL,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    site_id INTEGER,
    device_role VARCHAR(50),            -- Cached: 'switch', 'router', 'camera'
    
    -- Reachability status
    ping_status VARCHAR(20),            -- 'up', 'down', 'timeout', 'unreachable'
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
    
    -- Power (for PoE devices)
    poe_power_watts NUMERIC(8,2),
    poe_power_available_watts NUMERIC(8,2),
    
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE INDEX idx_avail_device_time ON availability_metrics (device_ip, recorded_at DESC);
CREATE INDEX idx_avail_site_time ON availability_metrics (site_id, recorded_at DESC);
CREATE INDEX idx_avail_role_time ON availability_metrics (device_role, recorded_at DESC);
```

### 2. Baseline & Anomaly Detection Tables (AI Foundation)

```sql
-- Baseline profiles - statistical model of "normal" for each metric
-- Updated periodically (daily/weekly) by baseline calculation job
CREATE TABLE metric_baselines (
    id SERIAL PRIMARY KEY,
    
    -- Scope: what this baseline applies to
    scope_type VARCHAR(30) NOT NULL,    -- 'device', 'interface', 'site', 'path', 'device_role', 'network'
    device_ip INET,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    device_role VARCHAR(50),
    
    -- Metric being baselined
    metric_name VARCHAR(50) NOT NULL,   -- 'rx_power', 'latency', 'utilization', 'error_rate'
    metric_unit VARCHAR(20),            -- 'dBm', 'ms', 'percent', 'ppm'
    
    -- Time context
    time_period VARCHAR(20) NOT NULL,   -- 'hourly', 'daily', 'weekly'
    hour_of_day INTEGER,                -- 0-23, NULL for daily/weekly
    day_of_week INTEGER,                -- 0-6, NULL for daily
    
    -- Statistical baseline (calculated from historical data)
    sample_count INTEGER NOT NULL,
    baseline_mean NUMERIC(12,4),
    baseline_median NUMERIC(12,4),
    baseline_stddev NUMERIC(12,4),
    baseline_min NUMERIC(12,4),
    baseline_max NUMERIC(12,4),
    baseline_p5 NUMERIC(12,4),          -- 5th percentile
    baseline_p95 NUMERIC(12,4),         -- 95th percentile
    baseline_p99 NUMERIC(12,4),         -- 99th percentile
    
    -- Threshold derivation (for anomaly detection)
    warn_threshold_low NUMERIC(12,4),   -- Below this = warning
    warn_threshold_high NUMERIC(12,4),  -- Above this = warning
    crit_threshold_low NUMERIC(12,4),   -- Below this = critical
    crit_threshold_high NUMERIC(12,4),  -- Above this = critical
    
    -- Baseline metadata
    baseline_start_date DATE NOT NULL,  -- Data range used
    baseline_end_date DATE NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    confidence_score NUMERIC(5,2),      -- How reliable is this baseline (0-100)
    
    UNIQUE (scope_type, device_ip, interface_name, metric_name, time_period, hour_of_day, day_of_week)
);

CREATE INDEX idx_baseline_device ON metric_baselines (device_ip, metric_name) WHERE device_ip IS NOT NULL;
CREATE INDEX idx_baseline_site ON metric_baselines (site_id, metric_name) WHERE site_id IS NOT NULL;
CREATE INDEX idx_baseline_scope ON metric_baselines (scope_type, metric_name);
```

```sql
-- Detected anomalies - deviations from baseline
CREATE TABLE anomaly_events (
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
    deviation_sigma NUMERIC(6,2),       -- How many std devs from mean
    deviation_pct NUMERIC(8,2),         -- % deviation from mean
    
    -- Severity
    severity VARCHAR(20) NOT NULL,      -- 'info', 'warning', 'critical'
    anomaly_type VARCHAR(30),           -- 'spike', 'drop', 'trend', 'flatline', 'oscillation'
    
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
    correlation_group_id UUID,          -- Links related anomalies
    root_cause_event_id BIGINT          -- Points to the root cause if identified
);

CREATE INDEX idx_anomaly_device_time ON anomaly_events (device_ip, detected_at DESC);
CREATE INDEX idx_anomaly_site_time ON anomaly_events (site_id, detected_at DESC);
CREATE INDEX idx_anomaly_severity ON anomaly_events (severity, detected_at DESC) WHERE resolved_at IS NULL;
CREATE INDEX idx_anomaly_correlation ON anomaly_events (correlation_group_id) WHERE correlation_group_id IS NOT NULL;
```

```sql
-- Network health scores - aggregated health metrics for dashboards/AI
CREATE TABLE health_scores (
    id BIGSERIAL,
    
    -- Scope
    scope_type VARCHAR(30) NOT NULL,    -- 'device', 'site', 'path', 'network'
    device_ip INET,
    netbox_device_id INTEGER,
    site_id INTEGER,
    path_id VARCHAR(100),               -- 'source_ip->dest_ip'
    
    -- Health scores (0-100, higher = healthier)
    overall_score NUMERIC(5,2),
    availability_score NUMERIC(5,2),
    performance_score NUMERIC(5,2),
    error_score NUMERIC(5,2),           -- Inverse of error rate
    capacity_score NUMERIC(5,2),        -- How much headroom
    
    -- Component scores
    optical_health NUMERIC(5,2),
    latency_health NUMERIC(5,2),
    throughput_health NUMERIC(5,2),
    
    -- Trend indicators (-100 to +100, negative = degrading)
    trend_1h NUMERIC(6,2),              -- Trend over last hour
    trend_24h NUMERIC(6,2),             -- Trend over last day
    trend_7d NUMERIC(6,2),              -- Trend over last week
    
    -- Active issues
    active_anomaly_count INTEGER DEFAULT 0,
    active_warning_count INTEGER DEFAULT 0,
    active_critical_count INTEGER DEFAULT 0,
    
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, calculated_at)
) PARTITION BY RANGE (calculated_at);

CREATE INDEX idx_health_device ON health_scores (device_ip, calculated_at DESC);
CREATE INDEX idx_health_site ON health_scores (site_id, calculated_at DESC);
CREATE INDEX idx_health_scope ON health_scores (scope_type, calculated_at DESC);
```

```sql
-- Metric correlations - discovered relationships between metrics
-- Used by AI to understand cause-effect relationships
CREATE TABLE metric_correlations (
    id SERIAL PRIMARY KEY,
    
    -- Metric A
    metric_a_name VARCHAR(50) NOT NULL,
    metric_a_scope_type VARCHAR(30),
    metric_a_device_ip INET,
    metric_a_interface VARCHAR(100),
    
    -- Metric B
    metric_b_name VARCHAR(50) NOT NULL,
    metric_b_scope_type VARCHAR(30),
    metric_b_device_ip INET,
    metric_b_interface VARCHAR(100),
    
    -- Correlation stats
    correlation_coefficient NUMERIC(6,4),  -- -1 to +1
    correlation_type VARCHAR(20),          -- 'positive', 'negative', 'lagged'
    lag_seconds INTEGER,                   -- If B follows A by N seconds
    confidence_score NUMERIC(5,2),
    sample_count INTEGER,
    
    -- Interpretation
    relationship_type VARCHAR(30),         -- 'causal', 'symptomatic', 'coincidental'
    description TEXT,
    
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_validated_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 3. Configuration & State Snapshot Tables

```sql
-- CLI configuration snapshots (for change tracking)
CREATE TABLE config_snapshots (
    id SERIAL PRIMARY KEY,
    device_ip INET NOT NULL,
    netbox_device_id INTEGER,
    
    config_type VARCHAR(50) NOT NULL,   -- 'running', 'startup', 'interfaces'
    config_hash VARCHAR(64) NOT NULL,   -- SHA256 for change detection
    config_content TEXT NOT NULL,
    
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_from_previous BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_config_device_type ON config_snapshots (device_ip, config_type, captured_at DESC);
CREATE INDEX idx_config_hash ON config_snapshots (config_hash);
```

```sql
-- Interface state snapshots (LLDP, optical details)
CREATE TABLE interface_snapshots (
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

CREATE INDEX idx_iface_snap_device ON interface_snapshots (device_ip, captured_at DESC);
```

### 4. Event & Change Tracking

```sql
-- Network events - significant occurrences for correlation
CREATE TABLE network_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- What
    event_type VARCHAR(50) NOT NULL,    -- 'link_down', 'link_up', 'config_change', 'failover', 'reboot'
    event_category VARCHAR(30),         -- 'availability', 'performance', 'security', 'config'
    severity VARCHAR(20),               -- 'info', 'warning', 'critical'
    
    -- Where
    device_ip INET,
    netbox_device_id INTEGER,
    site_id INTEGER,
    interface_name VARCHAR(100),
    
    -- Details
    description TEXT,
    details JSONB,                      -- Flexible additional data
    
    -- Timing
    event_time TIMESTAMPTZ NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER,           -- For events with duration
    
    -- Correlation
    correlation_group_id UUID,
    caused_by_event_id BIGINT,
    
    -- Source
    source_system VARCHAR(50),          -- 'snmp_trap', 'syslog', 'poll', 'manual'
    source_message TEXT
);

CREATE INDEX idx_events_device_time ON network_events (device_ip, event_time DESC);
CREATE INDEX idx_events_site_time ON network_events (site_id, event_time DESC);
CREATE INDEX idx_events_type_time ON network_events (event_type, event_time DESC);
CREATE INDEX idx_events_correlation ON network_events (correlation_group_id);
```

### 5. Job & Polling History

```sql
-- Polling job execution history
CREATE TABLE poll_history (
    id BIGSERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,      -- 'optical', 'snmp', 'availability'
    device_ip INET,                     -- NULL for batch jobs
    netbox_device_id INTEGER,
    
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    status VARCHAR(20) NOT NULL,        -- 'success', 'failed', 'timeout'
    error_message TEXT,
    records_collected INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_poll_history_type_time ON poll_history (job_type, started_at DESC);
CREATE INDEX idx_poll_history_device ON poll_history (device_ip, started_at DESC);
```

### 6. Credentials (Keep existing, add netbox_device_id)

```sql
-- Update device_credentials to use netbox_device_id
ALTER TABLE device_credentials 
    ADD COLUMN netbox_device_id INTEGER,
    ADD COLUMN device_name VARCHAR(255);  -- Cached from NetBox for display

-- Index for NetBox lookups
CREATE INDEX idx_device_creds_netbox ON device_credentials (netbox_device_id);
```

### 7. Aggregation Tables (For Fast Reporting & AI Training)

```sql
-- Hourly aggregates for all metrics (granular for recent data)
CREATE TABLE metrics_hourly (
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
    val_p50 NUMERIC(12,4),              -- Median
    val_p95 NUMERIC(12,4),
    val_p99 NUMERIC(12,4),
    
    PRIMARY KEY (id, stat_hour)
) PARTITION BY RANGE (stat_hour);

CREATE INDEX idx_hourly_device_metric ON metrics_hourly (device_ip, metric_name, stat_hour DESC);
CREATE INDEX idx_hourly_site_metric ON metrics_hourly (site_id, metric_name, stat_hour DESC);
```

```sql
-- Daily aggregates (for long-term trends and reporting)
CREATE TABLE metrics_daily (
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
    
    -- Availability (for that day)
    uptime_pct NUMERIC(5,2),
    downtime_seconds INTEGER,
    
    -- Anomaly summary
    anomaly_count INTEGER DEFAULT 0,
    
    UNIQUE (device_ip, interface_name, metric_name, stat_date)
);

CREATE INDEX idx_daily_device_metric ON metrics_daily (device_ip, metric_name, stat_date DESC);
CREATE INDEX idx_daily_site_metric ON metrics_daily (site_id, metric_name, stat_date DESC);
```

```sql
-- Site-level daily summaries (for executive dashboards)
CREATE TABLE site_daily_summary (
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
```

### 8. NetBox Cache Table (For Performance & Offline Operation)

```sql
-- Cached device info from NetBox (refreshed periodically)
CREATE TABLE netbox_device_cache (
    netbox_device_id INTEGER PRIMARY KEY,
    device_ip INET,
    device_name VARCHAR(255),
    device_type VARCHAR(255),
    manufacturer VARCHAR(100),
    site_id INTEGER,
    site_name VARCHAR(255),
    role_name VARCHAR(100),
    
    -- For grouping/filtering
    tags TEXT[],
    
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_netbox_cache_ip ON netbox_device_cache (device_ip);
CREATE INDEX idx_netbox_cache_site ON netbox_device_cache (site_id);
CREATE INDEX idx_netbox_cache_role ON netbox_device_cache (role_name);
```

### 9. AI/ML Support Tables

```sql
-- Training data snapshots for ML models
CREATE TABLE ml_training_snapshots (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,   -- 'anomaly_detector', 'failure_predictor'
    snapshot_type VARCHAR(30),          -- 'features', 'labels', 'full'
    
    -- Scope
    scope_type VARCHAR(30),
    device_ip INET,
    site_id INTEGER,
    
    -- Data
    feature_vector JSONB,               -- Input features
    label JSONB,                        -- Output labels (for supervised)
    
    -- Metadata
    data_start_time TIMESTAMPTZ,
    data_end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

```sql
-- Model performance tracking
CREATE TABLE ml_model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    
    -- Performance metrics
    accuracy NUMERIC(5,4),
    precision_score NUMERIC(5,4),
    recall_score NUMERIC(5,4),
    f1_score NUMERIC(5,4),
    false_positive_rate NUMERIC(5,4),
    
    -- Usage stats
    predictions_made INTEGER,
    true_positives INTEGER,
    false_positives INTEGER,
    
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Data Retention Policy

| Data Type | Raw Data | Hourly Aggregates | Daily Aggregates |
|-----------|----------|-------------------|------------------|
| Optical metrics | 90 days | 1 year | 5 years |
| Interface metrics | 30 days | 1 year | 5 years |
| Path metrics | 30 days | 1 year | 5 years |
| Availability | 90 days | 1 year | 5 years |
| Events | 1 year | N/A | N/A |
| Anomalies | 2 years | N/A | N/A |
| Health scores | 90 days | 1 year | 5 years |
| Baselines | Keep active | N/A | N/A |

## Migration Plan

### Phase 1: Create New Schema
1. Create all new tables with partitioning
2. Create indexes
3. Set up partition management (pg_partman or cron)

### Phase 2: Migrate Existing Data
```sql
-- Migrate optical_power_history to optical_metrics
INSERT INTO optical_metrics (device_ip, interface_name, interface_index, tx_power, rx_power, temperature, recorded_at)
SELECT ip_address, interface_name, interface_index, tx_power, rx_power, temperature, measurement_timestamp
FROM optical_power_history;

-- Migrate ssh_cli_scans to interface_snapshots
INSERT INTO interface_snapshots (device_ip, interface_name, interface_index, is_optical, medium, connector, speed, 
                                  lldp_remote_system, lldp_remote_port, lldp_remote_mgmt_ip, lldp_remote_chassis_id, captured_at)
SELECT ip_address, interface_name, interface_index, is_optical, medium, connector, speed,
       lldp_remote_system_name, lldp_remote_port, lldp_remote_mgmt_addr::inet, lldp_remote_chassis_id, scan_timestamp
FROM ssh_cli_scans;
```

### Phase 3: Populate NetBox Cache
```python
# Sync NetBox devices to cache table
for device in netbox_api.get_devices():
    db.execute("""
        INSERT INTO netbox_device_cache 
        (netbox_device_id, device_ip, device_name, device_type, site_id, site_name, role_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (netbox_device_id) DO UPDATE SET ...
    """, [device.id, device.primary_ip, device.name, ...])
```

### Phase 4: Calculate Initial Baselines
```sql
-- Calculate baseline for each device/interface/metric
INSERT INTO metric_baselines (scope_type, device_ip, interface_name, metric_name, ...)
SELECT 
    'interface',
    device_ip,
    interface_name,
    'rx_power',
    COUNT(*),
    AVG(rx_power),
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rx_power),
    STDDEV(rx_power),
    MIN(rx_power),
    MAX(rx_power),
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY rx_power),
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY rx_power),
    ...
FROM optical_metrics
WHERE recorded_at > NOW() - INTERVAL '30 days'
GROUP BY device_ip, interface_name;
```

### Phase 5: Update Application Code
1. Update pollers to write to new tables
2. Add baseline calculation job (runs daily)
3. Add anomaly detection job (runs with each poll)
4. Add health score calculation job (runs hourly)
5. Update API endpoints to use new schema
6. Add NetBox integration for device lookups

### Phase 6: Cleanup
1. Verify all data migrated correctly
2. Drop old tables
3. Set up automated partition maintenance
4. Set up data retention cleanup job

## Example Queries

### Optical Power Trend with Baseline Comparison
```sql
SELECT 
    date_trunc('hour', m.recorded_at) as hour,
    AVG(m.rx_power) as avg_rx,
    b.baseline_mean,
    b.baseline_mean - 2 * b.baseline_stddev as lower_bound,
    b.baseline_mean + 2 * b.baseline_stddev as upper_bound
FROM optical_metrics m
JOIN metric_baselines b ON b.device_ip = m.device_ip 
    AND b.interface_name = m.interface_name 
    AND b.metric_name = 'rx_power'
WHERE m.device_ip = '10.120.0.1'
  AND m.interface_name = 'port1'
  AND m.recorded_at > NOW() - INTERVAL '7 days'
GROUP BY 1, b.baseline_mean, b.baseline_stddev
ORDER BY 1;
```

### Site Health Dashboard
```sql
SELECT 
    nc.site_name,
    COUNT(DISTINCT nc.device_ip) as total_devices,
    AVG(hs.overall_score) as health_score,
    AVG(hs.availability_score) as availability,
    COUNT(ae.id) FILTER (WHERE ae.severity = 'critical' AND ae.resolved_at IS NULL) as critical_issues
FROM netbox_device_cache nc
LEFT JOIN health_scores hs ON hs.device_ip = nc.device_ip 
    AND hs.calculated_at > NOW() - INTERVAL '1 hour'
LEFT JOIN anomaly_events ae ON ae.device_ip = nc.device_ip 
    AND ae.detected_at > NOW() - INTERVAL '24 hours'
GROUP BY nc.site_name
ORDER BY health_score;
```

### Anomaly Detection Query (Run by Poller)
```sql
-- Find metrics that deviate significantly from baseline
WITH recent_metrics AS (
    SELECT device_ip, interface_name, rx_power as value, recorded_at
    FROM optical_metrics
    WHERE recorded_at > NOW() - INTERVAL '5 minutes'
)
SELECT 
    m.device_ip,
    m.interface_name,
    m.value,
    b.baseline_mean,
    b.baseline_stddev,
    (m.value - b.baseline_mean) / NULLIF(b.baseline_stddev, 0) as sigma_deviation,
    CASE 
        WHEN ABS((m.value - b.baseline_mean) / NULLIF(b.baseline_stddev, 0)) > 3 THEN 'critical'
        WHEN ABS((m.value - b.baseline_mean) / NULLIF(b.baseline_stddev, 0)) > 2 THEN 'warning'
        ELSE 'normal'
    END as severity
FROM recent_metrics m
JOIN metric_baselines b ON b.device_ip = m.device_ip 
    AND b.interface_name = m.interface_name 
    AND b.metric_name = 'rx_power'
    AND b.is_active = TRUE
WHERE ABS((m.value - b.baseline_mean) / NULLIF(b.baseline_stddev, 0)) > 2;
```

### Network-Wide Performance Summary (For AI Context)
```sql
SELECT 
    'network' as scope,
    NOW() as snapshot_time,
    jsonb_build_object(
        'total_devices', COUNT(DISTINCT device_ip),
        'avg_availability', AVG(CASE WHEN ping_status = 'up' THEN 100 ELSE 0 END),
        'avg_latency_ms', AVG(ping_latency_ms),
        'devices_with_issues', COUNT(DISTINCT device_ip) FILTER (WHERE ping_status != 'up'),
        'active_anomalies', (SELECT COUNT(*) FROM anomaly_events WHERE resolved_at IS NULL),
        'health_score', AVG(overall_score)
    ) as network_state
FROM availability_metrics a
JOIN health_scores h ON h.device_ip = a.device_ip
WHERE a.recorded_at > NOW() - INTERVAL '5 minutes'
  AND h.calculated_at > NOW() - INTERVAL '1 hour';
```

## Benefits

1. **AI-Ready Architecture**
   - Baseline tables capture "normal" behavior
   - Anomaly detection built into schema
   - Correlation tracking for root cause analysis
   - Health scores for quick assessment

2. **Performance Optimized**
   - Partitioned tables for fast time-range queries
   - Pre-computed aggregates for dashboards
   - Proper indexes for common access patterns

3. **Comprehensive Metrics**
   - Optical power with thresholds
   - Interface traffic and errors
   - Path latency and packet loss
   - Device availability and health

4. **Historical Analysis**
   - Hourly aggregates for recent trends
   - Daily aggregates for long-term analysis
   - Site-level summaries for executive reporting

5. **NetBox Integration**
   - Single source of truth for inventory
   - Cached device info for performance
   - No data duplication

6. **Scalable**
   - Can handle millions of metrics
   - Automatic partition management
   - Configurable data retention
