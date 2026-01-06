# OpsConductor System Architecture

## Executive Summary

OpsConductor is a **network operations platform** that integrates multiple systems to provide:
- Device inventory management (via NetBox)
- Network performance monitoring and metrics collection
- AI-ready baseline and anomaly detection
- Workflow automation
- Credential management
- Alerting and notifications

This document defines the overall architecture, system boundaries, integration points, and deployment considerations.

---

## System Landscape

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │   NetBox    │  │  Ciena MCP  │  │    PRTG     │  │   Network   │                │
│  │  (Inventory)│  │  (Optical)  │  │ (Legacy NMS)│  │   Devices   │                │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │
│         │                │                │                │                        │
│         │ REST API       │ REST API       │ REST API       │ SNMP/SSH/ICMP         │
│         │                │                │                │                        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           OPSCONDUCTOR PLATFORM                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                         FRONTEND (React/Vite)                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │  Inventory  │  │   Monitor   │  │  Workflows  │  │   System    │          │  │
│  │  │   Module    │  │   Module    │  │   Module    │  │   Module    │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                             │
│                                        │ HTTP/REST                                   │
│                                        ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                    BACKEND API (FastAPI - OpenAPI 3.x)                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │/identity/v1 │  │/inventory/v1│  │/automation/ │  │/monitoring/ │          │  │
│  │  │   Auth      │  │  Devices    │  │  v1 Jobs    │  │ v1 Metrics  │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                             │
│         ┌──────────────────────────────┼──────────────────────────────┐             │
│         │                              │                              │             │
│         ▼                              ▼                              ▼             │
│  ┌─────────────┐              ┌─────────────┐              ┌─────────────┐          │
│  │   Service   │              │   Celery    │              │   Service   │          │
│  │    Layer    │              │   Workers   │              │    Layer    │          │
│  │ (Sync Ops)  │              │ (Async Jobs)│              │ (Scheduled) │          │
│  └─────────────┘              └─────────────┘              └─────────────┘          │
│         │                              │                              │             │
│         └──────────────────────────────┼──────────────────────────────┘             │
│                                        │                                             │
│                                        ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                         DATA LAYER                                             │  │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────┐            │  │
│  │  │      PostgreSQL             │  │         Redis               │            │  │
│  │  │  (Time-series, Config,      │  │  (Cache, Message Broker,    │            │  │
│  │  │   Baselines, Anomalies)     │  │   Session Store)            │            │  │
│  │  └─────────────────────────────┘  └─────────────────────────────┘            │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. External Systems (Third-Party)

| System | Purpose | Integration Method | Data Flow |
|--------|---------|-------------------|-----------|
| **NetBox** | Device inventory, IPAM, topology | REST API | Bidirectional |
| **Ciena MCP** | Optical network management | REST API | Read-only |
| **PRTG** | Legacy monitoring (deprecated) | REST API | Read-only (migration) |
| **Network Devices** | Switches, routers, cameras, etc. | SNMP, SSH, ICMP | Read + Write |

### 2. OpsConductor Components

#### Frontend (React/Vite)
- **Location**: `frontend/`
- **Port**: 3000
- **Modules**:
  - Inventory - Device browsing, site views
  - Monitor - Dashboards, metrics, alerts
  - Workflows - Automation builder
  - Credentials - Secure credential vault
  - System - Settings, users, logs

#### Backend API (FastAPI - OpenAPI 3.x)
- **Location**: `backend/main.py`, `app.py`
- **Port**: 5000
- **Responsibilities**:
  - OpenAPI 3.x REST endpoints
  - Domain-based routing (/identity/v1, /inventory/v1, etc.)
  - Authentication/Authorization
  - Service orchestration

#### Celery Workers
- **Location**: `celery_app.py`, `celery_tasks.py`, `backend/tasks/`
- **Broker**: Redis
- **Responsibilities**:
  - Async job execution
  - Scheduled polling
  - Long-running operations
  - Workflow execution

#### PostgreSQL Database
- **Location**: External (192.168.10.50:5432)
- **Database**: `network_scan`
- **Responsibilities**:
  - Time-series metrics storage
  - Configuration storage
  - Baseline profiles
  - Anomaly records
  - Credential vault
  - Job history

