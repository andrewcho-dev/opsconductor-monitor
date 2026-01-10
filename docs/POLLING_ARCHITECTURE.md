# Polling Architecture

## Overview

OpsConductor v2 uses a **fan-out polling pattern** designed to scale to 2000+ devices with parallel processing and rate limiting.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Celery Beat (Scheduler)                            │
│                    Triggers poll_dispatch every 60 seconds                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         poll_dispatch (Dispatcher Task)                      │
│                                                                              │
│  1. Query all enabled addons with polling methods                           │
│  2. Query all targets due for polling (last_poll + interval < now)          │
│  3. Spawn poll_single_target.delay(target_id) for each due target           │
│                                                                              │
│  Lightweight - just dispatches, doesn't do actual polling                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    Spawns N individual tasks (fan-out)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Redis Queue: polling                            │
│                                                                              │
│  [target_1] [target_2] [target_3] ... [target_N]                            │
│                                                                              │
│  Rate limited: 100 tasks/second max                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    Workers pull tasks in parallel
                                      │
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Worker 1   │ │  Worker 2   │ │  Worker 3   │ │  Worker 4   │ │  Worker N   │
│ concurrency │ │ concurrency │ │ concurrency │ │ concurrency │ │ concurrency │
│     =4      │ │     =4      │ │     =4      │ │     =4      │ │     =4      │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │              │              │              │              │
        └──────────────┴──────────────┴──────────────┴──────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        poll_single_target (Worker Task)                      │
│                                                                              │
│  1. Load target and addon from database                                     │
│  2. Execute poll based on addon method:                                     │
│     - api_poll  → HTTP/HTTPS request                                        │
│     - snmp_poll → SNMP GET/WALK                                             │
│     - ssh       → SSH command execution                                     │
│  3. Parse response using addon manifest rules                               │
│  4. Create/update/resolve alerts via AlertEngine                            │
│  5. Update target.last_poll_at                                              │
│                                                                              │
│  Rate limited: 100/s across all workers                                     │
│  Retries: 3 attempts with exponential backoff                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Alert Engine                                    │
│                                                                              │
│  - Deduplication via fingerprint (addon_id + alert_type + device_ip)       │
│  - Auto-resolution when poll succeeds after failure                         │
│  - Real-time events via Redis pub/sub → WebSocket                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Scaling Characteristics

### Throughput Calculation

| Workers | Concurrency | Parallel Polls | 2000 Devices @ 0.5s/poll |
|---------|-------------|----------------|--------------------------|
| 1       | 4           | 4              | ~4 minutes               |
| 2       | 4           | 8              | ~2 minutes               |
| 4       | 4           | 16             | ~1 minute                |
| 8       | 4           | 32             | ~30 seconds              |

### Rate Limiting

```python
@shared_task(rate_limit='100/s')
def poll_single_target(target_id):
    ...
```

- **100 polls/second** max across all workers
- Prevents overwhelming network infrastructure
- Prevents DDoS-ing your own devices
- Configurable per-task or globally

### Retry Strategy

```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True
)
def poll_single_target(self, target_id):
    try:
        ...
    except Exception as e:
        raise self.retry(exc=e)
```

- 3 retry attempts
- Exponential backoff (30s, 60s, 120s)
- Failed after retries → alert created

## Task Definitions

### poll_dispatch (Scheduler Task)

**Purpose:** Lightweight dispatcher that identifies due targets and spawns individual poll tasks.

**Schedule:** Every 60 seconds via Celery Beat

**Queue:** `dispatch`

**Logic:**
```python
def poll_dispatch():
    for addon in get_polling_addons():
        targets = get_due_targets(addon.id)
        for target in targets:
            poll_single_target.delay(target['id'])
```

### poll_single_target (Worker Task)

**Purpose:** Poll a single target device using its addon's configuration.

**Queue:** `polling`

**Rate Limit:** 100/second

**Logic:**
```python
def poll_single_target(target_id):
    target = get_target(target_id)
    addon = get_addon(target['addon_id'])
    
    if addon.method == 'api_poll':
        result = poller.poll_api(...)
    elif addon.method == 'snmp_poll':
        result = poller.poll_snmp(...)
    elif addon.method == 'ssh':
        result = poller.poll_ssh(...)
    
    process_result(result, target, addon)
    update_last_poll_time(target_id)
```

### cleanup_resolved_alerts (Maintenance Task)

