# OpsConductor Infrastructure & Deployment Guide

## Physical Infrastructure Overview

This document describes how all system components should be deployed, what each component does, and how they communicate.

---

## Deployment Options

### Option 1: Current Setup (Development/Small Production)
Two physical/virtual servers

### Option 2: Recommended Production
Three or more servers with separation of concerns

### Option 3: Containerized (Docker/Kubernetes)
Fully containerized deployment

---

## Option 1: Current Two-Server Setup

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   NETWORK                                            │
│                              192.168.10.0/24                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
         │                                                      │
         │                                                      │
         ▼                                                      ▼
┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐
│     SERVER 1: OpsConductor          │    │     SERVER 2: NetBox                │
│     192.168.10.50                   │    │     192.168.10.51                   │
│                                     │    │                                     │
│  ┌───────────────────────────────┐  │    │  ┌───────────────────────────────┐  │
│  │      REACT FRONTEND           │  │    │  │      NETBOX (Docker)          │  │
│  │      Port: 3000               │  │    │  │      Port: 8000               │  │
│  │                               │  │    │  │                               │  │
│  │  Purpose: User Interface      │  │    │  │  Purpose: Device Inventory    │  │
│  │  - Dashboard views            │  │    │  │  - Device management          │  │
│  │  - Device browsing            │  │    │  │  - IPAM (IP addresses)        │  │
│  │  - Workflow builder           │  │    │  │  - Site/location management   │  │
│  │  - Credential management      │  │    │  │  - Cable/connection tracking  │  │
│  └───────────────────────────────┘  │    │  │  - Interface templates        │  │
│              │                      │    │  └───────────────────────────────┘  │
│              │ HTTP API calls       │    │              │                      │
│              ▼                      │    │              │                      │
│  ┌───────────────────────────────┐  │    │  ┌───────────────────────────────┐  │
│  │      FASTAPI BACKEND            │  │    │  │      POSTGRESQL (NetBox)      │  │
│  │      Port: 5000               │  │    │  │      Port: 5432 (internal)    │  │
│  │                               │  │    │  │                               │  │
│  │  Purpose: API & Orchestration │  │    │  │  Purpose: NetBox Data Store   │  │
│  │  - REST API endpoints         │  │    │  │  - Device records             │  │
│  │  - Authentication             │  │    │  │  - IP address records         │  │
│  │  - NetBox API proxy           │  │    │  │  - Site/rack data             │  │
│  │  - Service coordination       │  │    │  └───────────────────────────────┘  │
│  └───────────────────────────────┘  │    │              │                      │
│              │                      │    │  ┌───────────────────────────────┐  │
│              │                      │    │  │      REDIS (NetBox)           │  │
│  ┌───────────────────────────────┐  │    │  │      Port: 6379 (internal)    │  │
│  │      CELERY WORKERS           │  │    │  │                               │  │
│  │      (Background processes)   │  │    │  │  Purpose: NetBox Cache        │  │
│  │                               │  │    │  └───────────────────────────────┘  │
│  │  Purpose: Async Job Execution │  │    │                                     │
│  │  - Network polling (SNMP)     │  │    └─────────────────────────────────────┘
│  │  - Workflow execution         │  │
│  │  - Metric collection          │  │
│  │  - Baseline calculation       │  │
│  │  - Anomaly detection          │  │
│  │  - Notifications              │  │
│  └───────────────────────────────┘  │
│              │                      │
│  ┌───────────────────────────────┐  │
│  │      CELERY BEAT              │  │
│  │      (Scheduler)              │  │
│  │                               │  │
│  │  Purpose: Job Scheduling      │  │
│  │  - Trigger polling jobs       │  │
│  │  - Trigger baseline updates   │  │
│  │  - Trigger cleanup jobs       │  │
│  └───────────────────────────────┘  │
│              │                      │
│  ┌───────────────────────────────┐  │
│  │      POSTGRESQL               │  │
│  │      Port: 5432               │  │
│  │                               │  │
│  │  Purpose: OpsConductor Data   │  │
│  │  - Time-series metrics        │  │
│  │  - Baseline profiles          │  │
│  │  - Anomaly records            │  │
│  │  - Credentials (encrypted)    │  │
│  │  - Job history                │  │
│  │  - User accounts              │  │
│  │  - System settings            │  │
│  └───────────────────────────────┘  │
│              │                      │
│  ┌───────────────────────────────┐  │
│  │      REDIS                    │  │
│  │      Port: 6379               │  │
│  │                               │  │
│  │  Purpose: Message Broker      │  │
│  │  - Celery task queue          │  │
│  │  - API response cache         │  │
│  │  - Session storage            │  │
│  │  - Real-time pub/sub          │  │
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

