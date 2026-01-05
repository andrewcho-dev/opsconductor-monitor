"""
Generic Database-Driven Polling Task

This task reads polling configuration from the database and executes SNMP polls
based on the MIB mappings defined in snmp_oid_mappings table.

All polling should go through this task - no hardcoded OIDs.
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


class MibMappingLoader:
    """
    Loads OID mappings from the database for a given poll type.
    """
    
    def __init__(self, db):
        self.db = db
    
    def get_poll_type(self, poll_type_name: str) -> Optional[Dict]:
        """Get poll type definition from database."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT pt.*, p.name as profile_name, p.vendor, p.enterprise_oid
                FROM snmp_poll_types pt
                JOIN snmp_profiles p ON p.id = pt.profile_id
                WHERE pt.name = %s AND pt.enabled = true
            """, (poll_type_name,))
            return cursor.fetchone()
    
    def get_oids_for_poll_type(self, poll_type_name: str) -> List[Dict]:
        """
        Get all OID mappings for a poll type.
        
        Returns list of dicts with:
        - oid: The OID string
        - name: Field name (e.g., 'rx_power_dbm')
        - transform: Transformation to apply (e.g., 'divide:10000')
        - data_type: Data type (integer, counter, string, etc.)
        - group_name: The OID group name
        - is_table: Whether this is a table walk
        """
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.oid,
                    m.name,
                    m.transform,
                    m.data_type,
                    m.unit,
                    m.is_index,
                    g.name as group_name,
                    g.is_table,
                    g.base_oid
                FROM snmp_oid_mappings m
                JOIN snmp_oid_groups g ON g.id = m.group_id
                JOIN snmp_poll_type_groups ptg ON ptg.group_id = g.id
                JOIN snmp_poll_types pt ON pt.id = ptg.poll_type_id
                WHERE pt.name = %s
                ORDER BY ptg.poll_order, m.name
            """, (poll_type_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_oids_for_profile(self, profile_name: str) -> List[Dict]:
        """Get all OIDs for a vendor profile (e.g., 'ciena_saos6')."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.oid,
                    m.name,
                    m.transform,
                    m.data_type,
                    m.unit,
                    g.name as group_name,
                    g.is_table,
                    g.base_oid
                FROM snmp_oid_mappings m
                JOIN snmp_oid_groups g ON g.id = m.group_id
                JOIN snmp_profiles p ON p.id = g.profile_id
                WHERE p.name = %s
                ORDER BY g.name, m.name
            """, (profile_name,))
            return [dict(row) for row in cursor.fetchall()]


def apply_transform(value: Any, transform: str) -> Any:
    """Apply transformation to SNMP value based on transform string."""
    if not transform or value is None:
        return value
    
    try:
        if transform.startswith('divide:'):
            divisor = float(transform.split(':')[1])
            return float(value) / divisor
        elif transform.startswith('multiply:'):
            multiplier = float(transform.split(':')[1])
            return float(value) * multiplier
        elif transform == 'hex_to_mac':
            # Convert hex string to MAC address
            if isinstance(value, bytes):
                return ':'.join(f'{b:02x}' for b in value)
            return str(value)
        elif transform == 'timeticks_to_seconds':
            return int(value) / 100
    except (ValueError, TypeError, IndexError):
        pass
    
    return value


def parse_snmp_results(results: Dict[str, Any], oid_mappings: List[Dict]) -> Dict[str, Dict]:
    """
    Parse SNMP results using OID mappings.
    
    Returns dict keyed by index (e.g., port number) with field values.
    """
    parsed = {}  # index -> {field_name: value}
    
    for oid, raw_value in results.items():
        # Normalize OID - remove leading dot if present
        normalized_oid = oid.lstrip('.')
        
        # Find matching mapping
        for mapping in oid_mappings:
            mapping_oid = mapping['oid'].lstrip('.')
            
            # Check if this result OID starts with the mapping OID
            if normalized_oid.startswith(mapping_oid + '.') or normalized_oid == mapping_oid:
                try:
                    # Extract index from OID (last component after the base OID)
                    index = int(normalized_oid.split('.')[-1])
                    
                    if index not in parsed:
                        parsed[index] = {}
                    
                    # Apply transform
                    value = apply_transform(raw_value, mapping.get('transform'))
                    parsed[index][mapping['name']] = value
                    parsed[index][f"_group_{mapping['name']}"] = mapping['group_name']
                    
                except (ValueError, IndexError):
                    continue
                break
    
    return parsed


