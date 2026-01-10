# 06 - Connector Specifications

**OpsConductor MVP - All 9 Connector Implementations**

---

## 1. Connector Architecture

### 1.1 Base Interface

All connectors implement this interface:

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any

class BaseConnector(ABC):
    """Base class for all alert source connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = False
        self.status = "disconnected"
        self.error_message: Optional[str] = None
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return connector type identifier."""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start receiving/polling alerts."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop and cleanup resources."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity. Returns {success, message, details}."""
        pass
    
    @abstractmethod
    def get_normalizer(self) -> 'BaseNormalizer':
        """Return normalizer instance for this connector."""
        pass


class BaseNormalizer(ABC):
    """Base class for alert normalizers."""
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> 'NormalizedAlert':
        """Transform raw alert to standard schema."""
        pass
    
    @abstractmethod
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        pass
```

### 1.2 Connector Registry

```python
# backend/connectors/registry.py

CONNECTOR_REGISTRY = {
    "prtg": PRTGConnector,
    "mcp": MCPConnector,
    "snmp_trap": SNMPTrapConnector,
    "snmp_poll": SNMPPollConnector,
    "eaton": EatonConnector,
    "axis": AxisConnector,
    "milestone": MilestoneConnector,
    "cradlepoint": CradlepointConnector,
    "siklu": SikluConnector,
    "ubiquiti": UbiquitiConnector,
}
```

---

## 2. PRTG Connector

**Status:** Refactor from `prtg_service.py`

### 2.1 Overview

| Property | Value |
|----------|-------|
| Input Method | Webhook + API Poll |
| Protocol | HTTPS REST |
| Auth | API Token or Username/Passhash |
| Existing Code | `backend/services/prtg_service.py` |

### 2.2 Configuration

```json
{
  "url": "https://prtg.example.com",
  "api_token": "xxx",
  "username": "admin",
  "passhash": "xxx",
  "verify_ssl": true,
  "poll_interval": 60,
  "webhook_secret": "optional-secret"
}
```

### 2.3 Alert Fields Mapping

| PRTG Field | Normalized Field | Notes |
|------------|------------------|-------|
| sensorid | source_alert_id | |
| host | device_ip | |
| device | device_name | |
| status | severity | Map: Down→critical, Warning→warning |
| name (sensor) | alert_type | |
| message | message | |
| datetime | occurred_at | Parse PRTG format |

### 2.4 Severity Mapping

```python
PRTG_SEVERITY_MAP = {
    "Down": "critical",
    "Warning": "major",
    "Unusual": "warning",
    "Up": "clear",
    "Paused": "info",
    "Unknown": "warning",
}
```

### 2.5 Webhook Endpoint

```
POST /api/v1/connectors/prtg/webhook
Content-Type: application/x-www-form-urlencoded

sensorid=1234&deviceid=100&device=Switch&status=Down&message=Ping%20failed...
```

---

## 3. MCP Connector (Ciena)

**Status:** Refactor from `ciena_mcp_service.py`

### 3.1 Overview

| Property | Value |
|----------|-------|
| Input Method | API Poll |
| Protocol | HTTPS REST |
| Auth | Username/Password → Bearer Token |
| Existing Code | `backend/services/ciena_mcp_service.py` |

### 3.2 Configuration

```json
{
  "url": "https://mcp.example.com",
  "username": "admin",
  "password": "xxx",
  "verify_ssl": false,
  "poll_interval": 60
}
```

### 3.3 API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/tron/api/v1/tokens` | Authentication |
| `/nsi/api/v1/networkConstructs` | Equipment inventory |
| `/nsi/api/v1/alarms` | Active alarms |
| `/nsi/api/v1/events` | Event history |

### 3.4 Alert Fields Mapping

| MCP Field | Normalized Field | Notes |
|-----------|------------------|-------|
| alarmId | source_alert_id | |
| sourceIp | device_ip | |
| sourceName | device_name | |
| severity | severity | Map MCP severities |
| alarmType | alert_type | |
| description | message | |
| raisedTime | occurred_at | |

### 3.5 Severity Mapping

```python
MCP_SEVERITY_MAP = {
    "CRITICAL": "critical",
    "MAJOR": "major",
    "MINOR": "minor",
    "WARNING": "warning",
    "CLEARED": "clear",
}
```

---

## 4. SNMP Trap Connector

**Status:** Refactor from `snmp_trap_receiver.py`

### 4.1 Overview

| Property | Value |
|----------|-------|
| Input Method | UDP Listener |
| Protocol | SNMP v1/v2c/v3 |
| Port | 162 |
| Existing Code | `backend/services/snmp_trap_receiver.py` |

### 4.2 Configuration

```json
{
  "bind_address": "0.0.0.0",
  "port": 162,
  "community": "public",
  "snmpv3_users": [
    {
      "username": "admin",
      "auth_protocol": "SHA",
      "auth_password": "xxx",
      "priv_protocol": "AES",
      "priv_password": "xxx"
    }
  ]
}
```

### 4.3 Trap Processing Flow

```
1. Receive UDP packet on port 162
2. Decode SNMP trap (pysnmp)
3. Extract:
   - source_ip (from packet)
   - trap_oid (snmpTrapOID)
   - enterprise_oid
   - varbinds (key-value pairs)
4. Lookup trap_oid in oid_mappings table
5. Apply mapping OR use generic handler
6. Normalize to standard schema
```

### 4.4 Alert Fields Mapping

| Trap Field | Normalized Field | Notes |
|------------|------------------|-------|
| source_ip | device_ip | From UDP source |
| trap_oid | alert_type | Via OID mapping |
| - | category | Via OID mapping |
| - | severity | Via OID mapping |
| varbinds | message + raw_data | Formatted varbinds |

### 4.5 Standard Trap Mappings

Pre-seeded in `oid_mappings`:

| Trap OID | Alert Type | Severity |
|----------|------------|----------|
| 1.3.6.1.6.3.1.1.5.1 | cold_start | warning |
| 1.3.6.1.6.3.1.1.5.2 | warm_start | info |
| 1.3.6.1.6.3.1.1.5.3 | link_down | major |
| 1.3.6.1.6.3.1.1.5.4 | link_up | clear |
| 1.3.6.1.6.3.1.1.5.5 | auth_failure | warning |

---

## 5. SNMP Poll Connector

**Status:** Refactor from `async_snmp_poller.py`

### 5.1 Overview

| Property | Value |
|----------|-------|
| Input Method | Active Polling |
| Protocol | SNMP v1/v2c/v3 |
| Existing Code | `backend/services/async_snmp_poller.py` |

### 5.2 Configuration

```json
{
  "poll_interval": 300,
  "timeout": 5,
  "retries": 2,
  "targets": [
    {
      "ip": "10.1.1.1",
      "community": "public",
      "version": "2c",
      "oids": ["system", "interfaces", "optical"]
    }
  ]
}
```

### 5.3 Poll Types

| Type | OIDs | Alert Condition |
|------|------|-----------------|
| Reachability | sysUpTime | No response |
| Interface Status | ifOperStatus | Status change |
| Optical Power | vendor-specific | Threshold exceeded |
| CPU/Memory | vendor-specific | Threshold exceeded |

### 5.4 Alert Generation

Alerts generated when:
- Device unreachable
- Interface status changes (up→down)
- Metric exceeds configured threshold
- Metric returns to normal (clear)

---

## 6. Eaton UPS Connector

**Status:** Refactor from `eaton_snmp_service.py`

### 6.1 Overview

| Property | Value |
|----------|-------|
| Input Method | SNMP Poll |
| Protocol | SNMP v1/v2c |
| MIB | XUPS-MIB (PowerMIB) |
| Existing Code | `backend/services/eaton_snmp_service.py` |

### 6.2 Configuration

```json
{
  "targets": [
    {
      "ip": "10.1.2.1",
      "name": "UPS-Main",
      "community": "public",
      "poll_interval": 60
    }
  ],
  "thresholds": {
    "battery_capacity_low": 30,
    "battery_capacity_critical": 10,
    "load_warning": 80,
    "load_critical": 95,
    "temp_high": 40
  }
}
```

### 6.3 Monitored OIDs

| Metric | OID | Alert Condition |
|--------|-----|-----------------|
| Battery Status | 1.3.6.1.4.1.534.1.2.5.0 | Not "charging" or "floating" |
| Battery Capacity | 1.3.6.1.4.1.534.1.2.4.0 | Below threshold |
| Output Load | 1.3.6.1.4.1.534.1.4.1.0 | Above threshold |
| Output Source | 1.3.6.1.4.1.534.1.4.5.0 | Not "normal" (3) |
| Temperature | 1.3.6.1.4.1.534.1.6.1.0 | Above threshold |
| Alarm Flags | 1.3.6.1.4.1.534.1.7.* | Any alarm active |

### 6.4 Alarm Types

| Alarm | Category | Default Severity |
|-------|----------|------------------|
| on_battery | power | warning |
| low_battery | power | critical |
| battery_bad | power | major |
| output_overload | power | critical |
| on_bypass | power | warning |
| charger_failure | power | major |
| fan_failure | environment | major |
| shutdown_imminent | power | critical |

---

## 7. Axis VAPIX Connector

**Status:** NEW - Build from scratch

### 7.1 Overview

| Property | Value |
|----------|-------|
| Input Method | Event Stream + Poll |
| Protocol | HTTPS REST (VAPIX) |
| Auth | Basic or Digest |
| Documentation | [Axis VAPIX Library](https://www.axis.com/vapix-library/) |

### 7.2 Configuration

```json
{
  "targets": [
    {
      "ip": "10.1.3.1",
      "name": "Camera-Lobby",
      "username": "root",
      "password": "xxx",
      "events_enabled": true
    }
  ],
  "poll_interval": 60,
  "event_types": ["motion", "tampering", "disk", "network"]
}
```

### 7.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/axis-cgi/basicdeviceinfo.cgi` | Device info |
| `/axis-cgi/eventlist.cgi` | List event types |
| `/axis-cgi/events/notification.cgi` | Subscribe to events |
| `/axis-cgi/disks/list.cgi` | Storage status |
| `/axis-cgi/systemlog.cgi` | System logs |

### 7.4 Event Types

| Event | Category | Default Severity |
|-------|----------|------------------|
| Motion Detected | video | info |
| Tampering | security | major |
| Disk Full | storage | major |
| Disk Error | storage | critical |
| Network Lost | network | critical |
| Recording Error | video | major |
| Temperature High | environment | warning |

### 7.5 Implementation Notes

```python
class AxisConnector(BaseConnector):
    """Axis camera connector using VAPIX API."""
    
    async def poll_camera(self, target: dict) -> List[dict]:
        """Poll single camera for status and events."""
        # 1. Check reachability
        # 2. Get device status
        # 3. Get disk status
        # 4. Get recent events
        # 5. Generate alerts for issues
        pass
    
    async def subscribe_events(self, target: dict):
        """Subscribe to real-time event notifications."""
        # Uses VAPIX event subscription
        # Long-poll or WebSocket depending on camera
        pass
```

---

## 8. Milestone VMS Connector

**Status:** NEW - Build from scratch

### 8.1 Overview

| Property | Value |
|----------|-------|
| Input Method | API Poll + Events |
| Protocol | HTTPS REST |
| Auth | Basic or Windows Auth |
| Documentation | Milestone MIP SDK |

### 8.2 Configuration

```json
{
  "url": "https://milestone.example.com",
  "username": "admin",
  "password": "xxx",
  "auth_type": "basic",
  "poll_interval": 60
}
```

### 8.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/IServerCommandService/GetConfiguration` | System config |
| `/IRecorderCommandService/GetCameraStatus` | Camera status |
| `/IEventServerService/GetEvents` | Event stream |
| `/ISystemEventService/GetAlarms` | Active alarms |

### 8.4 Event Types

| Event | Category | Default Severity |
|-------|----------|------------------|
| Camera Communication Error | video | major |
| Recording Started/Stopped | video | info |
| Motion Detected | video | info |
| Analytics Event | video | warning |
| Storage Alert | storage | major |
| Server Error | compute | critical |
| License Warning | application | warning |

---

## 9. Cradlepoint NCOS Connector

**Status:** NEW - Build from scratch

### 9.1 Overview

| Property | Value |
|----------|-------|
| Input Method | API Poll |
| Protocol | HTTPS REST |
| Auth | Basic (local) or ECM API |
| Documentation | Cradlepoint NCOS API |

### 9.2 Configuration

```json
{
  "targets": [
    {
      "ip": "192.168.0.1",
      "name": "Router-Site1",
      "username": "admin",
      "password": "xxx"
    }
  ],
  "thresholds": {
    "rssi_warning": -85,
    "rssi_critical": -95,
    "rsrp_warning": -100,
    "rsrp_critical": -110,
    "sinr_warning": 5,
    "sinr_critical": 0
  },
  "poll_interval": 60
}
```

### 9.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/api/status/wan/devices/mdm-xxx/` | Modem status |
| `/api/status/wan/devices/mdm-xxx/diagnostics/` | Signal metrics |
| `/api/status/system/` | System status |
| `/api/status/wan/connection_state/` | WAN state |

### 9.4 Metrics & Thresholds

| Metric | Unit | Warning | Critical |
|--------|------|---------|----------|
| RSSI | dBm | < -85 | < -95 |
| RSRP | dBm | < -100 | < -110 |
| RSRQ | dB | < -12 | < -15 |
| SINR | dB | < 5 | < 0 |

### 9.5 Alert Types

| Alert | Category | Trigger |
|-------|----------|---------|
| Signal Low | wireless | RSSI/RSRP below threshold |
| Signal Critical | wireless | RSSI/RSRP critical |
| Connection Lost | wireless | No cellular connection |
| WAN Failover | network | Primary WAN failed |
| Carrier Change | wireless | Switched to different carrier |

---

## 10. Siklu Connector

**Status:** NEW - Build from scratch

### 10.1 Overview

| Property | Value |
|----------|-------|
| Input Method | API Poll + SNMP |
| Protocol | HTTPS REST / SNMP |
| Auth | Basic |
| Documentation | Siklu EtherHaul API |

### 10.2 Configuration

```json
{
  "targets": [
    {
      "ip": "10.1.4.1",
      "name": "Radio-Site1-A",
      "username": "admin",
      "password": "xxx",
      "peer_ip": "10.1.4.2"
    }
  ],
  "thresholds": {
    "rsl_warning": -55,
    "rsl_critical": -60,
    "modulation_min": "256QAM"
  },
  "poll_interval": 60
}
```

### 10.3 Monitored Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| RSL | dBm | Received Signal Level |
| Link State | up/down | Radio link status |
| Modulation | QAM level | Current modulation |
| Ethernet Port | up/down | Connected port status |
| Temperature | °C | Radio temperature |

### 10.4 Alert Types

| Alert | Category | Default Severity |
|-------|----------|------------------|
| Link Down | wireless | critical |
| RSL Low | wireless | warning |
| RSL Critical | wireless | major |
| Modulation Drop | wireless | warning |
| Ethernet Down | network | major |
| High Temperature | environment | warning |

---

## 11. Ubiquiti UISP Connector

**Status:** NEW - Build from scratch

### 11.1 Overview

| Property | Value |
|----------|-------|
| Input Method | API Poll |
| Protocol | HTTPS REST |
| Auth | API Token |
| Documentation | UISP API |

### 11.2 Configuration

```json
{
  "url": "https://uisp.example.com",
  "api_token": "xxx",
  "poll_interval": 60,
  "include_device_types": ["airMax", "airFiber", "edgeRouter"]
}
```

### 11.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/nms/api/v2.1/devices` | Device list |
| `/nms/api/v2.1/devices/{id}` | Device details |
| `/nms/api/v2.1/devices/{id}/statistics` | Device stats |
| `/nms/api/v2.1/outages` | Outage events |
| `/nms/api/v2.1/alerts` | System alerts |

### 11.4 Alert Types

| Alert | Category | Default Severity |
|-------|----------|------------------|
| Device Offline | network | critical |
| High CPU | compute | warning |
| High Memory | compute | warning |
| Interface Down | network | major |
| Signal Degraded | wireless | warning |
| Reboot Detected | network | info |
| Config Changed | security | info |

---

## 12. Connector Implementation Checklist

For each new connector:

- [ ] Create `backend/connectors/{name}/connector.py`
- [ ] Create `backend/connectors/{name}/normalizer.py`
- [ ] Implement `BaseConnector` interface
- [ ] Implement `BaseNormalizer` interface
- [ ] Add to `CONNECTOR_REGISTRY`
- [ ] Create database seed for connector
- [ ] Add OID mappings (if SNMP-based)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Document configuration options
- [ ] Test with real device

---

*Next: [07_FRONTEND.md](./07_FRONTEND.md)*
