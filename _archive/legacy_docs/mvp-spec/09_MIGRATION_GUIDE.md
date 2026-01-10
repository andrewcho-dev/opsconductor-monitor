# 09 - Migration Guide

**OpsConductor MVP - Steps to Refactor Existing Codebase**

---

## 1. Pre-Migration Checklist

Before starting migration:

- [ ] Back up current database
- [ ] Document current production configuration
- [ ] List all active integrations (PRTG, MCP, NetBox URLs)
- [ ] Export current credentials from vault
- [ ] Stop all non-essential services
- [ ] Create migration branch in git

---

## 2. Directory Structure Changes

### 2.1 Create New Directories

```bash
# Backend new structure
mkdir -p backend/core
mkdir -p backend/connectors/{prtg,mcp,snmp,eaton,axis,milestone,cradlepoint,siklu,ubiquiti}

# Move existing services to connectors
# (done in later steps)
```

### 2.2 Final Structure

```
backend/
├── connectors/           # NEW - All alert source connectors
│   ├── __init__.py
│   ├── base.py           # BaseConnector, BaseNormalizer
│   ├── registry.py       # Connector registry
│   ├── prtg/
│   ├── mcp/
│   ├── snmp/
│   ├── eaton/
│   ├── axis/
│   ├── milestone/
│   ├── cradlepoint/
│   ├── siklu/
│   └── ubiquiti/
│
├── core/                 # NEW - Core business logic
│   ├── __init__.py
│   ├── models.py
│   ├── alert_manager.py
│   ├── dependency_registry.py
│   ├── event_bus.py
│   └── notification_service.py
│
├── routers/              # MODIFY - Update routers
│   ├── alerts.py         # NEW
│   ├── dependencies.py   # NEW
│   ├── connectors.py     # NEW
│   ├── identity.py       # KEEP
│   ├── integrations.py   # MODIFY (remove workflow stuff)
│   ├── monitoring.py     # KEEP (for now)
│   ├── credentials.py    # KEEP
│   ├── system.py         # KEEP
│   └── notifications.py  # MODIFY
│
├── services/             # PRUNE - Remove unused
│   ├── auth_service.py   # KEEP
│   ├── credential_*.py   # KEEP
│   ├── health_service.py # KEEP
│   ├── netbox_*.py       # KEEP
│   ├── logging_service.py # KEEP
│   │
│   │ # REMOVE or MOVE:
│   ├── prtg_service.py   # → connectors/prtg/
│   ├── ciena_mcp_service.py # → connectors/mcp/
│   ├── snmp_trap_receiver.py # → connectors/snmp/
│   ├── eaton_snmp_service.py # → connectors/eaton/
│   ├── alert_service.py  # → core/alert_manager.py
│   ├── workflow_engine.py # REMOVE
│   ├── job_*.py          # REMOVE
│   ├── scheduler_*.py    # REMOVE
│   └── node_executors/   # REMOVE
│
├── utils/                # KEEP
│   ├── db.py
│   ├── http.py
│   └── errors.py
│
└── main.py               # MODIFY - Update router imports
```

---

## 3. Database Migration

### 3.1 Create Migration File

```bash
# Create new migration
touch backend/migrations/020_mvp_alert_tables.sql
```

### 3.2 Migration SQL

