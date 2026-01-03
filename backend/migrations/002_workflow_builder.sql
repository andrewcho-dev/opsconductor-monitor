-- OpsConductor Workflow Builder Schema
-- Migration: 002_workflow_builder
-- Created: 2025-12-11
-- Description: Adds tables and columns for the visual workflow builder

-- ============================================================================
-- JOB FOLDERS TABLE
-- Hierarchical folders for organizing jobs
-- ============================================================================
CREATE TABLE IF NOT EXISTS job_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    parent_id UUID REFERENCES job_folders(id) ON DELETE CASCADE,
    color VARCHAR(7) DEFAULT '#6B7280',
    icon VARCHAR(50) DEFAULT 'folder',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_folders_parent ON job_folders(parent_id);
CREATE INDEX IF NOT EXISTS idx_job_folders_name ON job_folders(name);

-- ============================================================================
-- JOB TAGS TABLE
-- Tags for categorizing and filtering jobs
-- ============================================================================
CREATE TABLE IF NOT EXISTS job_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_tags_name ON job_tags(name);

-- ============================================================================
-- WORKFLOWS TABLE
-- Stores visual workflow definitions (new format)
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    folder_id UUID REFERENCES job_folders(id) ON DELETE SET NULL,
    
    -- Workflow definition (nodes, edges, viewport)
    definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Workflow settings
    settings JSONB DEFAULT '{
        "error_handling": "continue",
        "timeout": 300,
        "notifications": {
            "on_success": false,
            "on_failure": true
        }
    }'::jsonb,
    
    -- Schedule configuration (null = manual only)
    schedule JSONB,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    
    -- Status
    enabled BOOLEAN DEFAULT true,
    is_template BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);
CREATE INDEX IF NOT EXISTS idx_workflows_folder ON workflows(folder_id);
CREATE INDEX IF NOT EXISTS idx_workflows_enabled ON workflows(enabled);
CREATE INDEX IF NOT EXISTS idx_workflows_template ON workflows(is_template);

-- ============================================================================
-- WORKFLOW TAGS TABLE
-- Many-to-many relationship between workflows and tags
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_tags (
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES job_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (workflow_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_tags_workflow ON workflow_tags(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_tags_tag ON workflow_tags(tag_id);

-- ============================================================================
-- WORKFLOW EXECUTIONS TABLE
-- Stores execution history for workflows
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    workflow_name VARCHAR(255) NOT NULL,
    workflow_version INTEGER NOT NULL,
    
    -- Execution status
    status VARCHAR(50) DEFAULT 'pending',
    trigger_type VARCHAR(50) DEFAULT 'manual',
    triggered_by VARCHAR(255),
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Results
    node_results JSONB DEFAULT '{}'::jsonb,
    variables JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    
    -- Statistics
    nodes_total INTEGER DEFAULT 0,
    nodes_completed INTEGER DEFAULT 0,
    nodes_failed INTEGER DEFAULT 0,
    nodes_skipped INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_wf_exec_workflow ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_wf_exec_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_wf_exec_started ON workflow_executions(started_at);

-- ============================================================================
-- WORKFLOW NODE EXECUTIONS TABLE
-- Stores per-node execution details within a workflow run
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_node_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(100) NOT NULL,
    node_name VARCHAR(255),
    
    -- Execution status
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Input/Output
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    
    -- For action nodes with multiple targets
    targets_total INTEGER DEFAULT 0,
    targets_success INTEGER DEFAULT 0,
    targets_failed INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_wf_node_exec_execution ON workflow_node_executions(execution_id);
CREATE INDEX IF NOT EXISTS idx_wf_node_exec_node ON workflow_node_executions(node_id);
CREATE INDEX IF NOT EXISTS idx_wf_node_exec_status ON workflow_node_executions(status);

-- ============================================================================
-- ENABLED PACKAGES TABLE
-- Tracks which node packages are enabled
-- ============================================================================
CREATE TABLE IF NOT EXISTS enabled_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id VARCHAR(100) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}'::jsonb,
    enabled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default enabled packages
INSERT INTO enabled_packages (package_id, enabled) VALUES
    ('core', true),
    ('network-discovery', true),
    ('snmp', true),
    ('ssh', true),
    ('database', true),
    ('notifications', true),
    ('ciena-saos', true)
ON CONFLICT (package_id) DO NOTHING;

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================
INSERT INTO schema_versions (version, description) 
VALUES ('002', 'Workflow builder tables')
ON CONFLICT (version) DO NOTHING;
