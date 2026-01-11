# Addon Module Architecture

## Overview

This document defines the **addon module architecture** - a system where addons contain all vendor-specific logic (polling, parsing, webhook handling) while the core system provides only infrastructure services (scheduling, storage, events).

## Design Principles

1. **Core is generic** - No vendor-specific code in core
2. **Addons are self-contained** - All vendor logic lives in the addon
3. **Modules are mandatory** - Every addon must implement required interfaces
4. **Core provides services** - HTTP clients, credentials, storage via well-defined interfaces

## Problem Statement

The previous addon system was **declarative-only**:
- Addons defined endpoints in `manifest.json`
- Core system interpreted the manifest and executed polling
- No way for addons to handle device-specific quirks (e.g., older firmware, fallback endpoints)
- Parsing logic was generic and couldn't handle vendor-specific formats

**Example:** Axis cameras with older firmware don't support `/axis-cgi/basicdeviceinfo.cgi`, causing false `camera_offline` alerts even though the camera is reachable via other endpoints.

## Solution: Addon Modules

Each addon **must** include Python modules that implement the required interfaces. The core system imports and calls these modules, passing in services (HTTP client, credentials, etc.).

---

## Addon Directory Structure

```
backend/addons/{addon_id}/
├── manifest.json       # REQUIRED: Metadata, alert mappings, UI config
├── __init__.py         # REQUIRED: Package marker
├── poll.py             # REQUIRED: Polling logic (for polling addons)
├── parse.py            # REQUIRED: Response parsing and alert extraction
├── webhook.py          # OPTIONAL: Webhook handler (if method=webhook)
├── trap.py             # OPTIONAL: SNMP trap handler (if method=snmp_trap)
└── utils.py            # OPTIONAL: Addon-specific helpers
```

---

## Core Services (Provided to Addons)

The core system provides these services to addon modules via dependency injection:

### HTTP Client
```python
class HttpClient:
    """Async HTTP client with connection pooling."""
    
    async def get(self, url: str, auth: tuple = None, headers: dict = None, 
                  timeout: int = 30, verify_ssl: bool = True) -> HttpResponse
    
    async def post(self, url: str, data: dict = None, json: dict = None,
                   auth: tuple = None, headers: dict = None) -> HttpResponse
    
    async def request(self, method: str, url: str, **kwargs) -> HttpResponse

@dataclass
class HttpResponse:
    success: bool
    status_code: int
    data: Any           # Parsed JSON or raw text
    error: str = None
    headers: dict = None
```

### SNMP Client
```python
class SnmpClient:
    """SNMP operations client."""
    
    async def get(self, host: str, oids: List[str], community: str = 'public',
                  version: str = '2c', port: int = 161) -> SnmpResponse
    
    async def walk(self, host: str, oid: str, community: str = 'public') -> SnmpResponse

@dataclass
class SnmpResponse:
    success: bool
    data: Dict[str, Any]  # OID -> value mapping
    error: str = None
```

### SSH Client
```python
class SshClient:
    """SSH command execution client."""
    
    async def exec(self, host: str, command: str, username: str, 
                   password: str = None, key_file: str = None,
                   port: int = 22, timeout: int = 30) -> SshResponse

@dataclass
class SshResponse:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    error: str = None
```

### Credentials
```python
@dataclass
class Credentials:
    """Resolved credentials for a target."""
    username: str = None
    password: str = None
    api_key: str = None
    community: str = None      # SNMP community string
    key_file: str = None       # SSH key path
```

### Target
```python
@dataclass
class Target:
    """Target device information."""
    id: str
    ip_address: str
    name: str
    port: int = None
    config: Dict[str, Any] = None  # Target-specific config
    enabled: bool = True
```

### Logger
```python
# Standard Python logger, pre-configured with addon context
logger = logging.getLogger(f"addon.{addon_id}")
```

---

## Module Interfaces

### poll.py (Required for polling addons)