@shared_task(
    name='polling.generic',
    queue='polling',
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def poll_by_type(
    self,
    poll_type_name: str,
    device_filter: Optional[Dict] = None,
    config_id: Optional[int] = None,
):
    """
    Generic polling task that uses database-driven MIB mappings.
    
    This is the main polling task - all polling should go through here.
    
    Args:
        poll_type_name: Name of poll type from snmp_poll_types table
                       (e.g., 'ciena_optical', 'ciena_traffic', 'ciena_raps')
        device_filter: Optional device filter (manufacturer, site, role)
        config_id: Optional polling_configs ID for tracking
    
    Returns:
        Dict with poll statistics
    """
    from backend.database import DatabaseConnection
    from backend.services.async_snmp_poller import AsyncSNMPPoller, SNMPTarget
    
    async def _poll():
        db = DatabaseConnection()
        started_at = datetime.utcnow()
        
        # Load poll type and OID mappings from database
        loader = MibMappingLoader(db)
        poll_type = loader.get_poll_type(poll_type_name)
        
        if not poll_type:
            logger.error(f"Poll type '{poll_type_name}' not found or disabled")
            return {
                'job_name': poll_type_name,
                'started_at': started_at.isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
                'error': f"Poll type '{poll_type_name}' not found",
                'total_devices': 0,
                'successful': 0,
                'failed': 0,
            }
        
        oid_mappings = loader.get_oids_for_poll_type(poll_type_name)
        
        if not oid_mappings:
            logger.error(f"No OID mappings found for poll type '{poll_type_name}'")
            return {
                'job_name': poll_type_name,
                'started_at': started_at.isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
                'error': 'No OID mappings configured',
                'total_devices': 0,
                'successful': 0,
                'failed': 0,
            }
        
        # Get unique base OIDs for walking
        oids_to_poll = list(set(m['oid'] for m in oid_mappings))
        
        logger.info(f"Poll type '{poll_type_name}': {len(oids_to_poll)} OIDs from {len(oid_mappings)} mappings")
        
        # Get target devices based on vendor profile and filter
        vendor = poll_type['vendor']
        with db.cursor() as cursor:
            query = """
                SELECT device_ip, device_name, site_name, manufacturer
                FROM netbox_device_cache
                WHERE device_ip IS NOT NULL
            """
            params = []
            
            # Filter by vendor/manufacturer
            if vendor:
                query += " AND manufacturer ILIKE %s"
                params.append(f"%{vendor}%")
            
            # Apply additional filters
            if device_filter:
                if device_filter.get('site'):
                    query += " AND site_name = %s"
                    params.append(device_filter['site'])
                if device_filter.get('role'):
                    query += " AND role_name = %s"
                    params.append(device_filter['role'])
                if device_filter.get('manufacturer'):
                    query += " AND manufacturer ILIKE %s"
                    params.append(f"%{device_filter['manufacturer']}%")
            
            cursor.execute(query, params if params else None)
            rows = cursor.fetchall()
        
        if not rows:
            logger.warning(f"No devices found for poll type '{poll_type_name}'")
            return {
                'job_name': poll_type_name,
                'started_at': started_at.isoformat(),
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
                community='public',  # TODO: Get from credential service
                device_type=row.get('manufacturer', 'unknown'),
                site=row.get('site_name', ''),
            )
            for row in rows
        ]
        
        logger.info(f"Polling {len(targets)} devices for '{poll_type_name}'")
        
        # Create async poller - optimized for 1000+ devices
        # max_concurrent=200: Allow 200 simultaneous SNMP connections
        # batch_size=50: Process 50 devices per batch for better throughput
        # default_timeout=5: Reduce timeout for faster failure detection
        poller = AsyncSNMPPoller(max_concurrent=200, batch_size=50, default_timeout=5)
        
        # Poll all devices
        results = await poller.walk_devices(targets, oids_to_poll)
        
        completed_at = datetime.utcnow()
        successful = 0
        failed = 0
        records_stored = 0
        
        # Process and store results
        target_table = poll_type.get('target_table')
        
        with db.cursor() as cursor:
            for result in results:
                if result.success and result.values:
                    successful += 1
                    
                    # Parse results using OID mappings
                    parsed_data = parse_snmp_results(result.values, oid_mappings)
                    
                    # Store in target table or generic polling_data
                    if target_table:
                        records_stored += _store_to_target_table(
                            cursor, target_table, result.target.ip, parsed_data
                        )
                    else:
                        # Store in generic polling_data table
                        for index, data in parsed_data.items():
                            # Remove internal group markers
                            clean_data = {k: v for k, v in data.items() if not k.startswith('_group_')}
                            cursor.execute("""
                                INSERT INTO polling_data 
                                (poll_type, device_ip, collected_at, data)
                                VALUES (%s, %s, NOW(), %s)
                            """, (poll_type_name, result.target.ip, 
                                  __import__('json').dumps(clean_data)))
                            records_stored += 1
                else:
                    failed += 1
                    if result.error:
                        logger.debug(f"Poll failed for {result.target.ip}: {result.error}")
            
            db.get_connection().commit()
        
        duration = (completed_at - started_at).total_seconds()
        logger.info(f"Poll '{poll_type_name}' complete: {successful}/{len(targets)} devices, "
                   f"{records_stored} records in {duration:.1f}s")
        
        return {
            'job_name': poll_type_name,
            'started_at': started_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'total_devices': len(targets),
            'successful': successful,
            'failed': failed,
            'records_stored': records_stored,
            'duration_seconds': duration,
        }
    
    result = _run_async(_poll())
    _record_execution(poll_type_name, result, config_id, self.request.id)
    return result


