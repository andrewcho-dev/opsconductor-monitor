-- Migration: 006_notification_templates
-- Description: Add notification templates for variable substitution
-- Date: 2025-12-12

-- ============================================================================
-- NOTIFICATION TEMPLATES TABLE
-- Stores reusable notification templates with variable placeholders
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Template type: 'system' or 'job'
    template_type VARCHAR(20) NOT NULL DEFAULT 'system',
    
    -- Template content with {{variable}} placeholders
    title_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    
    -- Available variables for this template (for UI hints)
    available_variables JSONB DEFAULT '[]',
    
    -- Is this a system default template?
    is_default BOOLEAN DEFAULT false,
    
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(name)
);

-- Add template_id to notification_rules
ALTER TABLE notification_rules 
ADD COLUMN IF NOT EXISTS template_id INTEGER REFERENCES notification_templates(id) ON DELETE SET NULL;

-- ============================================================================
-- DEFAULT SYSTEM TEMPLATES
-- ============================================================================
INSERT INTO notification_templates (name, template_type, title_template, body_template, available_variables, is_default)
VALUES 
(
    'Default Alert',
    'system',
    '[{{alert.severity}}] {{alert.title}}',
    '{{alert.message}}

Severity: {{alert.severity}}
Category: {{alert.category}}
Time: {{alert.triggered_at}}',
    '["alert.title", "alert.message", "alert.severity", "alert.category", "alert.triggered_at", "alert.details"]',
    true
),
(
    'Critical Alert',
    'system',
    '🚨 CRITICAL: {{alert.title}}',
    '⚠️ A critical alert has been triggered!

{{alert.message}}

Details:
- Severity: {{alert.severity}}
- Category: {{alert.category}}
- Time: {{alert.triggered_at}}

Please investigate immediately.',
    '["alert.title", "alert.message", "alert.severity", "alert.category", "alert.triggered_at", "alert.details"]',
    true
),
(
    'Job Completed',
    'job',
    '✅ Job Completed: {{job.name}}',
    'Job "{{job.name}}" has completed successfully.

Duration: {{job.duration}}
Started: {{job.started_at}}
Finished: {{job.finished_at}}

{{#if job.summary}}
Summary:
{{job.summary}}
{{/if}}',
    '["job.name", "job.id", "job.status", "job.duration", "job.started_at", "job.finished_at", "job.summary", "job.results", "workflow.variables"]',
    true
),
(
    'Job Failed',
    'job',
    '❌ Job Failed: {{job.name}}',
    'Job "{{job.name}}" has failed!

Error: {{job.error}}
Duration: {{job.duration}}
Started: {{job.started_at}}

Please check the job logs for more details.',
    '["job.name", "job.id", "job.status", "job.duration", "job.started_at", "job.error", "workflow.variables"]',
    true
),
(
    'Workflow Step Notification',
    'job',
    '{{workflow.name}} - {{step.name}}',
    '{{step.message}}

Workflow: {{workflow.name}}
Step: {{step.name}}
Status: {{step.status}}

{{#if step.data}}
Data:
{{step.data}}
{{/if}}',
    '["workflow.name", "workflow.id", "workflow.variables", "step.name", "step.status", "step.message", "step.data", "step.results"]',
    true
)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- Record migration
-- ============================================================================
INSERT INTO schema_versions (version, description)
VALUES (6, 'Notification templates with variable substitution')
ON CONFLICT (version) DO NOTHING;
