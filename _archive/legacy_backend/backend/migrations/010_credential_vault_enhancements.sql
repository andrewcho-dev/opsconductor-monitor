-- Migration: 010_credential_vault_enhancements.sql
-- Description: Enhance credential vault with comprehensive audit logging, certificate support, and expiration tracking
-- Created: 2025-12-15

-- ============================================================================
-- CREDENTIAL AUDIT LOG TABLE (Enhanced)
-- Comprehensive audit trail for all credential actions
-- ============================================================================
CREATE TABLE IF NOT EXISTS credential_audit_log (
    id SERIAL PRIMARY KEY,
    
    -- What credential was affected
    credential_id INTEGER REFERENCES credentials(id) ON DELETE SET NULL,
    credential_name VARCHAR(255) NOT NULL,  -- Stored separately for historical reference
    credential_type VARCHAR(50),
    
    -- What action was performed
    action VARCHAR(50) NOT NULL,  -- created, updated, deleted, accessed, used, expired, rotated, exported, imported
    action_detail TEXT,  -- Additional details about the action
    
    -- Who performed the action
    performed_by VARCHAR(255),  -- User or system component
    performed_by_ip VARCHAR(45),  -- IP address of the actor
    performed_by_user_agent TEXT,  -- Browser/client info
    
    -- Context of the action
    target_device VARCHAR(255),  -- Device IP/hostname if credential was used
    target_service VARCHAR(255),  -- Service name (SSH, WinRM, SNMP, etc.)
    workflow_id INTEGER,  -- If used in a workflow
    workflow_name VARCHAR(255),
    job_id INTEGER,  -- If used in a job
    job_name VARCHAR(255),
    
    -- Result of the action
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- What changed (for updates)
    previous_values JSONB,  -- Stores non-sensitive previous values
    new_values JSONB,  -- Stores non-sensitive new values
    
    -- Timestamps
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Session/request tracking
    session_id VARCHAR(255),
    request_id VARCHAR(255)
);

-- Indexes for audit log
CREATE INDEX IF NOT EXISTS idx_cred_audit_credential_id ON credential_audit_log(credential_id);
CREATE INDEX IF NOT EXISTS idx_cred_audit_action ON credential_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_cred_audit_performed_at ON credential_audit_log(performed_at);
CREATE INDEX IF NOT EXISTS idx_cred_audit_performed_by ON credential_audit_log(performed_by);
CREATE INDEX IF NOT EXISTS idx_cred_audit_success ON credential_audit_log(success);
CREATE INDEX IF NOT EXISTS idx_cred_audit_target_device ON credential_audit_log(target_device);

-- ============================================================================
-- ADD NEW COLUMNS TO CREDENTIALS TABLE
-- Support for certificates, expiration, and enhanced metadata
-- ============================================================================

-- Add expiration and validity tracking
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP WITH TIME ZONE;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS valid_until TIMESTAMP WITH TIME ZONE;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS is_expired BOOLEAN DEFAULT FALSE;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS expiration_warning_days INTEGER DEFAULT 30;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS last_rotation_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS rotation_interval_days INTEGER;

-- Add certificate-specific fields
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS certificate_fingerprint VARCHAR(255);
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS certificate_issuer TEXT;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS certificate_subject TEXT;
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS certificate_serial VARCHAR(255);
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS key_algorithm VARCHAR(50);  -- RSA, ECDSA, Ed25519
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS key_size INTEGER;  -- 2048, 4096, etc.

-- Add metadata and categorization
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS tags TEXT[];  -- Array of tags for filtering
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS category VARCHAR(100);  -- network, server, cloud, database, etc.
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS environment VARCHAR(50);  -- production, staging, development
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS owner VARCHAR(255);  -- Who owns/manages this credential
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS notes TEXT;  -- Additional notes

-- Add access control
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS access_level VARCHAR(50) DEFAULT 'standard';  -- restricted, standard, public
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS allowed_users TEXT[];  -- Users who can access this credential
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS allowed_groups TEXT[];  -- Groups who can access this credential

-- Add status tracking
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';  -- active, disabled, expired, revoked, pending_rotation

-- Indexes for new columns
CREATE INDEX IF NOT EXISTS idx_credentials_valid_until ON credentials(valid_until);
CREATE INDEX IF NOT EXISTS idx_credentials_is_expired ON credentials(is_expired);
CREATE INDEX IF NOT EXISTS idx_credentials_status ON credentials(status);
CREATE INDEX IF NOT EXISTS idx_credentials_category ON credentials(category);
CREATE INDEX IF NOT EXISTS idx_credentials_environment ON credentials(environment);
CREATE INDEX IF NOT EXISTS idx_credentials_tags ON credentials USING GIN(tags);

