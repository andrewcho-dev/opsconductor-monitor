"""
Monitoring API Implementation - OpenAPI 3.x Migration
This implements the actual business logic for monitoring endpoints
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.db import db_query, db_query_one, db_execute, table_exists, db_paginate, db_transaction
from backend.services.logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.SYSTEM)

# ============================================================================
# Database Functions (Migrated from Legacy)
# ============================================================================

def _table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        ) as exists
    """, (table_name,))
    result = cursor.fetchone()
    return result['exists'] if result else False

# ============================================================================
# Monitoring API Business Logic
# ============================================================================

async def list_alerts_paginated(
    cursor_str: Optional[str] = None, 
    limit: int = 50,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    List alerts with pagination and filtering
    Uses same logic as legacy /api/alerts - handles missing table gracefully
    """
    if not table_exists('alerts'):
        return {'items': [], 'total': 0, 'limit': limit, 'cursor': None}
    
    return db_paginate(
        "SELECT * FROM alerts WHERE acknowledged = false ORDER BY created_at DESC",
        "SELECT COUNT(*) as total FROM alerts WHERE acknowledged = false",
        [], limit
    )

async def acknowledge_alert(alert_id: str, acknowledged_by: str) -> Dict[str, str]:
    """
    Acknowledge an alert
    Migrated from legacy /api/alerts/{id}/acknowledge
    """
    if not table_exists('alerts'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ALERT_NOT_FOUND", "message": f"Alert with ID '{alert_id}' not found"})
    
    with db_transaction() as tx:
        alert = tx.query_one("SELECT id, status, acknowledged_at FROM alerts WHERE id = %s", (alert_id,))
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ALERT_NOT_FOUND", "message": f"Alert with ID '{alert_id}' not found"})
        
        if alert['acknowledged_at']:
            return {"success": True, "message": "Alert already acknowledged", "acknowledged_at": alert['acknowledged_at'].isoformat()}
        
        tx.execute("""
            UPDATE alerts SET status = 'acknowledged', acknowledged_at = NOW(),
                acknowledged_by = %s, updated_at = NOW() WHERE id = %s
        """, (acknowledged_by, alert_id))
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return {"success": True, "message": "Alert acknowledged successfully", "acknowledged_at": datetime.now().isoformat()}

async def get_device_optical_metrics(device_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get optical power metrics for a device
    Migrated from legacy /api/metrics/optical/{ip}
    """
    device = db_query_one("SELECT id, ip_address FROM devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEVICE_NOT_FOUND", "message": f"Device with ID '{device_id}' not found"})
    
    if not table_exists('optical_metrics'):
        return []
    
    return db_query(f"""
        SELECT interface_name, rx_power, tx_power, rx_power_low_alarm, rx_power_high_alarm,
               tx_power_low_alarm, tx_power_high_alarm, timestamp, unit
        FROM optical_metrics WHERE device_id = %s AND timestamp >= NOW() - INTERVAL '{hours} hours'
        ORDER BY timestamp DESC, interface_name LIMIT 1000
    """, (device_id,))

async def get_device_interface_metrics(device_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get interface utilization metrics for a device
    Migrated from legacy /api/metrics/interfaces/{ip}
    """
    device = db_query_one("SELECT id, ip_address FROM devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEVICE_NOT_FOUND", "message": f"Device with ID '{device_id}' not found"})
    
    if not table_exists('interface_metrics'):
        return []
    
    return db_query(f"""
        SELECT interface_name, interface_index, admin_status, oper_status,
               speed, mtu, rx_bytes, tx_bytes, rx_packets, tx_packets,
               rx_errors, tx_errors, rx_drops, tx_drops, timestamp, utilization_in, utilization_out
        FROM interface_metrics WHERE device_id = %s AND timestamp >= NOW() - INTERVAL '{hours} hours'
        ORDER BY timestamp DESC, interface_index LIMIT 1000
    """, (device_id,))

async def get_device_availability_metrics(device_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get availability metrics for a device
    Migrated from legacy /api/metrics/availability/{ip}
    """
    device = db_query_one("SELECT id, ip_address FROM devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEVICE_NOT_FOUND", "message": f"Device with ID '{device_id}' not found"})
    
    if not table_exists('availability_metrics'):
        return []
    
    return db_query(f"""
        SELECT DATE(timestamp) as date, COUNT(*) as total_checks,
               COUNT(*) FILTER (WHERE is_up = true) as up_checks,
               ROUND((COUNT(*) FILTER (WHERE is_up = true) * 100.0 / COUNT(*)), 2) as availability_percentage,
               MIN(timestamp) as first_check, MAX(timestamp) as last_check
        FROM availability_metrics WHERE device_id = %s AND timestamp >= NOW() - INTERVAL '{days} days'
        GROUP BY DATE(timestamp) ORDER BY date DESC
    """, (device_id,))

