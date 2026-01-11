"""
Celery Tasks

Scalable fan-out polling architecture for 2000+ devices.

Architecture:
- poll_dispatch: Lightweight dispatcher (runs every 60s via Beat)
- poll_single_target: Individual target polling (runs in parallel across workers)
- Rate limited to prevent overwhelming network/devices
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from celery import shared_task

from backend.core.db import query, query_one, execute
from backend.core.addon_registry import get_registry, Addon
from backend.core.poller import get_poller
from backend.core.parser import get_parser, ParsedAlert
from backend.core.alert_engine import get_engine
from backend.core.clients import get_clients
from backend.core.types import Target, Credentials, PollResult

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# DISPATCHER TASK (Lightweight - just spawns individual target tasks)
# =============================================================================

@shared_task(name='poll_dispatch')
def poll_dispatch() -> Dict[str, Any]:
    """
    Lightweight dispatcher that identifies due targets and spawns individual poll tasks.
    
    This task runs every 60 seconds via Celery Beat. It does NOT do actual polling -
    it just identifies which targets are due and spawns poll_single_target tasks
    for each one. This enables parallel polling across multiple workers.
    
    Returns:
        Dict with dispatched count and any errors
    """
    logger.info("Poll dispatch starting")
    
    results = {
        'dispatched': 0,
        'skipped': 0,
        'errors': 0,
    }
    
    # Get addons that support polling
    polling_methods = ['api_poll', 'snmp_poll', 'ssh']
    registry = get_registry()
    
    for addon in registry.get_enabled():
        if addon.method not in polling_methods:
            continue
        
        try:
            # Get targets due for polling in a single efficient query
            targets = query("""
                SELECT id, ip_address, last_poll_at, poll_interval
                FROM targets
                WHERE addon_id = %s 
                AND enabled = true
                AND (
                    last_poll_at IS NULL 
                    OR last_poll_at + (poll_interval || ' seconds')::interval < NOW()
                )
            """, (addon.id,))
            
            for target in targets:
                try:
                    # Spawn individual task for this target (fan-out)
                    poll_single_target.delay(target['id'])
                    results['dispatched'] += 1
                except Exception as e:
                    logger.error(f"Error dispatching target {target['id']}: {e}")
                    results['errors'] += 1
                    
        except Exception as e:
            logger.error(f"Error processing addon {addon.id}: {e}")
            results['errors'] += 1
    
    logger.info(f"Poll dispatch complete: {results}")
    return results


# =============================================================================
# SINGLE TARGET POLLING TASK (Rate limited, runs in parallel)
# =============================================================================

@shared_task(
    name='poll_single_target',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    rate_limit='100/s',  # Max 100 polls per second across all workers
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def poll_single_target(self, target_id: int) -> Dict[str, Any]:
    """
    Poll a single target device.
    
    This task is spawned by poll_dispatch for each target that is due for polling.
    It runs in parallel across multiple workers, with rate limiting to prevent
    overwhelming the network or devices.
    
    Args:
        target_id: Database ID of the target to poll
        
    Returns:
        Dict with poll results (success, alerts, error)
    """
    try:
        # Load target from database
        target = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
        if not target:
            return {'error': f'Target {target_id} not found'}
        
        # Load addon fresh from database (not cache) to get latest manifest
        from backend.core.addon_registry import get_addon_from_db
        addon = get_addon_from_db(target['addon_id'])
        if not addon:
            return {'error': f"Addon {target['addon_id']} not found"}
        
        # Get clients instance
        clients = get_clients()
        
        # Execute the poll
        alert_count = _run_async(_poll_target_async(addon, target, clients))
        
        # Update last poll time
        execute(
            "UPDATE targets SET last_poll_at = NOW() WHERE id = %s",
            (target_id,)
        )
        
        return {
            'success': True,
            'target_id': target_id,
            'ip': target['ip_address'],
            'alerts': alert_count,
        }
        
    except Exception as e:
        logger.error(f"Error polling target {target_id}: {e}")
        # Let Celery handle retry via autoretry_for
        raise


# Legacy alias for backward compatibility
@shared_task(name='poll_all_addons')
def poll_all_addons() -> Dict[str, Any]:
    """
    Legacy task name - redirects to poll_dispatch.
    
    Kept for backward compatibility with existing beat schedules.
    """
    return poll_dispatch()


def _resolve_credentials(target: Dict, addon: Addon) -> Credentials:
    """Resolve credentials from target config or addon defaults."""
    config = target.get('config', {}) or {}
    default_creds = addon.manifest.get('default_credentials', {})
    
    return Credentials(
        username=config.get('username') or default_creds.get('username'),
        password=config.get('password') or default_creds.get('password'),
        api_key=config.get('api_key') or default_creds.get('api_key'),
        community=config.get('community') or default_creds.get('community', 'public'),
        key_file=config.get('key_file') or default_creds.get('key_file'),
    )


def _build_target(target: Dict) -> Target:
    """Build Target object from database row."""
    return Target(
        id=str(target['id']),
        ip_address=target['ip_address'],
        name=target.get('name', target['ip_address']),
        addon_id=target['addon_id'],
        port=target.get('config', {}).get('port') if target.get('config') else None,
        config=target.get('config', {}) or {},
        enabled=target.get('enabled', True),
        last_poll_at=target.get('last_poll_at'),
    )


async def _poll_target_async(addon: Addon, target: Dict, clients) -> int:
    """
    Poll a single target using addon's poll module or fallback to declarative config.
    
    If the addon has a poll.py module, it will be used for full control over polling.
    Otherwise, falls back to declarative manifest-based polling (legacy).
    """
    engine = get_engine()
    alert_count = 0
    
    ip = target['ip_address']
    
    # Check if addon has a poll module
    if 'poll' in addon.modules and hasattr(addon.modules['poll'], 'poll'):
        # Use addon's poll module (new architecture)
        logger.debug(f"Using addon poll module for {addon.id}")
        
        # Build target and credentials
        target_obj = _build_target(target)
        credentials = _resolve_credentials(target, addon)
        addon_logger = logging.getLogger(f"addon.{addon.id}")
        
        # Call addon's poll function with timeout protection
        try:
            result = await asyncio.wait_for(
                addon.modules['poll'].poll(
                    target=target_obj,
                    credentials=credentials,
                    http=clients.http,
                    snmp=clients.snmp,
                    ssh=clients.ssh,
                    logger=addon_logger
                ),
                timeout=60.0  # 60 second timeout for addon poll
            )
        except asyncio.TimeoutError:
            logger.error(f"Addon poll timeout for {ip}")
            result = PollResult(
                success=False,
                reachable=False,
                alerts=[{'alert_type': 'poll_timeout', 'message': f'Poll timed out for {ip}'}],
                error='Poll timeout'
            )
        except Exception as e:
            logger.error(f"Addon poll error for {ip}: {e}")
            result = PollResult(
                success=False,
                reachable=False,
                alerts=[{'alert_type': 'poll_error', 'message': f'Poll failed: {str(e)}'}],
                error=str(e)
            )
        
        # Process poll result
        alert_count = await _process_poll_result(result, addon, target)
    
    else:
        # Fallback to declarative polling (legacy)
        logger.debug(f"Using declarative polling for {addon.id} (no poll module)")
        alert_count = await _poll_target_declarative(addon, target, clients)
    
    return alert_count


async def _process_poll_result(result: PollResult, addon: Addon, target: Dict) -> int:
    """Process PollResult from addon poll module."""
    engine = get_engine()
    alert_count = 0
    ip = target['ip_address']
    
    # Auto-resolve cleared alert types
    for alert_type in result.clear_types:
        resolved = await engine.auto_resolve(addon.id, alert_type, ip)
        if resolved:
            logger.debug(f"Auto-resolved {alert_type} for {ip}")
    
    # Create alerts
    for alert_data in result.alerts:
        parsed = ParsedAlert(
            addon_id=addon.id,
            alert_type=alert_data.get('alert_type', 'unknown'),
            device_ip=ip,
            device_name=target.get('name', ip),
            message=alert_data.get('message', ''),
            raw_data=alert_data,
            fields=alert_data.get('fields', {}),
            is_clear=alert_data.get('is_clear', False)
        )
        alert = await engine.process(parsed, addon)
        if alert:
            alert_count += 1
    
    return alert_count


async def _poll_target_declarative(addon: Addon, target: Dict, clients) -> int:
    """
    Legacy declarative polling using manifest configuration.
    
    Used when addon does not have a poll.py module.
    """
    parser = get_parser()
    engine = get_engine()
    alert_count = 0
    
    ip = target['ip_address']
    config = target.get('config', {}) or {}
    
    if addon.method == 'api_poll':
        # API polling
        api_config = addon.manifest.get('api_poll', {})
        default_creds = addon.manifest.get('default_credentials', {})
        base_url = api_config.get('base_url_template', '').format(
            host=ip,
            port=config.get('port', 80)
        )
        
        # Use target-specific credentials, fall back to addon default credentials
        username = config.get('username') or default_creds.get('username')
        password = config.get('password') or default_creds.get('password')
        auth_type = api_config.get('auth_type', 'digest')
        
        for endpoint in api_config.get('endpoints', []):
            url = f"{base_url}{endpoint['path']}"
            alert_on_failure = endpoint.get('alert_on_failure')
            
            result = await clients.http.request(
                method=endpoint.get('method', 'GET'),
                url=url,
                headers=config.get('headers', {}),
                auth=(username, password) if username else None,
                auth_type=auth_type,
                verify_ssl=api_config.get('verify_ssl', True)
            )
            
            logger.debug(f"Poll result for {ip}: success={result.success}, error={result.error}")
            
            if result.success:
                # Auto-resolve any existing failure alert for this device
                if alert_on_failure:
                    resolved = await engine.auto_resolve(addon.id, alert_on_failure, ip)
                    if resolved:
                        logger.debug(f"Auto-resolved {alert_on_failure} for {ip}")
                
                # Parse response for alerts if configured
                parsed = parser.parse(result.data, addon.manifest, addon.id)
                if parsed:
                    parsed.device_ip = ip
                    alert = await engine.process(parsed, addon)
                    if alert:
                        alert_count += 1
            else:
                # Create alert on failure if configured
                if alert_on_failure:
                    parsed = ParsedAlert(
                        addon_id=addon.id,
                        alert_type=alert_on_failure,
                        device_ip=ip,
                        device_name=target.get('name', ip),
                        message=f"Failed to reach {url}: {result.error}",
                        raw_data={'error': result.error, 'url': url},
                        fields={},
                        is_clear=False
                    )
                    alert = await engine.process(parsed, addon)
                    if alert:
                        alert_count += 1
                    break  # Don't try other endpoints if device is offline
    
    elif addon.method == 'snmp_poll':
        # SNMP polling
        snmp_config = addon.manifest.get('snmp_poll', {})
        
        for poll_group in snmp_config.get('poll_groups', []):
            oids = [o['oid'] for o in poll_group.get('oids', [])]
            
            result = await clients.snmp.get(
                host=ip,
                oids=oids,
                community=config.get('community', snmp_config.get('default_community', 'public')),
                version=snmp_config.get('version', '2c'),
                port=snmp_config.get('port', 161)
            )
            
            if result.success:
                # Check alert conditions
                for condition in poll_group.get('alert_conditions', []):
                    field = condition['field']
                    value = result.data.get(field)
                    
                    if _check_condition(value, condition):
                        parsed = parser.parse({
                            'device_ip': ip,
                            'alert_type': condition['alert_type'],
                            'oids': result.data,
                        }, addon.manifest, addon.id)
                        
                        if parsed:
                            await engine.process(parsed, addon)
                            alert_count += 1
    
    elif addon.method == 'ssh':
        # SSH polling
        ssh_config = addon.manifest.get('ssh', {})
        
        for cmd_config in ssh_config.get('commands', []):
            result = await clients.ssh.exec(
                host=ip,
                command=cmd_config['command'],
                username=config.get('username'),
                password=config.get('password'),
                key_file=config.get('key_file'),
                port=ssh_config.get('port', 22)
            )
            
            if result.success:
                parsed = parser.parse(
                    result.stdout,
                    addon.manifest,
                    addon.id
                )
                if parsed:
                    parsed.device_ip = ip
                    await engine.process(parsed, addon)
                    alert_count += 1
    
    return alert_count


def _check_condition(value, condition: Dict) -> bool:
    """Check if value meets alert condition."""
    if value is None:
        return False
    
    operator = condition.get('operator', 'equals')
    threshold = condition.get('value')
    
    try:
        value = float(value)
        threshold = float(threshold)
    except:
        pass
    
    if operator == 'equals':
        return value == threshold
    elif operator == 'not_equals':
        return value != threshold
    elif operator == 'greater_than':
        return value > threshold
    elif operator == 'less_than':
        return value < threshold
    elif operator == 'contains':
        return str(threshold) in str(value)
    
    return False


@shared_task(name='poll_addon')
def poll_addon(addon_id: str, target_id: int = None) -> Dict[str, Any]:
    """
    Poll a specific addon (or specific target).
    
    Called on-demand or for immediate polling.
    """
    from backend.core.addon_registry import get_addon_from_db
    addon = get_addon_from_db(addon_id)
    
    if not addon:
        return {'error': f'Addon {addon_id} not found'}
    
    clients = get_clients()
    
    # Get targets
    if target_id:
        targets = query("SELECT * FROM targets WHERE id = %s", (target_id,))
    else:
        targets = query(
            "SELECT * FROM targets WHERE addon_id = %s AND enabled = true",
            (addon_id,)
        )
    
    results = {'alerts': 0, 'errors': 0}
    
    for target in targets:
        try:
            count = _run_async(_poll_target_async(addon, target, clients))
            results['alerts'] += count
        except Exception as e:
            logger.error(f"Poll error: {e}")
            results['errors'] += 1
    
    return results


@shared_task(name='cleanup_resolved_alerts')
def cleanup_resolved_alerts(days: int = 30) -> Dict[str, int]:
    """
    Clean up old resolved alerts.
    
    By default, removes resolved alerts older than 30 days.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    result = execute("""
        DELETE FROM alerts
        WHERE status = 'resolved'
        AND resolved_at < %s
    """, (cutoff,))
    
    logger.info(f"Cleaned up {result} resolved alerts older than {days} days")
    
    return {'deleted': result, 'cutoff_days': days}


@shared_task(name='reconcile_alerts')
def reconcile_alerts(addon_id: str) -> Dict[str, int]:
    """
    Reconcile alerts for an addon.
    
    Resolves alerts that are no longer present in source system.
    Used for polling-based addons where absence = resolved.
    """
    # This would be called after a full poll cycle
    # Implementation depends on addon-specific logic
    return {'reconciled': 0}
