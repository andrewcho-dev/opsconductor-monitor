"""
Ciena MCP API Router - FastAPI.

Routes for Ciena MCP (Management Control Plane) operations.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPConnectionRequest(BaseModel):
    host: str
    username: str
    password: str
    port: int = 443
    verify_ssl: bool = False


def get_mcp_settings():
    """Get MCP settings from database."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT key, value FROM system_settings 
            WHERE key LIKE 'mcp_%'
        """)
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
    return {
        'url': settings.get('mcp_url', ''),
        'username': settings.get('mcp_username', ''),
        'password': settings.get('mcp_password', ''),
        'verify_ssl': settings.get('mcp_verify_ssl', 'false'),
    }


@router.get("/settings")
async def get_mcp_settings_endpoint():
    """Get MCP settings."""
    settings = get_mcp_settings()
    configured = bool(settings.get('url') and settings.get('username'))
    return success_response({
        "url": settings.get('url', ''),
        "username": settings.get('username', ''),
        "verify_ssl": settings.get('verify_ssl', 'false').lower() == 'true',
        "configured": configured,
    })


@router.get("/status")
async def get_mcp_status():
    """Get MCP connection status."""
    settings = get_mcp_settings()
    configured = bool(settings.get('url') and settings.get('username'))
    
    return success_response({
        "configured": configured,
        "url": settings.get('url', '')
    })


class MCPTestRequest(BaseModel):
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    verify_ssl: Optional[bool] = None


@router.post("/test")
async def test_mcp_connection(req: MCPTestRequest = None):
    """Test MCP connectivity using stored or provided credentials."""
    try:
        from backend.services.ciena_mcp_service import CienaMCPService
        
        # Use stored settings if not provided
        settings = get_mcp_settings()
        url = req.url if req and req.url else settings.get('url', '')
        username = req.username if req and req.username else settings.get('username', '')
        password = req.password if req and req.password else settings.get('password', '')
        verify_ssl = req.verify_ssl if req and req.verify_ssl is not None else settings.get('verify_ssl', 'false').lower() == 'true'
        
        if not url or not username:
            return success_response({
                "success": False,
                "connected": False,
                "message": "MCP not configured"
            })
        
        # Use the MCP service to test connection
        mcp = CienaMCPService(
            url=url,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        # Try to get a token - this validates credentials
        mcp._get_token()
        
        return success_response({
            "success": True,
            "connected": True,
            "url": url
        })
                
    except Exception as e:
        logger.error(f"MCP test error: {e}")
        return success_response({
            "success": False,
            "connected": False,
            "message": str(e)
        })


@router.get("/devices")
async def get_mcp_devices():
    """Get devices from MCP."""
    # This would connect to MCP API
    return success_response({
        "devices": [],
        "message": "MCP device fetch not implemented"
    })


@router.get("/alarms")
async def get_mcp_alarms(severity: Optional[str] = None):
    """Get alarms from MCP."""
    return success_response({
        "alarms": [],
        "message": "MCP alarm fetch not implemented"
    })


@router.get("/topology")
async def get_mcp_topology():
    """Get network topology from MCP."""
    return success_response({
        "nodes": [],
        "links": [],
        "message": "MCP topology fetch not implemented"
    })


@router.get("/services")
async def get_mcp_services():
    """Get services from MCP."""
    return success_response({
        "services": [],
        "message": "MCP services fetch not implemented"
    })


@router.post("/sync")
async def sync_from_mcp():
    """Sync devices and data from MCP."""
    return success_response({
        "synced": 0,
        "message": "MCP sync not implemented"
    })
