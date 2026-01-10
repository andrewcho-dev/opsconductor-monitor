-- Migration 012: RBAC and Authentication System
-- Adds user accounts, roles, permissions, sessions, and 2FA support

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),  -- NULL if using enterprise auth only
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(200),
    avatar_url TEXT,
    
    -- Account status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'locked', 'pending')),
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Authentication method
    auth_method VARCHAR(20) DEFAULT 'local' CHECK (auth_method IN ('local', 'ldap', 'active_directory', 'saml', 'oauth')),
    external_auth_id VARCHAR(255),  -- ID from external auth provider
    external_auth_provider VARCHAR(100),  -- e.g., 'corporate-ad', 'okta'
    
    -- Password policy
    password_changed_at TIMESTAMP WITH TIME ZONE,
    password_expires_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- 2FA settings
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_method VARCHAR(20) CHECK (two_factor_method IN ('totp', 'email', 'both')),
    totp_secret_encrypted TEXT,  -- Encrypted TOTP secret for authenticator apps
    totp_backup_codes_encrypted TEXT,  -- Encrypted backup codes (JSON array)
    
    -- Preferences
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferences JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip VARCHAR(45)
);

-- =============================================================================
-- ROLES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Role type
    role_type VARCHAR(20) DEFAULT 'custom' CHECK (role_type IN ('system', 'custom')),
    is_default BOOLEAN DEFAULT FALSE,  -- Assigned to new users automatically
    
    -- Hierarchy (optional, for role inheritance)
    parent_role_id INTEGER REFERENCES roles(id),
    priority INTEGER DEFAULT 0,  -- Higher = more privileged
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- PERMISSIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    
    -- Permission identifier: module.resource.action
    -- e.g., 'devices.device.create', 'jobs.job.run', 'credentials.credential.view'
    code VARCHAR(100) NOT NULL UNIQUE,
    
    -- Categorization
    module VARCHAR(50) NOT NULL,  -- e.g., 'devices', 'jobs', 'credentials', 'system'
    resource VARCHAR(50) NOT NULL,  -- e.g., 'device', 'job', 'credential', 'user'
    action VARCHAR(50) NOT NULL,  -- e.g., 'view', 'create', 'edit', 'delete', 'run'
    
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ROLE_PERMISSIONS (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    
    -- Optional: scope restrictions (e.g., only certain device groups)
    scope_type VARCHAR(50),  -- e.g., 'device_group', 'credential_group'
    scope_ids INTEGER[],  -- Array of allowed IDs
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(role_id, permission_id)
);

-- =============================================================================
-- USER_ROLES (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    
    -- Optional: time-limited role assignment
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,
    
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, role_id)
);

-- =============================================================================
-- SESSIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session token (hashed)
    session_token_hash VARCHAR(255) NOT NULL UNIQUE,
    refresh_token_hash VARCHAR(255),
    
    -- Session info
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_info JSONB,
    
    -- 2FA status for this session
    two_factor_verified BOOLEAN DEFAULT FALSE,
    two_factor_verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Expiration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Revocation
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_reason VARCHAR(100)
);

-- =============================================================================
-- 2FA VERIFICATION CODES (for email-based 2FA)
-- =============================================================================
CREATE TABLE IF NOT EXISTS two_factor_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    code_hash VARCHAR(255) NOT NULL,
    code_type VARCHAR(20) NOT NULL CHECK (code_type IN ('login', 'password_reset', 'email_verify')),
    
    -- Delivery
    sent_to VARCHAR(255),  -- email address
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Usage
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3
);

