# OpsConductor Refactoring Plan

## Overview

This document outlines a comprehensive plan to refactor the OpsConductor codebase to achieve:
- **Single Responsibility Principle (SRP)** - Each module/function does one thing
- **Modularization** - Logical separation of concerns
- **Standardization** - Consistent patterns, interfaces, and error handling
- **Reusability** - Shared utilities, no code duplication
- **Efficiency** - DRY principles throughout

---

## Current State Analysis

### Backend Files (Python)

| File | Size | Issues |
|------|------|--------|
| `app.py` | 71KB | Mixed: API routes, job seeding, serialization, business logic |
| `database.py` | 50KB | All DB operations in one file, no repository pattern |
| `scan_routes.py` | 54KB | All scanning logic, parsers, SSH handling mixed |
| `generic_job_scheduler.py` | 47KB | Job execution, targeting, parsing, database ops mixed |
| `celery_tasks.py` | 16KB | Task definitions with embedded business logic |

### Frontend Files (React)

| Area | Issues |
|------|--------|
| State Management | Each page manages own state, no centralized approach |
| API Calls | Duplicated fetch patterns across components |
| Utilities | Some centralization in `lib/utils.js`, but incomplete |
| Components | Some components have mixed presentation/logic |

---

## Phase 1: Backend Foundation (Weeks 1-2)

### 1.1 Create Directory Structure

```
backend/
├── __init__.py
├── api/                    # Flask Blueprints (routes only)
│   ├── __init__.py
│   ├── devices.py          # Device CRUD routes
│   ├── groups.py           # Device group routes
│   ├── jobs.py             # Job definition routes
│   ├── scheduler.py        # Scheduler routes
│   ├── scans.py            # Scan routes
│   ├── settings.py         # Settings routes
│   └── system.py           # System/health routes
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── device_service.py   # Device business logic
│   ├── group_service.py    # Group management logic
│   ├── job_service.py      # Job definition logic
│   ├── scheduler_service.py # Scheduler logic
│   ├── scan_service.py     # Scan orchestration
│   └── notification_service.py
│
├── repositories/           # Data access layer
│   ├── __init__.py
│   ├── base.py             # Base repository with common operations
│   ├── device_repo.py      # Device table operations
│   ├── group_repo.py       # Group table operations
│   ├── job_repo.py         # Job definition operations
│   ├── scheduler_repo.py   # Scheduler job operations
│   ├── execution_repo.py   # Execution history operations
│   └── scan_repo.py        # Scan results operations
│
├── models/                 # Data models/schemas
│   ├── __init__.py
│   ├── device.py           # Device model
│   ├── group.py            # Group model
│   ├── job.py              # Job definition model
│   ├── scheduler.py        # Scheduler models
│   └── scan.py             # Scan result models
│
├── parsers/                # Output parsers
│   ├── __init__.py
│   ├── base.py             # Base parser interface
│   ├── ciena/              # Ciena-specific parsers
│   │   ├── __init__.py
│   │   ├── port_xcvr.py
│   │   ├── port_show.py
│   │   ├── port_diagnostics.py
│   │   └── lldp.py
│   └── registry.py         # Parser registry
│
├── executors/              # Job execution engines
│   ├── __init__.py
│   ├── base.py             # Base executor interface
│   ├── ssh_executor.py     # SSH command executor
│   ├── snmp_executor.py    # SNMP executor
│   └── ping_executor.py    # Ping executor
│
├── targeting/              # Target resolution
│   ├── __init__.py
│   ├── base.py             # Base targeting interface
│   ├── database_query.py   # Database query targeting
│   ├── group_targeting.py  # Group-based targeting
│   └── static_targeting.py # Static IP list targeting
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── ip.py               # IP address utilities
│   ├── time.py             # Timestamp utilities
│   ├── serialization.py    # JSON serialization helpers
│   ├── validation.py       # Input validation
│   └── errors.py           # Custom exceptions
│
├── config/                 # Configuration
│   ├── __init__.py
│   ├── settings.py         # App settings
│   └── constants.py        # Constants
│
└── tasks/                  # Celery tasks (thin wrappers)
    ├── __init__.py
    ├── job_tasks.py        # Job execution tasks
    └── scan_tasks.py       # Scan tasks
```

