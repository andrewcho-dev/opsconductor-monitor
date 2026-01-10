# OpsConductor Core Infrastructure Audit Report

**Date:** January 9, 2026  
**Purpose:** Comprehensive assessment of core infrastructure before addon refactor

---

## Executive Summary

**Verdict: The core infrastructure requires significant cleanup before building the addon system on top of it.**

The codebase has grown organically with multiple overlapping systems, duplicated functionality, inconsistent patterns, and likely dead code. This creates a fragile foundation that would make the addon architecture difficult to implement correctly.

---

## Critical Issues

### 1. DUPLICATE ALERT SYSTEMS (Severity: HIGH)

There are **TWO separate alert systems** that appear to serve similar purposes:

| System | Location | Purpose |
|--------|----------|---------|
| **AlertManager** | `backend/core/alert_manager.py` | Processes NormalizedAlerts from connectors, stores in `alerts` table |
| **AlertService** | `backend/services/alert_service.py` | Evaluates alert rules, stores in `system_alerts` table |

**Problems:**
- Two different database tables (`alerts` vs `system_alerts`)
- Two different alert models with different severities/statuses
- Confusing: which one is the "real" alert system?
- Different APIs, different event patterns

**AlertManager (core):**
```python
class AlertManager:
    # Uses: alerts table
    # Statuses: ACTIVE, ACKNOWLEDGED, SUPPRESSED, RESOLVED
    # Severities: critical, major, minor, warning, info, clear
```

**AlertService (services):**
```python
class AlertService:
    # Uses: system_alerts table  
    # Statuses: ACTIVE, ACKNOWLEDGED, RESOLVED, EXPIRED
    # Severities: INFO, WARNING, CRITICAL
```

**Recommendation:** Consolidate into ONE alert system. The AlertManager in `core/` appears to be the intended primary system for connector alerts.

---

### 2. DUPLICATE SNMP IMPLEMENTATIONS (Severity: HIGH)

There are **FOUR different SNMP implementations**:

| File | Lines | Purpose |
|------|-------|---------|
| `services/async_snmp_poller.py` | 900 | "High-performance async SNMP poller" |
| `executors/snmp_executor.py` | 227 | Executor pattern for SNMP queries |
| `services/node_executors/snmp.py` | ~9KB | Node executor for job builder |
| `services/node_executors/snmp_walker.py` | 56KB | Massive SNMP walker implementation |

**Problems:**
- 4 different ways to do SNMP - which is canonical?
- `snmp_walker.py` is 56KB - suspiciously large, likely contains hardcoded OIDs
- Duplication of timeout handling, error handling, connection logic
- No clear guidance on when to use which

**Recommendation:** Consolidate into ONE SNMP client that all other code uses.

---

### 3. DUPLICATE POLLING SYSTEMS (Severity: HIGH)

Multiple overlapping polling mechanisms:

| Component | Location | Purpose |
|-----------|----------|---------|
| `poll_all_connectors` | `tasks/connector_polling.py` | Polls connectors by interval |
| `polling_scheduler_tick` | `tasks/polling_tasks.py` | Dispatches polls from `polling_configs` table |
| `generic_polling_task` | `tasks/generic_polling_task.py` | Database-driven OID polling |
| `PollingService` | `services/polling_service.py` | High-level polling orchestration |

**Problems:**
- Which polling system is active? Both?
- `connector_polling.py` polls connectors, `polling_tasks.py` polls devices - are these different?
- Unclear scheduling hierarchy
- Multiple ways to configure poll intervals

**Recommendation:** Unify into ONE polling dispatcher with clear separation between:
1. Connector alert polling (PRTG, MCP, etc.)
2. Device metric polling (SNMP OIDs)

---

### 4. INCONSISTENT DATABASE ACCESS (Severity: MEDIUM)

Two database access patterns coexist:

| Pattern | Location | Usage |
|---------|----------|-------|
| `DatabaseConnection` class | `backend/database.py` | Used by tasks, some services |
| `db_query`/`db_execute` functions | `backend/utils/db.py` | Used by core, some routers |

**Problems:**
- Some code uses `DatabaseConnection().cursor()`, others use `db_query()`
- Both are singletons wrapping the same connection
- Inconsistent error handling between them
- `database.py` has `autocommit=True`, but `utils/db.py` has transaction support

**Recommendation:** Standardize on ONE pattern (`utils/db.py` functions are cleaner).

---

### 5. MASSIVE SERVICE FILES (Severity: MEDIUM)

Several service files are suspiciously large:

| File | Size | Concern |
|------|------|---------|
| `services/auth_service.py` | 75KB | Way too large for auth |
| `services/ciena_mcp_service.py` | 50KB | Likely hardcoded mappings |
| `services/ciena_snmp_service.py` | 49KB | Likely hardcoded OIDs |
| `services/ciena_ssh_service.py` | 35KB | Likely hardcoded commands |
| `services/node_executors/snmp_walker.py` | 56KB | Definitely hardcoded |
| `executors/netbox_autodiscovery_executor.py` | 73KB | Massive |

**Problems:**
- Files this large are hard to maintain
- Likely contain hardcoded values that should be in database
- Difficult to test individual functions
- High likelihood of dead code

