"""
Scans API Router - FastAPI.

Routes for network scanning operations.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ScanRequest(BaseModel):
    ips: Optional[List[str]] = None
    network_range: Optional[str] = None
    scan_type: str = "full"  # full, ping, snmp, ssh


@router.get("")
async def list_scans(limit: int = 50, offset: int = 0):
    """List recent scan results."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, scan_type, started_at, completed_at, status,
                   target_count, success_count, failure_count
            FROM scan_history
            ORDER BY started_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        scans = [dict(row) for row in cursor.fetchall()]
    return list_response(scans)


@router.post("")
async def start_scan(req: ScanRequest):
    """Start a new network scan."""
    try:
        # This would trigger the actual scan
        # For now, return a placeholder response
        return success_response({
            "scan_id": 0,
            "status": "started",
            "message": f"Scan started for {len(req.ips or [])} targets"
        })
    except Exception as e:
        logger.error(f"Scan start error: {e}")
        return error_response('SCAN_ERROR', str(e))


@router.get("/{scan_id}")
async def get_scan(scan_id: int):
    """Get scan details."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, scan_type, started_at, completed_at, status,
                   target_count, success_count, failure_count, results
            FROM scan_history WHERE id = %s
        """, (scan_id,))
        scan = cursor.fetchone()
        if not scan:
            return error_response('NOT_FOUND', 'Scan not found')
    return success_response(dict(scan))


@router.get("/device/{ip}")
async def get_device_scan_results(ip: str, limit: int = 10):
    """Get scan results for a specific device."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT interface_name, interface_index, admin_status, oper_status,
                   rx_power_dbm, tx_power_dbm, lldp_remote_hostname, lldp_remote_port,
                   collected_at
            FROM interface_scans
            WHERE device_ip = %s
            ORDER BY collected_at DESC
            LIMIT %s
        """, (ip, limit))
        results = [dict(row) for row in cursor.fetchall()]
    return list_response(results)


@router.post("/snmp")
async def start_snmp_scan(req: ScanRequest):
    """Start an SNMP-only scan."""
    try:
        return success_response({
            "scan_id": 0,
            "status": "started",
            "scan_type": "snmp",
            "message": "SNMP scan started"
        })
    except Exception as e:
        logger.error(f"SNMP scan error: {e}")
        return error_response('SCAN_ERROR', str(e))


@router.post("/ssh")
async def start_ssh_scan(req: ScanRequest):
    """Start an SSH-only scan."""
    try:
        return success_response({
            "scan_id": 0,
            "status": "started",
            "scan_type": "ssh",
            "message": "SSH scan started"
        })
    except Exception as e:
        logger.error(f"SSH scan error: {e}")
        return error_response('SCAN_ERROR', str(e))


@router.get("/status")
async def get_scan_status():
    """Get current scan status."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM scan_history WHERE status = 'running') as running,
                (SELECT COUNT(*) FROM scan_history WHERE started_at > NOW() - INTERVAL '24 hours') as last_24h,
                (SELECT MAX(completed_at) FROM scan_history WHERE status = 'completed') as last_completed
        """)
        status = dict(cursor.fetchone())
    return success_response(status)