def _store_to_target_table(cursor, table_name: str, device_ip: str, parsed_data: Dict) -> int:
    """
    Store parsed data to the appropriate target table.
    
    Returns number of records stored.
    """
    records = 0
    
    if table_name == 'optical_metrics':
        for index, data in parsed_data.items():
            if 'rx_power_dbm' in data or 'tx_power_dbm' in data:
                cursor.execute("""
                    INSERT INTO optical_metrics 
                    (device_ip, interface_name, interface_index, rx_power, tx_power, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (
                    device_ip,
                    f"port{index}",
                    index,
                    data.get('rx_power_dbm'),
                    data.get('tx_power_dbm')
                ))
                records += 1
    
    elif table_name == 'interface_metrics':
        for index_key, data in parsed_data.items():
            if 'rx_bytes' in data or 'tx_bytes' in data:
                # Safely convert values to int, handling None and string values
                def safe_int(val, default=0):
                    if val is None:
                        return default
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return default
                
                # Convert index to int (dict keys from JSON are strings)
                index = safe_int(index_key, 0)
                if index == 0:
                    continue
                    
                interface_name = f"port{index}"
                rx_bytes = safe_int(data.get('rx_bytes'), None)
                tx_bytes = safe_int(data.get('tx_bytes'), None)
                rx_errors = safe_int(data.get('rx_errors')) + safe_int(data.get('rx_crc_errors'))
                rx_discards = safe_int(data.get('rx_discard'), None)
                
                # Calculate rate (Mbps) from previous reading
                rx_mbps = None
                tx_mbps = None
                
                cursor.execute("""
                    SELECT rx_bytes, tx_bytes, recorded_at 
                    FROM interface_metrics 
                    WHERE device_ip = %s AND interface_index = %s 
                    ORDER BY recorded_at DESC LIMIT 1
                """, (device_ip, index))
                prev = cursor.fetchone()
                
                if prev and prev.get('rx_bytes') is not None and prev.get('tx_bytes') is not None and rx_bytes is not None and tx_bytes is not None:
                    prev_rx, prev_tx, prev_time = prev['rx_bytes'], prev['tx_bytes'], prev['recorded_at']
                    # Calculate time delta in seconds
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    # Make prev_time timezone-aware if it isn't
                    if prev_time.tzinfo is None:
                        prev_time = prev_time.replace(tzinfo=timezone.utc)
                    delta_seconds = (now - prev_time).total_seconds()
                    
                    if delta_seconds > 0:
                        # Handle counter wrap (32-bit counter wraps at 2^32)
                        rx_delta = rx_bytes - prev_rx
                        tx_delta = tx_bytes - prev_tx
                        if rx_delta < 0:
                            rx_delta += 2**32
                        if tx_delta < 0:
                            tx_delta += 2**32
                        
                        # Convert bytes/sec to Mbps (megabits per second)
                        rx_mbps = round((rx_delta * 8) / (delta_seconds * 1_000_000), 3)
                        tx_mbps = round((tx_delta * 8) / (delta_seconds * 1_000_000), 3)
                
                cursor.execute("""
                    INSERT INTO interface_metrics 
                    (device_ip, interface_name, interface_index, 
                     rx_bytes, tx_bytes, rx_packets, tx_packets,
                     rx_bps, tx_bps, rx_errors, rx_discards, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    device_ip,
                    interface_name,
                    index,
                    rx_bytes,
                    tx_bytes,
                    safe_int(data.get('rx_pkts'), None),
                    safe_int(data.get('tx_pkts'), None),
                    int(rx_mbps * 1_000_000) if rx_mbps is not None else None,  # Store as bps for precision
                    int(tx_mbps * 1_000_000) if tx_mbps is not None else None,  # Store as bps for precision
                    rx_errors,
                    rx_discards
                ))
                records += 1
    
    elif table_name == 'raps_status':
        # Store G.8032 ring status
        for index, data in parsed_data.items():
            cursor.execute("""
                INSERT INTO polling_data 
                (poll_type, device_ip, collected_at, data)
                VALUES ('ciena_raps', %s, NOW(), %s)
            """, (device_ip, __import__('json').dumps(data)))
            records += 1
    
    elif table_name == 'device_alarms':
        # Store alarms
        for index, data in parsed_data.items():
            cursor.execute("""
                INSERT INTO polling_data 
                (poll_type, device_ip, collected_at, data)
                VALUES ('ciena_alarms', %s, NOW(), %s)
            """, (device_ip, __import__('json').dumps(data)))
            records += 1
    
    else:
        # Generic storage
        for index, data in parsed_data.items():
            clean_data = {k: v for k, v in data.items() if not k.startswith('_group_')}
            cursor.execute("""
                INSERT INTO polling_data 
                (poll_type, device_ip, collected_at, data)
                VALUES (%s, %s, NOW(), %s)
            """, (table_name, device_ip, __import__('json').dumps(clean_data)))
            records += 1
    
    return records


