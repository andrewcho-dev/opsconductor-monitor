# Axis Addon Documentation

## Overview

The Axis addon monitors Axis network cameras via the **VAPIX Event Service API**. It retrieves active alerts directly from the cameras rather than inferring status from endpoint responses.

**Addon ID:** `axis`  
**Method:** `api_poll`  
**Category:** `video`  
**Version:** `2.0.0`

---

## Architecture Compliance

This addon fully complies with the **Addon Module Architecture** defined in `docs/ADDON_POLLING_MODULES.md`.

### Directory Structure

```
backend/addons/axis/
├── manifest.json       # ✅ REQUIRED: Metadata, alert mappings, UI config
├── __init__.py         # ✅ REQUIRED: Package marker
└── poll.py             # ✅ REQUIRED: Polling logic
```

### Module Interface Compliance

The `poll.py` module implements the required interface:

```python
async def poll(
    target: Target,
    credentials: Credentials,
    http: HttpClient,
    snmp: SnmpClient,
    ssh: SshClient,
    logger: Logger
) -> PollResult
```

| Parameter | Type | Usage |
|-----------|------|-------|
| `target` | `Target` | Device info (ip_address, name, config) |
| `credentials` | `Credentials` | Resolved credentials (username, password) |
| `http` | `HttpClient` | Async HTTP client for API calls |
| `snmp` | `SnmpClient` | Not used for Axis (cameras use HTTP API) |
| `ssh` | `SshClient` | Not used for Axis |
| `logger` | `Logger` | Pre-configured logger with addon context |

### Return Type Compliance

The module returns a `PollResult` dataclass:

```python
@dataclass
class PollResult:
    success: bool                    # Overall poll success
    reachable: bool                  # Device responded
    alerts: List[Dict[str, Any]]     # Alerts to create
    clear_types: List[str]           # Alert types to auto-resolve
    error: str = None                # Error message if failed
    metrics: Dict[str, Any] = None   # Optional metrics data
```

---

## Polling Strategy

### Why VAPIX Event Service?

Previous implementations tried to **infer** camera status by checking various endpoints and parsing responses. This approach was flawed because:

1. **False positives** - Older firmware returns 404 on some endpoints, causing false "offline" alerts
2. **Incomplete coverage** - Only checked availability, missing tampering, temperature, storage alerts
3. **Reinventing the wheel** - Axis cameras already track and report their own events

The correct approach is to **ask the camera what alerts it has** via the VAPIX Event Service API.

### Polling Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: REACHABILITY CHECK                    │
│                                                                  │
│  Try: GET /axis-cgi/basicdeviceinfo.cgi                         │
│       ├─ 200 OK → Camera reachable (newer firmware)             │
│       ├─ 404 → Try fallback (older firmware)                    │
│       ├─ 401 → Auth failed alert                                │
│       └─ Connection error → Try fallback                        │
│                                                                  │
│  Fallback: GET /axis-cgi/param.cgi?action=list&group=Brand      │
│       ├─ 200 OK → Camera reachable (older firmware)             │
│       ├─ 401 → Auth failed alert                                │
│       └─ Error → Camera offline alert                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 STEP 2: GET CAMERA EVENTS                        │
│                                                                  │
│  POST /vapix/services                                            │
│  Content-Type: application/soap+xml                              │
│  Body: SOAP GetEventInstances request                            │
│                                                                  │
│  Response: XML with all camera event instances                   │
│  Parse: Find events with active state (value=1 or true)          │
│  Map: Camera event names → Our alert types                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: RETURN RESULTS                        │
│                                                                  │
│  PollResult:                                                     │
│    - alerts: List of active alerts from camera                   │
│    - clear_types: Alert types NOT active (can be auto-resolved)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## VAPIX Event Service API

### Endpoint

```
POST http://{camera_ip}/vapix/services
Content-Type: application/soap+xml
Authorization: Digest auth
```

### SOAP Request

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:aev="http://www.axis.com/vapix/ws/event1">
  <soap:Body>
    <aev:GetEventInstances/>
  </soap:Body>
</soap:Envelope>
```

### SOAP Response Structure

The camera returns an XML document containing all event instances. Each event has:

- **Topic** - Event category (e.g., `tnsaxis:Tampering`, `tns1:Device/tnsaxis:HardwareFailure`)
- **NiceName** - Human-readable name (e.g., "Camera tampering")
- **MessageInstance** - Event data with source and data instances
- **SimpleItemInstance** - Individual event fields with Name and Value

Example response fragment:

```xml
<tnsaxis:Tampering wstop:topic="true" aev:NiceName="Camera tampering">
  <aev:MessageInstance>
    <aev:SourceInstance>
      <aev:SimpleItemInstance aev:NiceName="Channel" Type="xsd:int" Name="channel">
        <aev:Value>1</aev:Value>
      </aev:SimpleItemInstance>
    </aev:SourceInstance>
    <aev:DataInstance>
      <aev:SimpleItemInstance aev:NiceName="Tampering" Type="xsd:int" Name="tampering">
        <aev:Value>1</aev:Value>
      </aev:SimpleItemInstance>
    </aev:DataInstance>
  </aev:MessageInstance>