**Purpose:** Delete old resolved alerts to prevent database bloat.

**Schedule:** Daily

**Queue:** `maintenance`

## Queue Configuration

```python
task_routes = {
    'poll_dispatch': {'queue': 'dispatch'},
    'poll_single_target': {'queue': 'polling'},
    'cleanup_resolved_alerts': {'queue': 'maintenance'},
}
```

### Queue Purposes

| Queue | Purpose | Workers |
|-------|---------|---------|
| `dispatch` | Lightweight scheduling tasks | 1 (low priority) |
| `polling` | Device polling tasks | Multiple (scale as needed) |
| `maintenance` | Cleanup, reconciliation | 1 (low priority) |

## Worker Deployment

### Development (Single Machine)

```bash
# Single worker handling all queues
celery -A backend.tasks.celery_app worker \
    --concurrency=4 \
    -Q dispatch,polling,maintenance \
    -l info
```

### Production (2000+ Devices)

```bash
# Dispatch worker (1 instance)
celery -A backend.tasks.celery_app worker \
    --concurrency=1 \
    -Q dispatch \
    -n dispatch@%h

# Polling workers (scale as needed)
celery -A backend.tasks.celery_app worker \
    --concurrency=4 \
    -Q polling \
    -n polling1@%h

celery -A backend.tasks.celery_app worker \
    --concurrency=4 \
    -Q polling \
    -n polling2@%h

# Maintenance worker (1 instance)
celery -A backend.tasks.celery_app worker \
    --concurrency=1 \
    -Q maintenance \
    -n maintenance@%h
```

## Polling Interval Configuration

### Per-Target Interval

Each target has its own `poll_interval` (in seconds):

```sql
-- targets table
poll_interval INTEGER DEFAULT 300  -- 5 minutes default
last_poll_at TIMESTAMP
```

### Due Calculation

A target is due for polling when:
```python
last_poll_at + poll_interval < now()
```

### Beat Schedule

Beat runs `poll_dispatch` every 60 seconds, but targets are only polled if their individual interval has elapsed.

```
Beat interval: 60s (how often we check)
Target interval: 300s (how often each target is actually polled)
```

## Communication Methods

### API Polling (`api_poll`)

```python
result = await poller.poll_api(
    url="http://10.1.1.100/axis-cgi/basicdeviceinfo.cgi",
    method="GET",
    auth=("user", "pass"),
    auth_type="digest",  # or "basic"
    verify_ssl=False,    # for self-signed certs
    timeout=30
)
```

### SNMP Polling (`snmp_poll`)

```python
result = await poller.poll_snmp(
    target="10.1.1.100",
    oids=["1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.5.0"],
    community="public",
    version="2c",
    port=161,
    timeout=10
)
```

### SSH Polling (`ssh`)

```python
result = await poller.poll_ssh(
    host="10.1.1.100",
    command="show system status",
    username="admin",
    password="secret",
    port=22,
    timeout=30
)
```

## Alert Flow

```
Poll Success                          Poll Failure
    │                                      │
    ▼                                      ▼
Auto-resolve existing                 Create/update alert
failure alert (if any)                (deduplicated by fingerprint)
    │                                      │
    ▼                                      ▼
Parse response for                    Emit alert_created or
condition-based alerts                alert_updated event
    │                                      │
    └──────────────┬───────────────────────┘
                   ▼
            Redis pub/sub
                   │
                   ▼
            WebSocket broadcast
                   │
                   ▼
            Frontend real-time update
```

## Monitoring

### Flower (Celery Monitoring)

```bash
celery -A backend.tasks.celery_app flower --port=5555
```

View at http://localhost:5555:
- Active/completed/failed tasks
- Worker status
- Task rate graphs
- Queue lengths

### Key Metrics to Watch

| Metric | Healthy | Warning |
|--------|---------|---------|
| Queue length (polling) | < 100 | > 500 |
| Task success rate | > 99% | < 95% |
| Avg task duration | < 2s | > 5s |
| Worker CPU | < 70% | > 90% |

## Future Enhancements

1. **Priority queues** - Critical devices polled first
2. **Adaptive intervals** - Increase frequency for flapping devices
3. **Bulk SNMP** - Poll multiple OIDs in single request
4. **Connection pooling** - Reuse HTTP connections per device
5. **Geographic distribution** - Workers close to device locations
