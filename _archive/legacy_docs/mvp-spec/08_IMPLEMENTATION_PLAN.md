# 08 - Implementation Plan

**OpsConductor MVP - Phased Implementation Strategy**

---

## 1. Implementation Approach

### 1.1 Strategy: Refactor, Don't Rebuild

We will **repurpose existing code** rather than starting from scratch:

- Core infrastructure (FastAPI, React, DB, auth) stays
- Existing services refactored into connector modules
- Unused features pruned
- New features built on existing patterns

### 1.2 Guiding Principles

1. **Incremental delivery** - Each phase produces working software
2. **Test as we go** - No phase complete without tests
3. **One connector at a time** - Fully complete before moving to next
4. **Frontend follows backend** - UI built after API stable

---

## 2. What to Keep, Refactor, Prune

### 2.1 KEEP (Use As-Is)

| Component | Files | Notes |
|-----------|-------|-------|
| FastAPI App | `main.py` | Entry point |
| Auth System | `auth_service.py`, `identity.py` | Working auth |
| Credential Store | `credential_service.py`, `credentials.py` | Encrypted vault |
| DB Utilities | `utils/db.py` | Query helpers |
| HTTP Clients | `utils/http.py` | NetBox, PRTG clients |
| Frontend Shell | `App.jsx`, layout components | React structure |
| User Management | Users, roles, sessions | Complete |

### 2.2 REFACTOR (Adapt to New Architecture)

| Current | Target | Changes |
|---------|--------|---------|
| `prtg_service.py` | `connectors/prtg/connector.py` | Extract connector logic, add normalizer |
| `ciena_mcp_service.py` | `connectors/mcp/connector.py` | Extract connector logic, add normalizer |
| `snmp_trap_receiver.py` | `connectors/snmp/trap_receiver.py` | Add OID mapping lookup, normalizer |
| `async_snmp_poller.py` | `connectors/snmp/poller.py` | Threshold-based alerting |
| `eaton_snmp_service.py` | `connectors/eaton/connector.py` | Add normalizer, alert generation |
| `alert_service.py` | `core/alert_manager.py` | New schema, dedup, correlation |
| `notification_service.py` | `core/notification_service.py` | Expand channels, rules |

### 2.3 PRUNE (Remove/Disable)

| Component | Files | Reason |
|-----------|-------|--------|
| Workflow Builder | `workflow_engine.py`, `node_executors/` | Out of MVP scope |
| Job Scheduler | `job_*.py`, `scheduler_service.py` | Out of MVP scope |
| Device Importer | `device_importer_service.py` | Nice-to-have |
| PRTG NetBox Importer | `prtg_netbox_importer.py` | Out of scope |
| Template Service | `template_service.py` | Workflow-related |
| Automation Router | `routers/automation.py` | Workflow-related |
| Frontend: Workflow Pages | `pages/workflows/` | Hide in nav |
| Frontend: Topology | If exists | Out of scope |

### 2.4 BUILD NEW

| Component | Priority | Dependencies |
|-----------|----------|--------------|
| `core/models.py` | HIGH | None |
| `core/alert_manager.py` | HIGH | models |
| `core/dependency_registry.py` | HIGH | models |
| `core/event_bus.py` | HIGH | None |
| `connectors/base.py` | HIGH | models |
| `connectors/*/normalizer.py` | HIGH | base |
| New connectors (5) | MEDIUM | base |
| `routers/alerts.py` | HIGH | alert_manager |
| `routers/dependencies.py` | HIGH | dependency_registry |
| `routers/connectors.py` | HIGH | connector registry |
| Alert Dashboard UI | HIGH | API |
| Dependencies UI | MEDIUM | API |
| Connectors UI | MEDIUM | API |

---

## 3. Phase Breakdown

### Phase 0: Foundation (Week 1)

**Goal:** Establish core architecture, create new tables, set up module structure

**Tasks:**

| # | Task | Est. Hours |
|---|------|------------|
| 0.1 | Create `core/` module structure | 2 |
| 0.2 | Implement `core/models.py` (dataclasses, enums) | 4 |
| 0.3 | Create database migration for new tables | 4 |
| 0.4 | Implement `core/event_bus.py` | 2 |
| 0.5 | Create `connectors/base.py` (interfaces) | 4 |
| 0.6 | Implement `core/alert_manager.py` (basic) | 8 |
| 0.7 | Implement `core/dependency_registry.py` | 4 |
| 0.8 | Create `routers/alerts.py` (basic CRUD) | 4 |
| 0.9 | Create `routers/dependencies.py` | 4 |
| 0.10 | Unit tests for core modules | 4 |