</tnsaxis:Tampering>
```

In this example, `Name="tampering"` with `<aev:Value>1</aev:Value>` indicates tampering is **active**.

---

## Event Parsing

### Active Event Detection

The module parses the XML response to find active events using regex pattern matching:

```python
pattern = r'Name="([^"]+)"[^>]*>(?:[^<]*<[^>]*>)*?<aev:Value[^>]*>([^<]+)</aev:Value>'
```

This extracts:
1. **Event name** - The `Name` attribute value
2. **Event value** - The content of the `<aev:Value>` element

An event is considered **active** if its value is one of:
- `1`
- `true` / `True`
- `yes` / `Yes`
- `active` / `Active`

### Skipped Fields

Some fields are metadata, not event states. These are skipped:
- `channel` - Video channel number
- `port` - I/O port number
- `port number` - Same as port
- `source` - Event source identifier
- `id` - Generic identifier
- `videosourceconfigurationtoken` - Video config reference

---

## Event to Alert Mapping

### Mapping Table

The `EVENT_NAME_MAP` dictionary maps camera event names to our alert types:

| Camera Event Name | Our Alert Type | Category |
|-------------------|----------------|----------|
| `tampering` | `tampering_detected` | Security |
| `camera tampering` | `tampering_detected` | Security |
| `shock` | `camera_moved` | Security |
| `shock detected` | `camera_moved` | Security |
| `globalscenechange` | `camera_moved` | Security |
| `fan_failure` | `fan_failure` | Hardware |
| `fanfailure` | `fan_failure` | Hardware |
| `power_critical` | `power_supply_error` | Hardware |
| `powersupplyfailure` | `power_supply_error` | Hardware |
| `temperature_critical` | `temperature_critical` | Environment |
| `temperaturecritical` | `temperature_critical` | Environment |
| `storagehealth` | `storage_failure` | Storage |
| `storagefailure` | `storage_failure` | Storage |
| `storage_failure` | `storage_failure` | Storage |
| `diskfull` | `storage_full` | Storage |
| `disk_full` | `storage_full` | Storage |
| `diskerror` | `disk_error` | Storage |
| `disk_error` | `disk_error` | Storage |
| `above` | `temperature_warning` | Environment |
| `below` | `temperature_low` | Environment |
| `above_or_below` | `temperature_warning` | Environment |
| `sensor_level` | `temperature_warning` | Environment |
| `videoloss` | `video_loss` | Video |
| `video_loss` | `video_loss` | Video |
| `ptz_error` | `ptz_error` | PTZ |
| `ptzmotorfailure` | `ptz_motor_failure` | PTZ |
| `recording` | `recording_stopped` | Recording |
| `motion` | `motion_detected` | Motion |
| `motiondetection` | `motion_detected` | Motion |
| `vmd` | `motion_detected` | Motion |

### Matching Logic

1. **Exact match first** - Look up the event name (lowercase) directly in the map
2. **Partial match fallback** - If no exact match, check if the event name contains or is contained by any map key

```python
# Try exact match first
alert_type = EVENT_NAME_MAP.get(event_lower)

# If no exact match, try partial match
if not alert_type:
    for pattern, mapped_type in EVENT_NAME_MAP.items():
        if mapped_type and (pattern in event_lower or event_lower in pattern):
            alert_type = mapped_type
            break
```

---

## Reachability Check with Fallback

### Problem: Older Firmware Compatibility

Axis cameras with older firmware (pre-5.40) don't support `/axis-cgi/basicdeviceinfo.cgi`. Without fallback logic, these cameras would be incorrectly reported as offline.

### Solution: Two-Tier Endpoint Check

```python
async def _check_reachability(base_url, auth, target, http, logger):
    # Try primary endpoint (newer firmware)
    primary_url = f"{base_url}/axis-cgi/basicdeviceinfo.cgi"
    resp = await http.get(url=primary_url, auth=auth, auth_type='digest', ...)
    
    if resp.success:
        return True, [], ['camera_offline', 'device_offline', 'auth_failed']
    
    # 404 = older firmware, try fallback
    if resp.status_code == 404:
        return await _try_fallback_reachability(base_url, auth, target, http, logger)
    
    # ... handle other cases ...
```

```python
async def _try_fallback_reachability(base_url, auth, target, http, logger):
    # Fallback endpoint (works on virtually all Axis cameras)
    fallback_url = f"{base_url}/axis-cgi/param.cgi?action=list&group=Brand"
    resp = await http.get(url=fallback_url, auth=auth, auth_type='digest', ...)
    
    if resp.success:
        logger.info(f"{ip}: Fallback endpoint successful (older firmware)")
        return True, [], ['camera_offline', 'device_offline', 'auth_failed']
    
    # ... handle failures ...
