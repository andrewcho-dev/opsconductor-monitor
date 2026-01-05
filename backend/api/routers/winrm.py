"""
WinRM API Router - FastAPI.

Routes for Windows Remote Management operations.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import logging
import asyncio

from backend.utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()


class WinRMCommandRequest(BaseModel):
    host: str
    username: str
    password: str
    command: str
    use_ssl: bool = False
    port: Optional[int] = None


class WinRMPowerShellRequest(BaseModel):
    host: str
    username: str
    password: str
    script: str
    use_ssl: bool = False
    port: Optional[int] = None


@router.post("/execute")
async def execute_command(req: WinRMCommandRequest):
    """Execute a command via WinRM."""
    try:
        import winrm
        
        def _run_command():
            port = req.port or (5986 if req.use_ssl else 5985)
            protocol = 'https' if req.use_ssl else 'http'
            
            session = winrm.Session(
                f"{protocol}://{req.host}:{port}/wsman",
                auth=(req.username, req.password),
                transport='ntlm'
            )
            
            result = session.run_cmd(req.command)
            
            return {
                "stdout": result.std_out.decode('utf-8') if result.std_out else "",
                "stderr": result.std_err.decode('utf-8') if result.std_err else "",
                "exit_code": result.status_code
            }
        
        result = await asyncio.to_thread(_run_command)
        return success_response(result)
        
    except Exception as e:
        logger.error(f"WinRM command error: {e}")
        return error_response('WINRM_ERROR', str(e))


@router.post("/powershell")
async def execute_powershell(req: WinRMPowerShellRequest):
    """Execute a PowerShell script via WinRM."""
    try:
        import winrm
        
        def _run_powershell():
            port = req.port or (5986 if req.use_ssl else 5985)
            protocol = 'https' if req.use_ssl else 'http'
            
            session = winrm.Session(
                f"{protocol}://{req.host}:{port}/wsman",
                auth=(req.username, req.password),
                transport='ntlm'
            )
            
            result = session.run_ps(req.script)
            
            return {
                "stdout": result.std_out.decode('utf-8') if result.std_out else "",
                "stderr": result.std_err.decode('utf-8') if result.std_err else "",
                "exit_code": result.status_code
            }
        
        result = await asyncio.to_thread(_run_powershell)
        return success_response(result)
        
    except Exception as e:
        logger.error(f"WinRM PowerShell error: {e}")
        return error_response('WINRM_ERROR', str(e))


@router.post("/test")
async def test_winrm_connection(req: WinRMCommandRequest):
    """Test WinRM connectivity."""
    try:
        import winrm
        
        def _test_connection():
            port = req.port or (5986 if req.use_ssl else 5985)
            protocol = 'https' if req.use_ssl else 'http'
            
            session = winrm.Session(
                f"{protocol}://{req.host}:{port}/wsman",
                auth=(req.username, req.password),
                transport='ntlm'
            )
            
            result = session.run_cmd('hostname')
            hostname = result.std_out.decode('utf-8').strip() if result.std_out else ""
            
            return {
                "connected": result.status_code == 0,
                "hostname": hostname
            }
        
        result = await asyncio.to_thread(_test_connection)
        return success_response(result)
        
    except Exception as e:
        logger.error(f"WinRM test error: {e}")
        return error_response('WINRM_ERROR', str(e))