---

## Communication Flows

### Flow 1: User Views Device List

```
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ User │───▶│ Frontend │───▶│  FastAPI   │───▶│  NetBox  │───▶│ NetBox   │
│      │    │ :3000    │    │  :5000   │    │ Service  │    │  :8000   │
└──────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   ▲                                                              │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
                        Device list JSON response
```

### Flow 2: User Views Optical Metrics

```
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ User │───▶│ Frontend │───▶│  FastAPI   │───▶│ Metrics  │───▶│PostgreSQL│
│      │    │ :3000    │    │  :5000   │    │ Service  │    │  :5432   │
└──────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   ▲                                                              │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
                     Metrics + baseline JSON response
```

### Flow 3: Scheduled Polling Job

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Celery  │───▶│  Redis   │───▶│  Celery  │───▶│ Network  │
│   Beat   │    │  Queue   │    │  Worker  │    │ Devices  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │               │
                                     │    SNMP/SSH   │
                                     │◀──────────────┘
                                     │
                                     ▼
                               ┌──────────┐
                               │PostgreSQL│
                               │ (metrics)│
                               └──────────┘
```

### Flow 4: Anomaly Detection

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Celery  │───▶│ Anomaly  │───▶│ Baseline │───▶│PostgreSQL│
│  Worker  │    │ Detector │    │  Lookup  │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │                               │
                     │ If anomaly detected           │
                     ▼                               │
               ┌──────────┐                          │
               │Notification                         │
               │ Service  │                          │
               └──────────┘                          │
                     │                               │
                     ▼                               │
               ┌──────────┐    Store anomaly         │
               │  Email/  │◀─────────────────────────┘
               │ Webhook  │
               └──────────┘
```

---

## Option 2: Recommended Production (3+ Servers)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   NETWORK                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   SERVER 1      │  │   SERVER 2      │  │   SERVER 3      │  │   SERVER 4      │
│   APPLICATION   │  │   WORKERS       │  │   DATA          │  │   NETBOX        │
│                 │  │                 │  │                 │  │                 │
│ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │
│ │  Frontend   │ │  │ │   Celery    │ │  │ │ PostgreSQL  │ │  │ │   NetBox    │ │
│ │  (Nginx)    │ │  │ │   Workers   │ │  │ │  Primary    │ │  │ │   Stack     │ │
│ └─────────────┘ │  │ │  (4-8)      │ │  │ └─────────────┘ │  │ └─────────────┘ │
│ ┌─────────────┐ │  │ └─────────────┘ │  │ ┌─────────────┐ │  │                 │
│ │   FastAPI     │ │  │ ┌─────────────┐ │  │ │ PostgreSQL  │ │  │  Purpose:       │
│ │   API       │ │  │ │   Celery    │ │  │ │  Replica    │ │  │  - Inventory    │
│ │  (Gunicorn) │ │  │ │   Beat      │ │  │ └─────────────┘ │  │  - IPAM         │
│ └─────────────┘ │  │ └─────────────┘ │  │ ┌─────────────┐ │  │  - Topology     │
│                 │  │                 │  │ │    Redis    │ │  │                 │
│  Purpose:       │  │  Purpose:       │  │ │   Cluster   │ │  │                 │
│  - Serve UI     │  │  - Polling      │  │ └─────────────┘ │  │                 │
│  - Handle API   │  │  - Workflows    │  │                 │  │                 │
│  - Auth         │  │  - Analysis     │  │  Purpose:       │  │                 │
│                 │  │  - Notifications│  │  - Data store   │  │                 │
│                 │  │                 │  │  - HA/Failover  │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Option 3: Docker Compose Deployment

