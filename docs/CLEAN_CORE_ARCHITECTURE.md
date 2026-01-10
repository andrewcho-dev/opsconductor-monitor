# OpsConductor Clean Core Architecture

## Design Principles

1. **Minimal** - Only what's needed for alert processing + addons
2. **Single Responsibility** - Each component does ONE thing
3. **No Duplication** - ONE implementation of each function
4. **Database-Driven** - Configuration in DB, not code
5. **Observable** - Easy to monitor, debug, troubleshoot
6. **Scalable** - Handle more addons/alerts by adding workers

---

## Core Components (7 Total)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLEAN CORE                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. DATABASE LAYER (PostgreSQL)                                          │
│     └── db.py - Single module for all DB access                          │
│                                                                          │
│  2. ADDON REGISTRY                                                       │
│     └── addon_registry.py - Load/register/lookup addons                  │
│                                                                          │
│  3. INBOUND HANDLERS (receive data from external systems)                │
│     ├── trap_receiver.py - SNMP trap listener (UDP 162)                  │
│     └── webhook_receiver.py - HTTP webhook endpoints                     │
│                                                                          │
│  4. OUTBOUND POLLERS (fetch data from external systems)                  │
│     └── poller.py - Single SNMP/API/SSH poller                           │
│                                                                          │
│  5. PARSER ENGINE                                                        │
│     └── parser.py - Apply addon parse rules to raw data                  │
│                                                                          │
│  6. ALERT ENGINE                                                         │
│     └── alert_engine.py - Normalize, dedupe, store, emit                 │
│                                                                          │
│  7. TASK SCHEDULER (Celery + Beat)                                       │
│     └── tasks.py - Poll scheduling, maintenance tasks                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
INBOUND (Event-Driven):
  External System → Trap/Webhook → Parser → Alert Engine → Database → Dashboard

OUTBOUND (Polling):
  Scheduler → Poller → External System → Parser → Alert Engine → Database → Dashboard
```

---

## File Structure

```
backend/
├── core/                      # THE CORE (7 files)
│   ├── __init__.py
│   ├── db.py                  # Database access (ONE module)
│   ├── addon_registry.py      # Addon loading and lookup
│   ├── trap_receiver.py       # SNMP trap handler
│   ├── webhook_receiver.py    # HTTP webhook handler
│   ├── poller.py              # SNMP/API/SSH polling
│   ├── parser.py              # Parse engine (JSON, regex, grok, etc.)
│   └── alert_engine.py        # Alert processing (dedupe, store, emit)
│
├── tasks/                     # Celery tasks (minimal)
│   ├── __init__.py
│   └── tasks.py               # Poll dispatcher, maintenance
│
├── api/                       # FastAPI routes (minimal)
│   ├── __init__.py
│   ├── main.py                # App entry point
│   ├── alerts.py              # Alert CRUD
│   ├── addons.py              # Addon management
│   └── system.py              # Health, stats
│
├── addons/                    # Installed addons (declarative)
│   ├── siklu/
│   │   └── manifest.json
│   ├── prtg/
│   │   └── manifest.json
│   └── ...
│
└── migrations/                # DB schema
    └── *.sql
```

**Total: ~15 files** (vs current ~200+ files)

---

## Component Specifications

### 1. db.py - Database Layer

```python
# Single module for ALL database access
# No other code touches psycopg2 directly

def query(sql, params=None) -> List[Dict]
def query_one(sql, params=None) -> Optional[Dict]
def execute(sql, params=None) -> int
def get_setting(key, default=None) -> Any
def set_setting(key, value) -> None
```

### 2. addon_registry.py - Addon Registry

```python
# Load addons from database, provide lookup

class AddonRegistry:
    def load_all() -> None                    # Load all enabled addons
    def get_addon(addon_id) -> Addon          # Get by ID
    def find_by_oid(oid) -> Addon             # Find by SNMP OID prefix
    def find_by_webhook(path) -> Addon        # Find by webhook path
    def get_enabled() -> List[Addon]          # List enabled addons
    