```

### HTTP Status Code Handling

| Status Code | Interpretation | Action |
|-------------|----------------|--------|
| 200 | Success | Camera reachable |
| 404 | Endpoint not found | Try fallback |
| 401 | Unauthorized | Return `auth_failed` alert |
| 400, 403, 500-503 | Server error | Try fallback |
| 0 (connection error) | Network issue | Try fallback, then offline |

---

## Alert Generation

### Alert Structure

Each alert returned in `PollResult.alerts` has this structure:

```python
{
    'alert_type': 'tampering_detected',
    'message': 'Tampering Detected active on camera 10.120.12.117',
    'fields': {
        'source': 'vapix_event_service',
        'camera_event': 'Camera tampering',
        'value': '1'
    }
}
```

### Clear Types

The `clear_types` list contains alert types that are **not active** on the camera. The core system uses this to auto-resolve any existing alerts of these types for this device.

For example, if the camera reports tampering but no temperature issues:
- `alerts` = `[{'alert_type': 'tampering_detected', ...}]`
- `clear_types` = `['temperature_critical', 'temperature_warning', 'fan_failure', ...]`

---

## Configuration

### Target Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `port` | number | 80 | HTTP port |
| `use_https` | boolean | false | Use HTTPS instead of HTTP |

### Credentials

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `username` | text | Yes | `root` |
| `password` | password | Yes | (empty) |

### Protocol Selection

```python
use_https = config.get('use_https', False)
port = config.get('port', 443 if use_https else 80)
protocol = 'https' if use_https else 'http'
base_url = f"{protocol}://{ip}:{port}"
```

---

## Detected Alert Types (Production Results)

After deployment, the addon detected the following alerts across the camera fleet:

| Alert Type | Count | Description |
|------------|-------|-------------|
| `io_error` | 203 | I/O port errors |
| `tampering_detected` | 136 | Camera tampering detected |
| `video_loss` | 76 | Video signal lost |
| `ir_failure` | 27 | Infrared illuminator failure |
| `camera_offline` | 21 | Camera not responding |
| `ptz_error` | 20 | PTZ mechanism errors |
| `fan_failure` | 5 | Cooling fan failure |
| `temperature_critical` | 4 | Temperature exceeds safe limit |
| `sensor_failure` | 3 | Image sensor failure |
| `temperature_warning` | 2 | Temperature elevated |
| `focus_failure` | 1 | Autofocus failure |

---

## Code Reference

### poll.py Functions

| Function | Purpose |
|----------|---------|
| `poll()` | Main entry point, orchestrates polling sequence |
| `_check_reachability()` | Check if camera responds, with fallback |
| `_try_fallback_reachability()` | Fallback endpoint for older firmware |
| `_get_camera_events()` | Call VAPIX Event Service and parse response |
| `_parse_active_events()` | Extract active events from XML |

### Constants

| Constant | Purpose |
|----------|---------|
| `SOAP_GET_EVENTS` | SOAP request body for GetEventInstances |
| `EVENT_NAME_MAP` | Camera event name to alert type mapping |

---

## Testing

### Manual Test

```python
import asyncio
from backend.addons.axis.poll import poll, PollResult

class MockTarget:
    def __init__(self, ip):
        self.ip_address = ip
        self.name = f'Camera {ip}'
        self.config = {}

class MockCredentials:
    def __init__(self, username, password):
        self.username = username
        self.password = password

async def test():
    from backend.core.clients import get_clients
    
    clients = get_clients()
    target = MockTarget('10.120.12.117')
    creds = MockCredentials('root', 'password')
    
    result = await poll(target, creds, clients.http, clients.snmp, clients.ssh, logger)
    
    print(f'Success: {result.success}')
    print(f'Reachable: {result.reachable}')
    print(f'Alerts: {len(result.alerts)}')
    for a in result.alerts:
        print(f'  - {a["alert_type"]}: {a["message"]}')

asyncio.run(test())
```

---

## Troubleshooting

### No Alerts Detected

1. **Check VAPIX availability** - Older cameras may not support `/vapix/services`
2. **Check authentication** - Digest auth required
3. **Check event mapping** - Event name may not be in `EVENT_NAME_MAP`

### False Offline Alerts

1. **Check fallback** - Ensure fallback endpoint is being tried
2. **Check network** - Firewall may block HTTP/HTTPS
3. **Check credentials** - 401 should return `auth_failed`, not `camera_offline`

### Missing Alert Types

Add new mappings to `EVENT_NAME_MAP`:

```python
EVENT_NAME_MAP = {
    # ... existing mappings ...
    'new_event_name': 'our_alert_type',
}
```

---

## References

- [VAPIX Event and Action Services](https://developer.axis.com/vapix/network-video/event-and-action-services/)
- [Axis Developer Documentation](https://developer.axis.com/vapix/)
- [Addon Module Architecture](./ADDON_POLLING_MODULES.md)
