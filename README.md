# OpsConductor Monitor

A modular network operations platform for device discovery, monitoring, job scheduling, and optical power tracking.

## Features

- **Device Discovery** - Ping, SNMP, and SSH-based network scanning
- **Interface Monitoring** - Track port status, transceivers, and LLDP neighbors
- **Optical Power Tracking** - Time-series monitoring of TX/RX power levels
- **Job Scheduler** - Define and schedule recurring network operations
- **Job Builder** - Visual UI for composing multi-step automation jobs
- **Topology Visualization** - Network topology based on LLDP data
- **Notifications** - Apprise-based alerts via email, Slack, Teams, etc.

## Architecture

```
├── backend/                 # Flask API server
│   ├── api/                 # REST API blueprints
│   ├── config/              # Settings and logging configuration
│   ├── executors/           # SSH, SNMP, Ping executors
│   ├── migrations/          # Database schema migrations
│   ├── parsers/             # Ciena and other device parsers
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic layer
│   ├── targeting/           # Target resolution strategies
│   └── tasks/               # Celery background tasks
├── frontend/                # React (Vite) application
│   ├── src/api/             # API client modules
│   ├── src/components/      # Reusable UI components
│   ├── src/hooks/           # Custom React hooks
│   └── src/pages/           # Page components
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── config/                  # YAML configuration files
├── data/                    # Data files (gitignored)
├── logs/                    # Log files (gitignored)
└── docs/                    # Documentation
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis (for Celery)

### Backend Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python3 backend/migrations/migrate.py

# Start the server
python3 run.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

### Environment Variables

```env
# Database
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=network_scan
PG_USER=postgres
PG_PASSWORD=postgres

# Redis (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/devices` | List all devices |
| `GET /api/groups` | List device groups |
| `GET /api/job-definitions` | List job definitions |
| `GET /api/scheduler/jobs` | List scheduled jobs |
| `GET /progress` | Scan progress status |
| `POST /scan` | Start network scan |

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=backend
```

## Project Structure

### Backend Modules

- **Executors** - `SSHExecutor`, `SNMPExecutor`, `PingExecutor` for device communication
- **Parsers** - `CienaPortXcvrParser`, `CienaLldpRemoteParser`, etc. for output parsing
- **Targeting** - `StaticTargeting`, `GroupTargeting`, `NetworkRangeTargeting` for job targets
- **Services** - `JobExecutor`, `NotificationService` for business logic

### Frontend Modules

- **API Client** - Centralized `apiClient` with error handling
- **Hooks** - `useDevices`, `useGroups`, `useScanProgress` for data fetching
- **Components** - `DeviceTable`, `JobBuilder`, `ScanProgress` UI components

## Documentation

- `docs/ARCHITECTURE_AND_ROADMAP.md` - System architecture and roadmap
- `docs/REFACTORING_PLAN.md` - Modularization progress
- `docs/MIGRATION_PLAN.md` - Migration from monolithic to modular
- `docs/REMEDIATION_PLAN.md` - Code quality improvements

## License

Proprietary - Internal Use Only