**Deliverables:**
- [ ] Core module structure in place
- [ ] Database tables created
- [ ] Alert CRUD API working
- [ ] Dependency CRUD API working

---

### Phase 1: Existing Connectors (Weeks 2-3)

**Goal:** Refactor existing services into connector architecture

**Week 2: PRTG + MCP**

| # | Task | Est. Hours |
|---|------|------------|
| 1.1 | Refactor `prtg_service.py` → `connectors/prtg/` | 8 |
| 1.2 | Create `PRTGNormalizer` | 4 |
| 1.3 | Wire PRTG webhook to alert_manager | 4 |
| 1.4 | Refactor `ciena_mcp_service.py` → `connectors/mcp/` | 8 |
| 1.5 | Create `MCPNormalizer` | 4 |
| 1.6 | Wire MCP polling to alert_manager | 4 |
| 1.7 | Integration tests | 4 |

**Week 3: SNMP + Eaton**

| # | Task | Est. Hours |
|---|------|------------|
| 1.8 | Refactor `snmp_trap_receiver.py` → `connectors/snmp/` | 8 |
| 1.9 | Implement OID mapping lookup | 4 |
| 1.10 | Create `SNMPNormalizer` | 4 |
| 1.11 | Seed OID mappings table | 4 |
| 1.12 | Refactor `eaton_snmp_service.py` → `connectors/eaton/` | 6 |
| 1.13 | Create `EatonNormalizer` | 4 |
| 1.14 | Integration tests | 4 |

**Deliverables:**
- [ ] PRTG connector receiving/normalizing alerts
- [ ] MCP connector polling/normalizing alerts
- [ ] SNMP trap receiver with OID mapping
- [ ] Eaton UPS connector generating alerts
- [ ] All 4 connectors storing to unified alerts table

---

### Phase 2: New Connectors (Weeks 4-6)

**Goal:** Implement 5 new connectors

**Week 4: Axis + Milestone**

| # | Task | Est. Hours |
|---|------|------------|
| 2.1 | Research Axis VAPIX API | 4 |
| 2.2 | Implement `connectors/axis/connector.py` | 8 |
| 2.3 | Implement `connectors/axis/normalizer.py` | 4 |
| 2.4 | Research Milestone API | 4 |
| 2.5 | Implement `connectors/milestone/connector.py` | 8 |
| 2.6 | Implement `connectors/milestone/normalizer.py` | 4 |
| 2.7 | Integration tests | 4 |

**Week 5: Cradlepoint + Siklu**

| # | Task | Est. Hours |
|---|------|------------|
| 2.8 | Research Cradlepoint NCOS API | 4 |
| 2.9 | Implement `connectors/cradlepoint/connector.py` | 8 |
| 2.10 | Implement thresholds-based alerting | 4 |
| 2.11 | Research Siklu API | 4 |
| 2.12 | Implement `connectors/siklu/connector.py` | 8 |
| 2.13 | Implement `connectors/siklu/normalizer.py` | 4 |
| 2.14 | Integration tests | 4 |

**Week 6: Ubiquiti + Connector UI**

| # | Task | Est. Hours |
|---|------|------------|
| 2.15 | Research UISP API | 4 |
| 2.16 | Implement `connectors/ubiquiti/connector.py` | 8 |
| 2.17 | Implement `connectors/ubiquiti/normalizer.py` | 4 |
| 2.18 | Create `routers/connectors.py` | 4 |
| 2.19 | Connector management API | 4 |
| 2.20 | Integration tests for all 9 connectors | 8 |

**Deliverables:**
- [ ] All 9 connectors implemented
- [ ] Connector configuration API
- [ ] All connectors tested with real devices

---

### Phase 3: Correlation & Deduplication (Week 7)

**Goal:** Implement intelligent alert processing

| # | Task | Est. Hours |
|---|------|------------|
| 3.1 | Implement fingerprint generation | 4 |
| 3.2 | Implement deduplication in alert_manager | 8 |
| 3.3 | Implement dependency lookup | 4 |
| 3.4 | Implement correlation logic | 8 |
| 3.5 | Implement suppression | 4 |
| 3.6 | Implement auto-resolve on clear | 4 |
| 3.7 | Unit tests for correlation | 4 |
| 3.8 | Integration tests | 4 |

**Deliverables:**
- [ ] Duplicate alerts merged (occurrence_count incremented)
- [ ] Downstream alerts suppressed when upstream fails
- [ ] Clear events auto-resolve alerts

---

### Phase 4: Alert Dashboard UI (Week 8)

**Goal:** Build primary user interface

