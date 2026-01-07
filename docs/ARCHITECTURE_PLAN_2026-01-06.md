# OpsConductor Modular Architecture Plan
**Date:** January 6, 2026  
**Status:** Planning Phase

---

## Vision

A modular alert aggregation platform that collects alarms/alerts from multiple external systems and devices, normalizes them, and presents them through a unified interface. Future modules will add AI-powered triage and intelligent incident management.

---

## Core Principles

1. **Fully Independent Modules** - Each module is self-contained
2. **Strict Communication Contracts** - No direct cross-module imports
3. **Standardized Internal Networking** - Defined message formats and APIs
4. **Hub + Bus Hybrid** - Synchronous requests via hub, async events via bus

---

## MVP Alert Source Connectors (First Delivery)

| # | Connector | Protocol | Status | Notes |
|---|-----------|----------|--------|-------|
| 1 | **PRTG** | REST API | Exists | Network monitoring alerts |
| 2 | **MCP** | REST API | Exists | Media/broadcast alerts |
| 3 | **SNMP Poller** | SNMP traps + polling | Exists | Generic device monitoring |
| 4 | **Eaton UPS** | TBD | New | Power/UPS alerts |
| 5 | **Axis VAPIX** | REST API | New | Camera alerts (motion, tampering, health) |
| 6 | **Milestone VMS** | REST API / MIP | New | Video management system alerts |
| 7 | **Cradlepoint NCOS** | REST API (local) | New | Cellular router signal/failover |
| 8 | **Siklu** | REST API | New | MW radio link status/RSL |
| 9 | **Ubiquiti** | UISP API or local | New | Network device alerts |

---

## Future Modules (Phase 2+)

| Module | Description |
|--------|-------------|
| **AI Triage Engine** | Understand, correlate, prioritize alerts; suggest remediation |
| **Playwright Scraper** | Web UI screen scraping for devices without APIs |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                               │
│                    (Web UI - React Frontend)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE HUB                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Auth       │  │  Alert      │  │  Device     │  │ Notification│    │
│  │  Service    │  │  Manager    │  │  Registry   │  │  Service    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
              ┌─────────────────┐     ┌─────────────────┐
              │   EVENT BUS     │     │   API GATEWAY   │
              │  (Async Events) │     │  (Sync Requests)│
              └─────────────────┘     └─────────────────┘
                        │                       │
        ┌───────────────┼───────────────────────┼───────────────┐
        │               │                       │               │
        ▼               ▼                       ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    PRTG     │ │    MCP      │ │    SNMP     │ │   Eaton     │
│  Connector  │ │  Connector  │ │   Poller    │ │    UPS      │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │               │               │               │
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    Axis     │ │  Milestone  │ │ Cradlepoint │ │   Siklu     │
│   VAPIX     │ │    VMS      │ │    NCOS     │ │   Radio     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │
┌─────────────┐
│  Ubiquiti   │
│   UISP      │
└─────────────┘
```

---

## Module Communication Design

### Hub (Synchronous)
- Request/response pattern
- Used for: auth checks, device lookups, config retrieval
- Central routing through API gateway

### Bus (Asynchronous)  
- Publish/subscribe pattern
- Used for: alert events, status changes, notifications
- Connectors publish normalized alerts to bus
- Core subscribes and processes

### Standardized Alert Schema (Draft)
```json
{
  "id": "uuid",
  "source_system": "prtg|mcp|snmp|eaton|axis|milestone|cradlepoint|siklu|ubiquiti",
  "source_device_id": "string",
  "source_alert_id": "string",
  "device_ip": "string",
  "device_name": "string",
  "severity": "critical|major|minor|warning|info",
  "category": "network|power|video|security|infrastructure",
  "title": "string",
  "message": "string",
  "timestamp": "ISO8601",
  "received_at": "ISO8601",
  "status": "active|acknowledged|resolved",
  "raw_data": {}
}
```

---

## Next Steps

1. [ ] Design inter-module communication contracts
2. [ ] Inventory existing PRTG/MCP/SNMP code
3. [ ] Define module directory structure
4. [ ] Create connector interface/base class
5. [ ] Implement alert normalization layer
6. [ ] Build notification service

---

*Document will be updated as architecture is finalized*