```yaml
# docker-compose.yml structure
version: '3.8'

services:
  # ═══════════════════════════════════════════════════════════════
  # FRONTEND - User Interface
  # ═══════════════════════════════════════════════════════════════
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    # Purpose: Serve React application via Nginx
    # Responsibility: All user-facing UI

  # ═══════════════════════════════════════════════════════════════
  # BACKEND API - REST API & Orchestration
  # ═══════════════════════════════════════════════════════════════
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - NETBOX_URL=http://netbox:8000
    # Purpose: Handle all API requests
    # Responsibility: Auth, routing, service coordination

  # ═══════════════════════════════════════════════════════════════
  # CELERY WORKERS - Background Job Processing
  # ═══════════════════════════════════════════════════════════════
  celery-polling:
    build: ./backend
    command: celery -A celery_app worker -Q polling -c 4
    depends_on:
      - postgres
      - redis
    # Purpose: Network device polling
    # Responsibility: SNMP queries, availability checks

  celery-workflows:
    build: ./backend
    command: celery -A celery_app worker -Q workflows -c 2
    depends_on:
      - postgres
      - redis
    # Purpose: Workflow execution
    # Responsibility: Multi-step automation tasks

  celery-analysis:
    build: ./backend
    command: celery -A celery_app worker -Q analysis -c 2
    depends_on:
      - postgres
      - redis
    # Purpose: Data analysis
    # Responsibility: Baseline calculation, anomaly detection

  celery-beat:
    build: ./backend
    command: celery -A celery_app beat
    depends_on:
      - redis
    # Purpose: Job scheduling
    # Responsibility: Trigger periodic tasks

  # ═══════════════════════════════════════════════════════════════
  # DATA SERVICES
  # ═══════════════════════════════════════════════════════════════
  postgres:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # Purpose: Primary data store
    # Responsibility: All persistent data

  redis:
    image: redis:7-alpine
    # Purpose: Message broker & cache
    # Responsibility: Task queue, caching, sessions

  # ═══════════════════════════════════════════════════════════════
  # NETBOX (Separate stack, shown for reference)
  # ═══════════════════════════════════════════════════════════════
  # netbox:
  #   image: netboxcommunity/netbox
  #   ports:
  #     - "8000:8080"
  #   # Purpose: Device inventory
  #   # Responsibility: Source of truth for devices
```

---

## Component Responsibilities Matrix

| Component | Purpose | Responsibilities | Stateful? | Scalable? |
|-----------|---------|------------------|-----------|-----------|
| **Frontend** | User Interface | Dashboard, device views, workflow builder, settings UI | No | Yes (CDN) |
| **FastAPI API** | API Gateway | REST endpoints, auth, request routing, NetBox proxy | No | Yes (horizontal) |
| **Celery Workers** | Job Execution | Polling, workflows, analysis, notifications | No | Yes (add workers) |
| **Celery Beat** | Scheduler | Trigger periodic jobs on schedule | Yes (single) | No (single instance) |
| **PostgreSQL** | Data Store | Metrics, baselines, anomalies, credentials, config | Yes | Yes (replicas) |
| **Redis** | Broker/Cache | Task queue, API cache, sessions, pub/sub | Yes | Yes (cluster) |
| **NetBox** | Inventory | Device records, IPs, sites, topology | Yes | Yes (separate) |

---

## Detailed Component Breakdown