-- =============================================================================
-- API KEYS (for programmatic access)
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,  -- First 8 chars for identification
    key_hash VARCHAR(255) NOT NULL,
    
    -- Permissions (can be more restrictive than user's roles)
    permissions TEXT[],  -- Array of permission codes
    
    -- Restrictions
    allowed_ips TEXT[],  -- IP whitelist
    rate_limit INTEGER,  -- Requests per minute
    
    -- Usage tracking
    last_used_at TIMESTAMP WITH TIME ZONE,
    last_used_ip VARCHAR(45),
    usage_count INTEGER DEFAULT 0,
    
    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- AUDIT LOG (for security events)
-- =============================================================================
CREATE TABLE IF NOT EXISTS auth_audit_log (
    id SERIAL PRIMARY KEY,
    
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(100),  -- Stored separately in case user is deleted
    
    event_type VARCHAR(50) NOT NULL,  -- login, logout, failed_login, password_change, 2fa_setup, etc.
    event_status VARCHAR(20) NOT NULL CHECK (event_status IN ('success', 'failure', 'warning')),
    
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    details JSONB,  -- Additional event-specific data
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_auth_method ON users(auth_method);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_two_factor_codes_user ON two_factor_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_two_factor_codes_expires ON two_factor_codes(expires_at);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

CREATE INDEX IF NOT EXISTS idx_auth_audit_user ON auth_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_type ON auth_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_audit_created ON auth_audit_log(created_at);

CREATE INDEX IF NOT EXISTS idx_permissions_module ON permissions(module);
CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions(code);

-- =============================================================================
-- INSERT DEFAULT ROLES
-- =============================================================================
INSERT INTO roles (name, display_name, description, role_type, priority) VALUES
    ('super_admin', 'Super Administrator', 'Full system access with all permissions', 'system', 1000),
    ('admin', 'Administrator', 'Administrative access to manage users, settings, and most resources', 'system', 900),
    ('operator', 'Operator', 'Can run jobs, manage devices, and use credentials', 'system', 500),
    ('viewer', 'Viewer', 'Read-only access to view resources and reports', 'system', 100)
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- INSERT DEFAULT PERMISSIONS
-- =============================================================================

-- Device permissions
INSERT INTO permissions (code, module, resource, action, display_name, description) VALUES
    ('devices.device.view', 'devices', 'device', 'view', 'View Devices', 'View device list and details'),
    ('devices.device.create', 'devices', 'device', 'create', 'Create Devices', 'Add new devices'),
    ('devices.device.edit', 'devices', 'device', 'edit', 'Edit Devices', 'Modify device settings'),
    ('devices.device.delete', 'devices', 'device', 'delete', 'Delete Devices', 'Remove devices'),
    ('devices.device.connect', 'devices', 'device', 'connect', 'Connect to Devices', 'SSH/console access'),
    ('devices.group.manage', 'devices', 'group', 'manage', 'Manage Device Groups', 'Create and manage device groups')
ON CONFLICT (code) DO NOTHING;

-- Job permissions
INSERT INTO permissions (code, module, resource, action, display_name, description) VALUES
    ('jobs.job.view', 'jobs', 'job', 'view', 'View Jobs', 'View job list and history'),
    ('jobs.job.create', 'jobs', 'job', 'create', 'Create Jobs', 'Create new jobs'),
    ('jobs.job.edit', 'jobs', 'job', 'edit', 'Edit Jobs', 'Modify job configurations'),
    ('jobs.job.delete', 'jobs', 'job', 'delete', 'Delete Jobs', 'Remove jobs'),
    ('jobs.job.run', 'jobs', 'job', 'run', 'Run Jobs', 'Execute jobs manually'),
    ('jobs.job.cancel', 'jobs', 'job', 'cancel', 'Cancel Jobs', 'Stop running jobs'),
    ('jobs.schedule.manage', 'jobs', 'schedule', 'manage', 'Manage Schedules', 'Create and manage job schedules'),
    ('jobs.template.manage', 'jobs', 'template', 'manage', 'Manage Templates', 'Create and manage job templates')
ON CONFLICT (code) DO NOTHING;

-- Credential permissions
INSERT INTO permissions (code, module, resource, action, display_name, description) VALUES
    ('credentials.credential.view', 'credentials', 'credential', 'view', 'View Credentials', 'View credential list (not secrets)'),
    ('credentials.credential.create', 'credentials', 'credential', 'create', 'Create Credentials', 'Add new credentials'),
    ('credentials.credential.edit', 'credentials', 'credential', 'edit', 'Edit Credentials', 'Modify credentials'),
    ('credentials.credential.delete', 'credentials', 'credential', 'delete', 'Delete Credentials', 'Remove credentials'),
    ('credentials.credential.use', 'credentials', 'credential', 'use', 'Use Credentials', 'Use credentials in jobs'),
    ('credentials.credential.reveal', 'credentials', 'credential', 'reveal', 'Reveal Secrets', 'View credential secrets'),
    ('credentials.group.manage', 'credentials', 'group', 'manage', 'Manage Credential Groups', 'Create and manage credential groups'),
    ('credentials.enterprise.manage', 'credentials', 'enterprise', 'manage', 'Manage Enterprise Auth', 'Configure enterprise auth servers')
ON CONFLICT (code) DO NOTHING;

-- System/Admin permissions
INSERT INTO permissions (code, module, resource, action, display_name, description) VALUES
    ('system.settings.view', 'system', 'settings', 'view', 'View Settings', 'View system settings'),
    ('system.settings.edit', 'system', 'settings', 'edit', 'Edit Settings', 'Modify system settings'),
    ('system.users.view', 'system', 'users', 'view', 'View Users', 'View user list'),
    ('system.users.create', 'system', 'users', 'create', 'Create Users', 'Add new users'),
    ('system.users.edit', 'system', 'users', 'edit', 'Edit Users', 'Modify user accounts'),
    ('system.users.delete', 'system', 'users', 'delete', 'Delete Users', 'Remove user accounts'),
    ('system.roles.manage', 'system', 'roles', 'manage', 'Manage Roles', 'Create and manage roles'),
    ('system.audit.view', 'system', 'audit', 'view', 'View Audit Logs', 'View security and audit logs'),
    ('system.backup.manage', 'system', 'backup', 'manage', 'Manage Backups', 'Create and restore backups')
ON CONFLICT (code) DO NOTHING;

-- Reports permissions
INSERT INTO permissions (code, module, resource, action, display_name, description) VALUES
    ('reports.report.view', 'reports', 'report', 'view', 'View Reports', 'View reports and dashboards'),
    ('reports.report.create', 'reports', 'report', 'create', 'Create Reports', 'Create custom reports'),
    ('reports.report.export', 'reports', 'report', 'export', 'Export Reports', 'Export reports to files')
ON CONFLICT (code) DO NOTHING;

-- =============================================================================
-- ASSIGN PERMISSIONS TO DEFAULT ROLES
-- =============================================================================

-- Super Admin gets ALL permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'super_admin'
ON CONFLICT DO NOTHING;

-- Admin gets most permissions except some system-level ones
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'admin' 
AND p.code NOT IN ('system.roles.manage', 'system.backup.manage')
ON CONFLICT DO NOTHING;

-- Operator gets operational permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'operator' 
AND p.code IN (
    'devices.device.view', 'devices.device.connect', 'devices.group.manage',
    'jobs.job.view', 'jobs.job.create', 'jobs.job.edit', 'jobs.job.run', 'jobs.job.cancel', 'jobs.schedule.manage',
    'credentials.credential.view', 'credentials.credential.use',
    'reports.report.view', 'reports.report.export'
)
ON CONFLICT DO NOTHING;

-- Viewer gets read-only permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'viewer' 
AND p.code IN (
    'devices.device.view',
    'jobs.job.view',
    'credentials.credential.view',
    'reports.report.view'
)
ON CONFLICT DO NOTHING;
