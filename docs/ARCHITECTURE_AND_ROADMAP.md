# OpsConductor Monitor – Architecture & Development Roadmap

## 1  Current High-Level Architecture

### Backend  (Python / Flask – port 5000)
* REST API: scan routes, poller routes & scheduler, settings/config.
* PostgreSQL via `database.py`.
* Handles long-running scans, poller scheduling, and job execution logic.

### Frontend  (React 19 / Vite – port 3000)
* Single-page app served from `frontend/` (dev) or `dist/` (prod).
* Key pages/components
  * `src/pages/Poller.jsx` – poller dashboard & Job Builder modal.
  * Modular Job Builder under `src/components/jobBuilder/` (header, sections, actions, target modal…).
* Styling: Tailwind CSS, icons: Lucide.

### Data Flow
1. Frontend requests → Vite proxy → Flask API.
2. Flask spawns threads/sub-processes for scans; updates DB & in-memory progress.
3. Frontend polls `/progress` & poller routes or (future) consumes WebSocket updates.

---

## 2  Smart Job Builder 2.0 – Target Design

| Layer | Purpose |
|-------|---------|
| **Command Library** (`commandLibrary.json`) | Defines each action (display name, template, default params, form schema, success criteria). |
| **Parser Library** (`parserLibrary.json`) | Ready-made regex / JSONPath parsers and field maps. |
| **Target Source Library** (`targetSourceLibrary.json`) | Describes network range, custom group, uploaded file, etc. |
| Hooks (`useCommandLibrary`, `useParserLibrary`, `useTargetLibrary`) | Load libraries & expose helpers. |
| Pickers (`CommandPicker`, `ParserPicker`, `TargetPicker`) | UI modals for selecting entries from libraries. |
| **Dynamic Form Generator** | Builds parameter/target forms at runtime from schema. |
| Live Preview | Shows rendered command template with current values. |
| Templates | Save / load whole job definitions as JSON. |
| Wizard / AI helper *(stretch)* | Prompt-driven assistant suggesting actions/targets/parsers. |

---

## 3  6-Month Development Roadmap

### Sprint cadence: 2 weeks each

| Sprint | Deliverables |
|--------|--------------|
| **0 (done)** | Documentation cleanup, root & frontend README, `.gitignore`. |
| **1** | `commandLibrary.json` + `useCommandLibrary` hook (console demo). |
| **2** | `CommandPicker` modal wired into `ActionCard`. |
| **3** | Dynamic parameter form generator + live command preview. |
| **4** | `parserLibrary.json` + `ParserPicker` with sample-output tester. |
| **5** | `targetSourceLibrary.json` + dynamic `ActionTargetsSection`. |
| **6** | Job template save/load UI (JSON files under `templates/`). |
| **7–8** | Unit / integration / E2E tests, GitHub Actions CI workflow. |
| **9** | Authentication & RBAC (JWT, role-based UI). |
| **10** | Worker pool (Celery/RQ) + WebSocket push for status/logs. |
| **11** | Docker/Compose stack, image build/publish pipeline. |
| **12** | AI Wizard MVP for guided job creation. |

---

## 4  Immediate Next-Steps (Sprint 1)

1. **Scaffold command library** with `ping`, `snmp_get`, `ssh_port`, `http_get`.
2. **Create `hooks/useCommandLibrary.js`** returning `{ commands, get(id) }`.
3. **Add “Choose Command” button** in each `ActionCard` that opens `CommandPicker` and injects defaults.

These steps give a no-code experience for adding new actions and set the foundation for fully modular, intelligent job building.

---

## 5  Long-Term Enhancements
* Structured logging & centralized error handling.
* Prometheus metrics, Grafana dashboards.
* API versioning with OpenAPI/Swagger docs.
* Dark-mode theme & accessibility improvements.
* Internationalisation (i18n) if needed.
* Plugin system to load third-party command libraries.