```sql
-- Migration 020: MVP Alert Tables
-- Date: 2026-01-XX

BEGIN;

-- ============================================
-- 1. Create updated_at trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- 2. Create alerts table
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system VARCHAR(50) NOT NULL,
    source_alert_id VARCHAR(255) NOT NULL,
    device_ip VARCHAR(45),
    device_name VARCHAR(255),
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    impact VARCHAR(20),
    urgency VARCHAR(20),
    priority VARCHAR(5),
    title VARCHAR(255) NOT NULL,
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_clear BOOLEAN DEFAULT FALSE,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    correlated_to_id UUID REFERENCES alerts(id),
    correlation_rule VARCHAR(100),
    tags TEXT[],
    custom_fields JSONB DEFAULT '{}',
    raw_data JSONB NOT NULL DEFAULT '{}',
    fingerprint VARCHAR(64),
    occurrence_count INTEGER DEFAULT 1,
    last_occurrence_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON alerts(category);
CREATE INDEX IF NOT EXISTS idx_alerts_device_ip ON alerts(device_ip);
CREATE INDEX IF NOT EXISTS idx_alerts_occurred_at ON alerts(occurred_at);
CREATE INDEX IF NOT EXISTS idx_alerts_source_system ON alerts(source_system);
CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint);

DROP TRIGGER IF EXISTS alerts_updated_at ON alerts;
CREATE TRIGGER alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. Create alert_history table
-- ============================================
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    user_id VARCHAR(100),
    user_name VARCHAR(255),
    notes TEXT,
    changes JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history(alert_id);

-- ============================================
-- 4. Create dependencies table
-- ============================================
CREATE TABLE IF NOT EXISTS dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_ip VARCHAR(45) NOT NULL,
    depends_on_ip VARCHAR(45) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'network',
    description TEXT,
    auto_discovered BOOLEAN DEFAULT FALSE,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT dependencies_no_self_reference CHECK (device_ip != depends_on_ip),
    CONSTRAINT dependencies_unique UNIQUE (device_ip, depends_on_ip, dependency_type)
);

CREATE INDEX IF NOT EXISTS idx_dependencies_device_ip ON dependencies(device_ip);
CREATE INDEX IF NOT EXISTS idx_dependencies_depends_on_ip ON dependencies(depends_on_ip);

-- ============================================
-- 5. Create connectors table
-- ============================================
CREATE TABLE IF NOT EXISTS connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'unknown',
    error_message TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    last_poll_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    alerts_received INTEGER DEFAULT 0,
    alerts_today INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_connectors_type ON connectors(type);

-- ============================================
-- 6. Create oid_mappings table
-- ============================================
CREATE TABLE IF NOT EXISTS oid_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oid_pattern VARCHAR(255) NOT NULL,
    vendor VARCHAR(50),
    alert_type VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    default_severity VARCHAR(20) NOT NULL,
    title_template VARCHAR(255),
    description TEXT,
    is_clear_event BOOLEAN DEFAULT FALSE,
    clear_oid_pattern VARCHAR(255),
    mib_name VARCHAR(100),
    mib_object VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT oid_mappings_unique UNIQUE (oid_pattern, vendor)
);

-- ============================================
-- 7. Create notification_rules table
-- ============================================
CREATE TABLE IF NOT EXISTS notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    conditions JSONB NOT NULL DEFAULT '{}',
    channels JSONB NOT NULL DEFAULT '[]',
    throttle_minutes INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- ============================================
-- 8. Create notification_log table
-- ============================================
CREATE TABLE IF NOT EXISTS notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES alerts(id),
    rule_id UUID REFERENCES notification_rules(id),
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    payload JSONB,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_notification_log_alert_id ON notification_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at);

-- ============================================
-- 9. Seed standard OID mappings
-- ============================================
INSERT INTO oid_mappings (oid_pattern, vendor, alert_type, category, default_severity, title_template, description, is_clear_event) VALUES
-- Standard RFC 3418 traps
('1.3.6.1.6.3.1.1.5.1', NULL, 'cold_start', 'network', 'warning', 'Device Cold Start - {device_name}', 'Device has rebooted (cold start)', false),
('1.3.6.1.6.3.1.1.5.2', NULL, 'warm_start', 'network', 'info', 'Device Warm Start - {device_name}', 'Device has rebooted (warm start)', false),
('1.3.6.1.6.3.1.1.5.3', NULL, 'link_down', 'network', 'major', 'Interface Down - {device_name}', 'Network interface has gone down', false),
('1.3.6.1.6.3.1.1.5.4', NULL, 'link_up', 'network', 'clear', 'Interface Up - {device_name}', 'Network interface has come up', true),
('1.3.6.1.6.3.1.1.5.5', NULL, 'auth_failure', 'security', 'warning', 'Auth Failure - {device_name}', 'SNMP authentication failure', false),

-- Ciena WWP traps (enterprise 6141)
('1.3.6.1.4.1.6141.2.60.5.*', 'ciena', 'equipment_alarm', 'network', 'major', 'Equipment Alarm - {device_name}', 'Ciena equipment alarm', false),

-- Eaton UPS (enterprise 534)
('1.3.6.1.4.1.534.1.7.3.*', 'eaton', 'on_battery', 'power', 'warning', 'UPS On Battery - {device_name}', 'UPS running on battery power', false),
('1.3.6.1.4.1.534.1.7.4.*', 'eaton', 'low_battery', 'power', 'critical', 'UPS Low Battery - {device_name}', 'UPS battery critically low', false),
('1.3.6.1.4.1.534.1.7.5.*', 'eaton', 'utility_restored', 'power', 'clear', 'UPS Utility Restored - {device_name}', 'AC power restored to UPS', true)

ON CONFLICT DO NOTHING;

-- ============================================
-- 10. Seed default connectors
-- ============================================
INSERT INTO connectors (name, type, enabled, config) VALUES
('PRTG', 'prtg', false, '{"url": "", "api_token": "", "poll_interval": 60}'),
('MCP', 'mcp', false, '{"url": "", "username": "", "password": "", "poll_interval": 60}'),
('SNMP Traps', 'snmp_trap', false, '{"port": 162, "community": "public"}'),
('Eaton UPS', 'eaton', false, '{"targets": [], "poll_interval": 60}'),
('Axis Cameras', 'axis', false, '{"targets": [], "poll_interval": 60}'),
('Milestone VMS', 'milestone', false, '{"url": "", "username": "", "password": ""}'),
('Cradlepoint', 'cradlepoint', false, '{"targets": [], "poll_interval": 60}'),
('Siklu', 'siklu', false, '{"targets": [], "poll_interval": 60}'),
('Ubiquiti UISP', 'ubiquiti', false, '{"url": "", "api_token": ""}')
ON CONFLICT (name) DO NOTHING;

COMMIT;
```

