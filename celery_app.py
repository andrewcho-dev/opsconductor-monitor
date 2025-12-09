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
        include=["celery_tasks"],
    )

    # Basic sensible defaults; we can tune later.
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
        # Celery Beat schedule: run the generic scheduler tick task
        # every 30 seconds to dispatch due jobs from scheduler_jobs.
        beat_schedule={
            "opsconductor-scheduler-tick": {
                "task": "opsconductor.scheduler.tick",
                "schedule": 30.0,
            }
        },
    )

    return app


celery_app: Celery = _make_celery()