#### Redis
- **Location**: External (192.168.10.50:6379)
- **Responsibilities**:
  - Celery message broker
  - Session cache
  - API response cache
  - Real-time pub/sub

---

## Component Boundaries & Isolation

### Standalone Components (Can Run Independently)

```
┌─────────────────────────────────────────────────────────────────┐
│                    STANDALONE SYSTEMS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │     NetBox      │     │   PostgreSQL    │                   │
│  │                 │     │                 │                   │
│  │  - Own Docker   │     │  - Own service  │                   │
│  │  - Own DB       │     │  - Shared by    │                   │
│  │  - Own UI       │     │    multiple     │                   │
│  │  - Independent  │     │    apps         │                   │
│  │    lifecycle    │     │                 │                   │
│  └─────────────────┘     └─────────────────┘                   │
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │      Redis      │     │   Ciena MCP     │                   │
│  │                 │     │                 │                   │
│  │  - Own service  │     │  - Vendor       │                   │
│  │  - Shared by    │     │    managed      │                   │
│  │    multiple     │     │  - External     │                   │
│  │    apps         │     │                 │                   │
│  └─────────────────┘     └─────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Tightly Coupled Components (Must Deploy Together)

```
┌─────────────────────────────────────────────────────────────────┐
│                 OPSCONDUCTOR CORE (Deploy Together)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   FastAPI Backend                         │    │
│  │  - OpenAPI 3.x endpoints                                 │    │
│  │  - Service layer                                         │    │
│  │  - Database access                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           │ Shared code, models, services        │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Celery Workers                         │    │
│  │  - Same codebase as FastAPI                                │    │
│  │  - Shares services, models                               │    │
│  │  - Must be version-synchronized                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           │ API calls                            │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   React Frontend                         │    │
│  │  - Consumes FastAPI OpenAPI                              │    │
│  │  - Can be deployed separately (CDN)                      │    │
│  │  - But version should match API                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Patterns

### Pattern 1: Device Inventory (NetBox as Source of Truth)

```
User Request: "Show me all devices at site X"

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend │────▶│ FastAPI  │────▶│  NetBox  │────▶│  NetBox  │
│          │     │   API    │     │  Service │     │   API    │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     ▲                                                   │
     │                                                   │
     └───────────────────────────────────────────────────┘
                    Device list response
```

### Pattern 2: Performance Metrics (OpsConductor as Source)

```
User Request: "Show optical power for device X"

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend │────▶│ FastAPI  │────▶│ Metrics  │────▶│PostgreSQL│
│          │     │   API    │     │ Service  │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     ▲                                                   │
     │                                                   │
     └───────────────────────────────────────────────────┘
                    Metrics + baseline response
```

### Pattern 3: Metrics Collection (Polling)

```
Scheduled Job: "Collect optical metrics every 5 minutes"

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Celery  │────▶│  Poller  │────▶│  Device  │     │          │
│   Beat   │     │  Worker  │     │  (SNMP)  │     │          │
└──────────┘     └──────────┘     └──────────┘     │          │
                      │                            │PostgreSQL│
                      │ Store metrics              │          │
                      └───────────────────────────▶│          │
                                                   └──────────┘
```

### Pattern 4: Anomaly Detection

```
After Metrics Collection: "Check for anomalies"

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Poller  │────▶│ Anomaly  │────▶│ Baseline │     │          │
│  Worker  │     │ Detector │     │  Lookup  │     │          │
└──────────┘     └──────────┘     └──────────┘     │          │
                      │                            │PostgreSQL│
                      │ If anomaly detected        │          │
                      │ - Store anomaly            │          │
                      │ - Trigger notification     │          │
                      └───────────────────────────▶│          │
                                                   └──────────┘
```

### Pattern 5: Workflow Execution

```
User Trigger: "Run backup workflow for site X"

┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend │────▶│ FastAPI  │────▶│  Celery  │
│          │     │   API    │     │  Queue   │
└──────────┘     └──────────┘     └──────────┘
                                       │
                                       ▼
                                 ┌──────────┐
                                 │ Workflow │
                                 │  Worker  │
                                 └──────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
    ┌──────────┐                ┌──────────┐                ┌──────────┐
    │  NetBox  │                │  Device  │                │PostgreSQL│
    │  (tags)  │                │  (SSH)   │                │ (results)│
    └──────────┘                └──────────┘                └──────────┘
```

