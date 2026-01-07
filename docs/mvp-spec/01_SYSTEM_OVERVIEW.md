# 01 - System Overview

**OpsConductor MVP - Alert Aggregation Platform**

---

## 1. Vision

OpsConductor is a **unified alert aggregation platform** that collects, normalizes, correlates, and presents alerts from multiple external monitoring systems and network devices. It provides operations teams with a single pane of glass for all infrastructure alerts.

---

## 2. Problem Statement

Modern infrastructure operations face:

1. **Alert Fragmentation** - Alerts scattered across PRTG, VMS, UPS systems, SNMP traps, etc.
2. **Alert Fatigue** - Too many alerts, no prioritization, duplicates
3. **Lack of Correlation** - Can't see that 5 camera alerts are caused by 1 switch failure
4. **No Unified View** - Must check multiple dashboards
5. **Delayed Response** - Time wasted correlating manually

---

## 3. Solution

A modular platform that:

1. **Collects** alerts from 9 external sources via connectors
2. **Normalizes** all alerts to a standard schema
3. **Correlates** related alerts using dependency relationships
4. **Suppresses** downstream alerts when root cause identified
5. **Prioritizes** alerts using ITIL-based Impact × Urgency
6. **Notifies** appropriate personnel via configurable channels
7. **Displays** unified dashboard for operations team

---

## 4. MVP Goals

| Goal | Description | Success Metric |
|------|-------------|----------------|
| **Unified View** | Single dashboard for all alerts | 100% of alerts visible in one place |
| **Real-time** | Alerts appear within seconds | < 5 second latency |
| **Normalized** | All alerts use standard schema | 100% compliance with standard |
| **Deduplicated** | No duplicate alerts shown | < 1% duplicate rate |
| **Correlated** | Related alerts grouped | Dependency suppression working |
| **Actionable** | Clear severity and priority | All alerts have severity + priority |

---

## 5. MVP Scope

### 5.1 IN Scope

| Feature | Description |
|---------|-------------|
| **9 Connectors** | PRTG, MCP, SNMP, Eaton, Axis, Milestone, Cradlepoint, Siklu, Ubiquiti |
| **Normalization** | All alerts converted to standard schema |
| **Alert Storage** | PostgreSQL with full history |
| **Deduplication** | Fingerprint-based duplicate detection |
| **Dependencies** | Device dependency graph for correlation |
| **Correlation** | Suppress downstream when upstream fails |
| **Dashboard** | Unified alert view with filtering/sorting |
| **Alert Actions** | Acknowledge, resolve, add notes |
| **Notifications** | Email + Webhook (basic) |
| **Auth** | Existing auth system (users, roles) |
| **Settings** | Connector configuration UI |

### 5.2 OUT of Scope (Future Phases)

| Feature | Phase | Reason |
|---------|-------|--------|
| AI Triage Engine | Phase 2 | Requires training data |
| Playwright Scraper | Phase 2 | Complex, low priority |
| Workflow Builder | Phase 2 | Exists but not core to MVP |
| Job Scheduler | Phase 2 | Exists but not core to MVP |
| Network Topology | Phase 2 | Nice-to-have visualization |
| Power Trends | Phase 2 | Analytics, not core alerting |
| Mobile App | Phase 3 | Desktop-first |
| SLA Tracking | Phase 2 | Requires stable alert data |
| Runbook Integration | Phase 2 | Depends on AI module |

---

## 6. Users

### 6.1 Primary Users

| Role | Description | Needs |
|------|-------------|-------|
| **NOC Operator** | Monitors alerts, first response | Real-time dashboard, clear priorities |
| **Network Engineer** | Investigates, resolves issues | Alert details, device context |
| **System Admin** | Configures connectors, dependencies | Settings UI, bulk operations |

### 6.2 User Stories

**As a NOC Operator:**
- I want to see all active alerts in one place so I don't miss anything
- I want alerts prioritized so I know what to handle first
- I want to acknowledge alerts so my team knows I'm working on it
- I want related alerts grouped so I understand the scope of an issue

**As a Network Engineer:**
- I want to see alert history for a device so I can identify patterns
- I want to see what a device depends on so I can find root cause
- I want to add notes to alerts so I can document my findings

**As a System Admin:**
- I want to configure connectors so I can add new alert sources
- I want to define dependencies so correlation works correctly
- I want to manage notification rules so the right people get alerted

---

## 7. Constraints

### 7.1 Technical Constraints

| Constraint | Details |
|------------|---------|
| **Backend** | Python 3.11+, FastAPI |
| **Frontend** | React 18+, Vite, TailwindCSS |
| **Database** | PostgreSQL 14+ |
| **Existing Code** | Must refactor, not rebuild from scratch |
| **Single Server** | Initial deployment on single VM |
| **No Cloud** | On-premise deployment only |

### 7.2 Operational Constraints

| Constraint | Details |
|------------|---------|
| **Availability** | 99% uptime target |
| **Alert Volume** | Handle 10,000+ alerts/day |
| **Retention** | 90 days alert history minimum |
| **Response Time** | < 5 seconds alert ingestion |

---

## 8. Success Criteria

MVP is complete when:

- [ ] All 9 connectors receiving alerts
- [ ] All alerts normalized to standard schema
- [ ] Deduplication working (same alert not duplicated)
- [ ] Dependencies can be defined in UI
- [ ] Correlation suppressing downstream alerts
- [ ] Dashboard showing all alerts with filtering
- [ ] Acknowledge/resolve actions working
- [ ] Email notifications sending
- [ ] System stable for 1 week with real data

---

## 9. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| API documentation unavailable for new connectors | Delays | Research early, have fallback to SNMP |
| Alert volume higher than expected | Performance | Implement pagination, archival |
| Dependency graph too complex | Usability | Start simple, expand incrementally |
| Existing code harder to refactor than expected | Delays | Time-box refactoring, rebuild if stuck |

---

## 10. Timeline (Estimated)

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 0: Foundation** | 1 week | Core module structure, alert schema, DB tables |
| **Phase 1: Existing Connectors** | 2 weeks | PRTG, MCP, SNMP, Eaton refactored |
| **Phase 2: New Connectors** | 3 weeks | Axis, Milestone, Cradlepoint, Siklu, Ubiquiti |
| **Phase 3: Correlation** | 1 week | Dependencies, dedup, suppression |
| **Phase 4: Dashboard** | 1 week | Alert UI, actions, filtering |
| **Phase 5: Notifications** | 1 week | Email, webhook delivery |
| **Phase 6: Testing** | 1 week | Integration testing, bug fixes |

**Total: ~10 weeks to MVP**

---

*Next: [02_ARCHITECTURE.md](./02_ARCHITECTURE.md)*
