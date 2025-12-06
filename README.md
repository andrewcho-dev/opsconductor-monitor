## OpsConductor Monitor

Modernized Flask + React stack for network discovery, polling, and job building.

- **Backend**: Flask API (port 5000) for scans, pollers, topology data, and settings.
- **Frontend**: React (Vite) app (port 3000) with a poller dashboard and modular Job Builder.
- **Data**: PostgreSQL (via `database.py`) for devices, poller history, and job data.

---

## Quick start

### Prereqs
- Python 3.10+
- Node 18+
- PostgreSQL reachable from the backend host

### Backend (Flask, port 5000)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py        # binds 0.0.0.0:5000
```

Environment (.env):
```
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=network_scan
PG_USER=postgres
PG_PASSWORD=postgres
```

### Frontend (React/Vite, port 3000)
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```
Build for production (outputs to `../dist`):
```bash
npm run build
```

Vite dev proxy forwards API calls to the backend at `http://192.168.10.50:5000` (see `frontend/vite.config.js`).

---

## Architecture & features
- **Poller dashboard**: start/stop/test discovery, interface, and optical pollers; view execution log.
- **Job Builder**: modular React UI for composing actions (ping/SNMP/SSH/RDP/custom), targeting, parsing, and DB writes. Lives at `/poller` via `frontend/src/pages/Poller.jsx`.
- **Scanning API**: async scans, progress polling, device CRUD, and settings management.
- **Target data**: network ranges, custom groups, and network groups fetched for target selection (see `useAvailableTargets` hook).
- **Regex testing**: built-in panel for validating parsing patterns per action.

---

## Key files
- `app.py` – Flask app wiring, CORS, static serving.
- `scan_routes.py` – async scan entrypoints and progress tracking.
- `poller_routes.py` / `poller_manager.py` – poller APIs and scheduler.
- `database.py` – PostgreSQL access helpers.
- `config.py` / `settings_routes.py` – config JSON load/save and validation endpoints.
- `frontend/` – React app (Vite) with the Job Builder components under `src/components/jobBuilder`.
- `frontend/vite.config.js` – dev server proxy to backend.

---

## Running & access
- Backend: http://localhost:5000 (or LAN IP on port 5000).
- Frontend dev: http://localhost:3000 (or LAN IP on port 3000) via `npm run dev -- --host 0.0.0.0 --port 3000`.
- Built frontend: served from `dist/` if you deploy a static host or integrate with Flask static serving.

---

## Notes
- Ensure PostgreSQL is reachable; schemas are managed via `database.py` helpers.
- CORS allows frontend origins on ports 3000/5173.
- Build artifacts live in `dist/` (ignored by git).
