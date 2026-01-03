"""
Polling Service

High-level service for network device polling that integrates:
- Async SNMP poller for high-performance queries
- NetBox integration for device inventory
- Database storage for metrics
- Credential resolution
- Staggered scheduling

This is the main entry point for all polling operations.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from .async_snmp_poller import (
    AsyncSNMPPoller, AsyncSNMPEngine, SNMPTarget, SNMPResult,
    CommonOIDs, PollerStats
)

logger = logging.getLogger(__name__)


@dataclass
class PollJob:
    """Definition of a polling job."""
    name: str
    device_filter: Dict[str, Any]  # NetBox filter criteria
    oids: List[str]
    interval_seconds: int = 300  # 5 minutes default
    use_bulk: bool = False
    enabled: bool = True
    priority: int = 1  # Higher = more important


@dataclass
class PollResult:
    """Result of a polling job execution."""
    job_name: str
    started_at: datetime
    completed_at: datetime
    total_devices: int
    successful: int
    failed: int
    duration_seconds: float
    stats: PollerStats
    errors: List[Dict[str, str]]


class PollingService:
    """
    Main polling service for network device monitoring.
    
    Coordinates between:
    - NetBox (device inventory)
    - SNMP poller (data collection)
    - Database (metrics storage)
    - Credentials (community strings)
    """
    
    def __init__(
        self,
        netbox_service=None,
        credential_service=None,
        db_connection=None,
        max_concurrent: int = 100,
        batch_size: int = 50,
    ):
        """
        Initialize the polling service.
        
        Args:
            netbox_service: NetBox service for device lookups
            credential_service: Credential service for SNMP communities
            db_connection: Database connection for storing results
            max_concurrent: Max concurrent SNMP sessions
            batch_size: Devices per batch
        """
        self.netbox_service = netbox_service
        self.credential_service = credential_service
        self.db = db_connection
        
        self.poller = AsyncSNMPPoller(
            max_concurrent=max_concurrent,
            batch_size=batch_size,
            stagger_delay=0.005,  # 5ms between queries
            default_timeout=2.0,
            default_retries=1,
        )
        
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._running_jobs: Dict[str, asyncio.Task] = {}
    
    async def poll_all_devices(
        self,
        oids: List[str],
        device_filter: Optional[Dict[str, Any]] = None,
        community: str = "public",
        store_results: bool = True,
    ) -> PollResult:
        """
        Poll all devices (or filtered subset) for specified OIDs.
        
        Args:
            oids: List of OIDs to query
            device_filter: Optional NetBox filter (role, site, etc.)
            community: Default SNMP community
            store_results: Whether to store results in database
        
        Returns:
            PollResult with statistics
        """
        started_at = datetime.utcnow()
        
        # Get devices from NetBox
        devices = await self._get_devices(device_filter)
        
        if not devices:
            logger.warning("No devices found for polling")
            return PollResult(
                job_name="poll_all",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                total_devices=0,
                successful=0,
                failed=0,
                duration_seconds=0,
                stats=PollerStats(),
                errors=[],
            )
        
        # Build SNMP targets with credentials
        targets = await self._build_targets(devices, community)
        
        logger.info(f"Starting poll of {len(targets)} devices for {len(oids)} OIDs")
        
        # Execute polling
        results = await self.poller.poll_devices(targets, oids)
        
        # Process and store results
        successful = 0
        failed = 0
        errors = []
        
        for result in results:
            if result.success:
                successful += 1
                if store_results:
                    await self._store_result(result)
            else:
                failed += 1
                errors.append({
                    "device": result.target.ip,
                    "error": result.error or "Unknown error",
                })
        
        completed_at = datetime.utcnow()
        duration = (completed_at - started_at).total_seconds()
        
        logger.info(
            f"Poll completed: {successful}/{len(targets)} successful "
            f"in {duration:.1f}s ({self.poller.stats.queries_per_second:.1f} q/s)"
        )
        
        return PollResult(
            job_name="poll_all",
            started_at=started_at,
            completed_at=completed_at,
            total_devices=len(targets),
            successful=successful,
            failed=failed,
            duration_seconds=duration,
            stats=self.poller.stats,
            errors=errors[:100],  # Limit error list
        )
    
    async def poll_availability(
        self,
        device_filter: Optional[Dict[str, Any]] = None,
    ) -> PollResult:
        """
        Poll device availability (sysUpTime).
        
        This is a lightweight poll to check if devices are responding.
        """
        return await self.poll_all_devices(
            oids=[CommonOIDs.SYS_UPTIME],
            device_filter=device_filter,
            store_results=True,
        )
    
    async def poll_interfaces(
        self,
        device_filter: Optional[Dict[str, Any]] = None,
    ) -> PollResult:
        """
        Poll interface statistics from switches/routers.
        
        Uses GETBULK for efficient table retrieval.
        """
        # Filter to only switches and routers
        if device_filter is None:
            device_filter = {}
        device_filter['role__in'] = [
            'backbone-switch', 'edge-switch', 'core-router', 'edge-router'
        ]
        
        devices = await self._get_devices(device_filter)
        targets = await self._build_targets(devices, "public")
        
        started_at = datetime.utcnow()
        results = []
        errors = []
        
        # Poll interface table using GETBULK
        for target in targets:
            try:
                # Get interface stats
                result = await self.poller.engine.get_bulk(
                    target,
                    CommonOIDs.IF_TABLE,
                    max_repetitions=50,
                )
                results.append(result)
                
                if result.success:
                    await self._store_interface_metrics(target.ip, result.values)
                else:
                    errors.append({"device": target.ip, "error": result.error})
                    
            except Exception as e:
                errors.append({"device": target.ip, "error": str(e)})
        
        completed_at = datetime.utcnow()
        successful = sum(1 for r in results if r.success)
        
        return PollResult(
            job_name="poll_interfaces",
            started_at=started_at,
            completed_at=completed_at,
            total_devices=len(targets),
            successful=successful,
            failed=len(targets) - successful,
            duration_seconds=(completed_at - started_at).total_seconds(),
            stats=self.poller.stats,
            errors=errors[:100],
        )
    
    async def poll_optical_power(
        self,
        device_filter: Optional[Dict[str, Any]] = None,
    ) -> PollResult:
        """
        Poll optical TX/RX power from switches with SFP ports.
        """
        # Filter to backbone switches (optical)
        if device_filter is None:
            device_filter = {}
        device_filter['role__in'] = ['backbone-switch']
        
        devices = await self._get_devices(device_filter)
        targets = await self._build_targets(devices, "public")
        
        started_at = datetime.utcnow()
        results = []
        errors = []
        
        # Poll optical power OIDs
        optical_oids = [
            CommonOIDs.CIENA_OPT_TX_POWER,
            CommonOIDs.CIENA_OPT_RX_POWER,
        ]
        
        for target in targets:
            try:
                # Use GETBULK for optical table
                tx_result = await self.poller.engine.get_bulk(
                    target, optical_oids[0], max_repetitions=50
                )
                rx_result = await self.poller.engine.get_bulk(
                    target, optical_oids[1], max_repetitions=50
                )
                
                if tx_result.success and rx_result.success:
                    await self._store_optical_metrics(
                        target.ip,
                        tx_result.values,
                        rx_result.values,
                    )
                    results.append(tx_result)
                else:
                    error = tx_result.error or rx_result.error
                    errors.append({"device": target.ip, "error": error})
                    
            except Exception as e:
                errors.append({"device": target.ip, "error": str(e)})
        
        completed_at = datetime.utcnow()
        successful = len(results)
        
        return PollResult(
            job_name="poll_optical",
            started_at=started_at,
            completed_at=completed_at,
            total_devices=len(targets),
            successful=successful,
            failed=len(targets) - successful,
            duration_seconds=(completed_at - started_at).total_seconds(),
            stats=self.poller.stats,
            errors=errors[:100],
        )
    
    async def _get_devices(
        self,
        device_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get devices from NetBox."""
        if self.netbox_service is None:
            logger.warning("NetBox service not configured, using mock data")
            return []
        
        try:
            # Call NetBox service (may need to run in executor if sync)
            loop = asyncio.get_event_loop()
            devices = await loop.run_in_executor(
                self._executor,
                lambda: self.netbox_service.get_devices(device_filter or {}),
            )
            return devices
        except Exception as e:
            logger.error(f"Failed to get devices from NetBox: {e}")
            return []
    
    async def _build_targets(
        self,
        devices: List[Dict[str, Any]],
        default_community: str,
    ) -> List[SNMPTarget]:
        """Build SNMP targets from device list with credentials."""
        targets = []
        
        for device in devices:
            ip = device.get('primary_ip4', {}).get('address', '').split('/')[0]
            if not ip:
                ip = device.get('name', '')
            
            if not ip:
                continue
            
            # Try to get SNMP community from credential service
            community = default_community
            if self.credential_service:
                try:
                    cred = self.credential_service.resolve_device_credentials(
                        ip, credential_type='snmp'
                    )
                    if cred:
                        community = cred.get('community', default_community)
                except Exception:
                    pass
            
            targets.append(SNMPTarget(
                ip=ip,
                community=community,
                device_type=device.get('device_type', {}).get('model', 'unknown'),
                site=device.get('site', {}).get('name', ''),
            ))
        
        return targets
    
    async def _store_result(self, result: SNMPResult):
        """Store poll result in database."""
        if self.db is None:
            return
        
        # This would store to the appropriate metrics table
        # Implementation depends on the specific metrics being collected
        pass
    
    async def _store_interface_metrics(
        self,
        device_ip: str,
        values: Dict[str, Any],
    ):
        """Store interface metrics in database."""
        if self.db is None:
            return
        
        # Parse interface table values and store
        # Implementation depends on database schema
        pass
    
    async def _store_optical_metrics(
        self,
        device_ip: str,
        tx_values: Dict[str, Any],
        rx_values: Dict[str, Any],
    ):
        """Store optical power metrics in database."""
        if self.db is None:
            return
        
        # Parse optical values and store
        # Implementation depends on database schema
        pass