### 1.2 Create Base Classes and Interfaces

**Task 1.2.1: Base Repository**
```python
# backend/repositories/base.py
class BaseRepository:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a query with standard error handling"""
        pass
    
    def get_by_id(self, id):
        """Get single record by ID"""
        pass
    
    def get_all(self, filters=None, limit=None, offset=None):
        """Get all records with optional filtering"""
        pass
    
    def create(self, data):
        """Create a new record"""
        pass
    
    def update(self, id, data):
        """Update an existing record"""
        pass
    
    def delete(self, id):
        """Delete a record"""
        pass
```

**Task 1.2.2: Base Service**
```python
# backend/services/base.py
class BaseService:
    def __init__(self, repository):
        self.repo = repository
```

**Task 1.2.3: Standard Response Format**
```python
# backend/utils/responses.py
def success_response(data=None, message=None):
    return {
        'success': True,
        'data': data,
        'message': message
    }

def error_response(code, message, details=None):
    return {
        'success': False,
        'error': {
            'code': code,
            'message': message,
            'details': details
        }
    }
```

**Task 1.2.4: Custom Exceptions**
```python
# backend/utils/errors.py
class AppError(Exception):
    def __init__(self, code, message, status_code=400):
        self.code = code
        self.message = message
        self.status_code = status_code

class NotFoundError(AppError):
    def __init__(self, resource, id):
        super().__init__(
            f'{resource.upper()}_NOT_FOUND',
            f'{resource} with ID {id} not found',
            404
        )

class ValidationError(AppError):
    def __init__(self, message, details=None):
        super().__init__('VALIDATION_ERROR', message, 400)
        self.details = details
```

### 1.3 Migrate Database Layer

**Task 1.3.1: Extract Device Repository**
- Move all device-related queries from `database.py` to `backend/repositories/device_repo.py`
- Methods: `get_device`, `get_all_devices`, `create_device`, `update_device`, `delete_device`

**Task 1.3.2: Extract Group Repository**
- Move group queries to `backend/repositories/group_repo.py`
- Methods: `get_group`, `get_all_groups`, `create_group`, `add_device_to_group`, etc.

**Task 1.3.3: Extract Job Repository**
- Move job definition queries to `backend/repositories/job_repo.py`
- Methods: `get_job_definition`, `get_all_job_definitions`, `upsert_job_definition`

**Task 1.3.4: Extract Scheduler Repository**
- Move scheduler queries to `backend/repositories/scheduler_repo.py`
- Methods: `get_scheduler_job`, `get_all_scheduler_jobs`, `upsert_scheduler_job`, `get_executions`

**Task 1.3.5: Extract Execution Repository**
- Move execution queries to `backend/repositories/execution_repo.py`
- Methods: `create_execution`, `update_execution`, `get_recent_executions`

**Task 1.3.6: Extract Scan Repository**
- Move scan result queries to `backend/repositories/scan_repo.py`
- Methods: `save_scan_result`, `get_scan_results`, `get_optical_history`

---

## Phase 2: Backend Services (Weeks 3-4)

### 2.1 Create Service Layer

**Task 2.1.1: Device Service**
```python
# backend/services/device_service.py
class DeviceService:
    def __init__(self, device_repo, group_repo):
        self.device_repo = device_repo
        self.group_repo = group_repo
    
    def get_device_with_groups(self, ip):
        """Get device with its group memberships"""
        pass
    
    def get_devices_by_filter(self, filter_type, filter_id):
        """Get devices filtered by network or custom group"""
        pass
```

**Task 2.1.2: Job Service**
```python
# backend/services/job_service.py
class JobService:
    def __init__(self, job_repo, scheduler_repo):
        self.job_repo = job_repo
        self.scheduler_repo = scheduler_repo
    
    def create_job_with_schedule(self, definition, schedule_config):
        """Create job definition and optionally schedule it"""
        pass
    
    def validate_job_definition(self, definition):
        """Validate job definition structure"""
        pass
```

