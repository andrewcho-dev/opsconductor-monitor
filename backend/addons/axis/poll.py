"""
Axis Camera Polling Module

Polls Axis cameras via reliable VAPIX CGI endpoints to get current status.
Only monitors alerts that can be queried directly with accurate current state.

Supported Alerts (13 total):
- camera_offline, auth_failed (reachability)
- fan_failure, heater_failure (temperaturecontrol.cgi)
- temperature_critical, temperature_warning (temperaturecontrol.cgi)
- storage_failure, storage_full, storage_readonly, storage_disconnected (disks/list.cgi)
- sd_card_wear_critical (disks/gethealth.cgi)
- power_warning (power-settings.cgi)
- ptz_not_ready (Event Service - Stateful event)

Documentation:
- https://developer.axis.com/vapix/network-video/temperature-control/
- https://developer.axis.com/vapix/network-video/edge-storage-api/
- https://developer.axis.com/vapix/network-video/power-settings/
- https://developer.axis.com/vapix/network-video/pantiltzoom-api/
"""

import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field


@dataclass
class PollResult:
    """Result from polling a single target."""
    success: bool
    reachable: bool
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    clear_types: List[str] = field(default_factory=list)
    error: str = None
    metrics: Dict[str, Any] = None


# All supported alert types for this addon
SUPPORTED_ALERT_TYPES = [
    'camera_offline',
    'auth_failed',
    'fan_failure',
    'heater_failure',
    'temperature_critical',
    'temperature_warning',
    'storage_failure',
    'storage_full',
    'storage_readonly',
    'storage_disconnected',
    'sd_card_wear_critical',
    'power_warning',
    'ptz_not_ready',
]

# Temperature thresholds (Celsius)
TEMP_WARNING_THRESHOLD = 60.0
TEMP_CRITICAL_THRESHOLD = 70.0

# SD card wear threshold (percentage)
SD_WEAR_CRITICAL_THRESHOLD = 95


async def poll(target, credentials, http, snmp, ssh, logger) -> PollResult:
    """
    Poll a single Axis camera via reliable VAPIX CGI endpoints.
    
    Queries specific CGI endpoints that return current state values:
    1. Reachability check (basicdeviceinfo.cgi)
    2. Temperature/Fan/Heater status (temperaturecontrol.cgi)
    3. Storage status (disks/list.cgi, disks/gethealth.cgi)
    4. Power status (power-settings.cgi)
    5. PTZ ready status (Event Service - Stateful)
    """
    ip = target.ip_address
    config = target.config or {}
    
    # Determine protocol and port
    use_https = config.get('use_https', False)
    port = config.get('port', 443 if use_https else 80)
    protocol = 'https' if use_https else 'http'
    base_url = f"{protocol}://{ip}:{port}"
    
    # Build auth tuple
    auth = None
    if credentials.username:
        auth = (credentials.username, credentials.password or '')
    
    all_alerts = []
    active_types: Set[str] = set()
    
    # Step 1: Reachability check
    reachable, reachability_alerts = await _check_reachability(
        base_url, auth, ip, http, logger
    )
    for alert in reachability_alerts:
        all_alerts.append(alert)
        active_types.add(alert['alert_type'])
    
    if not reachable:
        return PollResult(
            success=False,
            reachable=False,
            alerts=all_alerts,
            clear_types=[],
            error='Device not reachable'
        )
    
    # Step 2: Temperature/Fan/Heater status
    temp_alerts = await _check_temperature_control(base_url, auth, ip, http, logger)
    for alert in temp_alerts:
        all_alerts.append(alert)
        active_types.add(alert['alert_type'])
    
    # Step 3: Storage status
    storage_alerts = await _check_storage(base_url, auth, ip, http, logger)
    for alert in storage_alerts:
        all_alerts.append(alert)
        active_types.add(alert['alert_type'])
    
    # Step 4: Power status
    power_alerts = await _check_power(base_url, auth, ip, http, logger)
    for alert in power_alerts:
        all_alerts.append(alert)
        active_types.add(alert['alert_type'])
    
    # Step 5: PTZ ready status (only for PTZ cameras)
    if config.get('has_ptz', False):
        ptz_alerts = await _check_ptz_ready(base_url, auth, ip, http, logger)
        for alert in ptz_alerts:
            all_alerts.append(alert)
            active_types.add(alert['alert_type'])
    
    # Build clear list - all supported types that are NOT active
    clear_types = [t for t in SUPPORTED_ALERT_TYPES if t not in active_types]
    
    return PollResult(
        success=True,
        reachable=True,
        alerts=all_alerts,
        clear_types=clear_types
    )


