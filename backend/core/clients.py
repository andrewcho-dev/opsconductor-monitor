"""
Client Wrappers for Addon Modules

Provides HTTP, SNMP, and SSH clients that addons use for polling.
These wrap the existing poller functionality with a cleaner interface.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .types import HttpResponse, SnmpResponse, SshResponse

logger = logging.getLogger(__name__)


class HttpClient:
    """
    Async HTTP client for addon modules.
    
    Wraps httpx with connection pooling and standardized responses.
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = None
    
    async def _get_client(self):
        """Get or create httpx client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def get(
        self,
        url: str,
        auth: tuple = None,
        auth_type: str = 'digest',
        headers: dict = None,
        timeout: int = None,
        verify_ssl: bool = True
    ) -> HttpResponse:
        """
        HTTP GET request.
        
        Args:
            url: Full URL to request
            auth: Tuple of (username, password)
            auth_type: 'basic' or 'digest' (default: digest)
            headers: Additional headers
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            
        Returns:
            HttpResponse with success, status_code, data, error
        """
        return await self.request('GET', url, auth=auth, auth_type=auth_type,
                                   headers=headers, timeout=timeout, verify_ssl=verify_ssl)
    
    async def post(
        self,
        url: str,
        data: dict = None,
        json: dict = None,
        auth: tuple = None,
        auth_type: str = 'basic',
        headers: dict = None,
        timeout: int = None,
        verify_ssl: bool = True
    ) -> HttpResponse:
        """
        HTTP POST request.
        
        Args:
            url: Full URL to request
            data: Form data
            json: JSON body
            auth: Tuple of (username, password)
            auth_type: 'basic' or 'digest'
            headers: Additional headers
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            
        Returns:
            HttpResponse with success, status_code, data, error
        """
        return await self.request('POST', url, data=data, json=json, auth=auth,
                                   auth_type=auth_type, headers=headers, 
                                   timeout=timeout, verify_ssl=verify_ssl)
    
    async def request(
        self,
        method: str,
        url: str,
        data: dict = None,
        json: dict = None,
        auth: tuple = None,
        auth_type: str = None,
        headers: dict = None,
        timeout: int = None,
        verify_ssl: bool = True
    ) -> HttpResponse:
        """
        Generic HTTP request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Full URL to request
            data: Form data
            json: JSON body
            auth: Tuple of (username, password)
            auth_type: 'basic' or 'digest'
            headers: Additional headers
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            
        Returns:
            HttpResponse with success, status_code, data, error
        """
        import httpx
        
        start = time.time()
        request_timeout = timeout or self.timeout
        
        try:
            request_headers = headers or {}
            
            # Build auth object
            auth_obj = None
            if auth:
                if auth_type == 'digest':
                    auth_obj = httpx.DigestAuth(auth[0], auth[1])
                else:
                    auth_obj = httpx.BasicAuth(auth[0], auth[1])
            
            async with httpx.AsyncClient(verify=verify_ssl, timeout=request_timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    auth=auth_obj,
                    data=data,
                    json=json
                )
                
                # Parse response
                response_data = None
                response_text = response.text
                
                try:
                    response_data = response.json()
                except:
                    response_data = response_text
                
                duration = time.time() - start
                
                if response.status_code >= 400:
                    return HttpResponse(
                        success=False,
                        status_code=response.status_code,
                        data=response_data,
                        text=response_text,
                        error=f"HTTP {response.status_code}",
                        headers=dict(response.headers),
                        duration=duration
                    )
                
                return HttpResponse(
                    success=True,
                    status_code=response.status_code,
                    data=response_data,
                    text=response_text,
                    headers=dict(response.headers),
                    duration=duration
                )
                
        except asyncio.TimeoutError:
            return HttpResponse(
                success=False,
                status_code=0,
                error='Timeout',
                duration=time.time() - start
            )
        except Exception as e:
            return HttpResponse(
                success=False,
                status_code=0,
                error=str(e),
                duration=time.time() - start
            )
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class SnmpClient:
    """
    SNMP client for addon modules.
    
    Wraps pysnmp for SNMP GET and WALK operations.
    """
    
    def __init__(self, timeout: float = 10.0, retries: int = 1):
        self.timeout = timeout
        self.retries = retries
    
    async def get(
        self,
        host: str,
        oids: List[str],
        community: str = 'public',
        version: str = '2c',
        port: int = 161
    ) -> SnmpResponse:
        """
        SNMP GET request.
        
        Args:
            host: Target IP or hostname
            oids: List of OIDs to query
            community: SNMP community string
            version: SNMP version ('1', '2c')
            port: SNMP port
            
        Returns:
            SnmpResponse with OID -> value mapping
        """
        start = time.time()
        
        try:
            from pysnmp.hlapi.v3arch.asyncio import (
                get_cmd, SnmpEngine, CommunityData,
                UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
            )
            
            mp_model = 0 if version == '1' else 1
            
            error_indication, error_status, error_index, var_binds = await get_cmd(
                SnmpEngine(),
                CommunityData(community, mpModel=mp_model),
                await UdpTransportTarget.create((host, port), timeout=self.timeout, retries=self.retries),
                ContextData(),
                *[ObjectType(ObjectIdentity(oid)) for oid in oids]
            )
            
            if error_indication:
                return SnmpResponse(
                    success=False,
                    error=str(error_indication),
                    duration=time.time() - start
                )
            
            if error_status:
                return SnmpResponse(
                    success=False,
                    error=f"{error_status.prettyPrint()} at {error_index}",
                    duration=time.time() - start
                )
            
            results = {}
            for var_bind in var_binds:
                oid = str(var_bind[0])
                value = var_bind[1].prettyPrint()
                results[oid] = value
            
            return SnmpResponse(
                success=True,
                data=results,
                duration=time.time() - start
            )
            
        except ImportError:
            return SnmpResponse(
                success=False,
                error='pysnmp not installed',
                duration=time.time() - start
            )
        except Exception as e:
            return SnmpResponse(
                success=False,
                error=str(e),
                duration=time.time() - start
            )
    
    async def walk(
        self,
        host: str,
        oid: str,
        community: str = 'public',
        version: str = '2c',
        port: int = 161
    ) -> SnmpResponse:
        """
        SNMP WALK (GETBULK) request.
        
        Args:
            host: Target IP or hostname
            oid: Base OID to walk
            community: SNMP community string
            version: SNMP version ('1', '2c')
            port: SNMP port
            
        Returns:
            SnmpResponse with OID -> value mapping for all sub-OIDs
        """
        start = time.time()
        
        try:
            from pysnmp.hlapi.v3arch.asyncio import (
                bulk_cmd, SnmpEngine, CommunityData,
                UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
            )
            
            mp_model = 0 if version == '1' else 1
            results = {}
            
            async for (error_indication, error_status, error_index, var_binds) in bulk_cmd(
                SnmpEngine(),
                CommunityData(community, mpModel=mp_model),
                await UdpTransportTarget.create((host, port), timeout=self.timeout, retries=self.retries),
                ContextData(),
                0, 25,  # non-repeaters, max-repetitions
                ObjectType(ObjectIdentity(oid))
            ):
                if error_indication:
                    return SnmpResponse(
                        success=False,
                        error=str(error_indication),
                        duration=time.time() - start
                    )
                
                if error_status:
                    return SnmpResponse(
                        success=False,
                        error=f"{error_status.prettyPrint()} at {error_index}",
                        duration=time.time() - start
                    )
                
                for var_bind in var_binds:
                    result_oid = str(var_bind[0])
                    # Stop if we've walked past the base OID
                    if not result_oid.startswith(oid):
                        break
                    value = var_bind[1].prettyPrint()
                    results[result_oid] = value
            
            return SnmpResponse(
                success=True,
                data=results,
                duration=time.time() - start
            )
            
        except ImportError:
            return SnmpResponse(
                success=False,
                error='pysnmp not installed',
                duration=time.time() - start
            )
        except Exception as e:
            return SnmpResponse(
                success=False,
                error=str(e),
                duration=time.time() - start
            )


class SshClient:
    """
    SSH client for addon modules.
    
    Wraps asyncssh for command execution.
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
    
    async def exec(
        self,
        host: str,
        command: str,
        username: str,
        password: str = None,
        key_file: str = None,
        port: int = 22,
        timeout: int = None
    ) -> SshResponse:
        """
        Execute SSH command.
        
        Args:
            host: Target IP or hostname
            command: Command to execute
            username: SSH username
            password: SSH password
            key_file: Path to SSH private key
            port: SSH port
            timeout: Command timeout in seconds
            
        Returns:
            SshResponse with stdout, stderr, exit_code
        """
        start = time.time()
        exec_timeout = timeout or self.timeout
        
        try:
            import asyncssh
            
            connect_kwargs = {
                'host': host,
                'port': port,
                'username': username,
                'known_hosts': None,  # Don't check host keys
            }
            
            if password:
                connect_kwargs['password'] = password
            if key_file:
                connect_kwargs['client_keys'] = [key_file]
            
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await asyncio.wait_for(
                    conn.run(command),
                    timeout=exec_timeout
                )
                
                duration = time.time() - start
                
                if result.exit_status != 0:
                    return SshResponse(
                        success=False,
                        stdout=result.stdout or "",
                        stderr=result.stderr or "",
                        exit_code=result.exit_status,
                        error=f"Exit code {result.exit_status}",
                        duration=duration
                    )
                
                return SshResponse(
                    success=True,
                    stdout=result.stdout or "",
                    stderr=result.stderr or "",
                    exit_code=result.exit_status,
                    duration=duration
                )
                
        except ImportError:
            return SshResponse(
                success=False,
                error='asyncssh not installed',
                duration=time.time() - start
            )
        except asyncio.TimeoutError:
            return SshResponse(
                success=False,
                error='Timeout',
                duration=time.time() - start
            )
        except Exception as e:
            return SshResponse(
                success=False,
                error=str(e),
                duration=time.time() - start
            )


class Clients:
    """
    Container for all client instances.
    
    Passed to addon poll functions for dependency injection.
    """
    
    def __init__(self, http_timeout: float = 30.0, snmp_timeout: float = 10.0, ssh_timeout: float = 30.0):
        self.http = HttpClient(timeout=http_timeout)
        self.snmp = SnmpClient(timeout=snmp_timeout)
        self.ssh = SshClient(timeout=ssh_timeout)
    
    async def close(self):
        """Close all clients."""
        await self.http.close()


# Global clients instance
_clients: Optional[Clients] = None


def get_clients() -> Clients:
    """Get global clients instance."""
    global _clients
    if _clients is None:
        _clients = Clients()
    return _clients
