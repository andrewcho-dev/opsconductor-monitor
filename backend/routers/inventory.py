"""
Inventory API Router (/inventory/v1)

Handles devices, interfaces, sites, topology, and network inventory.
"""

from fastapi import APIRouter, Query, Path, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from backend.openapi.inventory_impl import (
    list_devices_paginated, get_device_by_id, list_device_interfaces,
    get_network_topology, list_sites, list_modules, list_racks,
    test_inventory_endpoints
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/inventory/v1", tags=["inventory", "devices", "network"])


@router.get("/devices", summary="List devices")
async def list_devices(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    site: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List network devices with filtering and pagination"""
    try:
        return await list_devices_paginated(limit, cursor, site, role, status)
    except Exception as e:
        logger.error(f"List devices error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_DEVICES_ERROR", "message": str(e)})


@router.get("/devices/{device_id}", summary="Get device")
async def get_device(
    device_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get device details"""
    try:
        device = await get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail={"code": "DEVICE_NOT_FOUND", "message": "Device not found"})
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get device error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "GET_DEVICE_ERROR", "message": str(e)})


@router.get("/devices/{device_id}/interfaces", summary="List device interfaces")
async def get_interfaces(
    device_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List interfaces for a device"""
    try:
        return await list_device_interfaces(device_id)
    except Exception as e:
        logger.error(f"List interfaces error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_INTERFACES_ERROR", "message": str(e)})


@router.get("/topology", summary="Get network topology")
async def get_topology(
    site: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get network topology data"""
    try:
        return await get_network_topology(site)
    except Exception as e:
        logger.error(f"Get topology error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "TOPOLOGY_ERROR", "message": str(e)})


@router.get("/sites", summary="List sites")
async def get_sites(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List all sites"""
    try:
        return await list_sites()
    except Exception as e:
        logger.error(f"List sites error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_SITES_ERROR", "message": str(e)})


@router.get("/modules", summary="List modules")
async def get_modules(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List device modules"""
    try:
        return await list_modules()
    except Exception as e:
        logger.error(f"List modules error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_MODULES_ERROR", "message": str(e)})


@router.get("/racks", summary="List racks")
async def get_racks(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List rack locations"""
    try:
        return await list_racks()
    except Exception as e:
        logger.error(f"List racks error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_RACKS_ERROR", "message": str(e)})


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Inventory API"""
    try:
        results = await test_inventory_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
