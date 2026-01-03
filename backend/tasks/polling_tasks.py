"""
Celery Tasks for SNMP Polling

High-performance polling tasks using the async SNMP poller.
These tasks are designed to be run by dedicated polling workers.

Queue: 'polling' (high priority, dedicated workers)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from celery import shared_task

logger = logging.getLogger(__name__)


def _get_event_loop():
    """Get or create event loop for async tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def _run_async(coro):
    """Run async coroutine in Celery task context."""
    loop = _get_event_loop()
    return loop.run_until_complete(coro)


@shared_task(
    name='polling.availability',
    queue='polling',
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def poll_availability(self, device_filter: Optional[Dict] = None):
    """
    Poll device availability across the network.
    
    This is a lightweight poll that checks if devices are responding
    to SNMP queries. Results are stored in availability_metrics table.
    
    Args:
        device_filter: Optional NetBox filter (site, role, etc.)
    
    Returns:
        Dict with poll statistics
    """
    from ..services.polling_service import PollingService
    from ..services.netbox_service import NetBoxService
    from ..services.credential_service import CredentialService
    
    async def _poll():
        # Initialize services
        netbox = NetBoxService()
        credentials = CredentialService()
        
        service = PollingService(
            netbox_service=netbox,
            credential_service=credentials,
            max_concurrent=100,
            batch_size=50,
        )
        
        result = await service.poll_availability(device_filter)
        
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
        }
    
    try:
        return _run_async(_poll())
    except Exception as e:
        logger.error(f"Availability poll failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(
    name='polling.interfaces',
    queue='polling',
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=720,
)
def poll_interfaces(self, device_filter: Optional[Dict] = None):
    """
    Poll interface statistics from switches and routers.
    
    Collects traffic counters, error counts, and operational status
    for all interfaces. Uses GETBULK for efficient retrieval.
    
    Args:
        device_filter: Optional NetBox filter
    
    Returns:
        Dict with poll statistics
    """
    from ..services.polling_service import PollingService
    from ..services.netbox_service import NetBoxService
    from ..services.credential_service import CredentialService
    
    async def _poll():
        netbox = NetBoxService()
        credentials = CredentialService()
        
        service = PollingService(
            netbox_service=netbox,
            credential_service=credentials,
            max_concurrent=50,  # Lower for bulk queries
            batch_size=25,
        )
        
        result = await service.poll_interfaces(device_filter)
        
        return {
            'job_name': result.job_name,
            'started_at': result.started_at.isoformat(),
            'completed_at': result.completed_at.isoformat(),
            'total_devices': result.total_devices,
            'successful': result.successful,
            'failed': result.failed,
            'duration_seconds': result.duration_seconds,
            'success_rate': result.stats.success_rate,
        }
    
    try:
        return _run_async(_poll())
    except Exception as e:
        logger.error(f"Interface poll failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(
    name='polling.optical',
    queue='polling',
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def poll_optical_power(self, device_filter: Optional[Dict] = None):
    """
    Poll optical TX/RX power from switches with SFP ports.
    
    Collects optical power readings for anomaly detection
    and trending. Targets backbone switches with optical interfaces.
    
    Args:
        device_filter: Optional NetBox filter
    
    Returns:
        Dict with poll statistics
    """
    from ..services.polling_service import PollingService
    from ..services.netbox_service import NetBoxService
    from ..services.credential_service import CredentialService
    
    async def _poll():
        netbox = NetBoxService()
        credentials = CredentialService()
        
        service = PollingService(
            netbox_service=netbox,
            credential_service=credentials,
            max_concurrent=50,
            batch_size=25,
        )
        
        result = await service.poll_optical_power(device_filter)
        
        return {
            'job_name': result.job_name,
            'started_at': result.started_at.isoformat(),
            'completed_at': result.completed_at.isoformat(),
            'total_devices': result.total_devices,
            'successful': result.successful,
            'failed': result.failed,
            'duration_seconds': result.duration_seconds,
            'success_rate': result.stats.success_rate,
        }
    
    try:
        return _run_async(_poll())
    except Exception as e:
        logger.error(f"Optical poll failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(
    name='polling.custom',
    queue='polling',
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=720,
)
def poll_custom_oids(
    self,
    oids: List[str],
    device_filter: Optional[Dict] = None,
    community: str = "public",
    use_bulk: bool = False,
):
    """
    Poll custom OIDs from devices.
    
    Flexible polling task for any SNMP OIDs.
    
    Args:
        oids: List of OIDs to query
        device_filter: Optional NetBox filter
        community: SNMP community string
        use_bulk: Use GETBULK instead of GET
    
    Returns:
        Dict with poll results
    """
    from ..services.polling_service import PollingService
    from ..services.netbox_service import NetBoxService
    from ..services.credential_service import CredentialService
    
    async def _poll():
        netbox = NetBoxService()
        credentials = CredentialService()
        
        service = PollingService(
            netbox_service=netbox,
            credential_service=credentials,
            max_concurrent=100,
            batch_size=50,
        )
        
        result = await service.poll_all_devices(
            oids=oids,
            device_filter=device_filter,
            community=community,
            store_results=True,
        )
        
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
        }
    
    try:
        return _run_async(_poll())
    except Exception as e:
        logger.error(f"Custom poll failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(
    name='polling.batch_devices',
    queue='polling',
    bind=True,
    soft_time_limit=120,
    time_limit=180,
)
def poll_device_batch(
    self,
    device_ips: List[str],
    oids: List[str],
    community: str = "public",
):
    """
    Poll a specific batch of devices.
    
    Used for targeted polling of specific devices rather than
    full network scans. Useful for on-demand queries.
    
    Args:
        device_ips: List of device IP addresses
        oids: List of OIDs to query
        community: SNMP community string
    
    Returns:
        Dict with device results
    """
    from ..services.async_snmp_poller import (
        AsyncSNMPPoller, SNMPTarget
    )
    
    async def _poll():
        targets = [
            SNMPTarget(ip=ip, community=community)
            for ip in device_ips
        ]
        
        poller = AsyncSNMPPoller(
            max_concurrent=len(targets),
            batch_size=len(targets),
            stagger_delay=0.001,
        )
        
        results = await poller.poll_devices(targets, oids)
        
        return {
            'total': len(results),
            'successful': sum(1 for r in results if r.success),
            'failed': sum(1 for r in results if not r.success),
            'results': [
                {
                    'ip': r.target.ip,
                    'success': r.success,
                    'values': r.values if r.success else {},
                    'error': r.error,
                    'duration_ms': r.duration * 1000,
                }
                for r in results
            ],
            'stats': {
                'success_rate': poller.stats.success_rate,
                'avg_latency_ms': poller.stats.avg_duration * 1000,
                'queries_per_second': poller.stats.queries_per_second,
            },
        }
    
    return _run_async(_poll())


# Scheduled polling configuration
POLLING_SCHEDULE = {
    'poll-availability-5min': {
        'task': 'polling.availability',
        'schedule': 300,  # 5 minutes
        'options': {'queue': 'polling'},
    },
    'poll-interfaces-5min': {
        'task': 'polling.interfaces',
        'schedule': 300,  # 5 minutes
        'options': {'queue': 'polling'},
    },
    'poll-optical-5min': {
        'task': 'polling.optical',
        'schedule': 300,  # 5 minutes
        'options': {'queue': 'polling'},
    },
}
