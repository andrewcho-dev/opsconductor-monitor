"""Celery application setup for OpsConductor Monitor.

Uses Redis by default for both the broker and result backend, but both
can be overridden via environment variables:

- CELERY_BROKER_URL
- CELERY_RESULT_BACKEND

This module exports a single `celery_app` instance that tasks should
import and use via the `@celery_app.task` decorator.
"""

import os

from celery import Celery


def _make_celery() -> Celery:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

    app = Celery(
        "opsconductor_monitor",
        broker=broker_url,
        backend=result_backend,
        include=["backend.tasks.job_tasks", "backend.tasks.polling_tasks", "backend.tasks.generic_polling_task", "backend.tasks.connector_polling"],
    )

    # Optimized for high-throughput SNMP/SSH polling of 1000+ devices
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
        
        # Worker optimization for I/O-bound tasks (SNMP, SSH, HTTP)
        # - prefetch_multiplier=4 allows workers to grab multiple tasks
        #   for better throughput with I/O-bound workloads
        # - task_acks_late=True ensures tasks are only ACKed after completion
        # - task_reject_on_worker_lost=True returns tasks to queue on crash
        worker_prefetch_multiplier=int(os.getenv("CELERY_PREFETCH_MULTIPLIER", "4")),
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        
        # Result backend optimization
        result_expires=3600,  # Results expire after 1 hour
        result_compression="gzip",  # Compress results to reduce Redis memory
        
        # Task routing for different workload types
        task_routes={
            'polling.*': {'queue': 'polling'},
            'workflows.*': {'queue': 'workflows'},
            'analysis.*': {'queue': 'analysis'},
            'notifications.*': {'queue': 'notifications'},
        },
        
        # Task time limits to prevent runaway tasks
        task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_LIMIT", "300")),  # 5 min soft limit
        task_time_limit=int(os.getenv("CELERY_TASK_HARD_LIMIT", "600")),  # 10 min hard limit
        
        # Broker connection optimization
        broker_pool_limit=int(os.getenv("CELERY_BROKER_POOL_LIMIT", "50")),
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600")),
            "socket_timeout": 30,
            "socket_connect_timeout": 30,
        },
        # Celery Beat schedule: run the generic scheduler tick task
        # every 30 seconds to dispatch due jobs from scheduler_jobs.
        beat_schedule={
            "opsconductor-scheduler-tick": {
                "task": "opsconductor.scheduler.tick",
                "schedule": 30.0,
            },
            "opsconductor-alerts-evaluate": {
                "task": "opsconductor.alerts.evaluate",
                "schedule": 60.0,  # Every minute
            },
            # Dynamic polling scheduler - reads from polling_configs table
            # All polling schedules are now controlled via the frontend
            "opsconductor-polling-scheduler": {
                "task": "polling.scheduler_tick",
                "schedule": 30.0,  # Check for due polls every 30 seconds
            },
            # Connector polling - polls PRTG, MCP, etc. for alerts
            "opsconductor-connector-polling": {
                "task": "poll_all_connectors",
                "schedule": 60.0,  # Check every 60 seconds (individual intervals in task)
            },
        },
    )

    return app


celery_app: Celery = _make_celery()
