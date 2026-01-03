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
    from backend.database import DatabaseConnection
    from ..services.async_snmp_poller import AsyncSNMPPoller, SNMPTarget, CommonOIDs
    
    async def _poll():
        # Get devices from local cache
        db = DatabaseConnection()
        with db.cursor() as cursor:
            query = """
                SELECT device_ip, device_name, role_name, site_name
                FROM netbox_device_cache
                WHERE device_ip IS NOT NULL
            """
            params = []
            if device_filter:
                if device_filter.get('role'):
                    query += " AND role_name = %s"
                    params.append(device_filter['role'])
                if device_filter.get('site'):
                    query += " AND site_name = %s"
                    params.append(device_filter['site'])
            query += " LIMIT 2000"  # Poll all devices
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        if not rows:
            logger.warning("No devices found for polling")
            from datetime import datetime
            return {
                'job_name': 'poll_availability',
                'started_at': datetime.utcnow().isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
                'total_devices': 0,
                'successful': 0,
                'failed': 0,
                'duration_seconds': 0,
            }
        
        # Build SNMP targets
        targets = [
            SNMPTarget(
                ip=str(row['device_ip']),
                community='public',
                device_type=row.get('role_name', 'unknown'),
                site=row.get('site_name', ''),
            )
            for row in rows
        ]
        
        logger.info(f"Polling availability for {len(targets)} devices")
        
        # Create poller and poll
        poller = AsyncSNMPPoller(max_concurrent=100, batch_size=50)
        from datetime import datetime
        started_at = datetime.utcnow()
        
        results = await poller.poll_devices(targets, [CommonOIDs.SYS_UPTIME])
        
        completed_at = datetime.utcnow()
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        # Store results in availability_metrics
        with db.cursor() as cursor:
            for result in results:
                status = 'up' if result.success else 'down'
                latency = result.duration * 1000 if result.duration else None
                cursor.execute("""
                    INSERT INTO availability_metrics 
                    (device_ip, ping_status, ping_latency_ms, snmp_status, snmp_response_ms, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (result.target.ip, status, latency, status, latency))
            db.get_connection().commit()
        
        logger.info(f"Availability poll complete: {successful}/{len(targets)} successful")
        
        return {
            'job_name': 'poll_availability',
            'started_at': started_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'total_devices': len(targets),
            'successful': successful,
            'failed': failed,
            'duration_seconds': (completed_at - started_at).total_seconds(),
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
    from backend.database import DatabaseConnection
    from ..services.async_snmp_poller import AsyncSNMPPoller, SNMPTarget, CommonOIDs
    
    async def _poll():
        # Get switches from local cache
        db = DatabaseConnection()
        with db.cursor() as cursor:
            query = """
                SELECT device_ip, device_name, role_name, site_name
                FROM netbox_device_cache
                WHERE device_ip IS NOT NULL
                AND role_name IN ('Backbone Switch', 'backbone-switch', 'Core Switch', 'core-switch', 
                                  'Edge Switch', 'edge-switch', 'Access Switch', 'access-switch')
            """
            params = []
            if device_filter:
                if device_filter.get('site'):
                    query += " AND site_name = %s"
                    params.append(device_filter['site'])
            query += " LIMIT 200"
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        if not rows:
            logger.warning("No switches found for interface polling")
            from datetime import datetime
            return {
                'job_name': 'poll_interfaces',
                'started_at': datetime.utcnow().isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
                'total_devices': 0,
                'successful': 0,
                'failed': 0,
                'duration_seconds': 0,
            }
        
        # Build SNMP targets
        targets = [
            SNMPTarget(
                ip=str(row['device_ip']),
                community='public',
                device_type=row.get('role_name', 'unknown'),
                site=row.get('site_name', ''),
            )
            for row in rows
        ]
        
        logger.info(f"Polling interfaces for {len(targets)} switches")
        
        # Create poller
        poller = AsyncSNMPPoller(max_concurrent=25, batch_size=10)
        from datetime import datetime
        started_at = datetime.utcnow()
        
        successful = 0
        failed = 0
        total_interfaces = 0
        
        # Poll each device for interface stats
        for target in targets:
            try:
                # Get interface names, in/out octets, errors
                if_names = await poller.engine.get_bulk(target, CommonOIDs.IF_DESCR, max_repetitions=50)
                if_in_octets = await poller.engine.get_bulk(target, CommonOIDs.IF_IN_OCTETS, max_repetitions=50)
                if_out_octets = await poller.engine.get_bulk(target, CommonOIDs.IF_OUT_OCTETS, max_repetitions=50)
                if_in_errors = await poller.engine.get_bulk(target, CommonOIDs.IF_IN_ERRORS, max_repetitions=50)
                if_out_errors = await poller.engine.get_bulk(target, CommonOIDs.IF_OUT_ERRORS, max_repetitions=50)
                
                if if_names.success:
                    successful += 1
                    # Store interface metrics
                    with db.cursor() as cursor:
                        for oid, if_name in if_names.values.items():
                            if_index = int(oid.split('.')[-1])
                            
                            in_octets_oid = f"{CommonOIDs.IF_IN_OCTETS}.{if_index}"
                            out_octets_oid = f"{CommonOIDs.IF_OUT_OCTETS}.{if_index}"
                            in_errors_oid = f"{CommonOIDs.IF_IN_ERRORS}.{if_index}"
                            out_errors_oid = f"{CommonOIDs.IF_OUT_ERRORS}.{if_index}"
                            
                            rx_bytes = if_in_octets.values.get(in_octets_oid) if if_in_octets.success else None
                            tx_bytes = if_out_octets.values.get(out_octets_oid) if if_out_octets.success else None
                            rx_errors = if_in_errors.values.get(in_errors_oid) if if_in_errors.success else None
                            tx_errors = if_out_errors.values.get(out_errors_oid) if if_out_errors.success else None
                            
                            cursor.execute("""
                                INSERT INTO interface_metrics 
                                (device_ip, interface_name, interface_index, rx_bytes, tx_bytes, rx_errors, tx_errors, recorded_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            """, (target.ip, str(if_name), if_index, rx_bytes, tx_bytes, rx_errors, tx_errors))
                            total_interfaces += 1
                        
                        db.get_connection().commit()
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Interface poll failed for {target.ip}: {e}")
                failed += 1
        
        completed_at = datetime.utcnow()
        logger.info(f"Interface poll complete: {successful}/{len(targets)} devices, {total_interfaces} interfaces")
        
        return {
            'job_name': 'poll_interfaces',
            'started_at': started_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'total_devices': len(targets),
            'successful': successful,
            'failed': failed,
            'total_interfaces': total_interfaces,
            'duration_seconds': (completed_at - started_at).total_seconds(),
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
    from backend.database import DatabaseConnection
    from ..services.async_snmp_poller import AsyncSNMPPoller, SNMPTarget, CommonOIDs
    
    async def _poll():
        # Get backbone switches from local cache
        db = DatabaseConnection()
        with db.cursor() as cursor:
            query = """
                SELECT device_ip, device_name, role_name, site_name
                FROM netbox_device_cache
                WHERE device_ip IS NOT NULL
                AND role_name IN ('Backbone Switch', 'backbone-switch', 'Core Switch', 'core-switch')
            """
            params = []
            if device_filter:
                if device_filter.get('site'):
                    query += " AND site_name = %s"
                    params.append(device_filter['site'])
            query += " LIMIT 100"
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        if not rows:
            logger.warning("No backbone switches found for optical polling")
            from datetime import datetime
            return {
                'job_name': 'poll_optical',
                'started_at': datetime.utcnow().isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
                'total_devices': 0,
                'successful': 0,
                'failed': 0,
                'duration_seconds': 0,
            }
        
        # Build SNMP targets
        targets = [
            SNMPTarget(
                ip=str(row['device_ip']),
                community='public',
                device_type=row.get('role_name', 'unknown'),
                site=row.get('site_name', ''),
            )
            for row in rows
        ]
        
        logger.info(f"Polling optical power for {len(targets)} backbone switches")
        
        # Create poller
        poller = AsyncSNMPPoller(max_concurrent=50, batch_size=25)
        from datetime import datetime
        started_at = datetime.utcnow()
        
        successful = 0
        failed = 0
        
        # Poll each device for optical power
        # Try both WWP-LEOS (older Ciena) and CES (newer Ciena) OIDs
        for target in targets:
            try:
                # Try WWP-LEOS OIDs first (most common for Ciena 3930 etc)
                tx_result = await poller.engine.get_bulk(
                    target, CommonOIDs.CIENA_WWP_TX_POWER, max_repetitions=50
                )
                rx_result = await poller.engine.get_bulk(
                    target, CommonOIDs.CIENA_WWP_RX_POWER, max_repetitions=50
                )
                
                # If WWP-LEOS fails, try CES OIDs
                if not tx_result.success and not rx_result.success:
                    tx_result = await poller.engine.get_bulk(
                        target, CommonOIDs.CIENA_CES_TX_POWER, max_repetitions=50
                    )
                    rx_result = await poller.engine.get_bulk(
                        target, CommonOIDs.CIENA_CES_RX_POWER, max_repetitions=50
                    )
                
                if tx_result.success or rx_result.success:
                    successful += 1
                    # Store optical metrics
                    with db.cursor() as cursor:
                        tx_values = tx_result.values if tx_result.success else {}
                        rx_values = rx_result.values if rx_result.success else {}
                        
                        # Combine TX and RX by interface index
                        all_indexes = set()
                        for oid in tx_values.keys():
                            all_indexes.add(int(oid.split('.')[-1]))
                        for oid in rx_values.keys():
                            all_indexes.add(int(oid.split('.')[-1]))
                        
                        records_stored = 0
                        for if_index in all_indexes:
                            # Check both OID formats (with and without leading dot)
                            tx_power = None
                            rx_power = None
                            for base_tx in [CommonOIDs.CIENA_WWP_TX_POWER, CommonOIDs.CIENA_CES_TX_POWER]:
                                for prefix in ['', '.']:
                                    tx_oid = f"{prefix}{base_tx}.{if_index}"
                                    if tx_oid in tx_values:
                                        tx_power = tx_values[tx_oid]
                                        break
                                if tx_power:
                                    break
                            for base_rx in [CommonOIDs.CIENA_WWP_RX_POWER, CommonOIDs.CIENA_CES_RX_POWER]:
                                for prefix in ['', '.']:
                                    rx_oid = f"{prefix}{base_rx}.{if_index}"
                                    if rx_oid in rx_values:
                                        rx_power = rx_values[rx_oid]
                                        break
                                if rx_power:
                                    break
                            
                            # Only store if we have actual power readings (non-zero)
                            tx_val = int(tx_power) if tx_power else 0
                            rx_val = int(rx_power) if rx_power else 0
                            
                            if tx_val > 0 or rx_val > 0:
                                # Values are in micro-watts, convert to dBm
                                # dBm = 10 * log10(uW / 1000)
                                import math
                                tx_dbm = None
                                rx_dbm = None
                                if tx_val > 0:
                                    tx_dbm = 10 * math.log10(tx_val / 1000.0)
                                if rx_val > 0:
                                    rx_dbm = 10 * math.log10(rx_val / 1000.0)
                                
                                if tx_dbm is not None or rx_dbm is not None:
                                    cursor.execute("""
                                        INSERT INTO optical_metrics 
                                        (device_ip, interface_name, interface_index, tx_power, rx_power, recorded_at)
                                        VALUES (%s, %s, %s, %s, %s, NOW())
                                    """, (target.ip, f'port{if_index}', if_index, tx_dbm, rx_dbm))
                                    records_stored += 1
                        
                        if records_stored > 0:
                            db.get_connection().commit()
                            logger.debug(f"Stored {records_stored} optical readings for {target.ip}")
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Optical poll failed for {target.ip}: {e}")
                failed += 1
        
        completed_at = datetime.utcnow()
        logger.info(f"Optical poll complete: {successful}/{len(targets)} successful")
        
        return {
            'job_name': 'poll_optical',
            'started_at': started_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'total_devices': len(targets),
            'successful': successful,
            'failed': failed,
            'duration_seconds': (completed_at - started_at).total_seconds(),
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