**Task 2.1.3: Scheduler Service**
```python
# backend/services/scheduler_service.py
class SchedulerService:
    def __init__(self, scheduler_repo, execution_repo, job_repo):
        self.scheduler_repo = scheduler_repo
        self.execution_repo = execution_repo
        self.job_repo = job_repo
    
    def run_job_now(self, job_name):
        """Trigger immediate job execution"""
        pass
    
    def get_job_status(self, job_name):
        """Get job status with recent executions"""
        pass
```

**Task 2.1.4: Scan Service**
```python
# backend/services/scan_service.py
class ScanService:
    def __init__(self, scan_repo, device_repo, executor_registry):
        self.scan_repo = scan_repo
        self.device_repo = device_repo
        self.executors = executor_registry
    
    def execute_scan(self, scan_type, targets, config):
        """Execute a scan against targets"""
        pass
```

### 2.2 Extract Parsers

**Task 2.2.1: Create Parser Interface**
```python
# backend/parsers/base.py
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw_output: str) -> dict:
        """Parse raw command output into structured data"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return parser identifier"""
        pass
```

**Task 2.2.2: Extract Ciena Parsers**
- `ciena_port_xcvr_show` → `backend/parsers/ciena/port_xcvr.py`
- `ciena_port_show` → `backend/parsers/ciena/port_show.py`
- `ciena_port_xcvr_diagnostics` → `backend/parsers/ciena/port_diagnostics.py`
- `ciena_lldp_remote` → `backend/parsers/ciena/lldp.py`

**Task 2.2.3: Create Parser Registry**
```python
# backend/parsers/registry.py
class ParserRegistry:
    _parsers = {}
    
    @classmethod
    def register(cls, name, parser_class):
        cls._parsers[name] = parser_class
    
    @classmethod
    def get(cls, name):
        return cls._parsers.get(name)
    
    @classmethod
    def parse(cls, parser_name, raw_output):
        parser = cls.get(parser_name)
        if not parser:
            raise ValueError(f"Unknown parser: {parser_name}")
        return parser().parse(raw_output)
```

### 2.3 Extract Executors

**Task 2.3.1: Create Executor Interface**
```python
# backend/executors/base.py
from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, target, command, config) -> dict:
        """Execute command against target"""
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """Return executor type identifier"""
        pass
```

**Task 2.3.2: Extract SSH Executor**
- Move SSH connection logic from `scan_routes.py` to `backend/executors/ssh_executor.py`
- Handle connection pooling, timeouts, retries

**Task 2.3.3: Extract SNMP Executor**
- Move SNMP logic to `backend/executors/snmp_executor.py`

**Task 2.3.4: Extract Ping Executor**
- Move ping logic to `backend/executors/ping_executor.py`

### 2.4 Extract Targeting

**Task 2.4.1: Create Targeting Interface**
```python
# backend/targeting/base.py
from abc import ABC, abstractmethod

class BaseTargeting(ABC):
    @abstractmethod
    def resolve(self, config) -> list:
        """Resolve targeting config to list of targets"""
        pass
```

**Task 2.4.2: Implement Targeting Strategies**
- `DatabaseQueryTargeting` - Execute SQL to get targets
- `GroupTargeting` - Get targets from device group
- `StaticTargeting` - Use static IP list

---

## Phase 3: Backend API Routes (Week 5)

### 3.1 Create Flask Blueprints

**Task 3.1.1: Device Routes Blueprint**
```python
# backend/api/devices.py
from flask import Blueprint, request, jsonify
from backend.services import device_service
from backend.utils.responses import success_response, error_response

devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')

@devices_bp.route('/', methods=['GET'])
def list_devices():
    """List all devices with optional filtering"""
    pass

@devices_bp.route('/<ip>', methods=['GET'])
def get_device(ip):
    """Get single device details"""
    pass
```

**Task 3.1.2: Groups Routes Blueprint**
- `/api/device_groups` endpoints

**Task 3.1.3: Jobs Routes Blueprint**
- `/api/job-definitions` endpoints

