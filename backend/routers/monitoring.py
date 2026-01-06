"""
Monitoring API Router (/monitoring/v1)

Handles alerts, metrics, SNMP polling, MIB profiles, and device monitoring.
"""

from fastapi import APIRouter, Query, Path, Body, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
import logging

from backend.utils.db import db_query, db_query_one
from backend.openapi.monitoring_impl import (
    list_alerts_paginated, acknowledge_alert, get_device_optical_metrics,
    get_device_interface_metrics, get_device_availability_metrics,
    get_telemetry_status, get_alert_stats, test_monitoring_endpoints
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/monitoring/v1", tags=["monitoring", "alerts", "metrics"])


@router.get("/alerts", summary="List alerts")
async def list_alerts(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List alerts with filtering"""
    try:
        return await list_alerts_paginated(limit, cursor, severity, status)
    except Exception as e:
        logger.error(f"List alerts error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_ALERTS_ERROR", "message": str(e)})


@router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge alert")
async def ack_alert(
    alert_id: int = Path(...),
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Acknowledge an alert"""
    try:
        return await acknowledge_alert(alert_id, request.get('notes', ''))
    except Exception as e:
        logger.error(f"Acknowledge alert error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "ACK_ALERT_ERROR", "message": str(e)})


@router.get("/alerts/stats", summary="Get alert statistics")
async def get_stats(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get alert statistics"""
    try:
        return await get_alert_stats()
    except Exception as e:
        logger.error(f"Get alert stats error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "ALERT_STATS_ERROR", "message": str(e)})


@router.get("/alerts/history", summary="Get alert history")
async def get_history(
    limit: int = Query(100, ge=1, le=1000),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get alert history"""
    return {"alerts": [], "total": 0}


@router.get("/alerts/rules", summary="Get alert rules")
async def get_rules(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get alert rules"""
    return {"rules": [], "total": 0}


@router.get("/devices/{device_id}/metrics/optical", summary="Get optical metrics")
async def get_optical(
    device_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get optical power metrics for a device"""
    try:
        return await get_device_optical_metrics(device_id)
    except Exception as e:
        logger.error(f"Get optical metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "OPTICAL_METRICS_ERROR", "message": str(e)})


@router.get("/devices/{device_id}/metrics/interfaces", summary="Get interface metrics")
async def get_interfaces(
    device_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get interface metrics for a device"""
    try:
        return await get_device_interface_metrics(device_id)
    except Exception as e:
        logger.error(f"Get interface metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "INTERFACE_METRICS_ERROR", "message": str(e)})


@router.get("/devices/{device_id}/metrics/availability", summary="Get availability metrics")
async def get_availability(
    device_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get availability metrics for a device"""
    try:
        return await get_device_availability_metrics(device_id)
    except Exception as e:
        logger.error(f"Get availability metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "AVAILABILITY_ERROR", "message": str(e)})


@router.post("/snmp/poll", summary="Poll device via SNMP")
async def snmp_poll(
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Poll a device via SNMP"""
    return {"success": True, "data": {}}


@router.get("/telemetry/status", summary="Get telemetry status")
async def telemetry_status(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get telemetry collection status"""
    try:
        return await get_telemetry_status()
    except Exception as e:
        logger.error(f"Get telemetry status error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "TELEMETRY_ERROR", "message": str(e)})


# Polling configuration endpoints
@router.get("/polling/status", summary="Get polling status")
async def polling_status(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get polling system status"""
    return {"status": "running", "configs_enabled": 0, "last_execution": None}


@router.get("/polling/configs", summary="Get polling configs")
async def get_polling_configs(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get polling configurations from database"""
    try:
        configs = db_query("""
            SELECT id, name, description, poll_type, enabled, interval_seconds,
                   target_type, target_device_ip, target_site_name, target_role,
                   target_manufacturer, snmp_community, tags, created_at, updated_at,
                   last_run_at, last_run_status, last_run_devices_polled
            FROM polling_configs ORDER BY name
        """)
        return {"configs": configs, "total": len(configs)}
    except Exception as e:
        logger.error(f"Get polling configs error: {str(e)}")
        return {"configs": [], "total": 0}


@router.get("/polling/executions", summary="Get polling executions")
async def get_polling_executions(
    limit: int = Query(20, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get polling executions from database"""
    try:
        executions = db_query("""
            SELECT e.id, e.config_id, c.name as config_name, e.started_at, e.completed_at, 
                   e.status, e.devices_polled, e.devices_success, e.devices_failed, 
                   e.error_message,
                   EXTRACT(EPOCH FROM (e.completed_at - e.started_at)) * 1000 as duration_ms
            FROM polling_executions e
            LEFT JOIN polling_configs c ON c.id = e.config_id
            ORDER BY e.started_at DESC LIMIT %s
        """, (limit,))
        return {"executions": executions, "total": len(executions)}
    except Exception as e:
        logger.error(f"Get polling executions error: {str(e)}")
        return {"executions": [], "total": 0}


@router.get("/polling/poll-types", summary="Get poll types")
async def get_poll_types(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get available poll types from database"""
    try:
        rows = db_query("""
            SELECT id, name, display_name, description, enabled
            FROM snmp_poll_types WHERE enabled = true ORDER BY display_name
        """)
        poll_types = [{"id": row['name'], "name": row['display_name'], 
                      "description": row['description']} for row in rows]
        return {"poll_types": poll_types}
    except Exception as e:
        logger.error(f"Get poll types error: {str(e)}")
        return {"poll_types": []}


@router.get("/polling/target-types", summary="Get target types")
async def get_target_types(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get available target types"""
    return {"target_types": [
        {"id": "device", "name": "Device", "description": "Single device"},
        {"id": "group", "name": "Group", "description": "Device group"},
        {"id": "site", "name": "Site", "description": "Site"}
    ]}


# MIB profiles endpoints
@router.get("/mib/profiles", summary="Get MIB profiles")
async def get_mib_profiles(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MIB profiles from database"""
    try:
        profiles = db_query("""
            SELECT p.id, p.name, p.vendor, p.description, p.created_at,
                   COUNT(g.id) as group_count
            FROM snmp_profiles p
            LEFT JOIN snmp_oid_groups g ON g.profile_id = p.id
            GROUP BY p.id ORDER BY p.vendor, p.name
        """)
        return {"profiles": profiles, "total": len(profiles)}
    except Exception as e:
        logger.error(f"Get MIB profiles error: {str(e)}")
        return {"profiles": [], "total": 0}


@router.get("/mib/profiles/{profile_id}", summary="Get MIB profile details")
async def get_mib_profile(
    profile_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get MIB profile with groups and mappings"""
    try:
        profile = db_query_one("SELECT * FROM snmp_profiles WHERE id = %s", (profile_id,))
        if not profile:
            return {"profile": None}
        
        groups = db_query("""
            SELECT g.id, g.name, g.description, g.is_table,
                   array_agg(json_build_object(
                       'id', m.id, 'name', m.name, 'oid', m.oid,
                       'data_type', m.data_type, 'description', m.description
                   )) as mappings
            FROM snmp_oid_groups g
            LEFT JOIN snmp_oid_mappings m ON m.group_id = g.id
            WHERE g.profile_id = %s GROUP BY g.id ORDER BY g.name
        """, (profile_id,))
        profile['groups'] = groups
        return {"profile": profile}
    except Exception as e:
        logger.error(f"Get MIB profile error: {str(e)}")
        return {"profile": None}


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Monitoring API"""
    try:
        results = await test_monitoring_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