### 3.3 Run Migration

```bash
cd backend
psql -h $PG_HOST -U $PG_USER -d $PG_DATABASE -f migrations/020_mvp_alert_tables.sql
```

---

## 4. Code Migration Steps

### 4.1 Step 1: Create Core Module

```bash
# Create core module files
touch backend/core/__init__.py
touch backend/core/models.py
touch backend/core/event_bus.py
touch backend/core/alert_manager.py
touch backend/core/dependency_registry.py
```

### 4.2 Step 2: Create Connector Base

```bash
# Create connector infrastructure
touch backend/connectors/__init__.py
touch backend/connectors/base.py
touch backend/connectors/registry.py
```

### 4.3 Step 3: Migrate PRTG Service

```bash
# Create PRTG connector directory
mkdir -p backend/connectors/prtg
touch backend/connectors/prtg/__init__.py
touch backend/connectors/prtg/connector.py
touch backend/connectors/prtg/normalizer.py

# Copy relevant code from prtg_service.py
# Refactor to implement BaseConnector
```

**Key changes:**
- Extract HTTP client logic to connector
- Create normalizer with severity/category mapping
- Remove workflow-related code
- Wire to alert_manager instead of old alert_service

### 4.4 Step 4: Migrate MCP Service

```bash
mkdir -p backend/connectors/mcp
touch backend/connectors/mcp/__init__.py
touch backend/connectors/mcp/connector.py
touch backend/connectors/mcp/normalizer.py
```

### 4.5 Step 5: Migrate SNMP Services

```bash
mkdir -p backend/connectors/snmp
touch backend/connectors/snmp/__init__.py
touch backend/connectors/snmp/trap_receiver.py
touch backend/connectors/snmp/poller.py
touch backend/connectors/snmp/normalizer.py
touch backend/connectors/snmp/oid_mapper.py
```

### 4.6 Step 6: Migrate Eaton Service

```bash
mkdir -p backend/connectors/eaton
touch backend/connectors/eaton/__init__.py
touch backend/connectors/eaton/connector.py
touch backend/connectors/eaton/normalizer.py
```

### 4.7 Step 7: Update main.py

```python
# backend/main.py - Router updates

# REMOVE these imports:
# from routers import automation
# from services import workflow_engine, job_service

# ADD these imports:
from routers import alerts, dependencies, connectors

# UPDATE router includes:
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(dependencies.router, prefix="/api/v1/dependencies", tags=["dependencies"])
app.include_router(connectors.router, prefix="/api/v1/connectors", tags=["connectors"])

# REMOVE:
# app.include_router(automation.router, ...)
```

### 4.8 Step 8: Update Frontend Routes

```jsx
// frontend/src/App.jsx

// ADD new routes:
import { AlertDashboard, AlertDetailPage } from './pages/alerts';
import { DependenciesPage, DependencyEditorPage } from './pages/dependencies';
import { ConnectorsPage, ConnectorConfigPage } from './pages/connectors';

// In router:
<Route path="/alerts" element={<AlertDashboard />} />
<Route path="/alerts/:id" element={<AlertDetailPage />} />
<Route path="/dependencies" element={<DependenciesPage />} />
<Route path="/dependencies/edit" element={<DependencyEditorPage />} />
<Route path="/connectors" element={<ConnectorsPage />} />
<Route path="/connectors/:id" element={<ConnectorConfigPage />} />

// HIDE workflow routes (don't delete yet):
{/* <Route path="/workflows" ... /> */}
```

---

## 5. Service Pruning

### 5.1 Files to Remove (After Migration Complete)

