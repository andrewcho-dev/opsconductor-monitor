"""
Celery Tasks for SNMP Polling - Scheduler Only

This module contains ONLY the scheduler tick task that dispatches polls
based on the polling_configs table in the database.

ALL polling logic is handled by the generic polling task in generic_polling_task.py,
which reads OID mappings from the snmp_oid_mappings table.

NO HARDCODED POLLING TASKS - Everything is database-driven via:
- polling_configs: Defines what to poll, when, and which devices
- snmp_poll_types: Defines poll type names and target tables
- snmp_oid_groups: Groups of related OIDs
- snmp_oid_mappings: Individual OID definitions with transforms

Queue: 'polling' (high priority, dedicated workers)
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='polling.scheduler_tick', queue='polling')
def polling_scheduler_tick():
    """
    Scheduler tick that checks polling_configs and dispatches due polls.
    
    This task runs every 30 seconds (configured in celery_app.py beat_schedule)
    and checks which polling configs are:
    1. Enabled
    2. Due to run (last_run_at + interval_seconds < now)
    
    It dispatches the generic 'polling.generic' task for each due config.
    The generic task reads OIDs from the database - no hardcoding.
    """
    from backend.database import DatabaseConnection
    from celery_app import celery_app
    
    db = DatabaseConnection()
    
    with db.cursor() as cursor:
        # Find enabled configs that are due to run
        cursor.execute("""
            SELECT pc.id, pc.name, pc.poll_type, pc.interval_seconds, pc.last_run_at,
                   pc.target_type, pc.target_manufacturer, pc.target_role, pc.target_site_name,
                   pc.snmp_community, pc.batch_size, pc.max_concurrent, pc.tags
            FROM polling_configs pc
            WHERE pc.enabled = true
            AND (
                pc.last_run_at IS NULL 
                OR pc.last_run_at + (pc.interval_seconds || ' seconds')::interval < NOW()
            )
        """)
        due_configs = cursor.fetchall()
    
    if not due_configs:
        return {'dispatched': 0, 'message': 'No polls due'}
    
    dispatched = 0
    for config in due_configs:
        poll_type = config['poll_type']
        
        # Build device filter from config
        device_filter = {}
        if config['target_manufacturer']:
            device_filter['manufacturer'] = config['target_manufacturer']
        if config['target_role']:
            device_filter['role'] = config['target_role']
        if config['target_site_name']:
            device_filter['site'] = config['target_site_name']
        
        try:
            # Dispatch the generic database-driven polling task
            celery_app.send_task(
                'polling.generic',
                kwargs={
                    'poll_type_name': poll_type,
                    'device_filter': device_filter if device_filter else None,
                    'config_id': config['id'],
                },
                queue='polling'
            )
            logger.info(f"Dispatched poll '{poll_type}' for config '{config['name']}' (id={config['id']})")
            dispatched += 1
            
            # Update last_run_at immediately to prevent duplicate dispatches
            with db.cursor() as cursor:
                cursor.execute(
                    "UPDATE polling_configs SET last_run_at = NOW() WHERE id = %s",
                    (config['id'],)
                )
                db.get_connection().commit()
                
        except Exception as e:
            logger.error(f"Failed to dispatch poll for config {config['id']}: {e}")
    
    return {'dispatched': dispatched, 'checked': len(due_configs)}
