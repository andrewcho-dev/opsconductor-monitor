"""
Settings API Router - FastAPI.

Routes for application settings management.
"""

import os
import json
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.utils.responses import success_response, error_response
from backend.utils.errors import AppError

router = APIRouter()


def get_settings_file_path():
    """Get path to settings file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'settings.json')


class SettingsUpdate(BaseModel):
    network_ranges: Optional[list] = None
    snmp_community: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_port: Optional[int] = None
    scan_timeout: Optional[int] = None
    max_threads: Optional[int] = None


class TestSettingsRequest(BaseModel):
    test_target: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_port: Optional[int] = 22
    snmp_community: Optional[str] = None


@router.get("")
async def get_settings():
    """Get current settings."""
    settings_path = get_settings_file_path()
    
    default_settings = {
        'network_ranges': [],
        'snmp_community': 'public',
        'ssh_username': '',
        'ssh_password': '',
        'ssh_port': 22,
        'scan_timeout': 5,
        'max_threads': 50,
    }
    
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return success_response(settings)
    except Exception:
        pass
    
    return success_response(default_settings)


@router.post("")
async def save_settings(request: Request):
    """Save settings."""
    settings_path = get_settings_file_path()
    data = await request.json()
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(data, f, indent=2)
        return success_response(data, message='Settings saved')
    except Exception as e:
        raise AppError('SETTINGS_ERROR', f'Failed to save settings: {str(e)}', 500)


@router.post("/test")
async def test_settings(req: TestSettingsRequest):
    """Test settings (connectivity test)."""
    results = {
        'ssh': None,
        'snmp': None,
    }
    
    if not req.test_target:
        return success_response(results, message='No test target specified')
    
    # Test SSH
    if req.ssh_username and req.ssh_password:
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=req.test_target,
                port=req.ssh_port or 22,
                username=req.ssh_username,
                password=req.ssh_password,
                timeout=5
            )
            client.close()
            results['ssh'] = {'success': True, 'message': 'SSH connection successful'}
        except Exception as e:
            results['ssh'] = {'success': False, 'message': str(e)}
    
    # Test SNMP
    if req.snmp_community:
        try:
            # Note: SNMP test would need async implementation
            results['snmp'] = {'success': True, 'message': 'SNMP test not implemented in async mode'}
        except Exception as e:
            results['snmp'] = {'success': False, 'message': str(e)}
    
    return success_response(results)


@router.get("/database")
async def get_database_settings():
    """Get database connection settings."""
    return success_response({
        'db_host': os.getenv('PG_HOST', 'localhost'),
        'db_port': int(os.getenv('PG_PORT', 5432)),
        'db_name': os.getenv('PG_DATABASE', 'opsconductor'),
        'db_username': os.getenv('PG_USER', 'postgres'),
        'db_ssl_mode': 'prefer',
    })


@router.post("/database/test")
async def test_database_connection():
    """Test database connection."""
    try:
        from backend.database import get_db
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
        if result:
            return success_response({'connected': True}, message='Database connection successful')
        else:
            return error_response('DB_ERROR', 'Query returned no results')
    except Exception as e:
        return error_response('DB_ERROR', f'Connection failed: {str(e)}')


# Legacy routes for backward compatibility
@router.get("/get_settings")
async def get_settings_legacy():
    """Legacy endpoint."""
    return await get_settings()


@router.post("/save_settings")
async def save_settings_legacy(request: Request):
    """Legacy endpoint."""
    return await save_settings(request)


@router.post("/test_settings")
async def test_settings_legacy(req: TestSettingsRequest):
    """Legacy endpoint."""
    return await test_settings(req)
