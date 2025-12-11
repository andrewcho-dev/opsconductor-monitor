"""Celery tasks for OpsConductor Monitor.

This module defines Celery tasks for the unified job execution system.
All jobs (discovery, interface, optical, ping, etc.) are now executed
via the generic `opsconductor.job.run` task which reads job definitions
from the database and executes them using the GenericJobScheduler.

Key tasks:
- opsconductor.job.run: Unified executor for all job definitions
- opsconductor.jobbuilder.run: Ad-hoc Job Builder execution
- opsconductor.scheduler.tick: Celery Beat dispatcher for scheduled jobs
- opsconductor.ping: Health check task
- opsconductor.ping_host: Simple ping utility task
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import json
import logging
import os
import subprocess
from croniter import croniter

from celery_app import celery_app
from database import db
from generic_job_scheduler import run_job_builder_job, run_job_spec


logger = logging.getLogger(__name__)


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
    worker_host = getattr(ping_host_task.request, "hostname", "unknown")
    try:
        logger.info(
            "scheduler_execution_start ping_host_task task_id=%s worker=%s config=%s",
            task_id,
            worker_host,
            json.dumps(config or {}, default=str),
        )
    except Exception:
        # Logging must never break task execution
        pass

    db.update_scheduler_job_execution(task_id, status="running", worker=worker_host)

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
        exec_meta = {
            "task_id": task_id,
            "worker_hostname": worker_host,
            "worker_pid": os.getpid(),
        }
        try:
            delivery = getattr(ping_host_task.request, "delivery_info", None) or {}
            exec_meta["queue"] = delivery.get("routing_key")
            exec_meta["delivery_info"] = delivery
        except Exception:
            pass

        result = {
            "host": host,
            "count": count,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "started_at": started.isoformat() + "Z",
            "finished_at": datetime.utcnow().isoformat() + "Z",
            "execution_meta": exec_meta,
        }
        db.update_scheduler_job_execution(
            task_id,
            status="success" if success else "failed",
            finished_at=datetime.utcnow(),
            error_message=None if success else (proc.stderr or "ping failed"),
            result=result,
            worker=worker_host,
        )
        try:
            logger.info(
                "scheduler_execution_finish ping_host_task task_id=%s worker=%s status=%s returncode=%s",
                task_id,
                worker_host,
                "success" if success else "failed",
                proc.returncode,
            )
        except Exception:
            pass
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
            worker=worker_host,
        )
        try:
            logger.exception(
                "scheduler_execution_error ping_host_task task_id=%s worker=%s error=%s",
                task_id,
                worker_host,
                str(exc),
            )
        except Exception:
            pass
        raise


@celery_app.task(name="opsconductor.job.run")
def run_job_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """Generic executor for stored job definitions.

    Config keys:
      - job_definition_id: UUID of the job_definitions row (required)
      - overrides: optional dict of runtime overrides to merge into
        the stored job definition's config.

    The stored definition can be either a high-level Job Builder-style
    spec (actions with nested login_method/targeting/execution blocks)
    or a pre-translated generic job spec compatible with
    GenericJobScheduler. We detect the shape at runtime and delegate to
    run_job_builder_job or run_job_spec accordingly.
    """
    task_id = run_job_task.request.id
    worker_host = getattr(run_job_task.request, "hostname", "unknown")

    db.update_scheduler_job_execution(task_id, status="running", worker=worker_host)

    started = datetime.utcnow()
    try:
        job_def_id = (config or {}).get("job_definition_id")
        if not job_def_id:
            raise ValueError("job_definition_id is required in config for opsconductor.job.run")

        job_def = db.get_job_definition(job_def_id)
        if not job_def:
            raise ValueError(f"No job_definition found with id {job_def_id}")

        definition = job_def.get("definition") or {}
        if not isinstance(definition, dict):
            raise ValueError("job_definition.definition must be a JSON object")

        overrides = (config or {}).get("overrides") or {}

        job_spec = dict(definition)
        base_config = dict(job_spec.get("config") or {})
        merged_config = {**base_config, **(overrides or {})}
        job_spec["config"] = merged_config

        job_spec.setdefault("job_id", str(job_def.get("id")))
        job_spec.setdefault("name", job_def.get("name"))

        actions = job_spec.get("actions") or []
        is_builder_style = False
        for action in actions:
            lm = action.get("login_method")
            if isinstance(lm, dict):
                is_builder_style = True
                break

        logger.error(f"[CELERY_DEBUG] Job {job_def.get('name')}: {len(actions)} actions, is_builder_style={is_builder_style}")
        if actions:
            logger.error(f"[CELERY_DEBUG] First action: type={actions[0].get('type')}, login_method type={type(actions[0].get('login_method'))}")
            exec_cfg = actions[0].get('execution', {})
            logger.error(f"[CELERY_DEBUG] First action execution keys: {list(exec_cfg.keys())}")

        if is_builder_style:
            result = run_job_builder_job(job_spec)
        else:
            result = run_job_spec(job_spec)

        delivery = getattr(run_job_task.request, "delivery_info", None) or {}
        exec_meta = {
            "task_id": task_id,
            "worker_hostname": worker_host,
            "worker_pid": os.getpid(),
            "queue": delivery.get("routing_key"),
            "delivery_info": delivery,
        }

        payload = dict(result) if isinstance(result, dict) else {"result": result}
        payload["job_definition_id"] = str(job_def.get("id"))
        payload["job_name"] = job_def.get("name")
        payload["execution_meta"] = exec_meta
        metrics = payload.get("metrics") or {}
        if not isinstance(metrics, dict):
            metrics = {"raw_metrics": metrics}
        metrics.setdefault(
            "duration_seconds",
            (datetime.utcnow() - started).total_seconds(),
        )
        payload["metrics"] = metrics

        status = payload.get("status") or ("success" if not payload.get("error") else "failed")

        db.update_scheduler_job_execution(
            task_id,
            status=status,
            finished_at=datetime.utcnow(),
            error_message=payload.get("error") or None,
            result=payload,
            worker=worker_host,
        )

        try:
            logger.info(
                "job_run_finish task_id=%s worker=%s job_definition_id=%s job_name=%s status=%s",
                task_id,
                worker_host,
                job_def_id,
                job_def.get("name"),
                status,
            )
        except Exception:
            pass

        return payload
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
            worker=worker_host,
        )
        try:
            logger.exception(
                "job_run_error task_id=%s worker=%s error=%s",
                task_id,
                worker_host,
                str(exc),
            )
        except Exception:
            pass
        raise


@celery_app.task(name="opsconductor.jobbuilder.run")
def run_job_builder_task(job_definition: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Job Builder style job definition using the generic scheduler.

    This is the Celery entrypoint used by the Job Builder UI; it simply
    delegates to `generic_job_scheduler.run_job_builder_job` and returns
    the resulting summary dict.
    """
    task_id = run_job_builder_task.request.id
    worker_host = getattr(run_job_builder_task.request, "hostname", "unknown")
    db.update_scheduler_job_execution(task_id, status="running", worker=worker_host)
    try:
        result = run_job_builder_job(job_definition or {})
        exec_meta = {
            "task_id": task_id,
            "worker_hostname": worker_host,
            "worker_pid": os.getpid(),
        }
        try:
            delivery = getattr(run_job_builder_task.request, "delivery_info", None) or {}
            exec_meta["queue"] = delivery.get("routing_key")
            exec_meta["delivery_info"] = delivery
        except Exception:
            pass
        try:
            payload = dict(result)
            payload["execution_meta"] = exec_meta
        except Exception:
            payload = {"result": result, "execution_meta": exec_meta}

        db.update_scheduler_job_execution(
            task_id,
            status="success",
            finished_at=datetime.utcnow(),
            result=payload,
            worker=worker_host,
        )
        return result
    except Exception as exc:
        db.update_scheduler_job_execution(
            task_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message=str(exc),
            worker=worker_host,
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

    try:
        logger.info(
            "scheduler_tick_start now=%s due_jobs=%s",
            now.isoformat() + "Z",
            [j["name"] for j in due_jobs],
        )
    except Exception:
        pass

    enqueued = []
    for job in due_jobs:
        job_name = job["name"]
        task_name = job["task_name"]
        cfg = job.get("config") or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}

        # Enqueue the actual worker task and record execution row
        try:
            async_result = celery_app.send_task(task_name, args=[cfg])
        except Exception as exc:
            # If we cannot enqueue the task at all, record a failed execution
            # row so the UI shows a clear error instead of pretending it ran.
            db.create_scheduler_job_execution(
                job_name=job_name,
                task_name=task_name,
                task_id=f"enqueue-error-{now.timestamp()}",
                status="failed",
                started_at=now,
                error_message=str(exc),
                result={"config": cfg, "enqueue_error": str(exc)},
            )
            try:
                logger.exception(
                    "scheduler_tick_enqueue_error job=%s task_name=%s error=%s",
                    job_name,
                    task_name,
                    str(exc),
                )
            except Exception:
                pass
            # Do not advance next_run_at so this job can be retried on the
            # next tick instead of being silently skipped.
            continue

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
        db.mark_scheduler_job_run(job_name, now, next_run)

        # Create execution record as queued
        db.create_scheduler_job_execution(
            job_name=job_name,
            task_name=task_name,
            task_id=async_result.id,
            status="queued",
            started_at=now,
            error_message=None,
            result={"config": cfg},
        )

        enqueued.append(job_name)
        try:
            logger.info(
                "scheduler_tick_enqueued job=%s task_name=%s task_id=%s config=%s",
                job_name,
                task_name,
                async_result.id,
                json.dumps(cfg or {}, default=str),
            )
        except Exception:
            pass
    # Mark any long-lived queued/running executions as timed out so the UI
    # does not show them as permanently queued. Use 10 minutes for queued jobs
    # (running jobs get 4x = 40 minutes before timeout).
    timed_out = db.mark_stale_scheduler_executions(timeout_seconds=600) or []

    try:
        if timed_out:
            logger.warning(
                "scheduler_tick_timeouts count=%s executions=%s",
                len(timed_out),
                [row["id"] for row in timed_out],
            )
    except Exception:
        pass

    return {
        "enqueued": enqueued,
        "timed_out": [
            {"id": row["id"], "job_name": row["job_name"], "task_id": row["task_id"]}
            for row in timed_out
        ],
        "timestamp": now.isoformat() + "Z",
    }
