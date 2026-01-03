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
        include=["backend.tasks.job_tasks", "backend.tasks.polling_tasks"],
    )

    # Basic sensible defaults; we can tune later.
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
        # Make worker behavior more predictable and resilient.
        # - worker_prefetch_multiplier=1 prevents a single worker from
        #   hoarding tasks and starving others.
        # - task_acks_late=True ensures tasks are only ACKed after the
        #   work is done so crashes cause re-delivery.
        # - task_reject_on_worker_lost=True makes sure tasks return to
        #   the queue if a worker process disappears.
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        # Visibility timeout should be comfortably larger than any
        # expected task runtime so Celery can recover tasks from
        # lost workers instead of dropping them.
        broker_transport_options={
            "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600")),
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
            "opsconductor-poll-optical": {
                "task": "polling.optical",
                "schedule": 300.0,  # Every 5 minutes
            },
            "opsconductor-poll-availability": {
                "task": "polling.availability",
                "schedule": 60.0,  # Every minute
            },
        },
    )

    return app


celery_app: Celery = _make_celery()