```python
"""
Axis Camera Polling Module

Handles all polling logic including fallbacks for older firmware.
"""

from typing import List
from dataclasses import dataclass, field

@dataclass
class PollResult:
    """Result from polling a single target."""
    success: bool                           # Overall poll success
    reachable: bool                         # Device responded (even if errors)
    alerts: List[dict] = field(default_factory=list)      # Alerts to create
    clear_types: List[str] = field(default_factory=list)  # Alert types to auto-resolve
    error: str = None                       # Error message if failed
    metrics: dict = None                    # Optional metrics data


async def poll(
    target: 'Target',
    credentials: 'Credentials',
    http: 'HttpClient',
    snmp: 'SnmpClient',
    ssh: 'SshClient',
    logger: 'Logger'
) -> PollResult:
    """
    Poll a single target device.
    
    This function has FULL CONTROL over:
    - Which endpoints/OIDs/commands to use
    - Fallback and retry logic
    - Error handling
    - What constitutes success vs failure
    
    Args:
        target: Target device info (ip_address, name, config)
        credentials: Resolved credentials (username, password, etc.)
        http: HTTP client for API calls
        snmp: SNMP client for SNMP operations
        ssh: SSH client for command execution
        logger: Pre-configured logger
        
    Returns:
        PollResult with alerts to create and alert types to clear
    """
    ip = target.ip_address
    
    # Try primary endpoint (newer Axis firmware)
    resp = await http.get(
        f"http://{ip}/axis-cgi/basicdeviceinfo.cgi",
        auth=(credentials.username, credentials.password),
        timeout=10
    )
    
    if resp.success:
        # Parse response and check for issues
        alerts = parse_device_info(resp.data, target)
        return PollResult(
            success=True,
            reachable=True,
            alerts=alerts,
            clear_types=['camera_offline']
        )
    
    # Fallback for older firmware (404 on basicdeviceinfo)
    if resp.status_code == 404:
        logger.debug(f"{ip}: Trying fallback endpoint for older firmware")
        resp = await http.get(
            f"http://{ip}/axis-cgi/param.cgi?action=list&group=Brand",
            auth=(credentials.username, credentials.password),
            timeout=10
        )
        
        if resp.success:
            return PollResult(
                success=True,
                reachable=True,
                alerts=[],
                clear_types=['camera_offline']
            )
    
    # Auth failure
    if resp.status_code == 401:
        return PollResult(
            success=False,
            reachable=True,  # Device responded, just auth failed
            alerts=[{
                'alert_type': 'auth_failed',
                'message': f'Authentication failed for {ip}'
            }],
            clear_types=[]
        )
    
    # Device truly offline
    return PollResult(
        success=False,
        reachable=False,
        alerts=[{
            'alert_type': 'camera_offline',
            'message': f'Camera {ip} is not responding: {resp.error}'
        }],
        clear_types=[],
        error=resp.error
    )


def parse_device_info(data: str, target: 'Target') -> List[dict]:
    """Parse basicdeviceinfo response for potential alerts."""
    alerts = []
    # Addon-specific parsing logic here
    return alerts
```

### parse.py (Required)

```python
"""
Axis Camera Response Parser

Parses raw responses into normalized alerts.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedAlert:
    """Normalized alert from parsed data."""
    alert_type: str
    device_ip: str
    message: str = None
    device_name: str = None
    timestamp: datetime = None
    is_clear: bool = False
    fields: dict = None       # Additional extracted fields
    raw_data: dict = None     # Original data for debugging


def parse(
    raw_data: any,
    target: 'Target',
    endpoint: str = None,
    logger: 'Logger' = None
) -> List[ParsedAlert]:
    """
    Parse raw response data into alerts.
    
    This function has FULL CONTROL over:
    - Field extraction logic
    - Alert type determination
    - Threshold evaluation
    - Clear event detection
    
    Args:
        raw_data: Raw response (dict, string, bytes)
        target: Target device info
        endpoint: Which endpoint this data came from
        logger: Pre-configured logger
        
    Returns:
        List of ParsedAlert objects (can be empty)
    """
    alerts = []
    
    if endpoint == 'temperature':
        alerts.extend(_parse_temperature(raw_data, target))
    elif endpoint == 'storage':
        alerts.extend(_parse_storage(raw_data, target))
    elif endpoint == 'events':
        alerts.extend(_parse_events(raw_data, target))
    
    return alerts


def _parse_temperature(data: str, target: 'Target') -> List[ParsedAlert]:
    """Parse temperature status response."""
    alerts = []
    
    # Example: root.Status.Temperature.Value=45
    for line in data.split('\n'):
        if 'Temperature.Value=' in line:
            temp = int(line.split('=')[1])
            
            if temp > 70:
                alerts.append(ParsedAlert(
                    alert_type='temperature_critical',
                    device_ip=target.ip_address,
                    device_name=target.name,
                    message=f'Temperature critical: {temp}°C',
                    fields={'temperature': temp}
                ))
            elif temp > 60:
                alerts.append(ParsedAlert(
                    alert_type='temperature_warning',
                    device_ip=target.ip_address,
                    device_name=target.name,
                    message=f'Temperature warning: {temp}°C',
                    fields={'temperature': temp}
                ))
    
    return alerts


def _parse_storage(data: str, target: 'Target') -> List[ParsedAlert]:
    """Parse storage/disk status response."""
    # Addon-specific parsing
    return []


def _parse_events(data: dict, target: 'Target') -> List[ParsedAlert]:
    """Parse event stream data."""
    # Addon-specific parsing
    return []
```