def _record_execution(poll_type: str, result: Dict, config_id: Optional[int], task_id: str):
    """Record polling execution in database."""
    try:
        from backend.database import DatabaseConnection
        db = DatabaseConnection()
        
        status = 'success' if result.get('failed', 0) == 0 else 'partial'
        if result.get('successful', 0) == 0 and result.get('total_devices', 0) > 0:
            status = 'failed'
        
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO polling_executions (
                    config_id, config_name, started_at, completed_at, duration_ms,
                    status, devices_targeted, devices_polled, devices_success,
                    devices_failed, records_collected, triggered_by, celery_task_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                config_id,
                result.get('job_name', poll_type),
                result.get('started_at'),
                result.get('completed_at'),
                int(result.get('duration_seconds', 0) * 1000),
                status,
                result.get('total_devices', 0),
                result.get('total_devices', 0),
                result.get('successful', 0),
                result.get('failed', 0),
                result.get('records_stored', 0),
                'schedule',
                task_id
            ))
            
            # Update polling_configs if config_id provided
            if config_id:
                cursor.execute("""
                    UPDATE polling_configs
                    SET last_run_at = %s,
                        last_run_status = %s,
                        last_run_duration_ms = %s,
                        last_run_devices_polled = %s,
                        last_run_devices_success = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    result.get('completed_at'),
                    status,
                    int(result.get('duration_seconds', 0) * 1000),
                    result.get('total_devices', 0),
                    result.get('successful', 0),
                    config_id
                ))
            
            db.get_connection().commit()
    except Exception as e:
        logger.warning(f"Failed to record polling execution: {e}")


@shared_task(name='polling.scheduler_tick_v2', queue='polling')
def polling_scheduler_tick_v2():
    """
    Scheduler tick that dispatches polls based on polling_configs.
    
    This replaces the old scheduler_tick and uses the generic poll_by_type task.
    """
    from backend.database import DatabaseConnection
    from celery_app import celery_app
    
    db = DatabaseConnection()
    
    with db.cursor() as cursor:
        # Find enabled configs that are due to run
        cursor.execute("""
            SELECT pc.id, pc.name, pc.poll_type, pc.interval_seconds, pc.last_run_at,
                   pc.target_type, pc.target_manufacturer, pc.target_role, pc.target_site_name,
                   pc.snmp_community, pc.batch_size, pc.max_concurrent,
                   pt.name as poll_type_name
            FROM polling_configs pc
            LEFT JOIN snmp_poll_types pt ON pt.name = pc.poll_type
            WHERE pc.enabled = true
            AND (
                pc.last_run_at IS NULL 
                OR pc.last_run_at + (pc.interval_seconds || ' seconds')::interval < NOW()
            )
        """)
        due_configs = cursor.fetchall()
    
    if not due_configs:
        return {'dispatched': 0, 'message': 'No polls due'}
    
    dispatched = 0
    for config in due_configs:
        poll_type_name = config.get('poll_type_name') or config['poll_type']
        
        # Build device filter
        device_filter = {}
        if config['target_manufacturer']:
            device_filter['manufacturer'] = config['target_manufacturer']
        if config['target_role']:
            device_filter['role'] = config['target_role']
        if config['target_site_name']:
            device_filter['site'] = config['target_site_name']
        
        try:
            # Dispatch the generic polling task
            celery_app.send_task(
                'polling.generic',
                kwargs={
                    'poll_type_name': poll_type_name,
                    'device_filter': device_filter if device_filter else None,
                    'config_id': config['id'],
                },
                queue='polling'
            )
            dispatched += 1
            logger.info(f"Dispatched poll '{poll_type_name}' for config '{config['name']}' (id={config['id']})")
            
            # Update last_run_at to prevent duplicate dispatches
            with db.cursor() as cursor:
                cursor.execute(
                    "UPDATE polling_configs SET last_run_at = NOW() WHERE id = %s",
                    (config['id'],)
                )
                db.get_connection().commit()
                
        except Exception as e:
            logger.error(f"Failed to dispatch poll for config {config['id']}: {e}")
    
    return {'dispatched': dispatched, 'checked': len(due_configs)}
