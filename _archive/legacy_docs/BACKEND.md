# OpsConductor Backend Documentation

This document provides comprehensive documentation for the OpsConductor backend, a FastAPI-based API server using OpenAPI 3.x specification that handles device management, workflow execution, authentication, and all business logic.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Application Entry Points](#application-entry-points)
4. [API Blueprints](#api-blueprints)
5. [Services Layer](#services-layer)
6. [Repositories Layer](#repositories-layer)
7. [Executors](#executors)
8. [Parsers](#parsers)
9. [Database](#database)
10. [Background Tasks](#background-tasks)
11. [Configuration](#configuration)

---

## Architecture Overview

The backend follows a layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI - OpenAPI 3.x)         │
│   /identity/v1, /inventory/v1, /automation/v1, etc.         │
├─────────────────────────────────────────────────────────────┤
│                      Services Layer                          │
│   Business logic, validation, orchestration                  │
├─────────────────────────────────────────────────────────────┤
│                    Repositories Layer                        │
│   Data access, SQL queries, CRUD operations                  │
├─────────────────────────────────────────────────────────────┤
│                      Database Layer                          │
│   PostgreSQL connection management                           │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **Separation of Concerns** - Each layer has a specific responsibility
- **Dependency Injection** - Services receive repositories as dependencies
- **Single Responsibility** - Each module handles one domain
- **Standardized Responses** - Consistent JSON response format

---

## Directory Structure

```
backend/
├── __init__.py              # Package initialization
├── main.py                  # FastAPI application (OpenAPI 3.x - 3500+ lines)
├── database.py              # Database connection singleton
│
├── openapi/                 # OpenAPI implementation modules
│   ├── identity_impl.py     # Authentication, users, roles
│   ├── inventory_impl.py    # Devices, interfaces, topology
│   ├── monitoring_impl.py   # Metrics, alerts, polling
│   ├── automation_impl.py   # Workflows, jobs, scheduling
│   ├── integrations_impl.py # NetBox, PRTG, MCP
│   └── system_impl.py       # Settings, logs, health
│
├── services/                # Business Logic Layer
│   ├── __init__.py
│   ├── base.py              # Base service class
│   ├── alert_service.py     # Alert management
│   ├── auth_service.py      # Authentication & RBAC
│   ├── credential_service.py # Encrypted credential storage
│   ├── credential_audit_service.py # Credential access auditing
│   ├── device_service.py    # Device business logic
│   ├── group_service.py     # Group management
│   ├── job_executor.py      # Job execution engine
│   ├── job_service.py       # Job definition management
│   ├── logging_service.py   # Centralized logging
│   ├── netbox_service.py    # NetBox API client
│   ├── notification_service.py # Notification dispatch
│   ├── scan_service.py      # Scan orchestration
│   ├── scheduler_service.py # Scheduler management
│   ├── template_service.py  # Notification templates
│   ├── variable_resolver.py # Expression/variable resolution
│   ├── workflow_engine.py   # Workflow execution engine
│   └── node_executors/      # Workflow node implementations
│       ├── database.py      # DB query/upsert nodes
│       ├── netbox.py        # NetBox nodes
│       ├── network.py       # Ping, traceroute, port scan
│       ├── notifications.py # Slack, email, webhook nodes
│       ├── snmp.py          # SNMP get/walk nodes
│       └── ssh.py           # SSH command nodes
│
├── repositories/            # Data Access Layer
│   ├── __init__.py
│   ├── base.py              # Base repository with CRUD
│   ├── audit_repo.py        # Audit log repository
│   ├── device_repo.py       # Device table operations
│   ├── execution_repo.py    # Execution history
│   ├── group_repo.py        # Group table operations
│   ├── job_repo.py          # Job definitions
│   ├── scan_repo.py         # Scan results
│   ├── scheduler_repo.py    # Scheduler jobs
│   └── workflow_repo.py     # Workflows, folders, tags
│
├── executors/               # Device Communication
│   ├── __init__.py
│   ├── base.py              # Base executor interface
│   ├── discovery_executor.py # Network discovery
│   ├── netbox_executor.py   # NetBox sync executor
│   ├── netbox_autodiscovery_executor.py # NetBox auto-discovery
│   ├── ping_executor.py     # ICMP ping
│   ├── registry.py          # Executor registry
│   ├── snmp_executor.py     # SNMP operations
│   ├── ssh_executor.py      # SSH commands
│   └── winrm_executor.py    # Windows Remote Management
│
├── parsers/                 # Output Parsers
│   ├── __init__.py
│   ├── base.py              # Base parser interface
│   ├── registry.py          # Parser registry
│   └── ciena/               # Ciena SAOS parsers
│       ├── port_xcvr.py
│       ├── port_show.py
│       └── lldp.py
│
├── targeting/               # Target Resolution
│   ├── __init__.py
│   ├── base.py              # Base targeting interface
│   ├── static.py            # Static IP list
│   └── group.py             # Device group targeting
│
├── migrations/              # Database Migrations
│   ├── migrate.py           # Migration runner
│   ├── 000_schema_versions.sql
│   ├── 001_job_audit_log.sql
│   ├── 002_workflow_builder.sql
│   ├── 003_system_logs.sql
│   ├── 004_system_alerts.sql
│   ├── 005_notifications.sql
│   ├── 006_notification_templates.sql
│   ├── 007_credentials.sql
│   ├── 010_credential_vault_enhancements.sql
│   ├── 011_enterprise_auth_support.sql
│   ├── 012_rbac_auth_system.sql
│   └── 013_password_policy.sql
│
├── config/                  # Configuration
│   ├── constants.py         # Application constants
│   └── logging.py           # Logging configuration
│
├── middleware/              # Request Middleware
│   └── request_logging.py   # Request/response logging
│
├── tasks/                   # Celery Tasks
│   └── scheduler_tasks.py   # Background job tasks
│
├── utils/                   # Utilities
│   ├── errors.py            # Custom exceptions
│   ├── responses.py         # Response helpers
│   ├── serialization.py     # JSON serialization
│   ├── time.py              # Time utilities
│   └── validation.py        # Input validation
│
└── models/                  # Data Models (schemas)
    └── __init__.py
```

---

## Application Entry Points

### Main Entry Point (`app.py`)

The root `app.py` delegates to the backend application factory:

```python
from backend.app import create_app, app

if __name__ == '__main__':
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', 5000))
    app.run(host=host, port=port, debug=True)
```

### Application Factory (`backend/app.py`)

```python
def create_app(config=None):
    """Create and configure FastAPI application."""
    app = FastAPI(__name__, static_folder='../frontend/dist')
    
    # Enable CORS
    CORS(app)
    
    # Initialize logging service
    logging_service.initialize(db_connection=db, log_level=log_level)
    
    # Initialize request logging middleware
    init_request_logging(app)
    
    # Register all blueprints
    register_blueprints(app)
    
    # Global error handlers
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify(error_response(...)), error.status_code
    
    return app
```

---

## API Blueprints

All API blueprints are registered in `backend/api/__init__.py`:

### Core Blueprints

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| `devices_bp` | `/api/devices` | Device CRUD operations |
| `groups_bp` | `/api/groups` | Device group management |
| `jobs_bp` | `/api/jobs` | Job definition management |
| `scheduler_bp` | `/api/scheduler` | Job scheduling |
| `scans_bp` | `/api/scans` | Network scanning |

### Workflow Blueprints

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| `workflows_bp` | `/api/workflows` | Workflow CRUD |
| `folders_bp` | `/api/workflows/folders` | Workflow folders |
| `tags_bp` | `/api/workflows/tags` | Workflow tags |
| `packages_bp` | `/api/packages` | Node packages |

### System Blueprints

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| `settings_bp` | `/api/settings` | Application settings |
| `system_bp` | `/api/system` | System health & info |
| `logs_bp` | `/api/logs` | System logs |
| `alerts_bp` | `/api/alerts` | Alert management |

### Security Blueprints

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| `auth_bp` | `/api/auth` | Authentication & sessions |
| `credentials_bp` | `/api/credentials` | Credential vault |

### Integration Blueprints

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| `notifications_bp` | `/api/notifications` | Notification channels |
| `netbox_bp` | `/api/netbox` | NetBox integration |
| `winrm_bp` | `/api/winrm` | Windows Remote Management |

### Legacy Blueprint

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| `legacy_bp` | `/` | Legacy endpoint compatibility |

---

## Services Layer

Services contain business logic and orchestrate operations between repositories and external systems.

### Base Service (`services/base.py`)

```python
class BaseService:
    """Base service with common operations."""
    
    def __init__(self, repository):
        self.repo = repository
    
    def get_by_id(self, id):
        return self.repo.get_by_id(id)
    
    def get_all(self, **filters):
        return self.repo.get_all(**filters)
```

### Key Services

#### AuthService (`services/auth_service.py`)

Handles authentication, authorization, and user management:

- **Password Management** - Hashing with bcrypt, policy enforcement
- **Session Management** - Token generation, validation, refresh
- **Two-Factor Authentication** - TOTP and email-based 2FA
- **RBAC** - Role-based access control with permissions

```python
class AuthService:
    def authenticate(self, username, password) -> dict
    def create_session(self, user_id) -> dict
    def verify_session(self, token) -> dict
    def setup_2fa(self, user_id, method) -> dict
    def verify_2fa(self, user_id, code) -> bool
    def check_permission(self, user_id, permission) -> bool
```

#### CredentialService (`services/credential_service.py`)

Manages encrypted credential storage:

- **Encryption** - AES-256 encryption via Fernet
- **Credential Types** - SSH, SNMP, API keys, certificates
- **Expiration Tracking** - Monitor credential expiration
- **Audit Logging** - Track all credential access

```python
class CredentialService:
    def create_credential(self, name, type, data, **metadata) -> dict
    def get_credential(self, id, decrypt=False) -> dict
    def update_credential(self, id, data) -> dict
    def delete_credential(self, id) -> bool
    def list_credentials(self, type=None, category=None) -> list
```

#### WorkflowEngine (`services/workflow_engine.py`)

Executes visual workflows by traversing the node graph:

- **Graph Traversal** - Execute nodes in topological order
- **Variable Resolution** - Pass data between nodes
- **Error Handling** - Handle node failures and branching
- **Execution Logging** - Record execution history

```python
class WorkflowEngine:
    def execute(self, workflow_id, trigger_data=None) -> ExecutionResult
    def execute_node(self, node, context) -> NodeResult
    def resolve_variables(self, template, context) -> str
```

#### NetBoxService (`services/netbox_service.py`)

Integrates with external NetBox instance:

- **Device Sync** - Sync devices from NetBox
- **Auto-Discovery** - Discover and create devices in NetBox
- **Lookup** - Query sites, roles, device types

```python
class NetBoxService:
    def get_devices(self, **filters) -> list
    def create_device(self, data) -> dict
    def update_device(self, id, data) -> dict
    def get_sites(self) -> list
    def get_device_roles(self) -> list
```

### Node Executors (`services/node_executors/`)

Implementations for workflow nodes:

| Module | Nodes |
|--------|-------|
| `network.py` | PingExecutor, TracerouteExecutor, PortScanExecutor |
| `snmp.py` | SNMPGetExecutor, SNMPWalkExecutor |
| `ssh.py` | SSHCommandExecutor |
| `database.py` | DBQueryExecutor, DBUpsertExecutor |
| `notifications.py` | SlackExecutor, EmailExecutor, WebhookExecutor |
| `netbox.py` | NetBoxAutodiscoveryExecutor, NetBoxDeviceCreateExecutor |

---

## Repositories Layer

Repositories handle all database operations with a consistent interface.

### Base Repository (`repositories/base.py`)

```python
class BaseRepository:
    table_name: str = None
    primary_key: str = 'id'
    resource_name: str = 'Resource'
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_by_id(self, id) -> dict
    def get_by_id_or_raise(self, id) -> dict
    def get_all(self, **filters) -> list
    def create(self, data) -> dict
    def update(self, id, data) -> dict
    def delete(self, id) -> bool
    def exists(self, id) -> bool
```

### Domain Repositories

| Repository | Table | Description |
|------------|-------|-------------|
| `DeviceRepository` | `devices` | Device records |
| `GroupRepository` | `device_groups` | Device groups |
| `WorkflowRepository` | `workflows` | Workflow definitions |
| `ExecutionRepository` | `workflow_executions` | Execution history |
| `SchedulerJobRepository` | `scheduler_jobs` | Scheduled jobs |
| `AuditRepository` | `audit_log` | Audit trail |

---

## Executors

Executors handle communication with network devices.

### Base Executor (`executors/base.py`)

```python
class BaseExecutor(ABC):
    @property
    @abstractmethod
    def executor_type(self) -> str:
        """Return executor type identifier (ssh, snmp, ping)."""
        pass
    
    @abstractmethod
    def execute(self, target, command, config=None) -> dict:
        """Execute command against target."""
        pass
    
    def safe_execute(self, target, command, config=None) -> dict:
        """Execute with error handling."""
        pass
    
    def execute_batch(self, targets, command, config=None) -> list:
        """Execute against multiple targets."""
        pass
```

### Available Executors

| Executor | Type | Description |
|----------|------|-------------|
| `SSHExecutor` | `ssh` | SSH command execution via Paramiko |
| `SNMPExecutor` | `snmp` | SNMP GET/WALK operations |
| `PingExecutor` | `ping` | ICMP ping |
| `WinRMExecutor` | `winrm` | Windows Remote Management |
| `DiscoveryExecutor` | `discovery` | Network discovery |
| `NetBoxExecutor` | `netbox` | NetBox API operations |

### Executor Registry (`executors/registry.py`)

```python
class ExecutorRegistry:
    def register(self, executor_type, executor_class)
    def get(self, executor_type) -> BaseExecutor
    def list_types() -> list
```

---

## Parsers

Parsers extract structured data from device command output.

### Base Parser (`parsers/base.py`)

```python
class BaseParser(ABC):
    @property
    @abstractmethod
    def parser_id(self) -> str:
        pass
    
    @abstractmethod
    def parse(self, output: str) -> dict:
        pass
    
    @abstractmethod
    def get_schema(self) -> dict:
        """Return JSON schema for parsed output."""
        pass
```

### Ciena SAOS Parsers (`parsers/ciena/`)

| Parser | Command | Output |
|--------|---------|--------|
| `PortXcvrParser` | `port xcvr show` | Transceiver info, power levels |
| `PortShowParser` | `port show` | Port status, speed, duplex |
| `LldpRemoteParser` | `lldp remote show` | LLDP neighbor info |

---

## Database

### Connection Management (`backend/database.py`)

```python
class DatabaseConnection:
    """Singleton database connection manager."""
    
    def get_connection(self) -> psycopg2.connection
    def cursor(self) -> ContextManager[cursor]
    def execute_query(self, query, params=None, fetch=True) -> list
    def execute_one(self, query, params=None) -> dict
    def close(self)

# Usage
db = get_db()
with db.cursor() as cursor:
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
```

### Migrations (`backend/migrations/`)

Migrations are SQL files executed in order by `migrate.py`:

```bash
python3 backend/migrations/migrate.py
```

Key migration files:
- `002_workflow_builder.sql` - Workflow tables
- `007_credentials.sql` - Credential vault
- `012_rbac_auth_system.sql` - Users, roles, permissions
- `013_password_policy.sql` - Password policy settings

---

## Background Tasks

### Celery Configuration (`celery_app.py`)

```python
celery = Celery('opsconductor')
celery.conf.update(
    broker_url=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    result_backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    task_serializer='json',
    accept_content=['json'],
    timezone='UTC',
)
```

### Task Definitions (`celery_tasks.py`)

```python
@celery.task
def run_scheduled_job(job_name):
    """Execute a scheduled job."""
    pass

@celery.task
def execute_workflow(workflow_id, trigger_data=None):
    """Execute a workflow."""
    pass
```

### Starting Workers

```bash
# Start worker
celery -A celery_app worker -l info --concurrency=4

# Start beat scheduler
celery -A celery_app beat -l info
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_HOST` | `localhost` | PostgreSQL host |
| `PG_PORT` | `5432` | PostgreSQL port |
| `PG_DATABASE` | `network_scan` | Database name |
| `PG_USER` | `postgres` | Database user |
| `PG_PASSWORD` | `postgres` | Database password |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `API_HOST` | `0.0.0.0` | FastAPI bind host |
| `API_PORT` | `5000` | FastAPI bind port |
| `API_DEBUG` | `true` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SECRET_KEY` | - | FastAPI secret key |
| `CREDENTIAL_MASTER_KEY` | - | Credential encryption key |
| `NETBOX_URL` | - | NetBox base URL |
| `NETBOX_TOKEN` | - | NetBox API token |

### Constants (`backend/config/constants.py`)

```python
# Job statuses
JOB_STATUS_QUEUED = 'queued'
JOB_STATUS_RUNNING = 'running'
JOB_STATUS_SUCCESS = 'success'
JOB_STATUS_FAILED = 'failed'

# Schedule types
SCHEDULE_TYPES = ['interval', 'cron', 'once']

# Credential types
CREDENTIAL_TYPES = ['ssh', 'snmp', 'api_key', 'certificate', 'winrm']
```

---

## Error Handling

### Custom Exceptions (`utils/errors.py`)

```python
class AppError(Exception):
    """Base application error."""
    def __init__(self, code, message, status_code=400, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

class NotFoundError(AppError):
    """Resource not found."""
    def __init__(self, resource, identifier):
        super().__init__('NOT_FOUND', f'{resource} not found: {identifier}', 404)

class ValidationError(AppError):
    """Validation failed."""
    pass

class DatabaseError(AppError):
    """Database operation failed."""
    pass
```

### Response Helpers (`utils/responses.py`)

```python
def success_response(data=None, message=None):
    return {'success': True, 'data': data, 'message': message}

def error_response(code, message, details=None):
    return {'success': False, 'error': {'code': code, 'message': message, 'details': details}}
```

---

## Logging

### Logging Service (`services/logging_service.py`)

Centralized logging with database persistence:

```python
class LoggingService:
    def initialize(self, db_connection, log_level='INFO')
    def log(self, level, message, source=None, category=None, **extra)
    def get_logs(self, level=None, source=None, limit=100) -> list

# Usage
logger = get_logger(__name__, LogSource.WORKFLOW)
logger.info("Workflow started", category='execution', workflow_id=123)
```

### Log Sources

```python
class LogSource(Enum):
    SYSTEM = 'system'
    API = 'api'
    WORKFLOW = 'workflow'
    SCHEDULER = 'scheduler'
    EXECUTOR = 'executor'
    AUTH = 'auth'
```
