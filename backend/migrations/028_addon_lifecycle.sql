-- Migration: 028_addon_lifecycle.sql
-- Description: Add installed flag and uninstalled_at for full addon lifecycle

-- Add installed column (defaults to true for existing addons)
ALTER TABLE installed_addons 
ADD COLUMN IF NOT EXISTS installed BOOLEAN DEFAULT true;

-- Add uninstalled_at timestamp
ALTER TABLE installed_addons 
ADD COLUMN IF NOT EXISTS uninstalled_at TIMESTAMPTZ DEFAULT NULL;

-- Create index for filtering installed addons
CREATE INDEX IF NOT EXISTS idx_installed_addons_installed ON installed_addons(installed);

-- Update existing addons to be marked as installed
UPDATE installed_addons SET installed = true WHERE installed IS NULL;
