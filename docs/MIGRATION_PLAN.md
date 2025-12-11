# OpsConductor Migration Plan

## Overview

This document tracks the migration from monolithic files to the new modular architecture.

## Source Files to Migrate

| File | Lines | Status |
|------|-------|--------|
| `app.py` | 1996 | ✅ Migrated |
| `database.py` | 1185 | ✅ Migrated |
| `scan_routes.py` | 1427 | ✅ Migrated |
| `generic_job_scheduler.py` | 1057 | ✅ Migrated |
| `celery_tasks.py` | 458 | ✅ Migrated |
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

### Step 1: Create New Main Application Entry Point ✅
- [x] Create `backend/app.py` with Flask application factory
- [x] Register all blueprints
- [x] Set up error handlers
- [x] Configure CORS

### Step 2: Migrate Database Functions ✅
- [x] Verify all database.py functions are covered by repositories
- [x] Update repositories to handle any missing functions
- [x] Create database connection management in backend

### Step 3: Migrate API Routes from app.py ✅
Routes migrated:
- [x] `/data` → legacy blueprint
- [x] `/api/job-definitions/*` → jobs blueprint  
- [x] `/api/scheduler/*` → scheduler blueprint
- [x] `/device_groups/*` → groups blueprint
- [x] `/power_history` → legacy blueprint
- [x] `/network_groups`, `/api/network-ranges` → legacy blueprint
- [x] `/progress`, `/scan`, `/cancel_scan` → system/legacy blueprints
- [x] `/get_settings`, `/save_settings` → settings blueprint
- [x] `/topology_data` → legacy blueprint
- [x] `/api/notify/*` → legacy blueprint

### Step 4: Migrate scan_routes.py ✅
- [x] SSH execution functions → SSHExecutor
- [x] SNMP functions → SNMPExecutor
- [x] Ping functions → PingExecutor
- [x] Parser functions → Ciena parsers
- [x] Scan orchestration → ScanService

### Step 5: Migrate generic_job_scheduler.py ✅
- [x] Create JobExecutor class in backend/services/
- [x] Migrate action handlers
- [x] Migrate database mappers
- [x] Migrate targeting logic (in targeting/)

### Step 6: Migrate celery_tasks.py ✅
- [x] Create thin task wrappers in backend/tasks/
- [x] Tasks call services, not direct logic

### Step 7: Update Frontend ✅
- [x] API endpoints unchanged (backward compatible)
- [x] All fetch calls work with new routes

### Step 8: Testing ✅
- [x] All imports verified working
- [x] Flask app creates with 8 blueprints
- [x] Compatibility wrappers tested

### Step 9: Cleanup ✅
- [x] Old files archived to _old/ directory
- [x] _old/ directory removed for clean codebase
- [x] Compatibility wrappers in place for existing imports

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