```bash
# Only after migration is verified working!

# Backend services to remove:
rm backend/services/workflow_engine.py
rm backend/services/job_service.py
rm backend/services/job_executor.py
rm backend/services/job_migration.py
rm backend/services/scheduler_service.py
rm backend/services/template_service.py
rm backend/services/variable_resolver.py
rm backend/services/prtg_netbox_importer.py
rm backend/services/device_importer_service.py
rm -rf backend/services/node_executors/

# Backend routers to remove:
rm backend/routers/automation.py

# Frontend pages to remove:
rm -rf frontend/src/pages/workflows/
rm -rf frontend/src/features/workflow-builder/
```

### 5.2 Files to Keep But Not Expose

Some files may be useful later but should be hidden from UI:

```jsx
// In ModuleSidebar.jsx, comment out:
// workflows: { ... }

// In App.jsx, comment out workflow routes
```

---

## 6. Configuration Migration

### 6.1 Migrate PRTG Settings

```sql
-- Copy existing PRTG settings to connectors table
UPDATE connectors 
SET config = jsonb_build_object(
    'url', (SELECT value FROM system_settings WHERE key = 'prtg_url'),
    'api_token', (SELECT value FROM system_settings WHERE key = 'prtg_api_token'),
    'username', (SELECT value FROM system_settings WHERE key = 'prtg_username'),
    'passhash', (SELECT value FROM system_settings WHERE key = 'prtg_passhash'),
    'verify_ssl', (SELECT COALESCE(value::boolean, true) FROM system_settings WHERE key = 'prtg_verify_ssl'),
    'poll_interval', 60
),
enabled = (SELECT COALESCE(value::boolean, false) FROM system_settings WHERE key = 'prtg_enabled')
WHERE type = 'prtg';
```

### 6.2 Migrate MCP Settings

```sql
UPDATE connectors 
SET config = jsonb_build_object(
    'url', (SELECT value FROM system_settings WHERE key = 'mcp_url'),
    'username', (SELECT value FROM system_settings WHERE key = 'mcp_username'),
    'password', (SELECT value FROM system_settings WHERE key = 'mcp_password'),
    'verify_ssl', false,
    'poll_interval', 60
),
enabled = (SELECT COALESCE(value::boolean, false) FROM system_settings WHERE key = 'mcp_enabled')
WHERE type = 'mcp';
```

---

## 7. Testing Migration

### 7.1 Verification Checklist

After each migration step, verify:

- [ ] Backend starts without errors
- [ ] Frontend builds without errors
- [ ] API endpoints respond correctly
- [ ] No 500 errors in logs
- [ ] Existing auth still works

### 7.2 Connector Verification

For each migrated connector:

- [ ] Test connection works
- [ ] Alerts received and normalized
- [ ] Alerts appear in database
- [ ] Alerts visible in dashboard

### 7.3 Rollback Plan

If migration fails:

1. Stop services
2. Restore database backup
3. Revert git branch
4. Restart services
5. Investigate failure before retry

---

## 8. Post-Migration Cleanup

### 8.1 Remove Old Settings Keys

```sql
-- After verifying connectors work
DELETE FROM system_settings WHERE key LIKE 'prtg_%';
DELETE FROM system_settings WHERE key LIKE 'mcp_%';
-- Keep other settings
```

### 8.2 Archive Old Tables

```sql
-- Rename instead of delete (can drop later)
ALTER TABLE IF EXISTS prtg_alerts RENAME TO _archive_prtg_alerts;
ALTER TABLE IF EXISTS workflows RENAME TO _archive_workflows;
ALTER TABLE IF EXISTS workflow_nodes RENAME TO _archive_workflow_nodes;
ALTER TABLE IF EXISTS jobs RENAME TO _archive_jobs;
```

### 8.3 Update Documentation

- [ ] Update README with new architecture
- [ ] Update API documentation
- [ ] Remove references to pruned features
- [ ] Document new connector configuration

---

## 9. Migration Sequence Summary

```
1. Create database backup
2. Run database migration (020_mvp_alert_tables.sql)
3. Create core/ module structure
4. Create connectors/ module structure
5. Migrate PRTG → connectors/prtg/
6. Migrate MCP → connectors/mcp/
7. Migrate SNMP → connectors/snmp/
8. Migrate Eaton → connectors/eaton/
9. Create new API routers
10. Update main.py imports
11. Update frontend routes
12. Migrate settings to connectors table
13. Test all connectors
14. Hide/remove unused features
15. Update documentation
```

---

*End of MVP Specification*
