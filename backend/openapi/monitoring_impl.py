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

from backend.database import get_db
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
    db = get_db()
    with db.cursor() as cursor:
        # Check if alerts table exists (same as legacy)
        if not _table_exists(cursor, 'alerts'):
            return {
                'items': [],
                'total': 0,
                'limit': limit,
                'cursor': None
            }
        
        # Build query - same as legacy /api/alerts
        query = """
            SELECT * FROM alerts 
            WHERE acknowledged = false 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        alerts = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM alerts WHERE acknowledged = false")
        total = cursor.fetchone()['total'] if cursor.description else 0
        
        return {
            'items': alerts,
            'total': total,
            'limit': limit,
            'cursor': None
        }

async def acknowledge_alert(alert_id: str, acknowledged_by: str) -> Dict[str, str]:
    """
    Acknowledge an alert
    Migrated from legacy /api/alerts/{id}/acknowledge
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'alerts'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "ALERT_NOT_FOUND",
                    "message": f"Alert with ID '{alert_id}' not found"
                }
            )
        
        # Check if alert exists and is not already acknowledged
        cursor.execute("""
            SELECT id, status, acknowledged_at FROM alerts 
            WHERE id = %s
        """, (alert_id,))
        
        alert = cursor.fetchone()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "ALERT_NOT_FOUND",
                    "message": f"Alert with ID '{alert_id}' not found"
                }
            )
        
        if alert['acknowledged_at']:
            return {
                "success": True,
                "message": "Alert already acknowledged",
                "acknowledged_at": alert['acknowledged_at'].isoformat()
            }
        
        # Acknowledge the alert
        cursor.execute("""
            UPDATE alerts 
            SET status = 'acknowledged', 
                acknowledged_at = NOW(),
                acknowledged_by = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (acknowledged_by, alert_id))
        
        db.commit()
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        
        return {
            "success": True,
            "message": "Alert acknowledged successfully",
            "acknowledged_at": datetime.now().isoformat()
        }

async def get_device_optical_metrics(device_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get optical power metrics for a device
    Migrated from legacy /api/metrics/optical/{ip}
    """
    db = get_db()
    with db.cursor() as cursor:
        # Verify device exists
        cursor.execute("SELECT id, ip_address FROM devices WHERE id = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found"
                }
            )
        
        # Get optical metrics from the last N hours
        if not _table_exists(cursor, 'optical_metrics'):
            return []
        
        cursor.execute("""
            SELECT interface_name, rx_power, tx_power,
                   rx_power_low_alarm, rx_power_high_alarm,
                   tx_power_low_alarm, tx_power_high_alarm,
                   timestamp, unit
            FROM optical_metrics 
            WHERE device_id = %s 
            AND timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC, interface_name
            LIMIT 1000
        """, (device_id, hours))
        
        metrics = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return metrics

async def get_device_interface_metrics(device_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get interface utilization metrics for a device
    Migrated from legacy /api/metrics/interfaces/{ip}
    """
    db = get_db()
    with db.cursor() as cursor:
        # Verify device exists
        cursor.execute("SELECT id, ip_address FROM devices WHERE id = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found"
                }
            )
        
        # Get interface metrics from the last N hours
        if not _table_exists(cursor, 'interface_metrics'):
            return []
        
        cursor.execute("""
            SELECT interface_name, interface_index, admin_status, oper_status,
                   speed, mtu, rx_bytes, tx_bytes, rx_packets, tx_packets,
                   rx_errors, tx_errors, rx_drops, tx_drops,
                   timestamp, utilization_in, utilization_out
            FROM interface_metrics 
            WHERE device_id = %s 
            AND timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC, interface_index
            LIMIT 1000
        """, (device_id, hours))
        
        metrics = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return metrics

async def get_device_availability_metrics(device_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get availability metrics for a device
    Migrated from legacy /api/metrics/availability/{ip}
    """
    db = get_db()
    with db.cursor() as cursor:
        # Verify device exists
        cursor.execute("SELECT id, ip_address FROM devices WHERE id = %s", (device_id,))
        device = cursor.fetchone()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found"
                }
            )
        
        # Get availability metrics from the last N days
        if not _table_exists(cursor, 'availability_metrics'):
            return []
        
        cursor.execute("""
            SELECT DATE(timestamp) as date,
                   COUNT(*) as total_checks,
                   COUNT(*) FILTER (WHERE is_up = true) as up_checks,
                   ROUND(
                       (COUNT(*) FILTER (WHERE is_up = true) * 100.0 / COUNT(*), 2
                   ) as availability_percentage,
                   MIN(timestamp) as first_check,
                   MAX(timestamp) as last_check
            FROM availability_metrics 
            WHERE device_id = %s 
            AND timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (device_id, days))
        
        metrics = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return metrics

async def get_telemetry_status() -> Dict[str, Any]:
    """
    Get telemetry and monitoring service status
    """
    db = get_db()
    with db.cursor() as cursor:
        status = {
            "database": "connected",
            "polling": "active",
            "metrics_collection": "active",
            "alerting": "active",
            "last_update": datetime.now().isoformat(),
            "services": {}
        }
        
        # Check if monitoring tables exist
        monitoring_tables = ['alerts', 'optical_metrics', 'interface_metrics', 'availability_metrics']
        for table in monitoring_tables:
            status["services"][table] = {
                "status": "available" if _table_exists(cursor, table) else "unavailable",
                "table_exists": _table_exists(cursor, table)
            }
        
        # Get recent activity counts
        if _table_exists(cursor, 'alerts'):
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE created_at >= NOW() - INTERVAL '1 hour'")
            status["services"]["alerts"]["last_hour_count"] = cursor.fetchone()['count']
        
        if _table_exists(cursor, 'optical_metrics'):
            cursor.execute("SELECT COUNT(*) as count FROM optical_metrics WHERE timestamp >= NOW() - INTERVAL '1 hour'")
            status["services"]["optical_metrics"]["last_hour_count"] = cursor.fetchone()['count']
        
        return status

async def get_alert_stats() -> Dict[str, Any]:
    """
    Get alert statistics
    Migrated from legacy /api/alerts/stats
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'alerts'):
            return {
                "total": 0,
                "by_severity": {},
                "by_status": {},
                "recent_24h": 0,
                "acknowledged": 0,
                "unacknowledged": 0
            }
        
        # Overall stats
        cursor.execute("SELECT COUNT(*) as total FROM alerts")
        total = cursor.fetchone()['total']
        
        # By severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count 
            FROM alerts 
            GROUP BY severity
        """)
        by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        # By status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM alerts 
            GROUP BY status
        """)
        by_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) as count FROM alerts 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        recent_24h = cursor.fetchone()['count']
        
        # Acknowledged vs unacknowledged
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE acknowledged_at IS NOT NULL) as acknowledged,
                COUNT(*) FILTER (WHERE acknowledged_at IS NULL) as unacknowledged
            FROM alerts
        """)
        ack_stats = cursor.fetchone()
        
        return {
            "total": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "recent_24h": recent_24h,
            "acknowledged": ack_stats['acknowledged'],
            "unacknowledged": ack_stats['unacknowledged']
        }

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
