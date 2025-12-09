"""Celery tasks for OpsConductor Monitor.

This module defines Celery tasks that wrap the existing discovery,
interface, optical, and Job Builder execution logic so they can be
run asynchronously and on a schedule via Celery Beat.

At this stage the tasks are thin wrappers; we will extend them to
record richer history and integrate tightly with poller_job_history
once the basic wiring is verified.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import json
import subprocess
from croniter import croniter

from celery_app import celery_app
from database import db

from poller_manager import run_discovery_scan, run_interface_scan, run_optical_scan
from generic_job_scheduler import run_job_builder_job


@celery_app.task(name="opsconductor.ping")
def celery_ping() -> Dict[str, Any]:
    """Lightweight health check task used to verify Celery wiring."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@celery_app.task(name="opsconductor.ping_host")
def ping_host_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """Ping a single host N times using the system ping command.

    Config keys:
      - host: IP or hostname to ping (required)
      - count: number of echo requests to send (default: 5)
      - timeout: per-ping timeout in seconds (optional)
    """
    task_id = ping_host_task.request.id
    db.update_scheduler_job_execution(task_id, status="running")

    host = (config or {}).get("host") or "10.127.0.1"
    count = int((config or {}).get("count") or 5)
    timeout = (config or {}).get("timeout")

    cmd = ["ping", "-c", str(count), host]
    if timeout:
        try:
            t = int(timeout)
            if t > 0:
                cmd.extend(["-W", str(t)])
        except Exception:
            pass

    started = datetime.utcnow()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        success = proc.returncode == 0
        result = {
            "host": host,
            "count": count,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "started_at": started.isoformat() + "Z",
            "finished_at": datetime.utcnow().isoformat() + "Z",
        }
        db.update_scheduler_job_execution(
            task_id,
            status="success" if success else "failed",
            finished_at=datetime.utcnow(),
            error_message=None if success else (proc.stderr or "ping failed"),
            result=result,
        )
        if not success:
            # Still return the result dict even on failure so callers can inspect
            return result
        return result
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
        )
        raise


@celery_app.task(name="opsconductor.discovery.run")
def run_discovery_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run a discovery scan via the existing poller_manager helper."""
    task_id = run_discovery_task.request.id
    # Mark as running
    db.update_scheduler_job_execution(task_id, status="running")
    try:
        result = run_discovery_scan(config or {})
        db.update_scheduler_job_execution(task_id, status="success", finished_at=datetime.utcnow(), result=result)
        return result
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
        )
        raise


@celery_app.task(name="opsconductor.interface.run")
def run_interface_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run an interface scan via the existing poller_manager helper."""
    task_id = run_interface_task.request.id
    db.update_scheduler_job_execution(task_id, status="running")
    try:
        result = run_interface_scan(config or {})
        db.update_scheduler_job_execution(task_id, status="success", finished_at=datetime.utcnow(), result=result)
        return result
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
        )
        raise


@celery_app.task(name="opsconductor.optical.run")
def run_optical_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run an optical scan via the existing poller_manager helper."""
    task_id = run_optical_task.request.id
    db.update_scheduler_job_execution(task_id, status="running")
    try:
        result = run_optical_scan(config or {})
        db.update_scheduler_job_execution(task_id, status="success", finished_at=datetime.utcnow(), result=result)
        return result
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
        )
        raise


@celery_app.task(name="opsconductor.jobbuilder.run")
def run_job_builder_task(job_definition: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Job Builder style job definition using the generic scheduler.

    This is the Celery entrypoint used by the Job Builder UI; it simply
    delegates to `generic_job_scheduler.run_job_builder_job` and returns
    the resulting summary dict.
    """
    task_id = run_job_builder_task.request.id
    db.update_scheduler_job_execution(task_id, status="running")
    try:
        result = run_job_builder_job(job_definition or {})
        db.update_scheduler_job_execution(task_id, status="success", finished_at=datetime.utcnow(), result=result)
        return result
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
        )
        raise


@celery_app.task(name="opsconductor.scheduler.tick")
def scheduler_tick() -> Dict[str, Any]:
    """Dispatcher task that enqueues due jobs from scheduler_jobs.

    Celery Beat should call this task periodically (e.g. every 30 seconds).
    It will look up all enabled jobs whose next_run_at is due, enqueue the
    corresponding Celery task with its config, and advance next_run_at by
    interval_seconds.
    """

    now = datetime.utcnow()
    due_jobs = db.get_due_scheduler_jobs(now)

    enqueued = []
    for job in due_jobs:
        task_name = job["task_name"]
        cfg = job.get("config") or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}

        # Enqueue the actual worker task and record execution row
        async_result = celery_app.send_task(task_name, args=[cfg])

        # Compute next run based on schedule type
        schedule_type = (job.get("schedule_type") or "interval").lower()
        next_run = None
        if schedule_type == "cron":
            expr = job.get("cron_expression")
            if expr:
                try:
                    next_run = croniter(expr, now).get_next(datetime)
                except Exception:
                    # If cron expression is invalid, leave next_run as None
                    next_run = None
        else:
            interval = job.get("interval_seconds") or 0
            try:
                interval = int(interval)
            except Exception:
                interval = 0
            if interval > 0:
                next_run = now + timedelta(seconds=interval)
        db.mark_scheduler_job_run(job["name"], now, next_run)

        # Create execution record as queued
        db.create_scheduler_job_execution(
            job_name=job["name"],
            task_name=task_name,
            task_id=async_result.id,
            status="queued",
            started_at=now,
            error_message=None,
            result={"config": cfg},
        )

        enqueued.append(job["name"])
    # Mark any long-lived queued/running executions as timed out so the UI
    # does not show them as permanently queued. Default timeout: 10 minutes.
    timed_out = db.mark_stale_scheduler_executions(timeout_seconds=600) or []

    return {
        "enqueued": enqueued,
        "timed_out": [
            {"id": row["id"], "job_name": row["job_name"], "task_id": row["task_id"]}
            for row in timed_out
        ],
        "timestamp": now.isoformat() + "Z",
    }
