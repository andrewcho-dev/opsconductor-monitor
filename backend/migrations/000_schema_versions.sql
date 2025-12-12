-- OpsConductor Schema Version Tracking
-- Migration: 000_schema_versions
-- Created: 2025-12-11
-- Note: This migration only creates the schema_versions table for tracking.
--       The existing database tables are already in use.

CREATE TABLE IF NOT EXISTS schema_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Record baseline
INSERT INTO schema_versions (version, description) 
VALUES ('000', 'Schema version tracking initialized - existing tables preserved')
ON CONFLICT (version) DO NOTHING;