async def _check_reachability(base_url: str, auth: tuple, ip: str, http, logger) -> Tuple[bool, List[Dict]]:
    """
    Check if camera is reachable via basicdeviceinfo.cgi with fallback.
    
    Returns: (is_reachable, list_of_alerts)
    """
    alerts = []
    
    # Try primary endpoint
    primary_url = f"{base_url}/axis-cgi/basicdeviceinfo.cgi"
    resp = await http.get(url=primary_url, auth=auth, auth_type='digest', timeout=15, verify_ssl=False)
    
    if resp.success:
        logger.debug(f"{ip}: Reachability check passed")
        return True, []
    
    # 404 = older firmware, try fallback
    if resp.status_code == 404:
        fallback_url = f"{base_url}/axis-cgi/param.cgi?action=list&group=Brand"
        resp = await http.get(url=fallback_url, auth=auth, auth_type='digest', timeout=15, verify_ssl=False)
        if resp.success:
            logger.debug(f"{ip}: Reachability check passed (fallback)")
            return True, []
    
    # Auth failure - camera is reachable but credentials are wrong
    if resp.status_code == 401:
        logger.warning(f"{ip}: Authentication failed")
        return True, [{
            'alert_type': 'auth_failed',
            'message': f'Authentication failed for camera {ip}',
            'fields': {'source': 'reachability_check'}
        }]
    
    # Camera offline
    logger.warning(f"{ip}: Camera offline - {resp.error}")
    return False, [{
        'alert_type': 'camera_offline',
        'message': f'Camera {ip} not responding: {resp.error}',
        'fields': {'source': 'reachability_check', 'status_code': resp.status_code}
    }]


async def _check_temperature_control(base_url: str, auth: tuple, ip: str, http, logger) -> List[Dict]:
    """
    Check temperature, fan, and heater status via temperaturecontrol.cgi.
    
    Endpoint: /axis-cgi/temperaturecontrol.cgi?action=statusall
    
    Response format:
        Sensor.S0.Celsius=43.50
        Fan.F0.Status=Running|Stopped|Fan Failure
        Heater.H0.Status=Running|Stopped|Heater Failure
    """
    alerts = []
    url = f"{base_url}/axis-cgi/temperaturecontrol.cgi?action=statusall"
    
    resp = await http.get(url=url, auth=auth, auth_type='digest', timeout=10, verify_ssl=False)
    
    if not resp.success:
        # This endpoint may not exist on all cameras - not an error
        logger.debug(f"{ip}: temperaturecontrol.cgi not available")
        return alerts
    
    # Parse key=value response
    for line in resp.text.strip().split('\n'):
        line = line.strip()
        if '=' not in line:
            continue
        
        key, value = line.split('=', 1)
        
        # Check fan status
        if key.startswith('Fan.') and key.endswith('.Status'):
            if value == 'Fan Failure':
                fan_id = key.split('.')[1]
                alerts.append({
                    'alert_type': 'fan_failure',
                    'message': f'Fan {fan_id} failure on camera {ip}',
                    'fields': {'source': 'temperaturecontrol.cgi', 'fan_id': fan_id}
                })
                logger.warning(f"{ip}: Fan failure detected - {fan_id}")
        
        # Check heater status
        elif key.startswith('Heater.') and key.endswith('.Status'):
            if value == 'Heater Failure':
                heater_id = key.split('.')[1]
                alerts.append({
                    'alert_type': 'heater_failure',
                    'message': f'Heater {heater_id} failure on camera {ip}',
                    'fields': {'source': 'temperaturecontrol.cgi', 'heater_id': heater_id}
                })
                logger.warning(f"{ip}: Heater failure detected - {heater_id}")
        
        # Check temperature
        elif key.startswith('Sensor.') and key.endswith('.Celsius'):
            try:
                temp = float(value)
                sensor_id = key.split('.')[1]
                
                # Skip invalid/sentinel values (999 = sensor not available)
                if temp >= 200 or temp <= -50:
                    logger.debug(f"{ip}: Ignoring invalid temperature reading {temp}°C from {sensor_id}")
                    continue
                
                if temp >= TEMP_CRITICAL_THRESHOLD:
                    alerts.append({
                        'alert_type': 'temperature_critical',
                        'message': f'Critical temperature {temp}°C on camera {ip}',
                        'fields': {'source': 'temperaturecontrol.cgi', 'sensor_id': sensor_id, 'temperature': temp}
                    })
                    logger.warning(f"{ip}: Critical temperature - {temp}°C")
                elif temp >= TEMP_WARNING_THRESHOLD:
                    alerts.append({
                        'alert_type': 'temperature_warning',
                        'message': f'High temperature {temp}°C on camera {ip}',
                        'fields': {'source': 'temperaturecontrol.cgi', 'sensor_id': sensor_id, 'temperature': temp}
                    })
                    logger.info(f"{ip}: Temperature warning - {temp}°C")
            except ValueError:
                pass
    
    return alerts


