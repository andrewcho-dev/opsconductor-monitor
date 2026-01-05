"""Ciena SNMP router - FastAPI (fully async).

This router calls async SNMP methods directly - compatible with uvicorn's event loop.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.services.ciena_snmp_service import (
    CienaSNMPService, CienaSNMPError,
    CIENA_OIDS, CES_ALARM_OIDS, WWP_OIDS,
    ALARM_SEVERITY, ALARM_OBJECT_CLASS,
)

router = APIRouter()


class SNMPTestRequest(BaseModel):
    host: str
    community: str = "public"


class SNMPPollRequest(BaseModel):
    host: str
    community: str = "public"


class SNMPBatchPollRequest(BaseModel):
    hosts: List[str]
    community: str = "public"


@router.post("/test")
async def test_connection(request: SNMPTestRequest):
    """Test SNMP connectivity to a Ciena switch."""
    try:
        service = CienaSNMPService(request.host, request.community)
        result = await service.test_connection()
        
        if result['success']:
            return {"success": True, "data": result, "message": f"Successfully connected to {request.host}"}
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Connection failed'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll")
async def poll_single(request: SNMPPollRequest):
    """Poll a single Ciena switch for all data."""
    try:
        result = await poll_switch(request.host, request.community)
        return {"success": True, "data": result}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll/batch")
async def poll_batch(request: SNMPBatchPollRequest):
    """Poll multiple Ciena switches."""
    try:
        results = await poll_multiple_switches(request.hosts, request.community)
        return {"success": True, "data": {"count": len(results), "results": results}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/{host}")
async def get_system_info(host: str, community: str = "public"):
    """Get system information from a switch."""
    try:
        service = CienaSNMPService(host, community)
        result = await service.get_system_info()
        return {"success": True, "data": result}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alarms/{host}")
async def get_alarms(host: str, community: str = "public"):
    """Get active alarms from a switch via SNMP."""
    import asyncio
    
    def _get_alarms_sync():
        """Run SNMP in separate thread with its own event loop."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            service = CienaSNMPService(host, community)
            return loop.run_until_complete(service._get_active_alarms_async())
        finally:
            loop.close()
    
    try:
        # Run sync SNMP code in thread pool to avoid blocking uvicorn
        alarms = await asyncio.to_thread(_get_alarms_sync)
        
        # Group by severity
        by_severity = {}
        for alarm in alarms:
            sev = alarm.get('severity', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return {
            "success": True,
            "data": {
                "host": host,
                "alarms": alarms,
                "count": len(alarms),
                "by_severity": by_severity
            }
        }
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rings/{host}")
async def get_rings(host: str, community: str = "public"):
    """Get G.8032 ring status from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        
        raps_global = None
        try:
            raps_global = await service.get_raps_global()
        except:
            pass
        
        rings = await service.get_virtual_rings()
        
        return {
            "success": True,
            "data": {
                "host": host,
                "raps_global": raps_global,
                "rings": rings,
                "count": len(rings)
            }
        }
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ports/{host}")
async def get_ports(host: str, community: str = "public"):
    """Get port status from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        ports = await service.get_ports()
        
        up_count = sum(1 for p in ports if p.get('oper_state') == 'up')
        down_count = sum(1 for p in ports if p.get('oper_state') == 'down')
        
        return {
            "success": True,
            "data": {
                "host": host,
                "ports": ports,
                "count": len(ports),
                "up": up_count,
                "down": down_count
            }
        }
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transceivers/{host}")
async def get_transceivers(host: str, community: str = "public"):
    """Get SFP/transceiver DOM data from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        xcvrs = await service.get_transceivers()
        
        return {
            "success": True,
            "data": {
                "host": host,
                "transceivers": xcvrs,
                "count": len(xcvrs)
            }
        }
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/port-stats/{host}")
async def get_port_stats(host: str, community: str = "public"):
    """Get port traffic statistics from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        stats = await service.get_port_stats()
        
        return {
            "success": True,
            "data": {
                "host": host,
                "port_stats": stats,
                "count": len(stats)
            }
        }
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chassis/{host}")
async def get_chassis_health(host: str, community: str = "public"):
    """Get chassis health from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        health = await service.get_chassis_health()
        return {"success": True, "data": health}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lag/{host}")
async def get_lag_status(host: str, community: str = "public"):
    """Get LAG status from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        lags = await service.get_lag_status()
        return {"success": True, "data": {"host": host, "lags": lags, "count": len(lags)}}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mstp/{host}")
async def get_mstp_status(host: str, community: str = "public"):
    """Get MSTP status from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        mstp = await service.get_mstp_status()
        return {"success": True, "data": mstp}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ntp/{host}")
async def get_ntp_status(host: str, community: str = "public"):
    """Get NTP status from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        ntp = await service.get_ntp_status()
        return {"success": True, "data": ntp}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cfm/{host}")
async def get_cfm_status(host: str, community: str = "public"):
    """Get CFM status from a switch via SNMP."""
    try:
        service = CienaSNMPService(host, community)
        cfm = await service.get_cfm_status()
        return {"success": True, "data": cfm}
    except CienaSNMPError as e:
        raise HTTPException(status_code=500, detail=str(e))