# Celery task wrapper for async polling
def run_poll_job(job_type: str, device_filter: Optional[Dict] = None):
    """
    Celery task wrapper for running poll jobs.
    
    This function is called by Celery and runs the async poller
    in an event loop.
    
    Args:
        job_type: Type of poll job ('availability', 'interfaces', 'optical')
        device_filter: Optional device filter
    
    Returns:
        Dict with poll results
    """
    async def _run():
        # Initialize services (would normally be injected)
        service = PollingService(
            max_concurrent=100,
            batch_size=50,
        )
        
        if job_type == 'availability':
            result = await service.poll_availability(device_filter)
        elif job_type == 'interfaces':
            result = await service.poll_interfaces(device_filter)
        elif job_type == 'optical':
            result = await service.poll_optical_power(device_filter)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
        
        return {
            'job_name': result.job_name,
            'started_at': result.started_at.isoformat(),
            'completed_at': result.completed_at.isoformat(),
            'total_devices': result.total_devices,
            'successful': result.successful,
            'failed': result.failed,
            'duration_seconds': result.duration_seconds,
            'success_rate': result.stats.success_rate,
            'queries_per_second': result.stats.queries_per_second,
            'avg_latency_ms': result.stats.avg_duration * 1000,
            'p95_latency_ms': result.stats.p95_duration * 1000,
            'error_count': len(result.errors),
        }
    
    # Run async function in event loop
    return asyncio.run(_run())


