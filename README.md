# OpsConductor Monitor

A comprehensive network operations platform for device discovery, monitoring, workflow automation, and infrastructure management. Built with a **FastAPI** backend and React frontend, OpsConductor provides a visual workflow builder for creating complex automation tasks without code.

## Key Features

### Inventory Management
- **Device Discovery** - Ping, SNMP, SSH, and WinRM-based network scanning
- **Device Groups** - Organize devices into logical groups for targeting
- **Interface Monitoring** - Track port status, transceivers, and LLDP neighbors
- **NetBox Integration** - Sync with NetBox as source of truth for device inventory

### Visual Workflow Builder
- **Drag-and-Drop Canvas** - Build automation workflows visually with React Flow
- **17+ Node Packages** - Pre-built nodes for network, SSH, SNMP, database, notifications, and more
- **Platform-Specific Nodes** - Ciena SAOS, Axis Cameras, Windows Systems, NetBox
- **Data Mapping** - Pass data between nodes with expression-based variable resolution
- **Validation** - Real-time workflow validation with prerequisite checking

### Monitoring & Alerting
- **Dashboard** - Real-time system overview with device status
- **Optical Power Tracking** - Time-series monitoring of TX/RX power levels
- **Topology Visualization** - Network topology based on LLDP data
- **Alert Rules** - Configurable alerting with multiple notification channels
- **Job History** - Complete execution history with detailed logs

### Security & Authentication
- **Role-Based Access Control (RBAC)** - Fine-grained permissions system
- **Two-Factor Authentication** - TOTP and email-based 2FA
- **Credential Vault** - Encrypted storage for SSH, SNMP, API keys, and certificates
- **Audit Logging** - Complete audit trail for credential access

### Notifications
- **Multi-Channel** - Email, Slack, Microsoft Teams, webhooks, and more via Apprise
- **Templates** - Customizable notification templates with variable substitution
- **Alert Rules** - Trigger notifications based on conditions

## Architecture Overview

```
opsconductor/
├── backend/                    # FastAPI Server (Python)
│   ├── api/                    # REST API Routers (30 modules)
│   ├── services/               # Business Logic Layer
│   │   ├── workflow_engine.py  # Workflow execution engine
│   │   ├── auth_service.py     # Authentication & RBAC
│   │   ├── credential_service.py # Encrypted credential vault
│   │   └── node_executors/     # Workflow node implementations
│   ├── executors/              # Device Communication (SSH, SNMP, Ping, WinRM)
│   ├── repositories/           # Data Access Layer
│   ├── parsers/                # Device Output Parsers
│   ├── migrations/             # Database Schema Migrations
│   └── tasks/                  # Celery Background Tasks
│
├── frontend/                   # React Application (Vite)
│   ├── src/
│   │   ├── features/
│   │   │   └── workflow-builder/  # Visual Workflow Builder
│   │   │       ├── components/    # Canvas, Toolbar, Node Editor
│   │   │       ├── packages/      # 17 Node Packages
│   │   │       └── hooks/         # Workflow state management
│   │   ├── pages/              # Application Pages
│   │   │   ├── inventory/      # Devices, Groups
│   │   │   ├── workflows/      # Workflow List & Builder
│   │   │   ├── monitor/        # Dashboard, Topology, Alerts
│   │   │   ├── credentials/    # Credential Vault
│   │   │   └── system/         # Settings, Users, Logs
│   │   ├── components/         # Shared UI Components
│   │   └── api/                # API Client Modules
│
├── docs/                       # Documentation
│   ├── BACKEND.md              # Backend architecture & API reference
│   ├── FRONTEND.md             # Frontend architecture & components
│   ├── WORKFLOW_BUILDER.md     # Workflow builder guide
│   ├── CREDENTIALS.md          # Credential vault & authentication
│   └── API_REFERENCE.md        # Complete API documentation
│
├── config/                     # Configuration Files
├── tests/                      # Test Suite
└── systemd/                    # Systemd Service Files
```

## Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **Redis** (for Celery background tasks)

### 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd opsconductor

# Create and configure environment
cp .env.example .env
# Edit .env with your settings (see Environment Variables below)
```

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python3 backend/migrations/migrate.py

# Start the backend server (FastAPI with uvicorn)
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
# Backend runs on http://localhost:5000
# API docs available at http://localhost:5000/api/docs
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
# Frontend runs on http://localhost:3000
```

### 4. Start Background Workers (Optional)

```bash
# Start Celery worker for background tasks
celery -A celery_app worker -l info --concurrency=4

# Start Celery beat for scheduled tasks
celery -A celery_app beat -l info
```

### Quick Start Script

```bash
# Start all services at once
./start.sh

# Stop all services
./stop.sh
```

## Environment Variables

```env
# Database (PostgreSQL)
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=network_scan
PG_USER=postgres
PG_PASSWORD=your_password

# Redis (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379

# API Server (FastAPI/Uvicorn)
API_HOST=0.0.0.0
API_PORT=5000
API_RELOAD=true

# Security
SECRET_KEY=your-secret-key
CREDENTIAL_MASTER_KEY=your-encryption-key  # For credential vault
ENCRYPTION_KEY=your-fernet-key             # For auth tokens

# NetBox Integration (optional)
NETBOX_URL=https://netbox.example.com
NETBOX_TOKEN=your-netbox-token

# Logging
LOG_LEVEL=INFO
```

## Application Modules

### Inventory (`/inventory`)
- **Devices** - View, search, and manage discovered devices
- **Device Detail** - Interface status, power levels, LLDP neighbors
- **Groups** - Create and manage device groups for targeting

### Workflows (`/workflows`)
- **Workflow List** - Browse, search, and manage workflows
- **Workflow Builder** - Visual drag-and-drop workflow editor
- **Execution** - Run workflows and view results

### Monitor (`/monitor`)
- **Dashboard** - System overview with device status
- **Topology** - Network topology visualization
- **Power Trends** - Optical power level charts
- **Alerts** - Active and historical alerts
- **Active Jobs** - Currently running jobs
- **Job History** - Execution history with logs

### Credentials (`/credentials`)
- **Credential Vault** - Encrypted credential storage
- **Credential Groups** - Organize credentials by purpose
- **Expiring** - Track credential expiration
- **Audit Log** - Credential access history

### System (`/system`)
- **Overview** - System health and statistics
- **Settings** - Application configuration
- **Users** - User management
- **Roles** - RBAC role configuration
- **Notifications** - Notification channels and rules
- **Logs** - System and application logs
- **Workers** - Celery worker status

## Documentation

| Document | Description |
|----------|-------------|
| [docs/BACKEND.md](docs/BACKEND.md) | Backend architecture, services, and API structure |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Frontend architecture, components, and routing |
| [docs/WORKFLOW_BUILDER.md](docs/WORKFLOW_BUILDER.md) | Visual workflow builder guide and node packages |
| [docs/CREDENTIALS.md](docs/CREDENTIALS.md) | Credential vault and authentication system |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete REST API documentation |

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=backend

# Run specific test file
python3 -m pytest tests/unit/test_workflow_engine.py -v
```

## Technology Stack

### Backend
- **Flask 2.3** - Web framework
- **PostgreSQL** - Primary database
- **Celery 5.3** - Background task queue
- **Redis** - Message broker for Celery
- **Paramiko** - SSH client
- **PyWinRM** - Windows Remote Management
- **Apprise** - Multi-platform notifications
- **bcrypt/pyotp** - Authentication and 2FA

### Frontend
- **React 19** - UI framework
- **Vite 7** - Build tool and dev server
- **React Flow** - Workflow canvas
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **Chart.js/Recharts** - Data visualization
- **React Router 6** - Client-side routing

## License

Proprietary - Internal Use Only
