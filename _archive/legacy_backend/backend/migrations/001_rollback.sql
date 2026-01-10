-- ============================================================================
-- OpsConductor Database Migration 001: ROLLBACK
-- ============================================================================
-- This script removes all tables created by migration 001.
-- WARNING: This will DELETE ALL DATA in these tables!
--
-- Run with: PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan -f 001_rollback.sql
-- ============================================================================

BEGIN;

-- Drop partitioned tables (drops all partitions automatically)
DROP TABLE IF EXISTS optical_metrics CASCADE;
DROP TABLE IF EXISTS interface_metrics CASCADE;
DROP TABLE IF EXISTS path_metrics CASCADE;
DROP TABLE IF EXISTS availability_metrics CASCADE;
DROP TABLE IF EXISTS health_scores CASCADE;
DROP TABLE IF EXISTS metrics_hourly CASCADE;

-- Drop regular tables
DROP TABLE IF EXISTS metric_baselines CASCADE;
DROP TABLE IF EXISTS anomaly_events CASCADE;
DROP TABLE IF EXISTS config_snapshots CASCADE;
DROP TABLE IF EXISTS interface_snapshots CASCADE;
DROP TABLE IF EXISTS network_events CASCADE;
DROP TABLE IF EXISTS poll_history CASCADE;
DROP TABLE IF EXISTS metrics_daily CASCADE;
DROP TABLE IF EXISTS site_daily_summary CASCADE;
DROP TABLE IF EXISTS netbox_device_cache CASCADE;
DROP TABLE IF EXISTS ml_training_snapshots CASCADE;
DROP TABLE IF EXISTS ml_model_metrics CASCADE;

-- Drop helper function
DROP FUNCTION IF EXISTS create_monthly_partitions(TEXT, DATE, INTEGER);

-- Remove migration record
DELETE FROM schema_migrations WHERE version = '001';

COMMIT;

SELECT 'Migration 001 rolled back successfully' AS status;
