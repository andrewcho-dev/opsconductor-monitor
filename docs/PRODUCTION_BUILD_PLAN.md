# OpsConductor Production Environment Build Plan

## Document Purpose

This document provides a **meticulous, step-by-step plan** to transform the current development environment into a production-ready system. Each step includes verification commands and rollback procedures.

**CRITICAL**: This plan is designed to be non-destructive. We will build new infrastructure alongside existing systems and migrate data only after verification.

---

## Current Infrastructure State

### Server 1: OpsConductor (192.168.10.50)

| Resource | Value |
|----------|-------|
| Hostname | opsconductor-ai-dev |
| OS | Ubuntu 22.04.5 LTS |
| CPU | 20 cores (Intel Xeon Gold 5120 @ 2.20GHz) |
| RAM | 48 GB (37 GB available) |
| Disk | 1 TB (841 GB available) |
| IP | 192.168.10.50/24 |

**Running Services:**
- PostgreSQL 14 (port 5432) - 164 MB database
- Redis 6.0.16 (port 6379) - 3.75 MB used
- Celery Workers (32 workers)
- Vite Dev Server (port 3000)
- Flask Backend (port 5000)

**Current Database:** 57 tables in `network_scan` database

### Server 2: NetBox (192.168.10.51)

| Resource | Value |
|----------|-------|
| OS | Ubuntu 22.04.5 LTS |
| CPU | 8 cores |
| RAM | 32 GB (27 GB available) |
| Disk | 243 GB (212 GB available) |
| IP | 192.168.10.51/24 |

**Running Docker Containers:**
- netbox-netbox-1 (NetBox application, port 8000)
- netbox-netbox-worker-2-1 (NetBox worker)
- netbox-postgres-1 (PostgreSQL 17)
- netbox-redis-1 (Valkey 8.1)
- netbox-redis-cache-1 (Valkey 8.1)

---

## Execution Phases Overview

| Phase | Description | Time Est. | Risk |
|-------|-------------|-----------|------|
| 0 | Backup & Preparation | 30 min | None |
| 1 | Database Schema Migration | 1-2 hrs | Low |
| 2 | Backend Service Updates | 2-4 hrs | Low |
| 3 | Frontend Updates | 2-4 hrs | Low |
| 4 | Production Deployment | 2-3 hrs | Medium |
| 5 | PostgreSQL Optimization | 1 hr | Low |
| 6 | Redis Optimization | 30 min | Low |
| 7 | Cutover | 30 min | Medium |
| 8 | Monitoring Setup | 1-2 hrs | None |

**Total Estimated Time: 10-18 hours**

---

## Phase 0: Preparation & Backup (CRITICAL)

### Step 0.1: Create Full Backup

```bash
# On 192.168.10.50
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p /home/opsconductor/backups/${BACKUP_DATE}

# Backup database
PGPASSWORD=postgres pg_dump -h localhost -U postgres network_scan \
  > /home/opsconductor/backups/${BACKUP_DATE}/network_scan.sql

# Backup application code
tar -czf /home/opsconductor/backups/${BACKUP_DATE}/opsconductor-app.tar.gz \
  /home/opsconductor/opsconductor-monitor/CascadeProjects/windsurf-project \
  --exclude='node_modules' --exclude='__pycache__' --exclude='.git'

# Backup Redis
redis-cli BGSAVE
sleep 5
cp /var/lib/redis/dump.rdb /home/opsconductor/backups/${BACKUP_DATE}/redis.rdb
```

**Verification:**
```bash
ls -la /home/opsconductor/backups/${BACKUP_DATE}/
# Expected: network_scan.sql ~20-50MB, app tarball ~50-100MB
```

### Step 0.2: Document Current State

```bash
ps aux > /home/opsconductor/backups/${BACKUP_DATE}/processes.txt
systemctl list-units --type=service --state=running \
  > /home/opsconductor/backups/${BACKUP_DATE}/services.txt
ss -tlnp > /home/opsconductor/backups/${BACKUP_DATE}/ports.txt
```

