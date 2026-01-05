"""SNMP Traps router - FastAPI."""

from fastapi import APIRouter, Query
from typing import Optional
from backend.database import get_db

router = APIRouter()


@router.get("/status")
async def get_trap_receiver_status():
    """Get SNMP trap receiver status."""
    db = get_db()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM trap_receiver_status 
            ORDER BY last_updated DESC 
            LIMIT 1
        """)
        status = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as total_traps,
                   COUNT(*) FILTER (WHERE received_at > NOW() - INTERVAL '1 hour') as last_hour,
                   COUNT(*) FILTER (WHERE received_at > NOW() - INTERVAL '24 hours') as last_24h
            FROM trap_log
        """)
        stats = dict(cursor.fetchone())
    
    return {
        "success": True,
        "data": {
            "status": dict(status) if status else None,
            "statistics": stats
        }
    }


@router.get("/log")
async def get_trap_log(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    source_ip: Optional[str] = None
):
    """Get trap log entries."""
    db = get_db()
    
    with db.cursor() as cursor:
        query = """
            SELECT id, source_ip, source_port, trap_oid, enterprise_oid,
                   uptime, varbinds, raw_pdu, received_at, processed
            FROM trap_log
        """
        params = []
        
        if source_ip:
            query += " WHERE source_ip = %s"
            params.append(source_ip)
        
        query += " ORDER BY received_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        traps = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM trap_log"
        if source_ip:
            count_query += " WHERE source_ip = %s"
            cursor.execute(count_query, [source_ip] if source_ip else [])
        else:
            cursor.execute(count_query)
        total = cursor.fetchone()[0]
    
    return {
        "success": True,
        "data": {
            "traps": traps,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/events")
async def get_trap_events(
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None
):
    """Get normalized trap events."""
    db = get_db()
    
    with db.cursor() as cursor:
        query = """
            SELECT id, source_ip, device_name, event_type, severity,
                   description, object_type, object_instance, 
                   acknowledged, acknowledged_by, acknowledged_at,
                   created_at, updated_at
            FROM trap_events
            WHERE 1=1
        """
        params = []
        
        if severity:
            query += " AND severity = %s"
            params.append(severity)
        
        if acknowledged is not None:
            query += " AND acknowledged = %s"
            params.append(acknowledged)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        events = [dict(row) for row in cursor.fetchall()]
    
    return {
        "success": True,
        "data": {
            "events": events,
            "count": len(events)
        }
    }
