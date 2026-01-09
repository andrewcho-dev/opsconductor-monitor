"""
Connector Polling Tasks

Celery tasks for polling enabled connectors and processing alerts.
"""

import sys
import os

# Ensure project root is in path for backend.* imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Set

from celery import shared_task

logger = logging.getLogger(__name__)


def generate_fingerprint(source_system: str, source_alert_id: str, device_identifier: str, alert_type: str) -> str:
    """Generate deduplication fingerprint matching AlertManager logic."""
    parts = [source_system, source_alert_id, device_identifier, alert_type]
    fingerprint_str = ":".join(str(p) for p in parts)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()


@shared_task(name='poll_all_connectors', queue='polling')
def poll_all_connectors():
    """
    Poll all enabled connectors for alerts.
    
    This task runs periodically (configured via Celery beat) to:
    1. Get all enabled connectors
    2. Check each connector's individual poll_interval
    3. Poll if due for polling
    4. Process any returned alerts through AlertManager
    5. Update connector stats
    """
    from backend.database import DatabaseConnection
    from backend.connectors.registry import create_connector
    from backend.core.alert_manager import get_alert_manager
    from backend.core.redis_pubsub import publish_alert_event_sync, publish_system_event_sync
    
    logger.info("Starting connector polling cycle")
    
    db = DatabaseConnection()
    
    # Get enabled connectors with their last poll time
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, type, config, last_poll_at,
                   EXTRACT(EPOCH FROM (NOW() - COALESCE(last_poll_at, '1970-01-01')))::INTEGER as seconds_since_poll
            FROM connectors
            WHERE enabled = true
            ORDER BY name
        """)
        rows = cursor.fetchall()
    
    if not rows:
        logger.info("No enabled connectors to poll")
        return {"polled": 0, "alerts": 0}
    
    total_alerts = 0
    polled_count = 0
    
    for row in rows:
        connector_id = str(row["id"])
        connector_type = row["type"]
        config = dict(row.get("config") or {})
        last_poll_at = row.get("last_poll_at")
        seconds_since_poll = row.get("seconds_since_poll") or 0
        
        # Get poll interval from config (default 60 seconds)
        poll_interval = config.get("poll_interval", 60)
        
        # Skip if not due for polling (with 5 second buffer)
        if last_poll_at and seconds_since_poll < (poll_interval - 5):
            logger.debug(f"Skipping {row['name']} - not due for polling (last: {seconds_since_poll}s ago, interval: {poll_interval}s)")
            continue
        
        try:
            # Create connector instance
            connector = create_connector(connector_type, config)
            if not connector:
                logger.warning(f"Unknown connector type: {connector_type}")
                continue
            
            logger.info(f"Polling {row['name']} (interval: {poll_interval}s)")
            
            # Poll for alerts
            alerts = asyncio.run(connector.poll())
            alert_count = len(alerts) if alerts else 0
            
            # Track fingerprints of alerts we received in this poll
            current_fingerprints: Set[str] = set()
            
            # Process alerts through AlertManager
            alert_manager = get_alert_manager()
            for alert in (alerts or []):
                try:
                    # Skip None alerts (disabled event types return None from normalizer)
                    if alert is None:
                        continue
                    # Validate alert is a proper NormalizedAlert object
                    if not hasattr(alert, 'device_ip'):
                        logger.warning(f"Invalid alert object from {row['name']}: {type(alert)}")
                        continue
                    # Generate fingerprint for reconciliation
                    device_id = alert.device_ip or alert.device_name or ""
                    fp = generate_fingerprint(alert.source_system, alert.source_alert_id, device_id, alert.alert_type)
                    current_fingerprints.add(fp)
                    
                    stored_alert = asyncio.run(alert_manager.process_alert(alert))
                    if stored_alert is None:
                        logger.warning(f"process_alert returned None for alert from {row['name']}")
                        continue
                    action = getattr(stored_alert, '_action', 'created')
                    logger.debug(f"{action.title()} alert {stored_alert.id} from {row['name']}")
                    
                    # Publish alert event to Redis for real-time WebSocket updates
                    publish_alert_event_sync(action, {
                        "id": str(stored_alert.id),
                        "title": stored_alert.title,
                        "severity": stored_alert.severity.value if hasattr(stored_alert.severity, 'value') else str(stored_alert.severity),
                        "device_name": stored_alert.device_name,
                        "device_ip": stored_alert.device_ip,
                        "source_system": stored_alert.source_system,
                        "status": stored_alert.status.value if hasattr(stored_alert.status, 'value') else str(stored_alert.status),
                        "source_status": getattr(stored_alert, 'source_status', None),
                    })
                except Exception as alert_err:
                    logger.warning(f"Error processing individual alert from {row['name']}: {alert_err}")
            
            if alert_count > 0:
                total_alerts += alert_count
                logger.info(f"Received {alert_count} alerts from {row['name']}")
            
            # RECONCILIATION: Resolve alerts that are no longer in poll results
            # Only for polling-based connectors (not event/trap based)
            if connector_type in ('prtg', 'eaton', 'cradlepoint', 'siklu', 'ubiquiti', 'axis'):
                resolved_count = reconcile_alerts(
                    db, connector_type, current_fingerprints, publish_alert_event_sync
                )
                if resolved_count > 0:
                    logger.info(f"Reconciled {resolved_count} alerts as resolved for {row['name']}")
            
            # Update connector stats and last poll time
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE connectors 
                    SET last_poll_at = NOW(),
                        alerts_received = alerts_received + %s,
                        alerts_today = alerts_today + %s,
                        status = 'connected',
                        error_message = NULL
                    WHERE id = %s
                """, (alert_count, alert_count, connector_id))
                db.get_connection().commit()
            
            polled_count += 1
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"CONNECTOR POLL ERROR - {row['name']} ({connector_type}): {e}")
            logger.error(f"FULL TRACEBACK:\n{tb}")
            
            # Update error status
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE connectors 
                    SET status = 'error',
                        error_message = %s,
                        last_poll_at = NOW()
                    WHERE id = %s
                """, (str(e), connector_id))
                db.get_connection().commit()
    
    logger.info(f"Polling complete: {polled_count} connectors polled, {total_alerts} alerts")
    
    # Publish poll complete event for real-time dashboard updates
    if polled_count > 0:
        publish_system_event_sync("poll_complete", {
            "connectors_polled": polled_count,
            "total_alerts": total_alerts,
        })
    
    return {"polled": polled_count, "alerts": total_alerts}


def reconcile_alerts(db, source_system: str, current_fingerprints: Set[str], publish_fn) -> int:
    """
    Reconcile alerts: resolve any active alerts from this source that are not in current poll.
    
    This implements the "if it's not in the poll, it's resolved" logic for polling-based connectors.
    """
    from datetime import datetime
    
    # Get all active/acknowledged/suppressed alerts from this source
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, fingerprint, title, device_name, device_ip
            FROM alerts
            WHERE source_system = %s
            AND status IN ('active', 'acknowledged', 'suppressed')
        """, (source_system,))
        existing_alerts = cursor.fetchall()
    
    if not existing_alerts:
        return 0
    
    resolved_count = 0
    now = datetime.utcnow()
    
    for alert_row in existing_alerts:
        alert_id = str(alert_row['id'])
        fingerprint = alert_row['fingerprint']
        
        # If this alert's fingerprint is NOT in current poll results, resolve it
        if fingerprint and fingerprint not in current_fingerprints:
            # Get current message before resolution
            with db.cursor() as cursor:
                cursor.execute("SELECT message FROM alerts WHERE id = %s", (alert_id,))
                msg_row = cursor.fetchone()
                message_before = msg_row['message'] if msg_row else None
            
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE alerts
                    SET status = 'resolved',
                        resolved_at = %s,
                        updated_at = %s,
                        message_before_resolution = COALESCE(message_before_resolution, %s),
                        resolution_message = %s,
                        resolution_source = %s
                    WHERE id = %s
                    AND status IN ('active', 'acknowledged', 'suppressed')
                """, (now, now, message_before, 
                      "Alert no longer present in source system poll results",
                      "reconciliation", alert_id))
                db.get_connection().commit()
                
                if cursor.rowcount > 0:
                    resolved_count += 1
                    logger.info(f"Auto-resolved alert {alert_id}: {alert_row['title']}")
                    
                    # Publish resolution event
                    publish_fn("resolved", {
                        "id": alert_id,
                        "title": alert_row['title'],
                        "device_name": alert_row['device_name'],
                        "device_ip": alert_row['device_ip'],
                        "source_system": source_system,
                        "status": "resolved",
                        "resolved_by": "system",
                        "resolution_source": "reconciliation",
                        "notes": "Alert no longer present in source system"
                    })
    
    return resolved_count
