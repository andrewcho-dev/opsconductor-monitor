# 02 - Architecture

**OpsConductor MVP - System Architecture**

---

## 1. Architectural Principles

| Principle | Description |
|-----------|-------------|
| **Modular** | Independent modules with clear boundaries |
| **Layered** | Strict separation of concerns |
| **Contract-Based** | Modules communicate via defined interfaces |
| **Standard-Compliant** | All alerts conform to classification standard |
| **Fail-Safe** | Graceful degradation, no data loss |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                                │
│  PRTG │ MCP │ SNMP Devices │ Eaton │ Axis │ Milestone │ Cradlepoint │ etc  │
└───────┴─────┴──────────────┴───────┴──────┴───────────┴─────────────┴──────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LAYER 1: CONNECTORS                                  │
│                                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   PRTG   │ │   MCP    │ │   SNMP   │ │  Eaton   │ │   Axis   │  ...     │
│  │Connector │ │Connector │ │Connector │ │Connector │ │Connector │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │            │                 │
│       └────────────┴────────────┴────────────┴────────────┘                 │
│                                 │                                            │
│                         Raw Alert Data                                       │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 2: NORMALIZATION                                 │
│                                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   PRTG   │ │   MCP    │ │   SNMP   │ │  Eaton   │ │   Axis   │  ...     │
│  │Normalizer│ │Normalizer│ │Normalizer│ │Normalizer│ │Normalizer│          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │            │                 │
│       └────────────┴────────────┴────────────┴────────────┘                 │
│                                 │                                            │
│                      Normalized Alert (Standard Schema)                      │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 3: CORE SERVICES                                 │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  Alert Manager  │  │   Dependency    │  │  Notification   │             │
│  │                 │  │    Registry     │  │    Service      │             │
│  │ - Receive alert │  │                 │  │                 │             │
│  │ - Dedup check   │  │ - Device graph  │  │ - Route alerts  │             │
│  │ - Correlate     │  │ - Dependencies  │  │ - Email/webhook │             │
│  │ - Store         │  │ - Lookup        │  │ - Templates     │             │
│  │ - Emit events   │  │                 │  │                 │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│  ┌────────┴────────────────────┴────────────────────┴────────┐             │
│  │                      EVENT BUS                             │             │
│  │           (Internal async event distribution)              │             │
│  └────────────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 4: API GATEWAY                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Router                               │   │
│  │                                                                      │   │
│  │  /alerts/*        /dependencies/*      /connectors/*    /system/*   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  - Authentication (JWT)                                                      │
│  - Rate limiting                                                             │
│  - Request validation                                                        │
│  - Response formatting                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 5: PRESENTATION                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         React Frontend                               │   │
│  │                                                                      │   │
│  │  Alert Dashboard │ Dependency Editor │ Connector Config │ Settings  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Details

### 3.1 Layer 1: Connectors

**Purpose:** Interface with external systems, receive/poll raw data

**Responsibilities:**
- Authenticate with external system
- Receive webhooks or poll for data
- Handle connection errors and retries
- Return raw data (no transformation)

**Interface:**
```python
class BaseConnector(ABC):
    @abstractmethod
    async def start(self) -> None:
        """Start receiving/polling alerts"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop and cleanup"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> dict:
        """Test connectivity to external system"""
        pass
    
    @abstractmethod
    def get_normalizer(self) -> BaseNormalizer:
        """Return the normalizer for this connector"""
        pass
```

**Connectors (9 total):**

| Connector | Input Method | Existing Code |
|-----------|--------------|---------------|
| PRTG | Webhook + Poll | `prtg_service.py` |
| MCP | Poll | `ciena_mcp_service.py` |
| SNMP Trap | UDP 162 | `snmp_trap_receiver.py` |
| SNMP Poll | Poll | `async_snmp_poller.py` |
| Eaton | SNMP Poll | `eaton_snmp_service.py` |
| Axis VAPIX | Poll + Events | NEW |
| Milestone | Poll + Events | NEW |
| Cradlepoint | Poll | NEW |
| Siklu | Poll | NEW |
| Ubiquiti | Poll | NEW |

---

### 3.2 Layer 2: Normalization

**Purpose:** Transform raw data to standard alert schema

**Responsibilities:**
- Map source fields to standard fields
- Apply severity mapping
- Apply category classification
- Preserve raw data for debugging

**Interface:**
```python
class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw_data: dict) -> NormalizedAlert:
        """Convert raw alert to standard schema"""
        pass
    
    @abstractmethod
    def get_severity(self, raw_data: dict) -> str:
        """Determine severity from raw data"""
        pass
    
    @abstractmethod
    def get_category(self, raw_data: dict) -> str:
        """Determine category from raw data"""
        pass
```

**Output:** `NormalizedAlert` conforming to Alert Classification Standard

---

### 3.3 Layer 3: Core Services

#### 3.3.1 Alert Manager

**Purpose:** Central processing of all normalized alerts

**Responsibilities:**
- Receive normalized alerts from all connectors
- Deduplication (fingerprint-based)
- Correlation (dependency lookup)
- Suppression (mark downstream alerts)
- Storage (PostgreSQL)
- Event emission (for notifications)

**Key Functions:**
```python
class AlertManager:
    async def process_alert(self, alert: NormalizedAlert) -> Alert:
        """Main entry point for all alerts"""
        
    async def check_duplicate(self, alert: NormalizedAlert) -> Optional[Alert]:
        """Check if alert is duplicate of existing"""
        
    async def correlate(self, alert: Alert) -> Optional[Alert]:
        """Find parent alert if this is downstream"""
        
    async def suppress(self, alert: Alert, parent: Alert) -> None:
        """Mark alert as suppressed due to parent"""
        
    async def acknowledge(self, alert_id: str, user: str, notes: str) -> Alert:
        """Mark alert as acknowledged"""
        
    async def resolve(self, alert_id: str, user: str, notes: str) -> Alert:
        """Mark alert as resolved"""
```

#### 3.3.2 Dependency Registry

**Purpose:** Manage device dependency graph

**Responsibilities:**
- Store device dependencies
- Query upstream/downstream devices
- Sync device list from NetBox
- Provide lookup for correlation

**Key Functions:**
```python
class DependencyRegistry:
    async def add_dependency(self, device_ip: str, depends_on_ip: str, 
                            dep_type: str) -> Dependency:
        """Create dependency relationship"""
        
    async def get_upstream(self, device_ip: str) -> List[Device]:
        """Get all devices this device depends on"""
        
    async def get_downstream(self, device_ip: str) -> List[Device]:
        """Get all devices that depend on this device"""
        
    async def has_active_upstream_alert(self, device_ip: str) -> Optional[Alert]:
        """Check if any upstream device has active alert"""
```

#### 3.3.3 Notification Service

**Purpose:** Deliver alerts to appropriate channels

**Responsibilities:**
- Route alerts based on rules
- Render notification templates
- Deliver via email, webhook
- Track delivery status

**Key Functions:**
```python
class NotificationService:
    async def notify(self, alert: Alert) -> List[DeliveryResult]:
        """Send notifications for alert"""
        
    async def send_email(self, recipients: List[str], alert: Alert) -> bool:
        """Send email notification"""
        
    async def send_webhook(self, url: str, alert: Alert) -> bool:
        """Send webhook notification"""
```

---

### 3.4 Layer 4: API Gateway

**Purpose:** REST API for frontend and external access

**Responsibilities:**
- Route requests to appropriate services
- Authenticate requests (JWT)
- Validate request payloads
- Format responses consistently

**Routers:**

| Router | Prefix | Purpose |
|--------|--------|---------|
| Alerts | `/api/v1/alerts` | Alert CRUD, actions |
| Dependencies | `/api/v1/dependencies` | Dependency management |
| Connectors | `/api/v1/connectors` | Connector config, status |
| Notifications | `/api/v1/notifications` | Notification rules |
| System | `/api/v1/system` | Health, settings |

---

### 3.5 Layer 5: Presentation

**Purpose:** User interface

**Responsibilities:**
- Display alerts dashboard
- Provide alert actions (ack, resolve)
- Dependency editor
- Connector configuration
- System settings

**Key Pages:**

| Page | Purpose |
|------|---------|
| Alert Dashboard | Main view - all alerts |
| Alert Detail | Single alert with history |
| Dependencies | View/edit device dependencies |
| Connectors | Configure external connections |
| Settings | System configuration |

---

## 4. Communication Patterns

### 4.1 Synchronous (Request/Response)

Used for:
- API requests from frontend
- Database queries
- External API calls to connectors

```
Frontend → API Gateway → Service → Database
                              ↓
Frontend ← API Gateway ← Response
```

### 4.2 Asynchronous (Event Bus)

Used for:
- Alert ingestion (connector → alert manager)
- Notification triggers (alert manager → notification service)
- Real-time UI updates (WebSocket)

```
Connector → Normalizer → Alert Manager ──┬──→ Database
                                         │
                                         └──→ Event Bus ──→ Notification Service
                                                       └──→ WebSocket (UI)
```

### 4.3 Event Bus Implementation

For MVP, use simple in-process async queues:

```python
# Simple event bus using asyncio
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers[event_type].append(handler)
    
    async def publish(self, event_type: str, data: Any):
        for handler in self._subscribers[event_type]:
            asyncio.create_task(handler(data))

# Usage
event_bus.subscribe("alert.created", notification_service.on_alert_created)
event_bus.subscribe("alert.created", websocket_manager.broadcast_alert)

await event_bus.publish("alert.created", alert)
```

---

## 5. Module Structure

```
backend/
├── connectors/                 # Layer 1: Connectors
│   ├── __init__.py
│   ├── base.py                 # BaseConnector, BaseNormalizer
│   ├── prtg/
│   │   ├── connector.py
│   │   └── normalizer.py
│   ├── mcp/
│   │   ├── connector.py
│   │   └── normalizer.py
│   ├── snmp/
│   │   ├── trap_receiver.py
│   │   ├── poller.py
│   │   ├── normalizer.py
│   │   └── oid_mappings.py
│   ├── eaton/
│   │   ├── connector.py
│   │   └── normalizer.py
│   ├── axis/
│   │   ├── connector.py
│   │   └── normalizer.py
│   ├── milestone/
│   │   ├── connector.py
│   │   └── normalizer.py
│   ├── cradlepoint/
│   │   ├── connector.py
│   │   └── normalizer.py
│   ├── siklu/
│   │   ├── connector.py
│   │   └── normalizer.py
│   └── ubiquiti/
│       ├── connector.py
│       └── normalizer.py
│
├── core/                       # Layer 3: Core Services
│   ├── __init__.py
│   ├── alert_manager.py
│   ├── dependency_registry.py
│   ├── notification_service.py
│   ├── event_bus.py
│   └── models.py               # NormalizedAlert, Alert, Dependency
│
├── routers/                    # Layer 4: API Gateway
│   ├── __init__.py
│   ├── alerts.py
│   ├── dependencies.py
│   ├── connectors.py
│   ├── notifications.py
│   └── system.py
│
├── utils/                      # Shared utilities
│   ├── db.py                   # Database access (existing)
│   ├── http.py                 # HTTP clients (existing)
│   └── errors.py               # Error handling
│
└── main.py                     # FastAPI app entry
```

---

## 6. Data Flow Example

### Alert Ingestion Flow

```
1. PRTG sends webhook to /api/connectors/prtg/webhook
   
2. PRTGConnector receives raw data:
   {
     "sensorid": "1234",
     "status": "Down",
     "device": "Core-Switch-1",
     "host": "10.1.1.1",
     ...
   }

3. PRTGNormalizer transforms to standard:
   {
     "id": "uuid-xxx",
     "source_system": "prtg",
     "device_ip": "10.1.1.1",
     "severity": "critical",
     "category": "network",
     "title": "Ping Sensor Down",
     ...
   }

4. AlertManager.process_alert():
   a. check_duplicate() → Not duplicate
   b. correlate() → Check if 10.1.1.1 has upstream with active alert
      - DependencyRegistry.get_upstream("10.1.1.1") → ["10.1.0.1"]
      - Check alerts for 10.1.0.1 → No active alert
   c. store() → Save to database
   d. event_bus.publish("alert.created", alert)

5. NotificationService receives event:
   a. Check notification rules
   b. Send email to NOC team
   c. Send webhook to Slack

6. WebSocket broadcasts to connected dashboards

7. Dashboard updates in real-time
```

---

## 7. Security

### Authentication
- JWT tokens for API access
- Existing auth system retained

### Authorization
- Role-based access control (existing)
- Connector credentials stored encrypted

### Data Protection
- Raw credentials never logged
- Audit trail for alert actions

---

## 8. Scalability Considerations

**MVP Design (Single Server):**
- All components on one server
- In-process event bus
- Single PostgreSQL instance

**Future Scaling:**
- Event bus → Redis/RabbitMQ
- Connectors → Separate workers
- Database → Read replicas
- Frontend → CDN

---

*Next: [03_DATA_MODELS.md](./03_DATA_MODELS.md)*