# Quick test function
async def test_polling_service():
    """Test the polling service with mock data."""
    print("Testing Polling Service...")
    
    # Create service without external dependencies
    service = PollingService(
        max_concurrent=50,
        batch_size=25,
    )
    
    # Test with a few IPs (replace with real IPs for actual test)
    test_devices = [
        {"name": "test1", "primary_ip4": {"address": "192.168.10.1/24"}},
        {"name": "test2", "primary_ip4": {"address": "192.168.10.2/24"}},
    ]
    
    # Build targets manually for testing
    targets = [
        SNMPTarget(ip="192.168.10.1", community="public"),
        SNMPTarget(ip="192.168.10.2", community="public"),
    ]
    
    # Test basic poll
    results = await service.poller.poll_devices(
        targets,
        [CommonOIDs.SYS_DESCR, CommonOIDs.SYS_UPTIME],
    )
    
    print(f"\nResults: {len(results)} devices polled")
    print(f"Success rate: {service.poller.stats.success_rate:.1f}%")
    print(f"Avg latency: {service.poller.stats.avg_duration*1000:.1f}ms")
    
    for result in results:
        status = "OK" if result.success else f"FAIL: {result.error}"
        print(f"  {result.target.ip}: {status}")


if __name__ == "__main__":
    asyncio.run(test_polling_service())