**Recommendation:** Audit each large file, extract hardcoded values to database, split into smaller modules.

---

### 6. CONNECTOR/ADDON CONFUSION (Severity: MEDIUM)

Two overlapping concepts:

| Concept | Implementation |
|---------|----------------|
| **Connectors** | `backend/connectors/` - Python classes with `poll()` method |
| **Addons** | `backend/core/addon_manager.py` - Registry of installable packages |

**Problems:**
- Connectors have Python code (poll, normalize)
- Addon system I built wraps connectors but doesn't replace them
- The new addon architecture wants DECLARATIVE definitions, not Python code
- Current connectors are tightly coupled to their normalizers

**Recommendation:** This is the core of the refactor - replace Python connector classes with declarative manifests.

---

### 7. DEAD/ORPHAN CODE (Severity: LOW-MEDIUM)

Likely dead or orphan code:

| Location | Concern |
|----------|---------|
| `services/_archived/` | Contains 2 archived files - why kept? |
| `backend/openapi/` | 7 items - is this used? |
| `backend/models/` | Only 1 item - incomplete? |
| `backend/repositories/` | 10 items - are these used? |
| `backend/workflows/` | 1 item - incomplete? |
| `backend/targeting/` | 4 items - used by job builder? |

**Recommendation:** Audit each directory, remove truly dead code, document what remains.

---

### 8. INCONSISTENT PATTERNS (Severity: LOW)

Various inconsistencies across the codebase:

| Pattern | Inconsistency |
|---------|---------------|
| **Singletons** | Some use `_instance` class variable, others use module-level `_var` |
| **Async** | Some services are async, others sync with `asyncio.run()` wrappers |
| **Logging** | Mixed use of `logging.getLogger(__name__)` vs custom LogService |
| **Config** | Some from env vars, some from database `system_settings`, some hardcoded |
| **Error handling** | Inconsistent - some return None, some raise, some return `{success: False}` |

---

## Directory Structure Assessment

```
backend/
├── core/                 # 9 files - Alert, Addon, Event, WebSocket managers
├── services/             # 46 items - TOO MANY, needs organization
│   └── node_executors/   # 11 files - Job builder specific
├── tasks/                # 6 files - Celery tasks (overlapping)
├── connectors/           # 34 items - Python connector implementations
├── executors/            # 10 files - SSH, SNMP, Ping executors
├── routers/              # 16 files - API routes (reasonable)
├── parsers/              # 8 files - Output parsers
├── utils/                # 12 files - Shared utilities (good)
├── repositories/         # 10 files - Data access (are these used?)
├── migrations/           # 34 files - DB migrations
├── config/               # 4 files - Configuration
├── middleware/           # 4 files - HTTP middleware
├── openapi/              # 7 files - ???
├── models/               # 1 file - ???
├── targeting/            # 4 files - ???
├── workflows/            # 1 file - ???
├── scripts/              # 6 files - Utility scripts
├── tools/                # 2 files - Addon packager
└── tests/                # 1 file - Severely lacking
```

**Key Concerns:**
- `services/` has 46 items - this is a dumping ground
- `repositories/` exists but might not be used consistently
- Several directories with only 1-4 files seem incomplete

---

## What Works Well

1. **Router organization** - `backend/routers/` is clean and modular
2. **Database utilities** - `backend/utils/db.py` is well-designed
3. **Core models** - `backend/core/models.py` defines clear data structures
4. **Event bus** - `backend/core/event_bus.py` provides good pub/sub pattern
5. **Connector base class** - `backend/connectors/base.py` defines good interfaces

---

## Recommended Cleanup Priority

### Phase 1: Eliminate Duplicates (HIGH PRIORITY)
1. Consolidate alert systems (AlertManager wins)
2. Consolidate SNMP implementations (one client)
3. Consolidate polling systems (one dispatcher)
4. Standardize database access (utils/db.py)

### Phase 2: Audit Large Files (MEDIUM PRIORITY)
1. Extract hardcoded values from Ciena services
2. Split massive files into smaller modules
3. Move configuration to database

### Phase 3: Remove Dead Code (LOWER PRIORITY)
1. Audit `repositories/`, `openapi/`, `models/`, `workflows/`, `targeting/`
2. Delete truly unused code
3. Archive or document legacy code

### Phase 4: Implement Addon Architecture (AFTER CLEANUP)
Only after core is clean should we:
1. Refactor connectors to declarative manifests
2. Build core parser library
3. Implement addon registration/lifecycle

---

## Questions for User

1. **AlertService vs AlertManager** - Which is the intended primary system? Can we deprecate one?
2. **Ciena services** - Are these actively used? Can hardcoded values move to database?
3. **repositories/** - Is the repository pattern in use, or is direct DB access the norm?
4. **Job Builder** - Is the node_executors/workflow system actively used?
5. **SNMP implementations** - Which one should be canonical?

---

## Conclusion

The core infrastructure is functional but has accumulated technical debt. Before implementing the declarative addon architecture, we should:

1. **Eliminate duplicates** to establish single sources of truth
2. **Audit large files** to extract configuration and reduce complexity
3. **Remove dead code** to reduce maintenance burden
4. **Document what remains** so the core is understandable

Estimated cleanup effort: **2-3 weeks** before addon implementation can begin on solid foundation.
