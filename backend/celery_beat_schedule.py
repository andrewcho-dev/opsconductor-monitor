"""
Celery Beat Schedule

Periodic tasks for OpsConductor.
"""

from celery.schedules import crontab
from celery_app import celery_app

# Import tasks to register them
from tasks.connector_polling import poll_all_connectors

# Schedule for connector polling
celery_app.conf.beat_schedule = {
    # Poll connectors every 60 seconds
    'poll-connectors': {
        'task': 'poll_all_connectors',
        'schedule': 60.0,  # seconds
    },
    
    # Reset daily alert counters at midnight
    'reset-daily-counters': {
        'task': 'reset_daily_alert_counters',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}

# Optional: Configure timezone
celery_app.conf.timezone = 'UTC'