### webhook.py (Optional - for webhook addons)

```python
"""
Webhook Handler for [Addon Name]

Handles incoming webhook payloads from the vendor system.
"""

from typing import List


def handle(
    payload: dict,
    headers: dict,
    source_ip: str,
    logger: 'Logger'
) -> List['ParsedAlert']:
    """
    Handle incoming webhook.
    
    This function has FULL CONTROL over:
    - Payload validation
    - Event extraction
    - Device identification
    - Alert mapping
    
    Args:
        payload: Parsed JSON body
        headers: HTTP headers
        source_ip: IP address of sender
        logger: Pre-configured logger
        
    Returns:
        List of ParsedAlert objects
    """
    alerts = []
    
    # Validate payload
    if 'event_type' not in payload:
        logger.warning(f"Invalid webhook payload from {source_ip}")
        return []
    
    # Extract and normalize
    # ... vendor-specific logic ...
    
    return alerts
```

### trap.py (Optional - for SNMP trap addons)

```python
"""
SNMP Trap Handler for [Addon Name]

Handles incoming SNMP traps from devices.
"""

from typing import List


def handle(
    trap_oid: str,
    varbinds: dict,
    source_ip: str,
    logger: 'Logger'
) -> List['ParsedAlert']:
    """
    Handle incoming SNMP trap.
    
    This function has FULL CONTROL over:
    - OID interpretation
    - Varbind extraction
    - Alert type mapping
    - Clear event detection
    
    Args:
        trap_oid: The trap OID
        varbinds: Dict of OID -> value
        source_ip: IP address of trap sender
        logger: Pre-configured logger
        
    Returns:
        List of ParsedAlert objects
    """
    alerts = []
    
    # Map OID to alert type
    # ... vendor-specific logic ...
    
    return alerts
```

---

## manifest.json (Updated Role)

The manifest now focuses on **metadata and configuration**, not polling logic:

```json
{
  "id": "axis",
  "name": "Axis Cameras",
  "version": "2.0.0",
  "description": "Axis camera monitoring via VAPIX API",
  "author": "OpsConductor",
  "method": "api_poll",
  "category": "video",
  
  "default_poll_interval": 300,
  
  "default_credentials": {
    "username": "root",
    "password": ""
  },
  
  "credential_fields": [
    {"name": "username", "type": "text", "required": true},
    {"name": "password", "type": "password", "required": true}
  ],
  
  "target_config_fields": [
    {"name": "port", "type": "number", "default": 80},
    {"name": "use_https", "type": "boolean", "default": false}
  ],
  
  "alert_mappings": [
    {
      "group": "Availability",
      "alerts": [
        {
          "alert_type": "camera_offline",
          "severity": "critical",
          "category": "video",
          "title": "Camera Offline",
          "description": "Camera is not responding"
        },
        {
          "alert_type": "auth_failed",
          "severity": "major",
          "category": "video",
          "title": "Authentication Failed",
          "description": "Camera rejected credentials"
        }
      ]
    },
    {
      "group": "Environmental",
      "alerts": [
        {
          "alert_type": "temperature_critical",
          "severity": "critical",
          "category": "environment",
          "title": "Temperature Critical",
          "description": "Camera temperature exceeds safe limit"
        },
        {
          "alert_type": "temperature_warning",
          "severity": "warning",
          "category": "environment",
          "title": "Temperature Warning",
          "description": "Camera temperature elevated"
        }
      ]
    }
  ]
}
```

