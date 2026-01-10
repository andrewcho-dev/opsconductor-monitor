# Celery Performance Tuning for 1000+ Devices

This document describes the optimized Celery configuration for high-throughput SNMP/SSH/HTTP polling of 1000+ network devices.

## System Requirements

For optimal performance with 1000+ devices:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU Cores | 8 | 16-20 |
| RAM | 16GB | 32-48GB |
| Redis | 6.x | 7.x |
| Network | 1Gbps | 10Gbps |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Celery Beat                               │
│                   (Scheduler - 1 process)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Dispatches tasks every 30s
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Redis                                    │
│                    (Message Broker)                              │
│              - polling queue (high priority)                     │
│              - workflows queue                                   │
│              - analysis queue                                    │
│              - notifications queue                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ General Worker  │ │ Polling Worker  │ │ Polling Worker  │
│  (32 processes) │ │  (16 processes) │ │  (16 processes) │
│                 │ │                 │ │                 │
│ - workflows     │ │ - SNMP polling  │ │ - SNMP polling  │
│ - analysis      │ │ - SSH commands  │ │ - SSH commands  │
│ - notifications │ │ - HTTP APIs     │ │ - HTTP APIs     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL                                  │
│                   (Result Storage)                               │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Files

### 1. Celery Application (`celery_app.py`)

Key settings for high throughput:

```python
app.conf.update(
    # Prefetch multiplier - how many tasks each worker grabs at once
    # Higher = better throughput for I/O-bound tasks
    worker_prefetch_multiplier=4,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=600,       # 10 min hard limit (kills task)
    
    # Broker connection pooling
    broker_pool_limit=50,
    
    # Result compression
    result_compression="gzip",
)
```

### 2. Systemd Services

#### General Worker (`opsconductor-celery.service`)
- **Concurrency**: 32 processes (1.6x CPU cores)
- **Queues**: polling, workflows, analysis, notifications
- **Prefetch**: 4 tasks per worker

#### Dedicated Polling Worker (`opsconductor-celery-polling.service`)
- **Concurrency**: 16 processes
- **Queues**: polling only
- **Prefetch**: 8 tasks per worker (higher for batch processing)

### 3. SNMP Poller (`async_snmp_poller.py`)

```python
AsyncSNMPPoller(
    max_concurrent=200,    # 200 simultaneous SNMP connections
    batch_size=100,        # Process 100 devices per batch
    stagger_delay=0.005,   # 5ms between starting queries
    default_timeout=5.0,   # 5 second timeout
)
```

## Installation

1. Copy systemd service files:
```bash
sudo cp systemd/opsconductor-celery.service /etc/systemd/system/
sudo cp systemd/opsconductor-celery-polling.service /etc/systemd/system/
sudo systemctl daemon-reload
```

2. Enable and start services:
```bash
sudo systemctl enable opsconductor-celery opsconductor-celery-polling
sudo systemctl start opsconductor-celery opsconductor-celery-polling
```

3. Increase system limits (add to `/etc/security/limits.conf`):
```
opsconductor soft nofile 65536
opsconductor hard nofile 65536
opsconductor soft nproc 65536
opsconductor hard nproc 65536
```

4. Optimize Redis (`/etc/redis/redis.conf`):
```
maxclients 10000
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

## Performance Targets

With the optimized configuration:

| Metric | Target | Notes |
|--------|--------|-------|
| Devices polled | 1000+ | Per polling cycle |
| Poll cycle time | < 60s | For all devices |
| SNMP queries/sec | 5000+ | Across all workers |
| Concurrent connections | 200 | Per worker process |
| Memory per worker | ~100MB | Depends on result size |

## Monitoring

### Check Worker Status
```bash
# View all workers
celery -A celery_app inspect active

# View queue lengths
celery -A celery_app inspect reserved

# View statistics
celery -A celery_app inspect stats
```

### API Endpoint
```bash
curl http://localhost:5000/api/scheduler/queues
```

Returns:
```json
{
  "success": true,
  "data": {
    "active": 5,
    "reserved": 10,
    "scheduled": 0,
    "workers": [
      {"name": "worker@host", "status": "online", "active_tasks": 2},
      {"name": "polling@host", "status": "online", "active_tasks": 3}
    ]
  }
}
```

## Troubleshooting

### Workers Not Starting
```bash
# Check logs
sudo journalctl -u opsconductor-celery -f
sudo journalctl -u opsconductor-celery-polling -f

# Check Redis connectivity
redis-cli ping
```

### Slow Polling
1. Check network latency to devices
2. Reduce `default_timeout` if devices respond quickly
3. Increase `max_concurrent` if CPU/memory allows
4. Check for SNMP community string issues

### Memory Issues
1. Reduce `max_concurrent`
2. Enable result compression
3. Reduce `max-tasks-per-child` to recycle workers more often

### Task Timeouts
1. Increase `task_soft_time_limit` and `task_time_limit`
2. Check for unresponsive devices
3. Consider splitting large polls into smaller batches

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `CELERY_RESULT_BACKEND` | Same as broker | Result backend URL |
| `CELERY_PREFETCH_MULTIPLIER` | `4` | Tasks per worker prefetch |
| `CELERY_TASK_SOFT_LIMIT` | `300` | Soft time limit (seconds) |
| `CELERY_TASK_HARD_LIMIT` | `600` | Hard time limit (seconds) |
| `CELERY_BROKER_POOL_LIMIT` | `50` | Broker connection pool size |
| `CELERY_VISIBILITY_TIMEOUT` | `3600` | Task visibility timeout |
