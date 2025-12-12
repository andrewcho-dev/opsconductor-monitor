# OpsConductor Remediation Plan

## Overview

This document outlines the remaining concerns identified during the code review and the steps to address them.

## Concerns to Address

### 1. Legacy HTML Files (HIGH)
**Issue:** Old server-rendered HTML files still present at root level:
- `simple_table.html` (82KB)
- `poller.html` (36KB)
- `device_detail.html` (40KB)
- `settings.html` (24KB)
- `topology.html` (7KB)
- `power_trends.html` (26KB)

**Impact:** Confusion about which UI is active, maintenance burden, potential security issues with old code.

**Fix:** Archive to `_legacy_html/` directory, update any references.

---

### 2. Root-Level Python Files (MEDIUM)
**Issue:** Several Python files remain at root that should be in `backend/`:
- `notification_service.py`
- `settings_routes.py`
- `config.py`
- `simple_test.py`
- `test_data.py`

**Impact:** Inconsistent project structure, harder to maintain.

**Fix:** Move to appropriate `backend/` subdirectories with compatibility wrappers.

---

### 3. No Database Schema/Migrations (HIGH)
**Issue:** No schema definitions or migration scripts. Repositories assume tables exist.

**Impact:** Cannot deploy to new environments, no version control for schema changes.

**Fix:** Create `backend/migrations/` with schema definitions and migration scripts.

---

### 4. No Test Suite (HIGH)
**Issue:** No `tests/` directory or test files.

**Impact:** Cannot verify functionality, risky to make changes, no regression protection.

**Fix:** Create `tests/` with unit tests for parsers, executors, services, and API routes.

---

### 5. Frontend API Client Not Integrated (MEDIUM)
**Issue:** Created `frontend/src/api/` but existing components still use direct fetch calls.

**Impact:** Inconsistent error handling, duplicated code, harder to maintain.

**Fix:** Update key components to use new API client and hooks.

---

### 6. Log Management (LOW)
**Issue:** `backend.log` at 2MB with no rotation.

**Impact:** Disk space issues over time, hard to search logs.

**Fix:** Add logging configuration with rotation.

---

### 7. Miscellaneous Cleanup (LOW)
**Issue:** Various files that should be cleaned up:
- `data.json` (test data?)
- `jobs.sqlite`, `poller_jobs.sqlite` (should use PostgreSQL)
- `snmp_fields_complete.txt` (411KB - reference file?)
- `network_analysis_*.json` (output files?)
- `links.yaml`, `discovered_links.yaml` (config or output?)

**Impact:** Cluttered project root.

**Fix:** Organize into appropriate directories or remove if unused.

---

## Remediation Steps

### Phase 1: Cleanup Legacy Files
- [x] 1.1 Archive legacy HTML files to `_legacy_html/`
- [x] 1.2 Move root Python files to `backend/`
- [x] 1.3 Clean up miscellaneous files

### Phase 2: Database Schema
- [x] 2.1 Create `backend/migrations/` directory
- [x] 2.2 Document existing schema from PostgreSQL
- [x] 2.3 Create initial migration script
- [x] 2.4 Add schema version tracking

### Phase 3: Test Suite
- [x] 3.1 Create `tests/` directory structure
- [x] 3.2 Add parser unit tests
- [x] 3.3 Add executor unit tests
- [x] 3.4 Add service unit tests
- [x] 3.5 Add API route tests
- [x] 3.6 Add pytest configuration

### Phase 4: Frontend Integration
- [x] 4.1 Update useDevices hook to use new API client
- [x] 4.2 Update useGroups hook to use new API client
- [x] 4.3 Update useScanProgress hook to use new API client
- [x] 4.4 Add missing methods to scans API

### Phase 5: Logging & Configuration
- [x] 5.1 Add logging configuration with rotation
- [x] 5.2 Clean up log files
- [x] 5.3 Update .gitignore for logs

---

## Progress Log

### 2025-12-11

**Remediation Complete!**

#### Phase 1: Cleanup Legacy Files
- Archived 6 legacy HTML files to `_legacy_html/`
- Converted `notification_service.py` and `config.py` to compatibility wrappers
- Removed `settings_routes.py`, `simple_test.py`, `test_data.py`
- Moved `data.json` and analysis files to `data/`
- Moved YAML config files to `config/`
- Moved `snmp_fields_complete.txt` to `reference/`
- Removed SQLite files (using PostgreSQL)

#### Phase 2: Database Schema
- Created `backend/migrations/` directory
- Created `001_initial_schema.sql` with full schema definition
- Created `migrate.py` migration runner with version tracking
- Schema includes: devices, device_groups, interface_scans, optical_power_readings, job_definitions, scheduler_jobs, job_executions, schema_versions

#### Phase 3: Test Suite
- Created `tests/` directory with unit and integration subdirectories
- Added `conftest.py` with pytest fixtures
- Added `test_parsers.py` for Ciena parser tests
- Added `test_executors.py` for executor tests
- Added `test_services.py` for service tests
- Added `test_api.py` for API route tests
- Added `pytest.ini` configuration

#### Phase 4: Frontend Integration
- Updated `useDevices` hook to use `devicesApi`
- Updated `useGroups` hook to use `groupsApi`
- Updated `useScanProgress` hook to use `scansApi`
- Added `getProgress`, `startScan`, `cancelScan` to scans API

#### Phase 5: Logging & Configuration
- Created `backend/config/logging.py` with RotatingFileHandler
- Created `logs/` directory for log files
- Updated `.gitignore` to exclude logs, legacy files, and sensitive configs

