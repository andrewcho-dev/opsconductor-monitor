-- OpsConductor v2 Clean Schema
-- Minimal, optimized schema for alert processing

-- Drop existing tables if rebuilding (CAUTION in production!)
-- DROP TABLE IF EXISTS alerts CASCADE;
-- DROP TABLE IF EXISTS addons CASCADE;
-- DROP TABLE IF EXISTS targets CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS api_keys CASCADE;
-- DROP TABLE IF EXISTS audit_log CASCADE;
-- DROP TABLE IF EXISTS system_settings CASCADE;

-- =============================================================================
-- ADDONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS addons (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(32) DEFAULT '1.0.0',
    method VARCHAR(32) NOT NULL,  -- snmp_trap, webhook, api_poll, snmp_poll, ssh
    category VARCHAR(64) DEFAULT 'unknown',
    description TEXT,
    manifest JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_addons_method ON addons(method);
CREATE INDEX IF NOT EXISTS idx_addons_enabled ON addons(enabled);

-- =============================================================================
-- ALERTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    addon_id VARCHAR(64) REFERENCES addons(id) ON DELETE SET NULL,
    fingerprint VARCHAR(64) NOT NULL,
    device_ip VARCHAR(45) NOT NULL,
    device_name VARCHAR(128),
    alert_type VARCHAR(128) NOT NULL,
    severity VARCHAR(32) NOT NULL,  -- critical, major, minor, warning, info
    category VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    message TEXT,
    status VARCHAR(32) DEFAULT 'active',  -- active, acknowledged, suppressed, resolved
    is_clear BOOLEAN DEFAULT false,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    occurrence_count INTEGER DEFAULT 1,
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_device_ip ON alerts(device_ip);
CREATE INDEX IF NOT EXISTS idx_alerts_addon_id ON alerts(addon_id);
CREATE INDEX IF NOT EXISTS idx_alerts_occurred_at ON alerts(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(status) WHERE status != 'resolved';

-- =============================================================================
-- TARGETS (devices to poll)
-- =============================================================================

CREATE TABLE IF NOT EXISTS targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    addon_id VARCHAR(64) REFERENCES addons(id) ON DELETE CASCADE,
    poll_interval INTEGER DEFAULT 300,  -- seconds
    enabled BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',  -- credentials, custom settings
    last_poll_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_targets_addon_id ON targets(addon_id);
CREATE INDEX IF NOT EXISTS idx_targets_enabled ON targets(enabled);
CREATE INDEX IF NOT EXISTS idx_targets_ip ON targets(ip_address);

-- =============================================================================
-- USERS & AUTH
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    email VARCHAR(128),
    role VARCHAR(32) DEFAULT 'viewer',  -- admin, operator, viewer, service
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(64) DEFAULT 'default',
    key_hash VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);

-- =============================================================================
-- SYSTEM SETTINGS
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Default admin user (password: admin - CHANGE IN PRODUCTION!)
INSERT INTO users (username, password_hash, email, role, is_active)
VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin@localhost', 'admin', true)
ON CONFLICT (username) DO NOTHING;

-- Default system settings
INSERT INTO system_settings (key, value) VALUES
    ('version', '2.0.0'),
    ('trap_receiver_port', '162'),
    ('alert_retention_days', '90')
ON CONFLICT (key) DO NOTHING;
