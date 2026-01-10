-- Password Policy and History Migration
-- Adds comprehensive password controls including complexity, expiration, and history

-- Password Policy Settings Table
CREATE TABLE IF NOT EXISTS password_policy (
    id SERIAL PRIMARY KEY,
    
    -- Complexity Requirements
    min_length INTEGER NOT NULL DEFAULT 8,
    max_length INTEGER NOT NULL DEFAULT 128,
    require_uppercase BOOLEAN NOT NULL DEFAULT TRUE,
    require_lowercase BOOLEAN NOT NULL DEFAULT TRUE,
    require_numbers BOOLEAN NOT NULL DEFAULT TRUE,
    require_special_chars BOOLEAN NOT NULL DEFAULT TRUE,
    special_chars_allowed VARCHAR(100) DEFAULT '!@#$%^&*()_+-=[]{}|;:,.<>?',
    min_uppercase INTEGER DEFAULT 1,
    min_lowercase INTEGER DEFAULT 1,
    min_numbers INTEGER DEFAULT 1,
    min_special INTEGER DEFAULT 1,
    
    -- Expiration Settings
    password_expires BOOLEAN NOT NULL DEFAULT TRUE,
    expiration_days INTEGER NOT NULL DEFAULT 90,
    expiration_warning_days INTEGER NOT NULL DEFAULT 14,
    
    -- History and Reuse
    password_history_count INTEGER NOT NULL DEFAULT 12,
    min_password_age_hours INTEGER DEFAULT 24,
    
    -- Lockout Settings
    max_failed_attempts INTEGER NOT NULL DEFAULT 5,
    lockout_duration_minutes INTEGER NOT NULL DEFAULT 30,
    reset_failed_count_minutes INTEGER DEFAULT 30,
    
    -- Additional Controls
    prevent_username_in_password BOOLEAN NOT NULL DEFAULT TRUE,
    prevent_email_in_password BOOLEAN NOT NULL DEFAULT TRUE,
    prevent_common_passwords BOOLEAN NOT NULL DEFAULT TRUE,
    require_password_change_on_first_login BOOLEAN NOT NULL DEFAULT TRUE,
    allow_password_reset BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id)
);

-- Password History Table
CREATE TABLE IF NOT EXISTS password_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for efficient lookups
    CONSTRAINT idx_password_history_user UNIQUE (user_id, password_hash)
);

CREATE INDEX IF NOT EXISTS idx_password_history_user_id ON password_history(user_id);
CREATE INDEX IF NOT EXISTS idx_password_history_created ON password_history(created_at);

-- Add password-related columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_never_expires BOOLEAN DEFAULT FALSE;

-- Common passwords table (for checking against known weak passwords)
CREATE TABLE IF NOT EXISTS common_passwords (
    id SERIAL PRIMARY KEY,
    password_hash VARCHAR(64) NOT NULL UNIQUE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default password policy
INSERT INTO password_policy (
    min_length, max_length,
    require_uppercase, require_lowercase, require_numbers, require_special_chars,
    min_uppercase, min_lowercase, min_numbers, min_special,
    password_expires, expiration_days, expiration_warning_days,
    password_history_count, min_password_age_hours,
    max_failed_attempts, lockout_duration_minutes,
    prevent_username_in_password, prevent_email_in_password, prevent_common_passwords,
    require_password_change_on_first_login
) VALUES (
    12, 128,
    TRUE, TRUE, TRUE, TRUE,
    1, 1, 1, 1,
    TRUE, 90, 14,
    12, 24,
    5, 30,
    TRUE, TRUE, TRUE,
    TRUE
) ON CONFLICT DO NOTHING;

-- Insert some common weak passwords (hashed with SHA-256 for comparison)
-- These are just examples - in production you'd load a larger list
INSERT INTO common_passwords (password_hash) VALUES
    (encode(sha256('password'::bytea), 'hex')),
    (encode(sha256('123456'::bytea), 'hex')),
    (encode(sha256('12345678'::bytea), 'hex')),
    (encode(sha256('qwerty'::bytea), 'hex')),
    (encode(sha256('abc123'::bytea), 'hex')),
    (encode(sha256('password1'::bytea), 'hex')),
    (encode(sha256('password123'::bytea), 'hex')),
    (encode(sha256('admin'::bytea), 'hex')),
    (encode(sha256('letmein'::bytea), 'hex')),
    (encode(sha256('welcome'::bytea), 'hex')),
    (encode(sha256('monkey'::bytea), 'hex')),
    (encode(sha256('dragon'::bytea), 'hex')),
    (encode(sha256('master'::bytea), 'hex')),
    (encode(sha256('login'::bytea), 'hex')),
    (encode(sha256('princess'::bytea), 'hex')),
    (encode(sha256('starwars'::bytea), 'hex')),
    (encode(sha256('passw0rd'::bytea), 'hex')),
    (encode(sha256('shadow'::bytea), 'hex')),
    (encode(sha256('sunshine'::bytea), 'hex')),
    (encode(sha256('trustno1'::bytea), 'hex'))
ON CONFLICT DO NOTHING;

-- Update existing users to have password_changed_at set
UPDATE users SET password_changed_at = created_at WHERE password_changed_at IS NULL AND password_hash IS NOT NULL;

COMMENT ON TABLE password_policy IS 'Stores organization-wide password policy settings';
COMMENT ON TABLE password_history IS 'Stores hashed previous passwords to prevent reuse';
COMMENT ON TABLE common_passwords IS 'List of common/weak passwords to prevent';