async def _check_storage(base_url: str, auth: tuple, ip: str, http, logger) -> List[Dict]:
    """
    Check storage status via disks/list.cgi and disks/gethealth.cgi.
    
    Detects: storage_failure, storage_full, storage_readonly, storage_disconnected, sd_card_wear_critical
    """
    alerts = []
    
    # Check disk list for status
    list_url = f"{base_url}/axis-cgi/disks/list.cgi"
    resp = await http.get(url=list_url, auth=auth, auth_type='digest', timeout=10, verify_ssl=False)
    
    if resp.success:
        try:
            root = ET.fromstring(resp.text)
            for disk in root.iter('disk'):
                disk_id = disk.get('diskid', 'unknown')
                status = disk.get('status', '')
                full = disk.get('full', 'no')
                readonly = disk.get('readonly', 'no')
                
                if status == 'failed':
                    alerts.append({
                        'alert_type': 'storage_failure',
                        'message': f'Storage {disk_id} failed on camera {ip}',
                        'fields': {'source': 'disks/list.cgi', 'disk_id': disk_id}
                    })
                    logger.warning(f"{ip}: Storage failure - {disk_id}")
                
                elif status == 'disconnected':
                    alerts.append({
                        'alert_type': 'storage_disconnected',
                        'message': f'Storage {disk_id} disconnected on camera {ip}',
                        'fields': {'source': 'disks/list.cgi', 'disk_id': disk_id}
                    })
                    logger.warning(f"{ip}: Storage disconnected - {disk_id}")
                
                if full == 'yes':
                    alerts.append({
                        'alert_type': 'storage_full',
                        'message': f'Storage {disk_id} full on camera {ip}',
                        'fields': {'source': 'disks/list.cgi', 'disk_id': disk_id}
                    })
                    logger.warning(f"{ip}: Storage full - {disk_id}")
                
                if readonly == 'yes':
                    alerts.append({
                        'alert_type': 'storage_readonly',
                        'message': f'Storage {disk_id} is read-only on camera {ip}',
                        'fields': {'source': 'disks/list.cgi', 'disk_id': disk_id}
                    })
                    logger.warning(f"{ip}: Storage read-only - {disk_id}")
        except ET.ParseError:
            logger.debug(f"{ip}: Failed to parse disks/list.cgi response")
    
    # Check disk health for SD card wear
    health_url = f"{base_url}/axis-cgi/disks/gethealth.cgi"
    resp = await http.get(url=health_url, auth=auth, auth_type='digest', timeout=10, verify_ssl=False)
    
    if resp.success:
        try:
            root = ET.fromstring(resp.text)
            for health in root.iter('HealthStatus'):
                disk_id = health.get('diskid', 'unknown')
                wear = health.get('wear', '-1')
                overall = health.get('overallhealth', '1')
                
                try:
                    wear_pct = int(wear)
                    if wear_pct >= SD_WEAR_CRITICAL_THRESHOLD:
                        alerts.append({
                            'alert_type': 'sd_card_wear_critical',
                            'message': f'SD card {disk_id} wear at {wear_pct}% on camera {ip}',
                            'fields': {'source': 'disks/gethealth.cgi', 'disk_id': disk_id, 'wear_percent': wear_pct}
                        })
                        logger.warning(f"{ip}: SD card wear critical - {disk_id} at {wear_pct}%")
                except ValueError:
                    pass
                
                if overall == '0':
                    # Only add if not already added as wear_critical
                    if not any(a['alert_type'] == 'sd_card_wear_critical' and a['fields'].get('disk_id') == disk_id for a in alerts):
                        alerts.append({
                            'alert_type': 'storage_failure',
                            'message': f'Storage {disk_id} health check failed on camera {ip}',
                            'fields': {'source': 'disks/gethealth.cgi', 'disk_id': disk_id}
                        })
                        logger.warning(f"{ip}: Storage health failed - {disk_id}")
        except ET.ParseError:
            logger.debug(f"{ip}: Failed to parse disks/gethealth.cgi response")
    
    return alerts