### 1. FRONTEND (React/Vite)

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                     Port: 3000 (dev) / 80 (prod)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Provide the user interface for all operations         │
│                                                                  │
│  RESPONSIBILITIES:                                               │
│  ├─ Render dashboards and visualizations                        │
│  ├─ Display device inventory (from NetBox)                      │
│  ├─ Show performance metrics and charts                         │
│  ├─ Display health scores and anomalies                         │
│  ├─ Workflow builder interface                                  │
│  ├─ Credential management UI                                    │
│  ├─ User authentication flows                                   │
│  └─ System settings and configuration                           │
│                                                                  │
│  COMMUNICATES WITH:                                              │
│  └─ FastAPI API (HTTP REST calls)                                 │
│                                                                  │
│  DOES NOT:                                                       │
│  ├─ Access database directly                                    │
│  ├─ Access NetBox directly                                      │
│  └─ Execute any backend logic                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. FASTAPI BACKEND (API Server)

```
┌─────────────────────────────────────────────────────────────────┐
│                       FASTAPI BACKEND                              │
│                         Port: 5000                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Central API gateway and service orchestrator          │
│                                                                  │
│  RESPONSIBILITIES:                                               │
│  ├─ REST API Endpoints                                          │
│  │   ├─ /api/auth/*       - Login, logout, tokens               │
│  │   ├─ /api/netbox/*     - Proxy to NetBox API                 │
│  │   ├─ /api/metrics/*    - Query metrics from DB               │
│  │   ├─ /api/health/*     - Query health scores                 │
│  │   ├─ /api/anomalies/*  - Query/manage anomalies              │
│  │   ├─ /api/workflows/*  - Workflow CRUD and execution         │
│  │   ├─ /api/credentials/*- Credential vault operations         │
│  │   └─ /api/jobs/*       - Job management                      │
│  │                                                               │
│  ├─ Authentication & Authorization                              │
│  │   ├─ JWT token validation                                    │
│  │   ├─ Role-based access control                               │
│  │   └─ Session management                                      │
│  │                                                               │
│  ├─ Service Coordination                                        │
│  │   ├─ Call appropriate services for each request              │
│  │   ├─ Queue async jobs to Celery                              │
│  │   └─ Aggregate data from multiple sources                    │
│  │                                                               │
│  └─ NetBox API Proxy                                            │
│      ├─ Forward requests to NetBox                              │
│      ├─ Transform responses for frontend                        │
│      └─ Cache frequently accessed data                          │
│                                                                  │
│  COMMUNICATES WITH:                                              │
│  ├─ PostgreSQL (direct DB queries)                              │
│  ├─ Redis (caching, session store)                              │
│  ├─ NetBox (HTTP API calls)                                     │
│  └─ Celery (queue async tasks)                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. CELERY WORKERS (Background Processing)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CELERY WORKERS                              │
│                    (Multiple processes)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Execute long-running and scheduled tasks              │
│                                                                  │
│  WORKER TYPES (by queue):                                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  POLLING WORKERS (Queue: polling)                        │    │
│  │  ├─ SNMP polling for metrics                            │    │
│  │  ├─ Availability checks (ping)                          │    │
│  │  ├─ SSH CLI data collection                             │    │
│  │  └─ Optical power readings                              │    │
│  │  Frequency: Every 1-5 minutes                           │    │
│  │  Workers: 2-4                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  WORKFLOW WORKERS (Queue: workflows)                     │    │
│  │  ├─ Execute multi-step workflows                        │    │
│  │  ├─ Config backup jobs                                  │    │
│  │  ├─ Bulk device operations                              │    │
│  │  └─ Report generation                                   │    │
│  │  Frequency: On-demand / scheduled                       │    │
│  │  Workers: 2-4                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ANALYSIS WORKERS (Queue: analysis)                      │    │
│  │  ├─ Baseline calculation (daily)                        │    │
│  │  ├─ Anomaly detection (after each poll)                 │    │
│  │  ├─ Health score calculation (hourly)                   │    │
│  │  ├─ Metric aggregation (hourly/daily)                   │    │
│  │  └─ Correlation discovery (weekly)                      │    │
│  │  Frequency: Varies                                      │    │
│  │  Workers: 1-2                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  NOTIFICATION WORKERS (Queue: notifications)             │    │
│  │  ├─ Send email alerts                                   │    │
│  │  ├─ Send webhook notifications                          │    │
│  │  ├─ Send SMS (if configured)                            │    │
│  │  └─ Log notifications                                   │    │
│  │  Frequency: On-demand (triggered by anomalies)          │    │
│  │  Workers: 1-2                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  COMMUNICATES WITH:                                              │
│  ├─ Redis (receive tasks from queue)                            │
│  ├─ PostgreSQL (read/write data)                                │
│  ├─ Network Devices (SNMP, SSH, ICMP)                           │
│  ├─ NetBox (API calls for device info)                          │
│  └─ External services (email, webhooks)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4. CELERY BEAT (Scheduler)

```
┌─────────────────────────────────────────────────────────────────┐
│                       CELERY BEAT                                │
│                    (Single instance)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Schedule periodic tasks                               │
│                                                                  │
│  RESPONSIBILITIES:                                               │
│  ├─ Trigger polling jobs on schedule                            │
│  │   └─ "Every 5 minutes, poll all switches"                    │
│  ├─ Trigger baseline recalculation                              │
│  │   └─ "Every day at 2am, recalculate baselines"               │
│  ├─ Trigger aggregation jobs                                    │
│  │   └─ "Every hour, aggregate metrics"                         │
│  ├─ Trigger cleanup jobs                                        │
│  │   └─ "Every week, delete old partitions"                     │
│  └─ Trigger health score updates                                │
│      └─ "Every hour, recalculate health scores"                 │
│                                                                  │
│  IMPORTANT: Only ONE instance should run                        │
│  (to avoid duplicate scheduled tasks)                           │
│                                                                  │
│  COMMUNICATES WITH:                                              │
│  └─ Redis (push tasks to queue)                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5. POSTGRESQL (Data Store)