---

## Integration Points

### NetBox Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     NETBOX INTEGRATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OpsConductor                          NetBox                    │
│  ───────────                          ──────                     │
│                                                                  │
│  READ Operations:                                                │
│  ├─ GET /api/netbox/devices      →    GET /api/dcim/devices/    │
│  ├─ GET /api/netbox/sites        →    GET /api/dcim/sites/      │
│  ├─ GET /api/netbox/interfaces   →    GET /api/dcim/interfaces/ │
│  ├─ GET /api/netbox/ip-addresses →    GET /api/ipam/ip-addresses│
│  └─ GET /api/netbox/prefixes     →    GET /api/ipam/prefixes/   │
│                                                                  │
│  WRITE Operations (if needed):                                   │
│  ├─ POST /api/netbox/devices     →    POST /api/dcim/devices/   │
│  └─ PATCH /api/netbox/devices/X  →    PATCH /api/dcim/devices/X │
│                                                                  │
│  Configuration:                                                  │
│  ├─ NETBOX_URL: http://192.168.10.51:8000                       │
│  └─ NETBOX_TOKEN: (stored in system_settings)                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Ciena MCP Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     CIENA MCP INTEGRATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OpsConductor                          Ciena MCP                 │
│  ───────────                          ─────────                  │
│                                                                  │
│  READ Operations:                                                │
│  ├─ Get network elements           →   GET /nsi/api/...         │
│  ├─ Get optical power              →   GET /nsi/api/...         │
│  ├─ Get alarms                     →   GET /nsi/api/...         │
│  └─ Get topology                   →   GET /nsi/api/...         │
│                                                                  │
│  Service: ciena_mcp_service.py                                  │
│  Node Executor: node_executors/ciena_mcp.py                     │
│                                                                  │
│  Configuration:                                                  │
│  ├─ MCP_URL: (stored in system_settings)                        │
│  ├─ MCP_USERNAME: (stored in credentials)                       │
│  └─ MCP_PASSWORD: (stored in credentials)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Network Device Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                  NETWORK DEVICE INTEGRATION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Protocol        Service/Executor           Use Case             │
│  ────────        ────────────────           ────────             │
│                                                                  │
│  SNMP v2c/v3     snmp_service.py            - Metrics collection │
│                  node_executors/snmp.py     - Device discovery   │
│                  node_executors/snmp_walker - Interface status   │
│                                             - Optical power      │
│                                                                  │
│  SSH/CLI         node_executors/ssh.py      - Config backup      │
│                                             - Command execution  │
│                                             - Optical DOM data   │
│                                                                  │
│  ICMP            node_executors/network.py  - Availability check │
│                                             - Latency measurement│
│                                                                  │
│  Credentials:                                                    │
│  ├─ SNMP community strings (credential_service)                 │
│  ├─ SSH username/password (credential_service)                  │
│  └─ SSH keys (credential_service)                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Current Deployment (Single Server)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVER: 192.168.10.50                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  OpsConductor Application                                │    │
│  │  ├─ FastAPI Backend (port 5000)                           │    │
│  │  ├─ Celery Workers (4 workers)                          │    │
│  │  ├─ Celery Beat (scheduler)                             │    │
│  │  └─ React Frontend (port 3000, dev) or Nginx (prod)     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Data Services                                           │    │
│  │  ├─ PostgreSQL (port 5432)                              │    │
│  │  └─ Redis (port 6379)                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SERVER: 192.168.10.51                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  NetBox (Docker Compose)                                 │    │
│  │  ├─ NetBox Application (port 8000)                      │    │
│  │  ├─ PostgreSQL (internal)                               │    │
│  │  ├─ Redis (internal)                                    │    │
│  │  └─ Nginx (reverse proxy)                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Production Deployment (Scalable)

