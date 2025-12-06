# Frontend (React/Vite) – OpsConductor Monitor

UI for the poller dashboard and modular Job Builder.

## Prereqs
- Node 18+
- Backend running at `http://192.168.10.50:5000` (or adjust proxy in `vite.config.js`)

## Install
```bash
npm install
```

## Run (dev, port 3000, all interfaces)
```bash
npm run dev -- --host 0.0.0.0 --port 3000
```
Vite proxy forwards API calls to the backend (see `vite.config.js`).

## Build (outputs to ../dist)
```bash
npm run build
```

## Lint
```bash
npm run lint
```

## Key entry points
- `src/main.jsx` – app bootstrap
- `src/App.jsx` – routes
- `src/pages/Poller.jsx` – poller dashboard + Job Builder modal
- `src/components/jobBuilder/` – modular Job Builder (CompleteJobBuilder, sections, actions, TargetSelectionModal, hooks)

## Notes
- Dev server listens on `0.0.0.0:3000` when run with the flags above for LAN access.
- Build artifacts go to `../dist` (gitignored).
