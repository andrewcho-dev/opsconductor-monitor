"""
Unified Poller

Single poller for SNMP, HTTP API, and SSH polling.
Used by Celery tasks to fetch data from external systems.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PollResult:
    """Result of a poll operation."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class Poller:
    """
    Unified poller for all outbound data collection.
    
    Supports:
    - SNMP GET/WALK/BULK
    - HTTP/REST API calls
    - SSH command execution
    
    Usage:
        poller = Poller()
        result = await poller.poll_snmp(target='10.1.1.1', oids=['1.3.6.1.2.1.1.1.0'])
        result = await poller.poll_api(url='https://api.example.com/alerts')
        result = await poller.poll_ssh(host='10.1.1.1', command='show alarms')
    """
    
    def __init__(self, timeout: float = 10.0, retries: int = 1):
        self.timeout = timeout
        self.retries = retries
        self._stats = {
            'polls_total': 0,
            'polls_success': 0,
            'polls_failed': 0,
        }
    
    async def poll_snmp(
        self,
        target: str,
        oids: List[str],
        community: str = 'public',
        version: str = '2c',
        port: int = 161,
        use_bulk: bool = False,
    ) -> PollResult:
        """
        Poll device via SNMP.
        
        Args:
            target: IP address or hostname
            oids: List of OIDs to query
            community: SNMP community string
            version: SNMP version ('1', '2c', '3')
            port: SNMP port (default 161)
            use_bulk: Use GETBULK for table walks
            
        Returns:
            PollResult with OID values
        """
        import time
        start = time.time()
        self._stats['polls_total'] += 1
        
        try:
            from pysnmp.hlapi.v3arch.asyncio import (
                get_cmd, bulk_cmd, SnmpEngine, CommunityData,
                UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
            )
            
            # Build SNMP version
            mp_model = 0 if version == '1' else 1
            
            results = {}
            
            if use_bulk:
                # Use GETBULK for efficiency
                async for (error_indication, error_status, error_index, var_binds) in bulk_cmd(
                    SnmpEngine(),
                    CommunityData(community, mpModel=mp_model),
                    await UdpTransportTarget.create((target, port), timeout=self.timeout, retries=self.retries),
                    ContextData(),
                    0, 25,  # non-repeaters, max-repetitions
                    *[ObjectType(ObjectIdentity(oid)) for oid in oids]
                ):
                    if error_indication:
                        return PollResult(
                            success=False,
                            data={},
                            error=str(error_indication),
                            duration=time.time() - start
                        )
                    
                    if error_status:
                        return PollResult(
                            success=False,
                            data={},
                            error=f"{error_status.prettyPrint()} at {error_index}",
                            duration=time.time() - start
                        )
                    
                    for var_bind in var_binds:
                        oid = str(var_bind[0])
                        value = var_bind[1].prettyPrint()
                        results[oid] = value
            else:
                # Use GET for specific OIDs
                error_indication, error_status, error_index, var_binds = await get_cmd(
                    SnmpEngine(),
                    CommunityData(community, mpModel=mp_model),
                    await UdpTransportTarget.create((target, port), timeout=self.timeout, retries=self.retries),
                    ContextData(),
                    *[ObjectType(ObjectIdentity(oid)) for oid in oids]
                )
                
                if error_indication:
                    self._stats['polls_failed'] += 1
                    return PollResult(
                        success=False,
                        data={},
                        error=str(error_indication),
                        duration=time.time() - start
                    )
                
                if error_status:
                    self._stats['polls_failed'] += 1
                    return PollResult(
                        success=False,
                        data={},
                        error=f"{error_status.prettyPrint()} at {error_index}",
                        duration=time.time() - start
                    )
                
                for var_bind in var_binds:
                    oid = str(var_bind[0])
                    value = var_bind[1].prettyPrint()
                    results[oid] = value
            
            self._stats['polls_success'] += 1
            return PollResult(
                success=True,
                data={'oids': results, 'target': target},
                duration=time.time() - start
            )
            
        except ImportError:
            return PollResult(
                success=False,
                data={},
                error='pysnmp not installed',
                duration=time.time() - start
            )
        except Exception as e:
            self._stats['polls_failed'] += 1
            return PollResult(
                success=False,
                data={},
                error=str(e),
                duration=time.time() - start
            )
    
    async def poll_api(
        self,
        url: str,
        method: str = 'GET',
        headers: Dict[str, str] = None,
        auth: tuple = None,
        auth_type: str = None,
        api_key: str = None,
        api_key_header: str = 'X-API-Key',
        body: Dict = None,
        verify_ssl: bool = True,
    ) -> PollResult:
        """
        Poll HTTP/REST API.
        
        Args:
            url: Full URL to request
            method: HTTP method (GET, POST, etc.)
            headers: Additional headers
            auth: Auth tuple (username, password)
            auth_type: Authentication type - 'basic', 'digest', or None (addon manifest must specify)
            api_key: API key for authentication
            api_key_header: Header name for API key
            body: Request body for POST/PUT
            verify_ssl: Verify SSL certificates
            
        Returns:
            PollResult with response data
        """
        import time
        import httpx
        
        start = time.time()
        self._stats['polls_total'] += 1
        
        try:
            request_headers = headers or {}
            
            if api_key:
                request_headers[api_key_header] = api_key
            
            auth_obj = None
            if auth:
                logger.debug(f"Using auth_type={auth_type} for {url}")
                if auth_type == 'digest':
                    auth_obj = httpx.DigestAuth(auth[0], auth[1])
                elif auth_type == 'basic':
                    auth_obj = httpx.BasicAuth(auth[0], auth[1])
                else:
                    # Default to basic auth if not specified
                    auth_obj = httpx.BasicAuth(auth[0], auth[1])
            else:
                logger.debug(f"No auth provided for {url}")
            
            async with httpx.AsyncClient(verify=verify_ssl, timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    auth=auth_obj,
                    json=body if body else None
                )
                
                if response.status_code >= 400:
                    self._stats['polls_failed'] += 1
                    return PollResult(
                        success=False,
                        data={'status': response.status_code},
                        error=f"HTTP {response.status_code}",
                        duration=time.time() - start
                    )
                
                # Try to parse JSON response
                try:
                    data = response.json()
                except:
                    data = {'text': response.text}
                
                self._stats['polls_success'] += 1
                return PollResult(
                    success=True,
                    data=data,
                    duration=time.time() - start
                )
                    
        except asyncio.TimeoutError:
            self._stats['polls_failed'] += 1
            return PollResult(
                success=False,
                data={},
                error='Timeout',
                duration=time.time() - start
            )
        except Exception as e:
            self._stats['polls_failed'] += 1
            return PollResult(
                success=False,
                data={},
                error=str(e),
                duration=time.time() - start
            )
    
    async def poll_ssh(
        self,
        host: str,
        command: str,
        username: str = None,
        password: str = None,
        key_file: str = None,
        port: int = 22,
    ) -> PollResult:
        """
        Execute command via SSH.
        
        Args:
            host: Hostname or IP
            command: Command to execute
            username: SSH username
            password: SSH password
            key_file: Path to SSH private key
            port: SSH port
            
        Returns:
            PollResult with command output
        """
        import time
        start = time.time()
        self._stats['polls_total'] += 1
        
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
                    timeout=self.timeout
                )
                
                if result.exit_status != 0:
                    self._stats['polls_failed'] += 1
                    return PollResult(
                        success=False,
                        data={'stdout': result.stdout, 'stderr': result.stderr},
                        error=f"Exit code {result.exit_status}",
                        duration=time.time() - start
                    )
                
                self._stats['polls_success'] += 1
                return PollResult(
                    success=True,
                    data={'stdout': result.stdout, 'host': host, 'command': command},
                    duration=time.time() - start
                )
                
        except ImportError:
            return PollResult(
                success=False,
                data={},
                error='asyncssh not installed',
                duration=time.time() - start
            )
        except asyncio.TimeoutError:
            self._stats['polls_failed'] += 1
            return PollResult(
                success=False,
                data={},
                error='Timeout',
                duration=time.time() - start
            )
        except Exception as e:
            self._stats['polls_failed'] += 1
            return PollResult(
                success=False,
                data={},
                error=str(e),
                duration=time.time() - start
            )
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get poller statistics."""
        return self._stats.copy()


# Global poller instance
_poller: Optional[Poller] = None


def get_poller() -> Poller:
    """Get global poller instance."""
    global _poller
    if _poller is None:
        _poller = Poller()
    return _poller


async def poll_snmp(target: str, oids: List[str], **kwargs) -> PollResult:
    """Convenience function for SNMP polling."""
    return await get_poller().poll_snmp(target, oids, **kwargs)


async def poll_api(url: str, **kwargs) -> PollResult:
    """Convenience function for API polling."""
    return await get_poller().poll_api(url, **kwargs)


async def poll_ssh(host: str, command: str, **kwargs) -> PollResult:
    """Convenience function for SSH polling."""
    return await get_poller().poll_ssh(host, command, **kwargs)