```
┌─────────────────────────────────────────────────────────────────┐
│                       POSTGRESQL                                 │
│                        Port: 5432                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Persistent data storage for OpsConductor              │
│                                                                  │
│  DATA STORED:                                                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  TIME-SERIES DATA (High write volume)                    │    │
│  │  ├─ optical_metrics      - TX/RX power readings         │    │
│  │  ├─ interface_metrics    - Traffic, errors              │    │
│  │  ├─ path_metrics         - Latency, packet loss         │    │
│  │  ├─ availability_metrics - Up/down status               │    │
│  │  └─ health_scores        - Calculated health            │    │
│  │  Partitioned by time for performance                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ANALYSIS DATA                                           │    │
│  │  ├─ metric_baselines     - Statistical baselines        │    │
│  │  ├─ anomaly_events       - Detected anomalies           │    │
│  │  ├─ metric_correlations  - Discovered relationships     │    │
│  │  └─ metrics_daily        - Aggregated daily stats       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  CONFIGURATION DATA (Low write volume)                   │    │
│  │  ├─ credentials          - Encrypted credentials        │    │
│  │  ├─ device_credentials   - Device-credential mapping    │    │
│  │  ├─ users                - User accounts                │    │
│  │  ├─ roles                - RBAC roles                   │    │
│  │  ├─ system_settings      - App configuration            │    │
│  │  ├─ workflows            - Workflow definitions         │    │
│  │  └─ notification_*       - Notification config          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  JOB HISTORY                                             │    │
│  │  ├─ poll_history         - Polling job results          │    │
│  │  ├─ workflow_executions  - Workflow run history         │    │
│  │  └─ job_audit_events     - Audit trail                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ACCESSED BY:                                                    │
│  ├─ FastAPI Backend (read/write)                                  │
│  └─ Celery Workers (read/write)                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6. REDIS (Message Broker & Cache)

```
┌─────────────────────────────────────────────────────────────────┐
│                          REDIS                                   │
│                        Port: 6379                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Fast in-memory data store for messaging and caching   │
│                                                                  │
│  RESPONSIBILITIES:                                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  CELERY MESSAGE BROKER                                   │    │
│  │  ├─ Task queues (polling, workflows, analysis, notify)  │    │
│  │  ├─ Task results (temporary)                            │    │
│  │  └─ Worker coordination                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  API CACHE                                               │    │
│  │  ├─ NetBox device list cache (TTL: 5 min)               │    │
│  │  ├─ NetBox site list cache (TTL: 1 hour)                │    │
│  │  ├─ Health score cache (TTL: 5 min)                     │    │
│  │  └─ Aggregated metrics cache (TTL: 1 hour)              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  SESSION STORE                                           │    │
│  │  ├─ User sessions                                       │    │
│  │  └─ JWT token blacklist                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  REAL-TIME PUB/SUB (Future)                              │    │
│  │  ├─ Live metric updates                                 │    │
│  │  └─ Alert notifications                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ACCESSED BY:                                                    │
│  ├─ FastAPI Backend (cache, sessions)                             │
│  ├─ Celery Workers (task queue)                                 │
│  └─ Celery Beat (task queue)                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7. NETBOX (External - Device Inventory)