**Task 3.1.4: Scheduler Routes Blueprint**
- `/api/scheduler/jobs` endpoints
- `/api/scheduler/executions` endpoints

**Task 3.1.5: Scans Routes Blueprint**
- `/api/scans` endpoints

**Task 3.1.6: System Routes Blueprint**
- `/api/system/health`
- `/api/system/stats`

### 3.2 Refactor app.py

**Task 3.2.1: Create Application Factory**
```python
# backend/__init__.py
from flask import Flask

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app
```

**Task 3.2.2: Register All Blueprints**
```python
def register_blueprints(app):
    from backend.api.devices import devices_bp
    from backend.api.groups import groups_bp
    from backend.api.jobs import jobs_bp
    from backend.api.scheduler import scheduler_bp
    from backend.api.scans import scans_bp
    from backend.api.system import system_bp
    
    app.register_blueprint(devices_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(scans_bp)
    app.register_blueprint(system_bp)
```

**Task 3.2.3: Global Error Handler**
```python
def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify(error_response(error.code, error.message)), error.status_code
    
    @app.errorhandler(Exception)
    def handle_generic_error(error):
        app.logger.exception(error)
        return jsonify(error_response('INTERNAL_ERROR', 'An unexpected error occurred')), 500
```

---

## Phase 4: Job Execution Refactor (Week 6)

### 4.1 Refactor generic_job_scheduler.py

**Task 4.1.1: Create Job Executor**
```python
# backend/services/job_executor.py
class JobExecutor:
    def __init__(self, targeting_registry, executor_registry, parser_registry, db_handler):
        self.targeting = targeting_registry
        self.executors = executor_registry
        self.parsers = parser_registry
        self.db = db_handler
    
    def execute(self, job_definition, config_overrides=None):
        """Execute a job definition"""
        targets = self._resolve_targets(job_definition)
        results = self._execute_actions(job_definition, targets)
        self._save_results(job_definition, results)
        return results
```

**Task 4.1.2: Create Action Handlers**
```python
# backend/services/action_handlers/
# - interface_discovery.py
# - optical_power_monitoring.py
# - network_discovery.py
# - ping_host.py
```

**Task 4.1.3: Simplify Celery Tasks**
```python
# backend/tasks/job_tasks.py
@celery.task(bind=True)
def run_job(self, config):
    """Thin wrapper that delegates to JobExecutor"""
    job_id = config.get('job_definition_id')
    job_def = job_repo.get_by_id(job_id)
    executor = JobExecutor(...)
    return executor.execute(job_def, config.get('overrides'))
```

---

## Phase 5: Frontend Refactor (Weeks 7-8)

### 5.1 Create Directory Structure

```
frontend/src/
├── api/                    # API client layer
│   ├── index.js            # API client instance
│   ├── devices.js          # Device API calls
│   ├── groups.js           # Group API calls
│   ├── jobs.js             # Job API calls
│   ├── scheduler.js        # Scheduler API calls
│   └── scans.js            # Scan API calls
│
├── hooks/                  # Custom React hooks
│   ├── useDevices.js       # Device data hook
│   ├── useGroups.js        # Group data hook
│   ├── useJobs.js          # Job data hook
│   ├── useScheduler.js     # Scheduler data hook
│   ├── usePolling.js       # Generic polling hook
│   └── usePagination.js    # Pagination hook
│
├── components/
│   ├── common/             # Reusable UI components
│   │   ├── Button.jsx
│   │   ├── Modal.jsx
│   │   ├── Table.jsx
│   │   ├── Dropdown.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── LoadingSpinner.jsx
│   │   └── ErrorMessage.jsx
│   │
│   ├── devices/            # Device-specific components
│   │   ├── DeviceTable.jsx
│   │   ├── DeviceRow.jsx
│   │   ├── DeviceFilters.jsx
│   │   └── DeviceActions.jsx
│   │
│   ├── jobs/               # Job-specific components
│   │   ├── JobList.jsx
│   │   ├── JobCard.jsx
│   │   ├── JobEditor.jsx
│   │   └── JobActions.jsx
│   │
│   ├── scheduler/          # Scheduler components
│   │   ├── SchedulerTable.jsx
│   │   ├── ExecutionHistory.jsx
│   │   └── ScheduleEditor.jsx
│   │
│   └── charts/             # Chart components
│       ├── OpticalPowerChart.jsx
│       ├── TimeRangeSelector.jsx
│       └── ChartLegend.jsx
│
├── lib/
│   ├── utils.js            # General utilities
│   ├── formatters.js       # Data formatting functions
│   ├── validators.js       # Input validation
│   └── constants.js        # App constants
│
├── context/                # React context providers
│   ├── AuthContext.jsx
│   └── ThemeContext.jsx
│
└── pages/                  # Page components (minimal logic)
    ├── inventory/
    ├── jobs/
    ├── scheduler/
    └── system/
```