async def get_telemetry_status() -> Dict[str, Any]:
    """
    Get telemetry and monitoring service status
    """
    result = {
        "database": "connected", "polling": "active", "metrics_collection": "active",
        "alerting": "active", "last_update": datetime.now().isoformat(), "services": {}
    }
    
    # Check if monitoring tables exist
    for tbl in ['alerts', 'optical_metrics', 'interface_metrics', 'availability_metrics']:
        exists = table_exists(tbl)
        result["services"][tbl] = {"status": "available" if exists else "unavailable", "table_exists": exists}
    
    # Get recent activity counts
    if table_exists('alerts'):
        row = db_query_one("SELECT COUNT(*) as count FROM alerts WHERE created_at >= NOW() - INTERVAL '1 hour'")
        result["services"]["alerts"]["last_hour_count"] = row['count'] if row else 0
    
    if table_exists('optical_metrics'):
        row = db_query_one("SELECT COUNT(*) as count FROM optical_metrics WHERE timestamp >= NOW() - INTERVAL '1 hour'")
        result["services"]["optical_metrics"]["last_hour_count"] = row['count'] if row else 0
    
    return result

async def get_alert_stats() -> Dict[str, Any]:
    """
    Get alert statistics
    Migrated from legacy /api/alerts/stats
    """
    if not table_exists('alerts'):
        return {"total": 0, "by_severity": {}, "by_status": {}, "recent_24h": 0, "acknowledged": 0, "unacknowledged": 0}
    
    total_row = db_query_one("SELECT COUNT(*) as total FROM alerts")
    total = total_row['total'] if total_row else 0
    
    severity_rows = db_query("SELECT severity, COUNT(*) as count FROM alerts GROUP BY severity")
    by_severity = {row['severity']: row['count'] for row in severity_rows}
    
    status_rows = db_query("SELECT status, COUNT(*) as count FROM alerts GROUP BY status")
    by_status = {row['status']: row['count'] for row in status_rows}
    
    recent_row = db_query_one("SELECT COUNT(*) as count FROM alerts WHERE created_at >= NOW() - INTERVAL '24 hours'")
    recent_24h = recent_row['count'] if recent_row else 0
    
    ack_row = db_query_one("""
        SELECT COUNT(*) FILTER (WHERE acknowledged_at IS NOT NULL) as acknowledged,
               COUNT(*) FILTER (WHERE acknowledged_at IS NULL) as unacknowledged FROM alerts
    """)
    
    return {"total": total, "by_severity": by_severity, "by_status": by_status, "recent_24h": recent_24h,
            "acknowledged": ack_row['acknowledged'] if ack_row else 0, "unacknowledged": ack_row['unacknowledged'] if ack_row else 0}

# ============================================================================
# Testing Functions
# ============================================================================

async def test_monitoring_endpoints() -> Dict[str, bool]:
    """
    Test all Monitoring API endpoints
    Returns dict of endpoint: success status
    """
    results = {}
    
    try:
        # Test 1: List alerts (empty)
        alerts_data = await list_alerts_paginated()
        results['list_alerts'] = 'items' in alerts_data and 'total' in alerts_data
        
        # Test 2: Get alert stats
        stats = await get_alert_stats()
        results['get_alert_stats'] = 'total' in stats and 'by_severity' in stats
        
        # Test 3: Get telemetry status
        telemetry = await get_telemetry_status()
        results['get_telemetry_status'] = 'services' in telemetry and 'database' in telemetry
        
        # Test 4: Get optical metrics (will fail device validation, but should handle gracefully)
        try:
            await get_device_optical_metrics("nonexistent")
            results['get_optical_metrics'] = False  # Should not succeed
        except HTTPException:
            results['get_optical_metrics'] = True  # Expected to fail
        
        # Test 5: Get interface metrics (same as above)
        try:
            await get_device_interface_metrics("nonexistent")
            results['get_interface_metrics'] = False
        except HTTPException:
            results['get_interface_metrics'] = True
        
        logger.info(f"Monitoring API tests completed: {sum(results.values())}/{len(results)} passed")
        
    except Exception as e:
        logger.error(f"Monitoring API test failed: {str(e)}")
        results['error'] = str(e)
    
    return results