@dataclass
class Addon:
    id: str
    manifest: Dict                            # Full manifest.json
    method: str                               # snmp_trap, webhook, api_poll, etc.
    enabled: bool
```

### 3. trap_receiver.py - SNMP Trap Handler

```python
# Listen for SNMP traps, dispatch to parser

class TrapReceiver:
    def start(port=162) -> None
    def stop() -> None
    
    async def handle_trap(trap: SNMPTrap) -> None:
        addon = registry.find_by_oid(trap.enterprise_oid)
        if addon:
            parsed = parser.parse(trap.data, addon.manifest)
            await alert_engine.process(parsed, addon)
```

### 4. webhook_receiver.py - Webhook Handler

```python
# HTTP endpoints for webhooks, dispatch to parser

async def handle_webhook(request, path: str) -> Response:
    addon = registry.find_by_webhook(path)
    if addon:
        data = await request.json()
        parsed = parser.parse(data, addon.manifest)
        await alert_engine.process(parsed, addon)
```

### 5. poller.py - Unified Poller

```python
# Single poller for SNMP, API, SSH

class Poller:
    async def poll_snmp(target, oids, community) -> Dict
    async def poll_api(url, method, headers, auth) -> Dict
    async def poll_ssh(host, command, credentials) -> str
```

### 6. parser.py - Parse Engine

```python
# Apply addon's parse rules to raw data

class Parser:
    def parse(raw_data: Any, manifest: Dict) -> ParsedAlert:
        parser_type = manifest['parser']['type']
        
        if parser_type == 'json':
            return self._parse_json(raw_data, manifest)
        elif parser_type == 'snmp':
            return self._parse_snmp(raw_data, manifest)
        elif parser_type == 'regex':
            return self._parse_regex(raw_data, manifest)
        elif parser_type == 'grok':
            return self._parse_grok(raw_data, manifest)
        # etc.

@dataclass
class ParsedAlert:
    addon_id: str
    alert_type: str
    device_ip: str
    message: str
    raw_data: Dict
    fields: Dict                              # Extracted fields
```

### 7. alert_engine.py - Alert Processing

```python
# Core alert processing: normalize, dedupe, store, emit

class AlertEngine:
    async def process(parsed: ParsedAlert, addon: Addon) -> Alert:
        # 1. Apply mappings from addon manifest
        severity = addon.manifest['severity_mappings'].get(parsed.alert_type, 'warning')
        category = addon.manifest['category_mappings'].get(parsed.alert_type, 'unknown')
        
        # 2. Generate fingerprint for deduplication
        fingerprint = self._fingerprint(parsed)
        
        # 3. Check for duplicate
        existing = await self._find_duplicate(fingerprint)
        
        if existing:
            # Update occurrence count
            return await self._update_alert(existing, parsed)
        else:
            # Create new alert
            alert = await self._create_alert(parsed, addon, fingerprint)
            
            # 4. Emit event for real-time updates
            await self._emit_event('alert_created', alert)
            
            return alert