### 5.2 Create API Client Layer

**Task 5.2.1: Base API Client**
```javascript
// frontend/src/api/index.js
const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };
  
  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }
  
  const response = await fetch(url, config);
  const data = await response.json();
  
  if (!response.ok) {
    throw new ApiError(data.error?.code, data.error?.message, response.status);
  }
  
  return data;
}

export const api = {
  get: (endpoint) => request(endpoint),
  post: (endpoint, body) => request(endpoint, { method: 'POST', body }),
  put: (endpoint, body) => request(endpoint, { method: 'PUT', body }),
  delete: (endpoint) => request(endpoint, { method: 'DELETE' }),
};
```

**Task 5.2.2: Domain-Specific API Modules**
```javascript
// frontend/src/api/devices.js
import { api } from './index';

export const devicesApi = {
  getAll: (filters) => api.get(`/devices?${new URLSearchParams(filters)}`),
  getOne: (ip) => api.get(`/devices/${ip}`),
  delete: (ip) => api.delete(`/devices/${ip}`),
  getInterfaces: (ip) => api.get(`/devices/${ip}/interfaces`),
};
```

### 5.3 Consolidate Hooks

**Task 5.3.1: Generic Data Fetching Hook**
```javascript
// frontend/src/hooks/useQuery.js
export function useQuery(queryFn, deps = [], options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const result = await queryFn();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, deps);
  
  useEffect(() => {
    refetch();
  }, [refetch]);
  
  return { data, loading, error, refetch };
}
```

**Task 5.3.2: Polling Hook**
```javascript
// frontend/src/hooks/usePolling.js
export function usePolling(queryFn, interval, enabled = true) {
  const query = useQuery(queryFn);
  
  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(query.refetch, interval);
    return () => clearInterval(id);
  }, [enabled, interval, query.refetch]);
  
  return query;
}
```

### 5.4 Create Reusable Components

**Task 5.4.1: Common Table Component**
```javascript
// frontend/src/components/common/Table.jsx
export function Table({ columns, data, loading, onRowClick, sortable }) {
  // Reusable table with sorting, loading state, row click handling
}
```

**Task 5.4.2: Common Modal Component**
```javascript
// frontend/src/components/common/Modal.jsx
export function Modal({ isOpen, onClose, title, children, footer }) {
  // Reusable modal with consistent styling
}
```

**Task 5.4.3: Status Badge Component**
```javascript
// frontend/src/components/common/StatusBadge.jsx
export function StatusBadge({ status, type }) {
  // Consistent status display across app
}
```

### 5.5 Extract Chart Components

**Task 5.5.1: Optical Power Chart Component**
- Extract from `DeviceDetail.jsx` to `components/charts/OpticalPowerChart.jsx`
- Include timescale selector, aggregation logic, legend toggle

**Task 5.5.2: Time Range Selector Component**
- Reusable time range selector for any chart

---

## Phase 6: Testing & Documentation (Week 9)

### 6.1 Backend Tests

**Task 6.1.1: Repository Tests**
- Test each repository method in isolation

**Task 6.1.2: Service Tests**
- Test business logic with mocked repositories

**Task 6.1.3: API Tests**
- Integration tests for API endpoints

### 6.2 Frontend Tests

**Task 6.2.1: Component Tests**
- Test common components with React Testing Library