---

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        CELERY TASK                               │
│                    poll_single_target                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CORE: LOAD ADDON                             │
│  1. Load manifest.json                                           │
│  2. Import poll.py module                                        │
│  3. Import parse.py module                                       │
│  4. Resolve credentials (target config → addon defaults)         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CORE: PREPARE SERVICES                         │
│  - Create/reuse HTTP client with connection pool                 │
│  - Create/reuse SNMP client                                      │
│  - Create/reuse SSH client                                       │
│  - Create logger with addon context                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ADDON: poll.poll()                            │
│  - Full control over polling logic                               │
│  - Uses provided HTTP/SNMP/SSH clients                           │
│  - Handles fallbacks, retries, errors                            │
│  - Returns PollResult with alerts and clear_types                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CORE: PROCESS RESULTS                           │
│  For each alert in PollResult.alerts:                            │
│    1. Look up severity/category/title from manifest              │
│    2. Generate fingerprint (addon:type:device_ip)                │
│    3. Deduplicate against existing alerts                        │
│    4. Store to database                                          │
│    5. Emit WebSocket event                                       │
│                                                                  │
│  For each type in PollResult.clear_types:                        │
│    1. Find active alert with matching type/device                │
│    2. Resolve alert                                              │
│    3. Emit WebSocket event                                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CORE: UPDATE TARGET                             │
│  - Set last_poll_at = NOW()                                      │
│  - Update any metrics                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core System Changes Required

### Files to Modify (ONE-TIME, requires approval)

| File | Change |
|------|--------|
| `backend/core/addon_registry.py` | Load poll.py and parse.py modules |
| `backend/tasks/tasks.py` | Call addon.poll() instead of declarative polling |
| `backend/core/types.py` | New file with shared types (PollResult, ParsedAlert, etc.) |
| `backend/core/clients.py` | New file with HttpClient, SnmpClient, SshClient wrappers |

### Addon Loader Changes

```python
# backend/core/addon_registry.py

import importlib.util
from pathlib import Path

def load_addon_modules(addon_id: str, addon_path: Path) -> dict:
    """Load Python modules from addon directory."""
    modules = {}
    
    for module_name in ['poll', 'parse', 'webhook', 'trap']:
        module_file = addon_path / f"{module_name}.py"
        if module_file.exists():
            spec = importlib.util.spec_from_file_location(
                f"addons.{addon_id}.{module_name}",
                module_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules[module_name] = module
    
    return modules
```

### Task Dispatcher Changes

```python
# backend/tasks/tasks.py

async def _poll_target_async(addon: Addon, target: Dict, clients: Clients) -> int:
    """Poll a single target using addon's poll module."""
    
    # Resolve credentials
    credentials = resolve_credentials(target, addon)
    
    # Create logger with addon context
    logger = logging.getLogger(f"addon.{addon.id}")
    
    # Call addon's poll function
    try:
        result = await addon.modules['poll'].poll(
            target=Target(**target),
            credentials=credentials,
            http=clients.http,
            snmp=clients.snmp,
            ssh=clients.ssh,
            logger=logger
        )
    except Exception as e:
        logger.error(f"Addon poll error for {target['ip_address']}: {e}")
        result = PollResult(
            success=False,
            reachable=False,
            alerts=[{
                'alert_type': 'poll_error',
                'message': f'Poll failed: {str(e)}'
            }],
            error=str(e)
        )
    
    # Process results through alert engine
    alert_count = await process_poll_result(result, addon, target)
    
    return alert_count
```

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Addon code runs in same process | Only install trusted addons |
| Addon could hang forever | Wrap poll() in asyncio.wait_for() with timeout |
| Addon could crash worker | Wrap in try/except, log error, continue |
| Addon could access filesystem | Future: Consider sandboxing |
| Addon could make arbitrary network calls | Acceptable - addons need network access |

---

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create `backend/core/types.py` with shared dataclasses
2. Create `backend/core/clients.py` with HTTP/SNMP/SSH wrappers
3. Update `backend/core/addon_registry.py` to load modules
4. Update `backend/tasks/tasks.py` to call addon modules
5. Remove declarative polling code from tasks.py

### Phase 2: Axis Addon Migration
1. Create `backend/addons/axis/__init__.py`
2. Create `backend/addons/axis/poll.py` with fallback logic
3. Create `backend/addons/axis/parse.py` with response parsing
4. Test with new and old cameras
5. Verify alerts work correctly

### Phase 3: Other Addons
1. Migrate remaining addons to new structure
2. Create addon template for new development
3. Update documentation

---

## Benefits Summary

| Benefit | Description |
|---------|-------------|
| **Core is generic** | No vendor-specific code, ever |
| **Addons are complete** | All vendor logic in one place |
| **Easy debugging** | Problem with Axis? Look at `addons/axis/` |
| **Easy testing** | Unit test addon modules in isolation |
| **Easy development** | Copy template, implement interfaces |
| **No core changes** | New vendor = new addon folder only |

---

## Approval Required

This architecture requires **one-time core changes** to enable the addon module system. After implementation:

- ✅ All future vendor-specific logic goes in addons
- ✅ Core never needs modification for new vendors
- ✅ Addons have full control over their behavior

**Ready for implementation upon approval.**