```
┌─────────────────────────────────────────────────────────────────┐
│                       LOAD BALANCER                              │
│                    (HAProxy / Nginx / AWS ALB)                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   API Server  │  │   API Server  │  │   API Server  │
│   (FastAPI)     │  │   (FastAPI)     │  │   (FastAPI)     │
│   Stateless   │  │   Stateless   │  │   Stateless   │
└───────────────┘  └───────────────┘  └───────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MESSAGE QUEUE                              │
│                         (Redis)                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Celery Worker │  │ Celery Worker │  │ Celery Worker │
│  (Polling)    │  │  (Workflows)  │  │  (Analysis)   │
└───────────────┘  └───────────────┘  └───────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
├─────────────────────────────┬───────────────────────────────────┤
│        PostgreSQL           │            Redis                   │
│   (Primary + Replica)       │      (Cluster Mode)               │
│                             │                                    │
│   - Time-series data        │   - Session cache                 │
│   - Partitioned tables      │   - API cache                     │
│   - Connection pooling      │   - Pub/sub                       │
└─────────────────────────────┴───────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
├─────────────────────────────┬───────────────────────────────────┤
│          NetBox             │         Ciena MCP                  │
│   (Separate deployment)     │    (Vendor managed)               │
└─────────────────────────────┴───────────────────────────────────┘
```

---

## Service Isolation Recommendations

### 1. Database Isolation

**Current**: Single PostgreSQL instance for everything
**Recommended**: Consider separation for scale

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE ISOLATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option A: Single DB, Multiple Schemas (Current)                │
│  ─────────────────────────────────────────────────              │
│  ├─ public schema: All tables                                   │
│  └─ Pros: Simple, single connection                             │
│                                                                  │
│  Option B: Separate Databases (Recommended for Scale)           │
│  ─────────────────────────────────────────────────              │
│  ├─ opsconductor_metrics: Time-series data (high write)        │
│  ├─ opsconductor_config: Configuration, credentials (low write)│
│  └─ opsconductor_jobs: Job history, workflows (medium write)   │
│                                                                  │
│  Option C: TimescaleDB for Metrics (Best for Time-Series)       │
│  ─────────────────────────────────────────────────              │
│  ├─ TimescaleDB: Metrics, baselines, anomalies                 │
│  └─ PostgreSQL: Everything else                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Worker Isolation

**Current**: Single Celery worker pool
**Recommended**: Separate queues for different workloads