**Task 6.2.2: Hook Tests**
- Test custom hooks

### 6.3 Documentation

**Task 6.3.1: API Documentation**
- Document all API endpoints with request/response examples

**Task 6.3.2: Architecture Documentation**
- Update README with new architecture diagram

**Task 6.3.3: Developer Guide**
- How to add new parsers, executors, API endpoints

---

## Phase 7: Migration & Cleanup (Week 10)

### 7.1 Gradual Migration

**Task 7.1.1: Parallel Running**
- Keep old code working while migrating
- Use feature flags to switch between old/new

**Task 7.1.2: Route-by-Route Migration**
- Migrate one API route at a time
- Verify functionality before moving to next

### 7.2 Cleanup

**Task 7.2.1: Remove Old Code**
- Delete migrated code from monolithic files
- Remove unused imports

**Task 7.2.2: Remove Temporary Files**
- Clean up old HTML templates
- Remove unused SQLite files

**Task 7.2.3: Final Verification**
- Full regression testing
- Performance comparison

---

## Execution Tracking

### Phase 1: Backend Foundation ✅ COMPLETED (2025-12-11)
- [x] 1.1 Create directory structure
- [x] 1.2.1 Base Repository (`backend/repositories/base.py`)
- [x] 1.2.2 Base Service (`backend/services/base.py`)
- [x] 1.2.3 Standard Response Format (`backend/utils/responses.py`)
- [x] 1.2.4 Custom Exceptions (`backend/utils/errors.py`)
- [x] 1.3.1 Device Repository (`backend/repositories/device_repo.py`)
- [x] 1.3.2 Group Repository (`backend/repositories/group_repo.py`)
- [x] 1.3.3 Job Repository (`backend/repositories/job_repo.py`)
- [x] 1.3.4 Scheduler Repository (`backend/repositories/scheduler_repo.py`)
- [x] 1.3.5 Execution Repository (`backend/repositories/execution_repo.py`)
- [x] 1.3.6 Scan Repository (`backend/repositories/scan_repo.py`)
- [x] Additional: IP utilities (`backend/utils/ip.py`)
- [x] Additional: Time utilities (`backend/utils/time.py`)
- [x] Additional: Validation utilities (`backend/utils/validation.py`)
- [x] Additional: Serialization utilities (`backend/utils/serialization.py`)
- [x] Additional: Config/Settings (`backend/config/settings.py`, `constants.py`)

### Phase 2: Backend Services ✅ COMPLETED (2025-12-11)
- [x] 2.1.1 Device Service (`backend/services/device_service.py`)
- [x] 2.1.2 Group Service (`backend/services/group_service.py`)
- [x] 2.1.3 Job Service (`backend/services/job_service.py`)
- [x] 2.1.4 Scheduler Service (`backend/services/scheduler_service.py`)
- [x] 2.1.5 Scan Service (`backend/services/scan_service.py`)
- [x] 2.2.1 Parser Interface (`backend/parsers/base.py`)
- [x] 2.2.3 Parser Registry (`backend/parsers/registry.py`)
- [x] 2.3.1 Executor Interface (`backend/executors/base.py`)
- [x] 2.3.2 Executor Registry (`backend/executors/registry.py`)
- [x] 2.4.1 Targeting Interface (`backend/targeting/base.py`)
- [x] 2.4.2 Targeting Registry (`backend/targeting/registry.py`)
- [x] 2.2.2 Extract Ciena Parsers (`backend/parsers/ciena/`) - COMPLETED 2025-12-11
  - `port_xcvr.py`: CienaPortXcvrParser
  - `port_show.py`: CienaPortShowParser  
  - `port_diagnostics.py`: CienaPortDiagnosticsParser
  - `lldp.py`: CienaLldpRemoteParser