```

---

## Database Schema (Minimal)

```sql
-- Addons registry
CREATE TABLE addons (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(32),
    method VARCHAR(32) NOT NULL,
    manifest JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    installed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alerts (single table, not two!)
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    addon_id VARCHAR(64) REFERENCES addons(id),
    fingerprint VARCHAR(64) NOT NULL,
    device_ip VARCHAR(45) NOT NULL,
    device_name VARCHAR(128),
    alert_type VARCHAR(128) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    category VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    message TEXT,
    status VARCHAR(32) DEFAULT 'active',
    is_clear BOOLEAN DEFAULT false,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    occurrence_count INTEGER DEFAULT 1,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_fingerprint ON alerts(fingerprint);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_device_ip ON alerts(device_ip);
CREATE INDEX idx_alerts_occurred_at ON alerts(occurred_at);

-- System settings
CREATE TABLE system_settings (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Targets (devices to poll)
CREATE TABLE targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    addon_id VARCHAR(64) REFERENCES addons(id),
    poll_interval INTEGER DEFAULT 300,
    enabled BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    last_poll_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## What Gets Removed

| Current | Action |
|---------|--------|
| `services/` (46 files) | DELETE - rebuild only what's needed |
| `executors/` (10 files) | DELETE - replaced by `poller.py` |
| `connectors/` (34 items) | CONVERT to declarative addons |
| `repositories/` (10 files) | DELETE - use `db.py` directly |
| `parsers/` (8 files) | MERGE into `parser.py` |
| `openapi/` (7 files) | DELETE |
| `models/` (1 file) | MERGE into core modules |
| `workflows/` (1 file) | DELETE |
| `targeting/` (4 files) | DELETE |
| `middleware/` (4 files) | KEEP only auth if needed |

---

## Implementation Order

1. **Create new `core/` modules** (db, registry, parser, alert_engine)
2. **Create minimal `api/`** (main, alerts, addons, system)
3. **Create trap_receiver and webhook_receiver**
4. **Create poller**
5. **Create Celery tasks**
6. **Migrate data** (alerts, settings)
7. **Convert connectors to addons**
8. **Archive/delete old code**

---

## Benefits

| Metric | Current | New |
|--------|---------|-----|
| Files | ~200+ | ~15 |
| Lines of code | ~50K+ | ~3K |
| Concepts to understand | Dozens | 7 |
| Time to onboard dev | Days | Hours |
| Debug complexity | High | Low |
| Performance | Unknown | Optimized |

---

## Confirmed Requirements

1. **Celery + Beat** - Keep for task scheduling and background jobs
2. **FastAPI** - Keep as API framework
3. **WebSocket** - Yes, for real-time dashboard updates
4. **Enterprise Auth** - Robust, enterprise-level authentication

---

## Updated Component List (11 Modules)

```
backend/
├── core/                      # CORE ENGINE (7 files)
│   ├── db.py                  # Database access
│   ├── addon_registry.py      # Addon loading/lookup
│   ├── trap_receiver.py       # SNMP trap handler
│   ├── webhook_receiver.py    # HTTP webhook handler
│   ├── poller.py              # SNMP/API/SSH polling
│   ├── parser.py              # Parse engine
│   └── alert_engine.py        # Alert processing
│
├── api/                       # API LAYER (5 files)
│   ├── main.py                # FastAPI app
│   ├── routes/
│   │   ├── alerts.py          # Alert CRUD
│   │   ├── addons.py          # Addon management
│   │   └── system.py          # Health, stats, config
│   ├── websocket.py           # Real-time updates
│   └── auth.py                # Enterprise authentication
│
├── tasks/                     # CELERY (2 files)
│   ├── celery_app.py          # Celery configuration
│   └── tasks.py               # Scheduled tasks
│
└── addons/                    # INSTALLED ADDONS
    └── {addon_id}/manifest.json
```

---

## Enterprise Authentication

```python
# auth.py - Enterprise-grade authentication

Features:
- JWT tokens with refresh
- Role-based access control (RBAC)
- API key support for service accounts
- Session management
- Audit logging
- Optional LDAP/AD integration
- Optional SAML/SSO support
- Rate limiting
- IP allowlisting

Roles:
- admin: Full system access
- operator: Alert management, addon config
- viewer: Read-only dashboard access
- service: API-only access for integrations
```

---

## WebSocket Real-Time Updates

```python
# websocket.py - Real-time dashboard updates

Events:
- alert_created: New alert
- alert_updated: Alert status change
- alert_resolved: Alert resolved
- system_status: Health updates
- addon_status: Addon enable/disable

Pattern:
- Client connects to /ws
- Authenticates with JWT
- Subscribes to event types
- Receives real-time updates
```

---

## Ready to Build

Total files: ~15 (vs current ~200+)

Starting with:
1. `core/db.py` - Database foundation
2. `core/addon_registry.py` - Addon system foundation

Shall I begin?