```
┌─────────────────────────────────────────────────────────────────┐
│                     WORKER ISOLATION                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Queue: polling (high frequency, time-sensitive)                │
│  ├─ Workers: 2-4                                                │
│  ├─ Tasks: SNMP polling, availability checks                    │
│  └─ Priority: High                                              │
│                                                                  │
│  Queue: workflows (user-triggered, variable duration)           │
│  ├─ Workers: 2-4                                                │
│  ├─ Tasks: Workflow execution, config backups                   │
│  └─ Priority: Medium                                            │
│                                                                  │
│  Queue: analysis (background, can be delayed)                   │
│  ├─ Workers: 1-2                                                │
│  ├─ Tasks: Baseline calculation, anomaly detection              │
│  └─ Priority: Low                                               │
│                                                                  │
│  Queue: notifications (must be reliable)                        │
│  ├─ Workers: 1-2                                                │
│  ├─ Tasks: Email, webhook, SMS notifications                    │
│  └─ Priority: High                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. API Isolation

**Current**: Single FastAPI application
**Recommended**: Consider API gateway for external integrations

```
┌─────────────────────────────────────────────────────────────────┐
│                      API ISOLATION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Internal API (FastAPI - port 5000)                               │
│  ├─ /api/auth/*        - Authentication                         │
│  ├─ /api/devices/*     - Device operations                      │
│  ├─ /api/metrics/*     - Metrics queries                        │
│  ├─ /api/workflows/*   - Workflow management                    │
│  └─ /api/credentials/* - Credential vault                       │
│                                                                  │
│  NetBox Proxy (FastAPI - same port, could separate)               │
│  └─ /api/netbox/*      - Proxied to NetBox                      │
│                                                                  │
│  Future: External API (separate service)                        │
│  ├─ Rate limiting                                               │
│  ├─ API key authentication                                      │
│  ├─ Webhook endpoints                                           │
│  └─ Third-party integrations                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY BOUNDARIES                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ZONE 1: Public (Internet-facing)                               │
│  ────────────────────────────────                               │
│  └─ Nothing currently (internal network only)                   │
│                                                                  │
│  ZONE 2: DMZ (If exposing externally)                           │
│  ────────────────────────────────────                           │
│  ├─ Load balancer / Reverse proxy                               │
│  └─ API gateway (rate limiting, auth)                           │
│                                                                  │
│  ZONE 3: Application (Internal network)                         │
│  ────────────────────────────────────                           │
│  ├─ OpsConductor Frontend (192.168.10.50:3000)                 │
│  ├─ OpsConductor Backend (192.168.10.50:5000)                  │
│  ├─ NetBox (192.168.10.51:8000)                                │
│  └─ Celery Workers                                              │
│                                                                  │
│  ZONE 4: Data (Most restricted)                                 │
│  ────────────────────────────────                               │
│  ├─ PostgreSQL (192.168.10.50:5432)                            │
│  ├─ Redis (192.168.10.50:6379)                                 │
│  └─ Credential vault (encrypted at rest)                        │
│                                                                  │
│  ZONE 5: Network Devices (Managed network)                      │
│  ────────────────────────────────────────                       │
│  ├─ Switches, routers (SNMP, SSH access)                       │
│  ├─ Cameras (SNMP access)                                       │
│  └─ Ciena MCP (API access)                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Future Expansion Considerations

### 1. AI/ML Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI/ML INTEGRATION                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option A: Embedded (Python libraries in Celery workers)        │
│  ├─ Pros: Simple, no new infrastructure                         │
│  ├─ Cons: Limited scale, blocks workers                         │
│  └─ Use for: Baseline calculation, simple anomaly detection     │
│                                                                  │
│  Option B: Separate ML Service (Recommended)                    │
│  ├─ Dedicated service for ML inference                          │
│  ├─ Can use GPU if needed                                       │
│  ├─ Scales independently                                        │
│  └─ Use for: Complex predictions, LLM integration               │
│                                                                  │
│  Data Flow:                                                      │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │PostgreSQL│────▶│ML Service│────▶│Predictions│               │
│  │(metrics) │     │          │     │(anomalies)│               │
│  └──────────┘     └──────────┘     └──────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Multi-Tenancy (If Needed)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-TENANCY                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option A: Single Instance, Data Isolation                      │
│  ├─ Add tenant_id to all tables                                 │
│  ├─ Row-level security in PostgreSQL                            │
│  └─ Shared infrastructure, isolated data                        │
│                                                                  │
│  Option B: Separate Instances per Tenant                        │
│  ├─ Each tenant gets own OpsConductor + NetBox                 │
│  ├─ Complete isolation                                          │
│  └─ Higher cost, easier compliance                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. High Availability

```
┌─────────────────────────────────────────────────────────────────┐
│                    HIGH AVAILABILITY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Component          HA Strategy                                  │
│  ─────────          ───────────                                  │
│  FastAPI API          Multiple instances + load balancer          │
│  Celery Workers     Multiple workers (already supported)        │
│  PostgreSQL         Primary + streaming replica                 │
│  Redis              Redis Sentinel or Cluster                   │
│  NetBox             Multiple instances + load balancer          │
│                                                                  │
│  Failure Scenarios:                                              │
│  ├─ API server down    → LB routes to healthy instance         │
│  ├─ Worker down        → Other workers pick up tasks           │
│  ├─ PostgreSQL down    → Failover to replica                   │
│  ├─ Redis down         → Celery pauses, resumes on recovery    │
│  └─ NetBox down        → Cached data, degraded inventory       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary: What Can Stand Alone

| Component | Standalone? | Dependencies | Notes |
|-----------|-------------|--------------|-------|
| **NetBox** | ✅ Yes | Own PostgreSQL, Redis | Completely independent |
| **PostgreSQL** | ✅ Yes | None | Shared service |
| **Redis** | ✅ Yes | None | Shared service |
| **Ciena MCP** | ✅ Yes | Vendor managed | External system |
| **FastAPI API** | ❌ No | PostgreSQL, Redis, NetBox | Core application |
| **Celery Workers** | ❌ No | Same as FastAPI | Shares codebase |
| **React Frontend** | ⚠️ Partial | FastAPI API | Can deploy separately |

---

## Recommended Architecture Decisions

1. **Keep NetBox separate** - It's already isolated and works well
2. **Consider TimescaleDB** - For better time-series performance at scale
3. **Separate Celery queues** - For workload isolation
4. **Add API caching** - Redis cache for NetBox responses
5. **Plan for ML service** - Separate service when AI features mature
6. **Document API contracts** - OpenAPI spec for all endpoints