---

## Phase 1: Database Schema Migration

### Step 1.1: Create Migration File

Create `/home/opsconductor/.../backend/migrations/001_add_metrics_tables.sql`

This migration adds new tables WITHOUT modifying existing ones:
- `optical_metrics` - Time-series optical power data
- `interface_metrics` - Interface traffic/errors
- `metric_baselines` - Statistical baselines
- `anomaly_events` - Detected anomalies
- `health_scores` - Calculated health scores

### Step 1.2: Run Migration

```bash
cd /home/opsconductor/opsconductor-monitor/CascadeProjects/windsurf-project
PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan \
  -f backend/migrations/001_add_metrics_tables.sql
```

**Verification:**
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan \
  -c "\dt public.*" | grep -E "optical_metrics|metric_baselines"
```

**Rollback:** Drop new tables only (existing tables untouched)

---

## Phase 2: Backend Service Updates

### Step 2.1: Create New Services

New files (do not modify existing):
- `backend/services/metrics_service.py`
- `backend/services/health_service.py`
- `backend/services/anomaly_service.py`
- `backend/services/baseline_service.py`

### Step 2.2: Create New API Endpoints

New files:
- `backend/api/metrics.py` → `/api/metrics/*`
- `backend/api/health.py` → `/api/health/*`
- `backend/api/anomalies.py` → `/api/anomalies/*`

### Step 2.3: Test

```bash
python -m pytest tests/ -v
curl http://localhost:5000/api/health/status
```

---

## Phase 3: Frontend Updates

### Step 3.1: Create New Hooks

- `frontend/src/hooks/useMetrics.js`
- `frontend/src/hooks/useHealth.js`

### Step 3.2: Create New Components

- `frontend/src/components/health/HealthGauge.jsx`
- `frontend/src/components/anomalies/AnomalyBadge.jsx`
- `frontend/src/components/metrics/MetricsChart.jsx`

### Step 3.3: Build for Production

```bash
cd frontend && npm run build
ls -la dist/
```

---

## Phase 4: Production Deployment

### Step 4.1: Install Nginx

```bash
sudo apt update && sudo apt install -y nginx
```

### Step 4.2: Configure Nginx

Create `/etc/nginx/sites-available/opsconductor`:

```nginx
server {
    listen 80;
    server_name 192.168.10.50;

    location / {
        root /home/opsconductor/.../frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

### Step 4.3: Create Systemd Services

Create services for:
- `opsconductor-api.service` (Gunicorn)
- `opsconductor-celery.service` (Workers)
- `opsconductor-beat.service` (Scheduler)

---

## Phase 5-6: Database & Redis Optimization

Optimize PostgreSQL for 48GB RAM server:
- `shared_buffers = 12GB`
- `effective_cache_size = 36GB`

Optimize Redis:
- `maxmemory 4gb`
- `maxmemory-policy allkeys-lru`

---

## Phase 7: Cutover

```bash
# Stop dev services
./stop.sh && pkill -f "vite"

# Start production
sudo systemctl start opsconductor-api opsconductor-celery opsconductor-beat

# Verify
curl http://192.168.10.50/
curl http://192.168.10.50/api/health/status
```

---

## Rollback Procedure

```bash
# Stop production
sudo systemctl stop opsconductor-api opsconductor-celery opsconductor-beat nginx

# Restore backup if needed
PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan \
  < /home/opsconductor/backups/BACKUP_DATE/network_scan.sql

# Start dev services
./start.sh
cd frontend && npm run dev -- --host 0.0.0.0 --port 3000
```

---

## Verification Checklist

- [ ] All backups created and verified
- [ ] Database migration successful
- [ ] New API endpoints working
- [ ] Frontend builds successfully
- [ ] Nginx configured and running
- [ ] Systemd services enabled
- [ ] Production accessible at http://192.168.10.50/
- [ ] NetBox integration working
- [ ] Celery tasks executing
- [ ] No errors in logs
