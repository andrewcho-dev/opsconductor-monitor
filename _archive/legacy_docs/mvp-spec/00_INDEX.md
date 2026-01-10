# OpsConductor MVP Specification

**Version:** 1.0  
**Date:** January 6, 2026  
**Status:** Planning

---

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 01 | [System Overview](./01_SYSTEM_OVERVIEW.md) | Vision, goals, scope, constraints |
| 02 | [Architecture](./02_ARCHITECTURE.md) | Layers, modules, communication patterns |
| 03 | [Data Models](./03_DATA_MODELS.md) | Database schema, entity relationships |
| 04 | [Alert Standard](../standards/ALERT_CLASSIFICATION_STANDARD.md) | Classification taxonomy (already defined) |
| 05 | [API Specification](./05_API_SPECIFICATION.md) | REST endpoints, request/response formats |
| 06 | [Connector Specifications](./06_CONNECTORS.md) | All 9 connector implementations |
| 07 | [Frontend Modules](./07_FRONTEND.md) | UI components, pages, workflows |
| 08 | [Implementation Plan](./08_IMPLEMENTATION_PLAN.md) | Phases, milestones, what to keep/prune |
| 09 | [Migration Guide](./09_MIGRATION_GUIDE.md) | Steps to refactor existing code |

---

## Quick Reference

### MVP Scope

**IN Scope:**
- Alert aggregation from 9 sources
- Normalization to standard schema
- Deduplication and correlation
- Dependency-based suppression
- Unified alert dashboard
- Basic notification (email/webhook)

**OUT of Scope (Phase 2+):**
- AI Triage Engine
- Playwright Web Scraper
- Workflow Builder
- Job Scheduler
- Network Topology Visualization
- Power Trends Dashboard

### Alert Sources (9 Connectors)

| # | Connector | Status |
|---|-----------|--------|
| 1 | PRTG | Refactor existing |
| 2 | MCP (Ciena) | Refactor existing |
| 3 | SNMP (Traps + Polling) | Refactor existing |
| 4 | Eaton UPS | Refactor existing |
| 5 | Axis VAPIX | Build new |
| 6 | Milestone VMS | Build new |
| 7 | Cradlepoint NCOS | Build new |
| 8 | Siklu | Build new |
| 9 | Ubiquiti UISP | Build new |

### Key Decisions

| Decision | Choice |
|----------|--------|
| Severity Levels | RFC 5424: critical, major, minor, warning, info, clear |
| Categories | 10: network, power, video, wireless, security, environment, compute, storage, application, unknown |
| Priority | ITIL: P1-P5 (Impact × Urgency) |
| Dependencies | Stored in OpsConductor (not NetBox) |
| Device Registry | Sync from NetBox, link table in OpsConductor |
| Communication | Hub (sync) + Bus (async events) hybrid |

---

## Document Status

| Document | Status |
|----------|--------|
| 00_INDEX | ✅ Complete |
| 01_SYSTEM_OVERVIEW | ✅ Complete |
| 02_ARCHITECTURE | ✅ Complete |
| 03_DATA_MODELS | ✅ Complete |
| 05_API_SPECIFICATION | ✅ Complete |
| 06_CONNECTORS | ✅ Complete |
| 07_FRONTEND | ✅ Complete |
| 08_IMPLEMENTATION_PLAN | ✅ Complete |
| 09_MIGRATION_GUIDE | ✅ Complete |
