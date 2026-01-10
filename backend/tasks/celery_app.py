"""
Celery Application Configuration

Minimal Celery setup for scheduled polling tasks.
"""

import os
from celery import Celery

# Redis connection
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
celery_app = Celery(
    'opsconductor',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['backend.tasks.tasks']
)

# Configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing - separate queues for different workloads
    task_routes={
        'poll_dispatch': {'queue': 'dispatch'},       # Lightweight dispatcher
        'poll_single_target': {'queue': 'polling'},   # Individual target polls (parallel)
        'poll_addon': {'queue': 'polling'},           # On-demand polling
        'poll_all_addons': {'queue': 'dispatch'},     # Legacy alias
        'cleanup_resolved_alerts': {'queue': 'maintenance'},
        'reconcile_alerts': {'queue': 'maintenance'},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        'poll-dispatch-60s': {
            'task': 'poll_dispatch',
            'schedule': 60.0,  # Every 60 seconds - spawns individual target tasks
        },
        'cleanup-alerts-daily': {
            'task': 'cleanup_resolved_alerts',
            'schedule': 86400.0,  # Daily
        },
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,
    
    # Enable task events for Flower monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


if __name__ == '__main__':
    celery_app.start()