| # | Task | Est. Hours |
|---|------|------------|
| 4.1 | Create `hooks/useAlerts.js` | 4 |
| 4.2 | Create `AlertStats` component | 2 |
| 4.3 | Create `AlertFilters` component | 4 |
| 4.4 | Create `AlertTable` component | 6 |
| 4.5 | Create `AlertDashboard` page | 4 |
| 4.6 | Create `AlertDetailPage` | 6 |
| 4.7 | Implement acknowledge/resolve actions | 4 |
| 4.8 | Implement WebSocket real-time updates | 6 |
| 4.9 | Update navigation/sidebar | 2 |
| 4.10 | UI polish and testing | 4 |

**Deliverables:**
- [ ] Alert dashboard with filtering/sorting
- [ ] Alert detail page with history
- [ ] Real-time updates via WebSocket
- [ ] Acknowledge/resolve actions working

---

### Phase 5: Dependencies & Notifications UI (Week 9)

**Goal:** Complete remaining UI and notification service

| # | Task | Est. Hours |
|---|------|------------|
| 5.1 | Create `DependenciesPage` | 6 |
| 5.2 | Create `DependencyEditor` | 6 |
| 5.3 | Bulk dependency import | 4 |
| 5.4 | Create `ConnectorsPage` | 6 |
| 5.5 | Create connector config forms | 8 |
| 5.6 | Expand `notification_service.py` | 8 |
| 5.7 | Create notification rules UI | 6 |
| 5.8 | Email notification delivery | 4 |
| 5.9 | Webhook notification delivery | 4 |

**Deliverables:**
- [ ] Dependencies editable via UI
- [ ] Connectors configurable via UI
- [ ] Email notifications working
- [ ] Webhook notifications working

---

### Phase 6: Testing & Stabilization (Week 10)

**Goal:** Integration testing, bug fixes, documentation

| # | Task | Est. Hours |
|---|------|------------|
| 6.1 | End-to-end testing | 8 |
| 6.2 | Performance testing | 4 |
| 6.3 | Bug fixes | 16 |
| 6.4 | Documentation updates | 8 |
| 6.5 | Deployment testing | 4 |

**Deliverables:**
- [ ] All features tested end-to-end
- [ ] No critical bugs
- [ ] Documentation complete
- [ ] Ready for production

---

## 4. Timeline Summary

```
Week 1:  Phase 0 - Foundation
Week 2:  Phase 1a - PRTG + MCP
Week 3:  Phase 1b - SNMP + Eaton
Week 4:  Phase 2a - Axis + Milestone
Week 5:  Phase 2b - Cradlepoint + Siklu
Week 6:  Phase 2c - Ubiquiti + Connector API
Week 7:  Phase 3 - Correlation
Week 8:  Phase 4 - Alert Dashboard
Week 9:  Phase 5 - Dependencies + Notifications
Week 10: Phase 6 - Testing & Stabilization
```

**Total: ~10 weeks to MVP**

---

## 5. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API docs unavailable for new connectors | Research early; fallback to SNMP |
| Refactoring takes longer than expected | Time-box to 150% estimate; rebuild if stuck |
| Real device testing delays | Use mock data for development; test with real later |
| Alert volume overwhelms system | Implement pagination early; optimize queries |
| Correlation logic too complex | Start simple; enhance iteratively |

---

## 6. Definition of Done

### Per Connector
- [ ] Connector class implements BaseConnector
- [ ] Normalizer outputs valid NormalizedAlert
- [ ] Configuration stored/loaded from database
- [ ] Test connection endpoint works
- [ ] Integration test with real device passes
- [ ] Alerts appearing in dashboard

### Per Phase
- [ ] All tasks completed
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] No regressions
- [ ] Documentation updated

### MVP Complete
- [ ] All 9 connectors operational
- [ ] Deduplication working
- [ ] Correlation working
- [ ] Dashboard showing real-time alerts
- [ ] Acknowledge/resolve working
- [ ] Notifications sending
- [ ] System stable for 1 week

---

## 7. Dependencies Between Phases

```
Phase 0 (Foundation)
    │
    ├──► Phase 1 (Existing Connectors)
    │         │
    │         └──► Phase 2 (New Connectors)
    │                   │
    └──► Phase 3 (Correlation) ◄───┘
              │
              └──► Phase 4 (Dashboard)
                        │
                        └──► Phase 5 (Dependencies/Notifications)
                                  │
                                  └──► Phase 6 (Testing)
```

---

*Next: [09_MIGRATION_GUIDE.md](./09_MIGRATION_GUIDE.md)*
