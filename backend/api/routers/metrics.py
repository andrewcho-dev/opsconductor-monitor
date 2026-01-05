"""
Metrics API Router - FastAPI.

Routes for device metrics (optical, interface, availability).
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from backend.database import get_db
from backend.utils.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/optical/{ip}")
async def get_optical_metrics(ip: str, hours: int = 24):
    """Get optical power metrics for a device."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT port_id, port_name, rx_power_dbm, tx_power_dbm, temperature, collected_at
            FROM optical_metrics
            WHERE device_ip = %s AND collected_at > NOW() - INTERVAL '%s hours'
            ORDER BY collected_at DESC
        """, (ip, hours))
        metrics = [dict(row) for row in cursor.fetchall()]
    return success_response(metrics)


@router.get("/interfaces/{ip}")
async def get_interface_metrics(ip: str, hours: int = 24):
    """Get interface traffic metrics for a device."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT interface_name, rx_bytes, tx_bytes, rx_packets, tx_packets, collected_at
            FROM interface_metrics
            WHERE device_ip = %s AND collected_at > NOW() - INTERVAL '%s hours'
            ORDER BY collected_at DESC
        """, (ip, hours))
        metrics = [dict(row) for row in cursor.fetchall()]
    return success_response(metrics)


@router.get("/availability/{ip}")
async def get_availability_metrics(ip: str, hours: int = 24):
    """Get availability metrics for a device."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT device_ip, is_available, response_time_ms, check_type, checked_at
            FROM availability_metrics
            WHERE device_ip = %s AND checked_at > NOW() - INTERVAL '%s hours'
            ORDER BY checked_at DESC
        """, (ip, hours))
        metrics = [dict(row) for row in cursor.fetchall()]
    return success_response(metrics)


@router.get("/summary")
async def get_metrics_summary():
    """Get overall metrics summary."""
    db = get_db()
    with db.cursor() as cursor:
        # Get counts
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM optical_metrics WHERE collected_at > NOW() - INTERVAL '24 hours') as optical_24h,
                (SELECT COUNT(*) FROM interface_metrics WHERE collected_at > NOW() - INTERVAL '24 hours') as interface_24h,
                (SELECT COUNT(*) FROM availability_metrics WHERE checked_at > NOW() - INTERVAL '24 hours') as availability_24h
        """)
        counts = dict(cursor.fetchone())
    
    return success_response(counts)


@router.get("/power-history")
async def get_power_history(
    ip: Optional[str] = None,
    ip_list: Optional[str] = None,
    interface_index: Optional[int] = None,
    hours: int = 24
):
    """Get optical power history."""
    db = get_db()
    
    # Parse ip_list if provided
    ips = []
    if ip:
        ips = [ip]
    elif ip_list:
        ips = [i.strip() for i in ip_list.split(',')]
    
    if not ips:
        return success_response({'history': []})
    
    with db.cursor() as cursor:
        all_history = []
        for device_ip in ips:
            query = """
                SELECT device_ip, port_id, port_name, rx_power_dbm, tx_power_dbm, collected_at
                FROM optical_metrics
                WHERE device_ip = %s AND collected_at > NOW() - INTERVAL '%s hours'
            """
            params = [device_ip, hours]
            
            if interface_index is not None:
                query += " AND port_id = %s"
                params.append(interface_index)
            
            query += " ORDER BY collected_at DESC"
            cursor.execute(query, params)
            all_history.extend([dict(row) for row in cursor.fetchall()])
    
    return success_response({'history': all_history})