- [x] 2.3.3 SSH Executor (`backend/executors/ssh_executor.py`) - COMPLETED 2025-12-11
- [x] 2.3.4 SNMP Executor (`backend/executors/snmp_executor.py`) - COMPLETED 2025-12-11
- [x] 2.3.5 Ping Executor (`backend/executors/ping_executor.py`) - COMPLETED 2025-12-11
- [x] 2.4.3 Targeting Strategies (`backend/targeting/strategies.py`) - COMPLETED 2025-12-11
  - StaticTargeting, DatabaseQueryTargeting, GroupTargeting
  - NetworkRangeTargeting, PreviousResultTargeting

### Phase 3: Backend API Routes ✅ COMPLETED (2025-12-11)
- [x] 3.1.1 Device Routes Blueprint (`backend/api/devices.py`)
- [x] 3.1.2 Groups Routes Blueprint (`backend/api/groups.py`)
- [x] 3.1.3 Jobs Routes Blueprint (`backend/api/jobs.py`)
- [x] 3.1.4 Scheduler Routes Blueprint (`backend/api/scheduler.py`)
- [x] 3.1.5 Scans Routes Blueprint (`backend/api/scans.py`)
- [ ] 3.1.6 System Routes Blueprint (pending)
- [ ] 3.2.1 Application Factory (pending)
- [x] 3.2.2 Register Blueprints (`backend/api/__init__.py:register_blueprints()`)
- [x] 3.2.3 Global Error Handler (per-blueprint error handlers)

### Phase 4: Job Execution Refactor
- [ ] 4.1.1 Job Executor
- [ ] 4.1.2 Action Handlers
- [ ] 4.1.3 Simplify Celery Tasks

### Phase 5: Frontend Refactor ✅ COMPLETED (2025-12-11)
- [x] 5.1 Create directory structure (`frontend/src/api/`, `frontend/src/hooks/`, `frontend/src/components/common/`)
- [x] 5.2.1 Base API Client (`frontend/src/api/client.js`)
- [x] 5.2.2 Domain API Modules:
  - `devices.js`: Device CRUD operations
  - `groups.js`: Group management
  - `jobs.js`: Job definitions
  - `scheduler.js`: Scheduler jobs and executions
  - `scans.js`: Interface scans and optical power
- [x] 5.3.1 Generic Query Hook (`frontend/src/hooks/useApi.js`)
- [x] 5.3.2 Polling Hook (`frontend/src/hooks/usePolling.js`)
- [ ] 5.4.1 Common Table (pending - existing DeviceTable can be generalized)
- [x] 5.4.2 Common Modal (`frontend/src/components/common/Modal.jsx`)
- [x] 5.4.3 Status Badge (`frontend/src/components/common/StatusBadge.jsx`)
- [x] 5.4.4 Loading Spinner (`frontend/src/components/common/LoadingSpinner.jsx`)
- [x] 5.4.5 Error Message (`frontend/src/components/common/ErrorMessage.jsx`)
- [ ] 5.5.1 Optical Power Chart (pending - existing in DeviceDetail)
- [ ] 5.5.2 Time Range Selector (pending - existing in DeviceDetail)

### Phase 6: Testing & Documentation
- [ ] 6.1.1 Repository Tests
- [ ] 6.1.2 Service Tests
- [ ] 6.1.3 API Tests
- [ ] 6.2.1 Component Tests
- [ ] 6.2.2 Hook Tests
- [ ] 6.3.1 API Documentation
- [ ] 6.3.2 Architecture Documentation
- [ ] 6.3.3 Developer Guide

### Phase 7: Migration & Cleanup
- [ ] 7.1.1 Parallel Running
- [ ] 7.1.2 Route-by-Route Migration
- [ ] 7.2.1 Remove Old Code
- [ ] 7.2.2 Remove Temporary Files
- [ ] 7.2.3 Final Verification

---

## Success Criteria

1. **No file > 500 lines** (except generated/data files)
2. **Each module has single responsibility**
3. **All API responses use standard format**
4. **No duplicated code** - shared utilities for common operations
5. **All parsers registered in registry**
6. **All executors registered in registry**
7. **Frontend components are reusable**
8. **Test coverage > 70%**
9. **Documentation complete**

---

## Notes

- This is a living document - update as we progress
- Each task should be a separate commit
- Maintain backward compatibility during migration
- Run full test suite after each phase