```
┌─────────────────────────────────────────────────────────────────┐
│                         NETBOX                                   │
│                        Port: 8000                                │
│                   (Separate server/stack)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PURPOSE: Single source of truth for device inventory           │
│                                                                  │
│  RESPONSIBILITIES:                                               │
│  ├─ Device Management                                           │
│  │   ├─ Device records (name, type, serial, status)            │
│  │   ├─ Device types and manufacturers                         │
│  │   ├─ Interface templates                                    │
│  │   └─ Module bay templates                                   │
│  │                                                               │
│  ├─ IPAM (IP Address Management)                                │
│  │   ├─ IP addresses and assignments                           │
│  │   ├─ IP prefixes (subnets)                                  │
│  │   ├─ IP ranges                                              │
│  │   └─ VRFs and VLANs                                         │
│  │                                                               │
│  ├─ Site/Location Management                                    │
│  │   ├─ Sites (physical locations)                             │
│  │   ├─ Racks and rack positions                               │
│  │   └─ Locations within sites                                 │
│  │                                                               │
│  └─ Connectivity                                                │
│      ├─ Cables and connections                                 │
│      ├─ Interface assignments                                  │
│      └─ Circuit tracking                                       │
│                                                                  │
│  ACCESSED BY:                                                    │
│  ├─ OpsConductor FastAPI (API proxy)                              │
│  ├─ OpsConductor Celery (device lookups)                        │
│  └─ Users directly (NetBox UI)                                  │
│                                                                  │
│  DOES NOT STORE:                                                 │
│  ├─ Performance metrics (OpsConductor does this)               │
│  ├─ Historical data (OpsConductor does this)                   │
│  └─ Credentials (OpsConductor does this)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Network Ports Summary

| Component | Port | Protocol | Direction | Purpose |
|-----------|------|----------|-----------|---------|
| Frontend | 3000 | HTTP | Inbound | User access |
| FastAPI API | 5000 | HTTP | Inbound | API requests |
| PostgreSQL | 5432 | TCP | Internal | Database |
| Redis | 6379 | TCP | Internal | Message broker |
| NetBox | 8000 | HTTP | Internal | Inventory API |
| Network Devices | 161 | UDP | Outbound | SNMP polling |
| Network Devices | 22 | TCP | Outbound | SSH access |
| Network Devices | - | ICMP | Outbound | Ping checks |

---

## Hardware Recommendations

### Minimum (Development/Small)
- **Server 1 (OpsConductor)**: 4 CPU, 8GB RAM, 100GB SSD
- **Server 2 (NetBox)**: 2 CPU, 4GB RAM, 50GB SSD

### Recommended (Production)
- **Server 1 (Application)**: 4 CPU, 16GB RAM, 100GB SSD
- **Server 2 (Workers)**: 8 CPU, 16GB RAM, 50GB SSD
- **Server 3 (Data)**: 4 CPU, 32GB RAM, 500GB SSD (NVMe)
- **Server 4 (NetBox)**: 4 CPU, 8GB RAM, 100GB SSD

### Large Scale
- **Application**: 2x servers behind load balancer
- **Workers**: 4x servers (dedicated queues)
- **Data**: PostgreSQL cluster + Redis cluster
- **NetBox**: HA deployment

---

## Summary Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              OPSCONDUCTOR SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   USERS                                                                              │
│     │                                                                                │
│     │ HTTPS                                                                          │
│     ▼                                                                                │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                           PRESENTATION LAYER                                 │   │
│   │                                                                              │   │
│   │   ┌─────────────┐                        ┌─────────────┐                    │   │
│   │   │  FRONTEND   │◀──────HTTP API────────▶│   FASTAPI   │                    │   │
│   │   │  (React)    │                        │   BACKEND   │                    │   │
│   │   │             │                        │             │                    │   │
│   │   │  Dashboard  │                        │  REST API   │                    │   │
│   │   │  Inventory  │                        │  Auth       │                    │   │
│   │   │  Workflows  │                        │  Routing    │                    │   │
│   │   └─────────────┘                        └─────────────┘                    │   │
│   │                                                 │                            │   │
│   └─────────────────────────────────────────────────┼────────────────────────────┘   │
│                                                     │                                │
│   ┌─────────────────────────────────────────────────┼────────────────────────────┐   │
│   │                           PROCESSING LAYER      │                            │   │
│   │                                                 │                            │   │
│   │   ┌─────────────┐    ┌─────────────┐    ┌──────┴──────┐    ┌─────────────┐  │   │
│   │   │   CELERY    │◀───│    REDIS    │◀───│   CELERY    │───▶│   NETWORK   │  │   │
│   │   │    BEAT     │    │   (Queue)   │    │   WORKERS   │    │   DEVICES   │  │   │
│   │   │             │    │             │    │             │    │             │  │   │
│   │   │  Scheduler  │    │  Broker     │    │  Polling    │    │  SNMP/SSH   │  │   │
│   │   │             │    │  Cache      │    │  Workflows  │    │             │  │   │
│   │   │             │    │             │    │  Analysis   │    │             │  │   │
│   │   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │   │
│   │                                                 │                            │   │
│   └─────────────────────────────────────────────────┼────────────────────────────┘   │
│                                                     │                                │
│   ┌─────────────────────────────────────────────────┼────────────────────────────┐   │
│   │                             DATA LAYER          │                            │   │
│   │                                                 │                            │   │
│   │   ┌─────────────────────────────────────────────┴───────────────────────┐   │   │
│   │   │                         POSTGRESQL                                   │   │   │
│   │   │                                                                      │   │   │
│   │   │   Time-Series    Baselines    Anomalies    Credentials    Config    │   │   │
│   │   │     Metrics                                                          │   │   │
│   │   └──────────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                              │   │
│   └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────┐   │
│   │                          EXTERNAL SYSTEMS                                     │   │
│   │                                                                              │   │
│   │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │   │
│   │   │   NETBOX    │    │  CIENA MCP  │    │   EMAIL/    │                     │   │
│   │   │             │    │             │    │   WEBHOOK   │                     │   │
│   │   │  Inventory  │    │  Optical    │    │             │                     │   │
│   │   │  IPAM       │    │  Network    │    │  Alerts     │                     │   │
│   │   │  Topology   │    │  Mgmt       │    │             │                     │   │
│   │   └─────────────┘    └─────────────┘    └─────────────┘                     │   │
│   │                                                                              │   │
│   └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```
