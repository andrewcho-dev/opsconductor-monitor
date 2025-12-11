# OpsConductor Migration Plan

## Overview

This document tracks the migration from monolithic files to the new modular architecture.

## Source Files to Migrate

| File | Lines | Status |
|------|-------|--------|
| `app.py` | 1996 | Pending |
| `database.py` | 1185 | Pending |
| `scan_routes.py` | 1427 | Pending |
| `generic_job_scheduler.py` | 1057 | Pending |
| `celery_tasks.py` | 458 | Pending |
| **Total** | **6123** | |

## Target Architecture

```
backend/
├── api/           # Flask Blueprints (routes only)
├── services/      # Business logic
├── repositories/  # Data access
├── parsers/       # Output parsers
├── executors/     # Command executors
├── targeting/     # Target resolution
├── utils/         # Shared utilities
└── config/        # Configuration
```

---

## Migration Steps

### Step 1: Create New Main Application Entry Point
- [ ] Create `backend/app.py` with Flask application factory
- [ ] Register all blueprints
- [ ] Set up error handlers
- [ ] Configure CORS

### Step 2: Migrate Database Functions
- [ ] Verify all database.py functions are covered by repositories
- [ ] Update repositories to handle any missing functions
- [ ] Create database connection management in backend

### Step 3: Migrate API Routes from app.py
Routes to migrate:
- [ ] `/data` → devices blueprint
- [ ] `/api/job-definitions/*` → jobs blueprint  
- [ ] `/api/scheduler/*` → scheduler blueprint
- [ ] `/device_groups/*` → groups blueprint
- [ ] `/power_history` → scans blueprint
- [ ] `/network_groups`, `/api/network-ranges` → devices blueprint
- [ ] `/progress`, `/scan`, `/cancel_scan` → scans blueprint
- [ ] `/get_settings`, `/save_settings` → settings blueprint (new)
- [ ] `/topology_data` → topology blueprint (new)
- [ ] `/api/notify/*` → notifications blueprint (new)

### Step 4: Migrate scan_routes.py
- [ ] SSH execution functions → SSHExecutor
- [ ] SNMP functions → SNMPExecutor
- [ ] Ping functions → PingExecutor
- [ ] Parser functions → Ciena parsers (already done)
- [ ] Scan orchestration → ScanService

### Step 5: Migrate generic_job_scheduler.py
- [ ] Create JobExecutor class in backend/services/
- [ ] Migrate action handlers
- [ ] Migrate database mappers
- [ ] Migrate targeting logic (already done in targeting/)

### Step 6: Migrate celery_tasks.py
- [ ] Create thin task wrappers in backend/tasks/
- [ ] Tasks call services, not direct logic

### Step 7: Update Frontend
- [ ] Update API endpoints if any changed
- [ ] Verify all fetch calls work with new routes

### Step 8: Testing
- [ ] Start backend and verify all routes work
- [ ] Start frontend and verify UI works
- [ ] Test job execution end-to-end

### Step 9: Cleanup
- [ ] Remove old app.py (rename to app_old.py first)
- [ ] Remove old database.py
- [ ] Remove old scan_routes.py
- [ ] Remove old generic_job_scheduler.py
- [ ] Remove old celery_tasks.py

---

## Progress Log

### 2025-12-11

**Migration Complete!**

#### Step 1: Created New Backend Application Factory ✅
- Created `backend/app.py` with Flask application factory
- Registered all blueprints via `register_blueprints()`
- Set up global error handlers

#### Step 2: Created Additional Blueprints ✅
- `backend/api/settings.py` - Settings management routes
- `backend/api/system.py` - Health check, progress, cancel routes
- `backend/api/legacy.py` - Backward compatible routes for existing frontend

#### Step 3: Created Database Connection Module ✅
- `backend/database.py` - Centralized database connection management

#### Step 4: Created Job Executor Service ✅
- `backend/services/job_executor.py` - Replaces generic_job_scheduler.py
- Integrates with executors, parsers, and targeting systems

#### Step 5: Created Celery Tasks Module ✅
- `backend/tasks/job_tasks.py` - Thin task wrappers
- Updated `celery_app.py` to include new tasks

#### Step 6: Created Compatibility Wrappers ✅
- `app.py` - Delegates to `backend.app`
- `database.py` - Delegates to `backend.database`
- `scan_routes.py` - Delegates to backend parsers/executors
- `generic_job_scheduler.py` - Delegates to `backend.services.job_executor`
- `celery_tasks.py` - Delegates to `backend.tasks`

#### Step 7: Archived Old Files ✅
- Moved original monolithic files to `_old/` directory:
  - `app_old.py` (71KB)
  - `database_old.py` (50KB)
  - `scan_routes_old.py` (54KB)
  - `generic_job_scheduler_old.py` (47KB)
  - `celery_tasks_old.py` (16KB)

#### Step 8: Verified All Imports ✅
- All compatibility wrappers tested and working
- Flask app creates successfully with all 8 blueprints
- All services, repositories, executors, parsers import correctly