async def _check_power(base_url: str, auth: tuple, ip: str, http, logger) -> List[Dict]:
    """
    Check power status via power-settings.cgi (JSON API).
    
    Detects: power_warning when currentPower approaches maxPower
    """
    alerts = []
    url = f"{base_url}/axis-cgi/power-settings.cgi"
    
    payload = {
        "apiVersion": "1.2",
        "method": "getPowerStatus"
    }
    
    resp = await http.post(
        url=url,
        auth=auth,
        auth_type='digest',
        timeout=10,
        verify_ssl=False,
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    if not resp.success:
        logger.debug(f"{ip}: power-settings.cgi not available")
        return alerts
    
    try:
        data = json.loads(resp.text)
        if 'data' in data and 'usage' in data['data']:
            usage = data['data']['usage']
            current = usage.get('currentPower', 0)
            max_power = usage.get('maxPower', 0)
            
            if max_power > 0 and current > 0:
                usage_pct = (current / max_power) * 100
                if usage_pct >= 90:
                    alerts.append({
                        'alert_type': 'power_warning',
                        'message': f'Power usage at {usage_pct:.0f}% on camera {ip}',
                        'fields': {
                            'source': 'power-settings.cgi',
                            'current_power': current,
                            'max_power': max_power,
                            'usage_percent': usage_pct
                        }
                    })
                    logger.warning(f"{ip}: Power warning - {usage_pct:.0f}% usage")
    except (json.JSONDecodeError, KeyError):
        logger.debug(f"{ip}: Failed to parse power-settings.cgi response")
    
    return alerts


async def _check_ptz_ready(base_url: str, auth: tuple, ip: str, http, logger) -> List[Dict]:
    """
    Check PTZ ready status via VAPIX Event Service.
    
    The PTZ Ready event is Stateful with isPropertyState=true.
    ready=false means PTZ is not operational.
    """
    alerts = []
    
    # SOAP request to get PTZ ready event
    soap_request = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:aev="http://www.axis.com/vapix/ws/event1">
  <soap:Body>
    <aev:GetEventInstances/>
  </soap:Body>
</soap:Envelope>'''
    
    url = f"{base_url}/vapix/services"
    resp = await http.post(
        url=url,
        auth=auth,
        auth_type='digest',
        timeout=10,
        verify_ssl=False,
        data=soap_request,
        headers={'Content-Type': 'application/soap+xml'}
    )
    
    if not resp.success:
        logger.debug(f"{ip}: VAPIX Event Service not available for PTZ check")
        return alerts
    
    try:
        root = ET.fromstring(resp.text)
        ns_aev = '{http://www.axis.com/vapix/ws/event1}'
        ns_wstop = '{http://docs.oasis-open.org/wsn/t-1}'
        
        # Find PTZ ready topic
        for elem in root.iter():
            if elem.get(f'{ns_wstop}topic') != 'true':
                continue
            
            nice_name = elem.get(f'{ns_aev}NiceName', '')
            if nice_name != 'PTZ ready':
                continue
            
            # Find the ready field with isPropertyState=true
            for item in elem.iter():
                if 'SimpleItemInstance' not in str(item.tag):
                    continue
                
                if item.get('isPropertyState', '') == 'true':
                    # Get value
                    for child in item:
                        if 'Value' in str(child.tag) and child.text:
                            value = child.text.strip().lower()
                            if value in ['false', '0', 'no']:
                                alerts.append({
                                    'alert_type': 'ptz_not_ready',
                                    'message': f'PTZ not ready on camera {ip}',
                                    'fields': {'source': 'vapix_event_service', 'ready': False}
                                })
                                logger.warning(f"{ip}: PTZ not ready")
                            break
    except ET.ParseError:
        logger.debug(f"{ip}: Failed to parse VAPIX response for PTZ check")
    
    return alerts
