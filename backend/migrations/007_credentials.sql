-- Migration: 007_credentials.sql
-- Description: Create credential vault tables for secure credential storage
-- Created: 2025-12-12

-- Credentials table - stores encrypted credentials
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    credential_type VARCHAR(50) NOT NULL DEFAULT 'ssh',  -- ssh, snmp, api_key, password
    
    -- Encrypted credential data (JSON encrypted with AES-256)
    encrypted_data TEXT NOT NULL,
    
    -- Metadata (not encrypted, for display/filtering)
    username VARCHAR(255),  -- Optional, for display only
    
    -- Usage tracking
    used_by_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Credential groups - for organizing credentials
CREATE TABLE IF NOT EXISTS credential_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many relationship between credentials and groups
CREATE TABLE IF NOT EXISTS credential_group_members (
    credential_id INTEGER REFERENCES credentials(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES credential_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (credential_id, group_id)
);

-- Device credential assignments - which credentials are assigned to which devices
CREATE TABLE IF NOT EXISTS device_credentials (
    id SERIAL PRIMARY KEY,
    device_id INTEGER,  -- References devices table if exists
    ip_address VARCHAR(45),  -- Alternative to device_id
    credential_id INTEGER REFERENCES credentials(id) ON DELETE CASCADE,
    credential_type VARCHAR(50),  -- ssh, snmp, etc. - allows multiple creds per device
    priority INTEGER DEFAULT 0,  -- Higher priority = try first
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, credential_id, credential_type),
    UNIQUE(ip_address, credential_id, credential_type)
);

-- Credential usage audit log
CREATE TABLE IF NOT EXISTS credential_usage_log (
    id SERIAL PRIMARY KEY,
    credential_id INTEGER REFERENCES credentials(id) ON DELETE SET NULL,
    credential_name VARCHAR(255),  -- Stored separately in case credential is deleted
    used_by VARCHAR(255),  -- Job name, workflow name, etc.
    used_for VARCHAR(255),  -- Target device/IP
    success BOOLEAN,
    error_message TEXT,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credentials_type ON credentials(credential_type);
CREATE INDEX IF NOT EXISTS idx_credentials_name ON credentials(name);
CREATE INDEX IF NOT EXISTS idx_credentials_not_deleted ON credentials(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_device_credentials_ip ON device_credentials(ip_address);
CREATE INDEX IF NOT EXISTS idx_device_credentials_device ON device_credentials(device_id);
CREATE INDEX IF NOT EXISTS idx_credential_usage_log_credential ON credential_usage_log(credential_id);
CREATE INDEX IF NOT EXISTS idx_credential_usage_log_time ON credential_usage_log(used_at);

-- Comments
COMMENT ON TABLE credentials IS 'Secure credential storage with AES-256 encryption';
COMMENT ON COLUMN credentials.encrypted_data IS 'AES-256 encrypted JSON containing sensitive data (password, private_key, community_string, api_key, etc.)';
COMMENT ON COLUMN credentials.username IS 'Display-only username, actual auth data is in encrypted_data';
