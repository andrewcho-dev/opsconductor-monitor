-- Migration: 005_notifications
-- Description: Create notification channels and notification rules tables
-- Date: 2025-12-12

-- ============================================================================
-- NOTIFICATION CHANNELS TABLE
-- Stores configured notification channels (email, slack, webhook, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,  -- email, slack, webhook, pagerduty, teams, etc.
    config JSONB NOT NULL DEFAULT '{}',  -- Channel-specific configuration
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_test_at TIMESTAMP WITH TIME ZONE,
    last_test_success BOOLEAN,
    UNIQUE(name)
);

-- ============================================================================
-- NOTIFICATION RULES TABLE
-- Maps alert conditions to notification channels
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    
    -- What triggers this notification
    trigger_type VARCHAR(50) NOT NULL,  -- alert, job_status, system_event
    trigger_config JSONB NOT NULL DEFAULT '{}',  -- Conditions for triggering
    
    -- Which channels to notify
    channel_ids INTEGER[] NOT NULL DEFAULT '{}',
    
    -- Filtering
    severity_filter VARCHAR(20)[],  -- Only notify for these severities
    category_filter VARCHAR(50)[],  -- Only notify for these categories
    
    -- Rate limiting
    cooldown_minutes INTEGER DEFAULT 5,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name)
);

-- ============================================================================
-- NOTIFICATION HISTORY TABLE
-- Tracks sent notifications for auditing
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_history (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER REFERENCES notification_channels(id) ON DELETE SET NULL,
    rule_id INTEGER REFERENCES notification_rules(id) ON DELETE SET NULL,
    
    title VARCHAR(255) NOT NULL,
    message TEXT,
    
    -- What triggered this notification
    trigger_type VARCHAR(50),
    trigger_id VARCHAR(100),  -- e.g., alert ID, job execution ID
    
    -- Result
    status VARCHAR(20) NOT NULL,  -- sent, failed, skipped
    error_message TEXT,
    
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notification_channels_type ON notification_channels(channel_type);
CREATE INDEX IF NOT EXISTS idx_notification_channels_enabled ON notification_channels(enabled);
CREATE INDEX IF NOT EXISTS idx_notification_rules_enabled ON notification_rules(enabled);
CREATE INDEX IF NOT EXISTS idx_notification_rules_trigger ON notification_rules(trigger_type);
CREATE INDEX IF NOT EXISTS idx_notification_history_sent ON notification_history(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_history_channel ON notification_history(channel_id);

-- ============================================================================
-- Record migration
-- ============================================================================
INSERT INTO schema_versions (version, description)
VALUES (5, 'Notification channels and rules')
ON CONFLICT (version) DO NOTHING;
