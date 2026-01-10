# OpsConductor v2

A clean, modular alert monitoring platform with a database-driven addon system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React + Vite)                     │
│              Dashboard, Alerts, Addons, Targets                  │
└─────────────────────────────────────────────────────────────────┘
                              │ Socket.IO
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                   REST API + WebSocket                           │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   PostgreSQL    │ │     Redis       │ │     Celery      │
│   (Database)    │ │  (Broker/PubSub)│ │   (Workers)     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Core Design Principles

1. **Minimal** - 7 core files, not 200+
2. **Single Responsibility** - Each component does ONE thing
3. **No Duplication** - ONE implementation of each function
4. **Database-Driven** - Configuration in DB/manifests, not code
5. **Observable** - Easy to monitor and debug
6. **Scalable** - Add workers to handle more load

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

### Backend

```bash
cd backend
pip install -r requirements.txt

# Start FastAPI server
uvicorn api.main:app --host 0.0.0.0 --port 5001

# Start Celery worker (separate terminal)
celery -A tasks.celery_app worker -l info

# Start Celery beat (separate terminal)
celery -A tasks.celery_app beat -l info
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --port 3000
```

## Project Structure

```
├── backend/                    # FastAPI + Celery backend
│   ├── core/                   # Core modules (7 files)
│   │   ├── db.py              # Database access
│   │   ├── addon_registry.py  # Addon loading
│   │   ├── alert_engine.py    # Alert processing
│   │   ├── parser.py          # Data parsing
│   │   ├── poller.py          # SNMP/API/SSH polling
│   │   ├── trap_receiver.py   # SNMP trap handler
│   │   └── webhook_receiver.py # HTTP webhook handler
│   ├── api/                    # FastAPI routes
│   ├── tasks/                  # Celery tasks
│   └── addons/                 # Addon manifests (JSON)
│
├── frontend/                   # React + Vite frontend
│   └── src/
│       ├── pages/             # Page components
│       ├── components/        # Reusable components
│       └── hooks/             # Custom hooks
│
├── docs/                       # Documentation
│   ├── CLEAN_CORE_ARCHITECTURE.md
│   ├── ADDON_MANIFEST_SCHEMA.md
│   └── ...
│
└── _archive/                   # Legacy code (reference only)
```

## Addon System

Addons are **declarative JSON manifests** - no Python code required.

### Supported Methods
- `api_poll` - HTTP/REST API polling
- `snmp_poll` - SNMP GET/WALK polling
- `snmp_trap` - SNMP trap receiver
- `webhook` - HTTP webhook receiver
- `ssh` - SSH command execution

### Example Addon Manifest

```json
{
  "id": "axis",
  "name": "Axis Cameras",
  "method": "api_poll",
  "category": "video",
  "api_poll": {
    "base_url_template": "http://{host}",
    "auth_type": "digest",
    "endpoints": [
      {
        "path": "/axis-cgi/basicdeviceinfo.cgi",
        "alert_on_failure": "camera_offline"
      }
    ]
  },
  "alert_mappings": [...]
}
```

See [ADDON_MANIFEST_SCHEMA.md](docs/ADDON_MANIFEST_SCHEMA.md) for full schema.

## Documentation

- [Clean Core Architecture](docs/CLEAN_CORE_ARCHITECTURE.md) - Design principles
- [Addon Manifest Schema](docs/ADDON_MANIFEST_SCHEMA.md) - How to create addons
- [Addon System](docs/ADDON_SYSTEM.md) - Addon architecture overview

## Legacy Code

Legacy v1 code is archived in `_archive/` for reference only. Do not use.

## License

Proprietary - All rights reserved
