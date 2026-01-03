"""
Celery tasks - Compatibility wrapper.

This module provides backward compatibility with code that imports from celery_tasks.py.
It delegates to the new backend.tasks module.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.tasks import run_job, run_scheduled_job
from celery_app import celery_app

# Re-export the celery app
celery = celery_app

# Register tasks for backward compatibility
@celery.task(name='opsconductor.job.run')
def celery_run_job(job_config):
    """Run a job from configuration."""
    return run_job(job_config)


@celery.task(name='opsconductor.scheduler.tick')
def scheduler_tick():
    """Scheduler tick - check for due jobs and dispatch them."""
    from datetime import datetime
    from database import DatabaseManager
    
    db = DatabaseManager()
    
    # Get due jobs
    query = """
        SELECT * FROM scheduler_jobs 
        WHERE enabled = true 
        AND (next_run_at IS NULL OR next_run_at <= NOW())
    """
    
    try:
        jobs = db.execute_query(query)
        if not jobs:
            return {'dispatched': 0}
        
        dispatched = 0
        for job in jobs:
            job_name = job.get('name')
            config = job.get('config', {})
            
            # Dispatch the job
            try:
                celery_run_job.delay(config)
                dispatched += 1
                
                # Update next_run_at
                interval = job.get('interval_seconds', 300)
                update_query = """
                    UPDATE scheduler_jobs 
                    SET last_run_at = NOW(), 
                        next_run_at = NOW() + INTERVAL '%s seconds',
                        run_count = COALESCE(run_count, 0) + 1
                    WHERE name = %s
                """
                db.execute_query(update_query, (interval, job_name))
                
            except Exception as e:
                print(f"Failed to dispatch job {job_name}: {e}")
        
        return {'dispatched': dispatched}
        
    except Exception as e:
        return {'error': str(e)}


__all__ = ['celery', 'celery_run_job', 'scheduler_tick', 'run_job', 'run_scheduled_job']
