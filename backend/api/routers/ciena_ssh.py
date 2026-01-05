"""
Ciena SSH API Router - FastAPI.

Routes for Ciena switch SSH operations.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import logging
import asyncio

from backend.utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()


class SSHCommandRequest(BaseModel):
    host: str
    username: str
    password: str
    command: str
    port: int = 22


class SSHBatchCommandRequest(BaseModel):
    host: str
    username: str
    password: str
    commands: List[str]
    port: int = 22


@router.post("/execute")
async def execute_command(req: SSHCommandRequest):
    """Execute a single SSH command on a Ciena switch."""
    try:
        import paramiko
        
        def _run_command():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=req.password,
                timeout=30
            )
            
            stdin, stdout, stderr = client.exec_command(req.command, timeout=60)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            client.close()
            
            return {
                "output": output,
                "error": error,
                "exit_code": exit_code
            }
        
        result = await asyncio.to_thread(_run_command)
        return success_response(result)
        
    except Exception as e:
        logger.error(f"SSH command error: {e}")
        return error_response('SSH_ERROR', str(e))


@router.post("/execute/batch")
async def execute_batch_commands(req: SSHBatchCommandRequest):
    """Execute multiple SSH commands on a Ciena switch."""
    try:
        import paramiko
        
        def _run_commands():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=req.password,
                timeout=30
            )
            
            results = []
            for cmd in req.commands:
                stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')
                exit_code = stdout.channel.recv_exit_status()
                
                results.append({
                    "command": cmd,
                    "output": output,
                    "error": error,
                    "exit_code": exit_code
                })
            
            client.close()
            return results
        
        results = await asyncio.to_thread(_run_commands)
        return success_response({"results": results, "count": len(results)})
        
    except Exception as e:
        logger.error(f"SSH batch command error: {e}")
        return error_response('SSH_ERROR', str(e))


@router.post("/test")
async def test_ssh_connection(req: SSHCommandRequest):
    """Test SSH connectivity to a Ciena switch."""
    try:
        import paramiko
        
        def _test_connection():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=req.password,
                timeout=10
            )
            
            # Run a simple command to verify
            stdin, stdout, stderr = client.exec_command("show system", timeout=10)
            output = stdout.read().decode('utf-8')
            
            client.close()
            
            return {"connected": True, "output_preview": output[:500]}
        
        result = await asyncio.to_thread(_test_connection)
        return success_response(result)
        
    except Exception as e:
        logger.error(f"SSH test error: {e}")
        return error_response('SSH_ERROR', str(e))


@router.get("/interfaces/{host}")
async def get_interfaces_via_ssh(
    host: str,
    username: str,
    password: str,
    port: int = 22
):
    """Get interface information via SSH CLI."""
    try:
        import paramiko
        
        def _get_interfaces():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=30
            )
            
            stdin, stdout, stderr = client.exec_command("port show", timeout=60)
            output = stdout.read().decode('utf-8')
            
            client.close()
            
            # Parse output (basic parsing)
            interfaces = []
            for line in output.split('\n'):
                if line.strip() and not line.startswith('+') and not line.startswith('|Port'):
                    parts = line.split('|')
                    if len(parts) >= 5:
                        interfaces.append({
                            "port": parts[1].strip() if len(parts) > 1 else "",
                            "admin": parts[2].strip() if len(parts) > 2 else "",
                            "oper": parts[3].strip() if len(parts) > 3 else "",
                            "speed": parts[4].strip() if len(parts) > 4 else "",
                        })
            
            return interfaces
        
        interfaces = await asyncio.to_thread(_get_interfaces)
        return success_response({"host": host, "interfaces": interfaces, "count": len(interfaces)})
        
    except Exception as e:
        logger.error(f"SSH interfaces error: {e}")
        return error_response('SSH_ERROR', str(e))