-- ============================================================================
-- CREDENTIAL ACCESS REQUESTS TABLE
-- Track requests to access sensitive credentials
-- ============================================================================
CREATE TABLE IF NOT EXISTS credential_access_requests (
    id SERIAL PRIMARY KEY,
    credential_id INTEGER REFERENCES credentials(id) ON DELETE CASCADE,
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, denied, expired
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    access_granted_until TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cred_access_req_credential ON credential_access_requests(credential_id);
CREATE INDEX IF NOT EXISTS idx_cred_access_req_status ON credential_access_requests(status);
CREATE INDEX IF NOT EXISTS idx_cred_access_req_requested_by ON credential_access_requests(requested_by);

-- ============================================================================
-- CREDENTIAL ROTATION HISTORY TABLE
-- Track credential rotations
-- ============================================================================
CREATE TABLE IF NOT EXISTS credential_rotation_history (
    id SERIAL PRIMARY KEY,
    credential_id INTEGER REFERENCES credentials(id) ON DELETE CASCADE,
    rotated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rotated_by VARCHAR(255),
    rotation_type VARCHAR(50),  -- manual, automatic, scheduled, emergency
    previous_valid_until TIMESTAMP WITH TIME ZONE,
    new_valid_until TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_cred_rotation_credential ON credential_rotation_history(credential_id);
CREATE INDEX IF NOT EXISTS idx_cred_rotation_rotated_at ON credential_rotation_history(rotated_at);

-- ============================================================================
-- UPDATE CREDENTIAL TYPES
-- Add support for new credential types
-- ============================================================================
COMMENT ON COLUMN credentials.credential_type IS 'Credential type: ssh, snmp, api_key, password, winrm, certificate, pki, oauth, bearer_token, kerberos';

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for credentials with expiration status
CREATE OR REPLACE VIEW v_credentials_with_status AS
SELECT 
    c.*,
    CASE 
        WHEN c.valid_until IS NULL THEN 'no_expiration'
        WHEN c.valid_until < CURRENT_TIMESTAMP THEN 'expired'
        WHEN c.valid_until < CURRENT_TIMESTAMP + (c.expiration_warning_days || ' days')::INTERVAL THEN 'expiring_soon'
        ELSE 'valid'
    END as expiration_status,
    CASE 
        WHEN c.valid_until IS NOT NULL THEN 
            EXTRACT(DAY FROM (c.valid_until - CURRENT_TIMESTAMP))::INTEGER
        ELSE NULL
    END as days_until_expiration
FROM credentials c
WHERE c.is_deleted = FALSE;

-- View for recent audit activity
CREATE OR REPLACE VIEW v_recent_credential_activity AS
SELECT 
    cal.*,
    c.name as current_credential_name,
    c.credential_type as current_credential_type
FROM credential_audit_log cal
LEFT JOIN credentials c ON cal.credential_id = c.id
ORDER BY cal.performed_at DESC;

-- ============================================================================
-- FUNCTIONS FOR CREDENTIAL MANAGEMENT
-- ============================================================================

-- Function to update expired status
CREATE OR REPLACE FUNCTION update_credential_expiration_status()
RETURNS void AS $$
BEGIN
    UPDATE credentials
    SET 
        is_expired = TRUE,
        status = 'expired'
    WHERE 
        valid_until IS NOT NULL 
        AND valid_until < CURRENT_TIMESTAMP 
        AND is_expired = FALSE
        AND is_deleted = FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to get credentials expiring soon
CREATE OR REPLACE FUNCTION get_expiring_credentials(days_ahead INTEGER DEFAULT 30)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR(255),
    credential_type VARCHAR(50),
    valid_until TIMESTAMP WITH TIME ZONE,
    days_remaining INTEGER,
    owner VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.name,
        c.credential_type,
        c.valid_until,
        EXTRACT(DAY FROM (c.valid_until - CURRENT_TIMESTAMP))::INTEGER as days_remaining,
        c.owner
    FROM credentials c
    WHERE 
        c.is_deleted = FALSE
        AND c.valid_until IS NOT NULL
        AND c.valid_until > CURRENT_TIMESTAMP
        AND c.valid_until < CURRENT_TIMESTAMP + (days_ahead || ' days')::INTERVAL
    ORDER BY c.valid_until ASC;
END;
$$ LANGUAGE plpgsql;

-- Record this migration
INSERT INTO schema_versions (version, description) 
VALUES ('010', 'Credential vault enhancements - audit logging, certificates, expiration tracking')
ON CONFLICT (version) DO NOTHING;
