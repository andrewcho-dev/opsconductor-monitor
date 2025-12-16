-- Migration: 011_enterprise_auth_support.sql
-- Description: Add enterprise authentication support for job execution
-- Created: 2025-12-15

-- Add auth_method to device_credentials to specify how the device authenticates
-- This allows jobs to know whether to use local credentials or enterprise auth
ALTER TABLE device_credentials 
ADD COLUMN IF NOT EXISTS auth_method VARCHAR(50) DEFAULT 'local';

-- Add comment explaining auth_method values
COMMENT ON COLUMN device_credentials.auth_method IS 
'Authentication method: local (direct creds), tacacs, radius, ldap, active_directory';

-- Create a table to store enterprise auth server configurations
-- These are referenced by credentials of type tacacs, radius, ldap, active_directory
CREATE TABLE IF NOT EXISTS enterprise_auth_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    auth_type VARCHAR(50) NOT NULL,  -- tacacs, radius, ldap, active_directory
    credential_id INTEGER REFERENCES credentials(id) ON DELETE SET NULL,  -- Link to credential with server details
    is_default BOOLEAN DEFAULT FALSE,  -- Default server for this auth type
    priority INTEGER DEFAULT 0,  -- For failover ordering
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for quick lookup by auth type
CREATE INDEX IF NOT EXISTS idx_enterprise_auth_type ON enterprise_auth_configs(auth_type);
CREATE INDEX IF NOT EXISTS idx_enterprise_auth_default ON enterprise_auth_configs(auth_type, is_default) WHERE is_default = TRUE;

-- Add a table to map user credentials for enterprise auth
-- This stores the username/password that gets validated against the enterprise server
CREATE TABLE IF NOT EXISTS enterprise_auth_users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    auth_config_id INTEGER REFERENCES enterprise_auth_configs(id) ON DELETE CASCADE,
    -- Encrypted username/password for enterprise auth
    encrypted_credentials TEXT NOT NULL,
    -- Metadata
    username VARCHAR(255),  -- Display only
    is_service_account BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_enterprise_auth_users_config ON enterprise_auth_users(auth_config_id);

-- Add enterprise_auth_user_id to device_credentials for enterprise auth scenarios
ALTER TABLE device_credentials 
ADD COLUMN IF NOT EXISTS enterprise_auth_user_id INTEGER REFERENCES enterprise_auth_users(id) ON DELETE SET NULL;

-- Comments
COMMENT ON TABLE enterprise_auth_configs IS 'Configuration for enterprise authentication servers (TACACS+, RADIUS, LDAP, AD)';
COMMENT ON TABLE enterprise_auth_users IS 'User credentials validated against enterprise auth servers';
COMMENT ON COLUMN device_credentials.enterprise_auth_user_id IS 'Reference to enterprise auth user for non-local authentication';
