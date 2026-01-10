# Axis Camera Alert Mapping

This document defines the complete mapping between Axis camera VAPIX API responses and OpsConductor's normalized alert structure.

**Connector Type:** `axis`  
**Source System:** `axis`  
**Last Updated:** 2026-01-07  
**Version:** 1.0

---

## Table of Contents

1. [Normalized Alert Structure](#normalized-alert-structure)
2. [Severity Definitions](#severity-definitions)
3. [Category Definitions](#category-definitions)
4. [Status Definitions](#status-definitions)
5. [VAPIX Endpoints Used](#vapix-endpoints-used)
6. [Alert Mappings by Category](#alert-mappings-by-category)
   - [Availability Alerts](#availability-alerts)
   - [Storage Alerts](#storage-alerts)
   - [Recording Alerts](#recording-alerts)
   - [Video/Stream Alerts](#videostream-alerts)
   - [Security/Tampering Alerts](#securitytampering-alerts)
   - [Power Alerts](#power-alerts)
   - [PTZ Alerts](#ptz-alerts)
   - [Environmental Alerts](#environmental-alerts)
   - [Hardware Alerts](#hardware-alerts)
   - [Network Alerts](#network-alerts)
   - [Firmware/System Alerts](#firmwaresystem-alerts)
7. [System Log Pattern Matching](#system-log-pattern-matching)
8. [Fingerprint Generation](#fingerprint-generation)
9. [Reconciliation Logic](#reconciliation-logic)

---

## Normalized Alert Structure

All Axis camera alerts are normalized to the following structure:

```python
NormalizedAlert(
    source_system="axis",
    source_alert_id="{camera_ip}_{alert_type}_{hash}",
    severity=<Severity>,           # critical, major, minor, warning, info
    category=<Category>,           # availability, hardware, application, security, etc.
    status="active",               # active, acknowledged, suppressed, resolved
    title="{Alert Name}: {Camera Name}",
    description="{Detailed description of the alert condition}",
    device_ip="{camera_ip}",
    device_name="{camera_name}",
    alert_type="{alert_type_code}",
    occurred_at=<timestamp>,
    raw_data={
        "camera_ip": "{ip}",
        "camera_name": "{name}",
        "camera_model": "{model}",
        "firmware_version": "{version}",
        "vapix_endpoint": "{endpoint_that_detected_issue}",
        "raw_response": "{original_response_data}",
        "event_type": "{alert_type_code}",
        "additional_context": {...}
    }
)
```

---

## Severity Definitions

| Severity | Code | Usage |
|----------|------|-------|
| **Critical** | `critical` | Immediate action required. Camera offline, storage failed, video loss, tampering, overheating, PTZ failure |
| **Major** | `major` | Significant issue. Auth failed, storage missing, recording error, power issues, lens errors |
| **Minor** | `minor` | Notable issue requiring attention. Currently unused for Axis |
| **Warning** | `warning` | Potential issue. Storage >80%, temperature elevated, network degraded, focus issues |
| **Info** | `info` | Informational. Firmware outdated, camera rebooted, configuration changes |

---

## Category Definitions

| Category | Code | Usage |
|----------|------|-------|
| **Availability** | `availability` | Camera reachability, connectivity issues |
| **Hardware** | `hardware` | Physical components: storage, sensors, fans, lenses, power |
| **Application** | `application` | Software functions: recording, streaming, analytics |
| **Security** | `security` | Tampering, unauthorized access, physical security |
| **Environmental** | `environmental` | Temperature, humidity, weather-related |
| **Network** | `network` | Network configuration, connectivity quality |
| **Maintenance** | `maintenance` | Firmware updates, system restarts, configuration |

---

## Status Definitions

| Status | Code | Description |
|--------|------|-------------|
| **Active** | `active` | Alert condition currently exists |
| **Acknowledged** | `acknowledged` | Operator has seen and acknowledged the alert |
| **Suppressed** | `suppressed` | Alert is temporarily suppressed (maintenance window) |
| **Resolved** | `resolved` | Alert condition no longer exists |

---

## VAPIX Endpoints Used

| Endpoint | Purpose | Poll Frequency |
|----------|---------|----------------|
| `/axis-cgi/basicdeviceinfo.cgi` | Device info, connectivity check | Every poll cycle |
| `/axis-cgi/disks/list.cgi` | Storage status, capacity | Every 5 minutes |
| `/axis-cgi/record/list.cgi` | Recording status | Every poll cycle |
| `/axis-cgi/jpg/image.cgi` | Video signal check | Every 5 minutes |
| `/axis-cgi/systemlog.cgi` | System log for errors/warnings | Every poll cycle |
| `/axis-cgi/param.cgi?action=list&group=Status` | System status flags | Every poll cycle |
| `/axis-cgi/param.cgi?action=list&group=Status.Temperature` | Temperature readings | Every 5 minutes |
| `/axis-cgi/eventlist.cgi` | Event subscriptions | Real-time if supported |

---

## Alert Mappings by Category

### Availability Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `camera_offline` | **Camera Offline** | `critical` | `availability` | Connection to `/axis-cgi/basicdeviceinfo.cgi` | Connection timeout (>10s) or connection refused |
| `camera_auth_failed` | **Camera Auth Failed** | `major` | `availability` | Any VAPIX endpoint | HTTP 401 or 403 response |
| `camera_unreachable` | **Camera Unreachable** | `critical` | `availability` | Any VAPIX endpoint | DNS resolution failure or network unreachable |

**Resolution:** Alert auto-resolves when camera responds successfully to basicdeviceinfo.cgi

---

### Storage Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `storage_failure` | **Storage Failure** | `critical` | `hardware` | `/axis-cgi/disks/list.cgi` | Disk status = "fail" or "error" |
| `storage_full` | **Storage Full** | `critical` | `hardware` | `/axis-cgi/disks/list.cgi` | Disk usage ≥ 95% |
| `storage_warning` | **Storage Warning** | `warning` | `hardware` | `/axis-cgi/disks/list.cgi` | Disk usage ≥ 80% and < 95% |
| `storage_missing` | **No Storage Detected** | `major` | `hardware` | `/axis-cgi/disks/list.cgi` | No disk/SD card found in response |
| `storage_readonly` | **Storage Read-Only** | `major` | `hardware` | `/axis-cgi/disks/list.cgi` | Disk mounted as read-only |

**Resolution:** Alert auto-resolves when storage returns to normal status

---

### Recording Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `recording_stopped` | **Recording Stopped** | `critical` | `application` | `/axis-cgi/record/list.cgi` | Recording status = "off" or "stopped" when expected "on" |
| `recording_error` | **Recording Error** | `major` | `application` | `/axis-cgi/record/list.cgi` | Recording status = "error" or API returns error |
| `recording_schedule_error` | **Recording Schedule Error** | `warning` | `application` | `/axis-cgi/record/list.cgi` | Schedule configuration invalid |

**Resolution:** Alert auto-resolves when recording resumes

---

### Video/Stream Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `video_loss` | **Video Loss** | `critical` | `hardware` | `/axis-cgi/jpg/image.cgi` | Returns error, black frame, or no image data |
| `stream_timeout` | **Stream Timeout** | `major` | `application` | Video stream request | Stream request times out (>30s) |
| `video_degraded` | **Video Quality Degraded** | `warning` | `hardware` | Image analysis | Significant quality reduction detected |

**Resolution:** Alert auto-resolves when video signal is restored

---

### Security/Tampering Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `tampering_detected` | **Camera Tampering** | `critical` | `security` | Event API: `tns1:VideoSource/GlobalSceneChange/ImagingService` | Camera view obstructed, spray, covered |
| `tampering_physical` | **Physical Tampering** | `critical` | `security` | Event API: `tns1:Device/Trigger/DigitalInput` | Physical tamper switch triggered |
| `camera_moved` | **Camera Position Changed** | `major` | `security` | Event API: Scene change detection | Camera orientation significantly changed |
| `unauthorized_access` | **Unauthorized Access Attempt** | `major` | `security` | System log | Multiple failed login attempts |

**Resolution:** Alert auto-resolves when tampering condition clears (for scene-based), or requires manual resolution for physical tampering

---

### Power Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `power_insufficient` | **Insufficient Power** | `major` | `hardware` | System log | Log contains "insufficient power", "PoE budget", "power limit" |
| `poe_warning` | **PoE Power Warning** | `warning` | `hardware` | System log | Log contains "PoE" warning messages |
| `power_supply_error` | **Power Supply Error** | `critical` | `hardware` | Event API: `tns1:Device/HardwareFailure/PowerSupply` | Power supply failure event |
| `ups_battery_low` | **UPS Battery Low** | `warning` | `hardware` | System log | UPS battery warning (if camera has UPS input) |

**Resolution:** Alert auto-resolves when power condition normalizes

---

### PTZ Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `ptz_error` | **PTZ Error** | `major` | `hardware` | System log | Log contains "PTZ" error messages |
| `ptz_power_insufficient` | **PTZ Power Insufficient** | `major` | `hardware` | System log | Log contains "not enough power for PTZ", "PTZ power" |
| `ptz_motor_failure` | **PTZ Motor Failure** | `critical` | `hardware` | System log | Log contains "motor", "pan", "tilt" failure messages |
| `ptz_preset_failure` | **PTZ Preset Failure** | `warning` | `hardware` | Event API: `tns1:PTZController/PTZPresets/Failure` | Preset position cannot be reached |
| `ptz_limit_reached` | **PTZ Limit Reached** | `info` | `hardware` | System log | PTZ reached mechanical limit |

**Resolution:** Alert auto-resolves when PTZ operates normally

---

### Environmental Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `temperature_critical` | **Camera Overheating** | `critical` | `environmental` | `/axis-cgi/param.cgi?action=list&group=Status.Temperature` | Temperature > 70°C |
| `temperature_warning` | **Camera Temperature Warning** | `warning` | `environmental` | `/axis-cgi/param.cgi?action=list&group=Status.Temperature` | Temperature > 60°C and ≤ 70°C |
| `temperature_low` | **Camera Temperature Low** | `warning` | `environmental` | `/axis-cgi/param.cgi?action=list&group=Status.Temperature` | Temperature < -20°C (below operating range) |
| `heater_failure` | **Heater Failure** | `major` | `environmental` | System log | Log contains "heater" failure messages |
| `fan_failure` | **Fan Failure** | `critical` | `environmental` | System log | Log contains "fan" failure messages |
| `housing_open` | **Housing Open** | `major` | `environmental` | Event API or system log | Camera housing/enclosure opened |

**Resolution:** Alert auto-resolves when environmental condition normalizes

---

### Hardware Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `lens_error` | **Lens Error** | `major` | `hardware` | System log | Log contains "lens" error messages |
| `focus_failure` | **Auto-Focus Failed** | `warning` | `hardware` | System log | Log contains "focus" failure messages |
| `ir_failure` | **IR Illuminator Failure** | `warning` | `hardware` | System log | Log contains "IR", "illuminator" failure messages |
| `sensor_failure` | **Image Sensor Failure** | `critical` | `hardware` | System log | Log contains "sensor", "imager" failure messages |
| `audio_failure` | **Audio System Failure** | `warning` | `hardware` | System log | Log contains "audio", "microphone", "speaker" failure |
| `io_error` | **I/O Port Error** | `warning` | `hardware` | System log | Log contains "I/O", "digital input", "relay" errors |

**Resolution:** Alert auto-resolves when hardware operates normally or requires manual intervention

---

### Network Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `network_config_error` | **Network Config Error** | `major` | `network` | `/axis-cgi/param.cgi` network params | Invalid or conflicting network configuration |
| `network_degraded` | **Network Degraded** | `warning` | `network` | Response time analysis | Average response time > 5 seconds |
| `ip_conflict` | **IP Address Conflict** | `major` | `network` | System log | Log contains "IP conflict", "duplicate IP" |
| `dns_failure` | **DNS Resolution Failure** | `warning` | `network` | System log | Log contains "DNS" failure messages |

**Resolution:** Alert auto-resolves when network condition normalizes

---

### Firmware/System Alerts

| Alert Type Code | Alert Name | Severity | Category | VAPIX Source | Trigger Condition |
|-----------------|------------|----------|----------|--------------|-------------------|
| `firmware_outdated` | **Firmware Outdated** | `info` | `maintenance` | `/axis-cgi/basicdeviceinfo.cgi` | Firmware version below defined threshold |
| `camera_rebooted` | **Camera Rebooted** | `info` | `maintenance` | System log or uptime check | Camera uptime < 5 minutes |
| `config_changed` | **Configuration Changed** | `info` | `maintenance` | System log | Log contains configuration change entries |
| `certificate_expiring` | **Certificate Expiring** | `warning` | `maintenance` | Certificate check | SSL certificate expires within 30 days |
| `certificate_expired` | **Certificate Expired** | `major` | `maintenance` | Certificate check | SSL certificate has expired |
| `system_error` | **System Error** | `major` | `maintenance` | System log | Log contains unclassified "error" messages |

**Resolution:** Info alerts auto-resolve after acknowledgment period; certificate alerts resolve when renewed

---

## System Log Pattern Matching

The connector parses `/axis-cgi/systemlog.cgi` for the following patterns:

```python
SYSTEM_LOG_PATTERNS = {
    # Power patterns
    r"insufficient power": ("power_insufficient", "major", "hardware"),
    r"PoE budget": ("power_insufficient", "major", "hardware"),
    r"power limit": ("power_insufficient", "major", "hardware"),
    r"power supply": ("power_supply_error", "critical", "hardware"),
    
    # PTZ patterns
    r"not enough power for PTZ": ("ptz_power_insufficient", "major", "hardware"),
    r"PTZ.*error": ("ptz_error", "major", "hardware"),
    r"PTZ.*fail": ("ptz_error", "major", "hardware"),
    r"motor.*fail": ("ptz_motor_failure", "critical", "hardware"),
    r"pan.*fail": ("ptz_motor_failure", "critical", "hardware"),
    r"tilt.*fail": ("ptz_motor_failure", "critical", "hardware"),
    
    # Hardware patterns
    r"fan.*fail": ("fan_failure", "critical", "environmental"),
    r"heater.*fail": ("heater_failure", "major", "environmental"),
    r"lens.*error": ("lens_error", "major", "hardware"),
    r"focus.*fail": ("focus_failure", "warning", "hardware"),
    r"IR.*fail": ("ir_failure", "warning", "hardware"),
    r"illuminator.*fail": ("ir_failure", "warning", "hardware"),
    r"sensor.*fail": ("sensor_failure", "critical", "hardware"),
    r"imager.*fail": ("sensor_failure", "critical", "hardware"),
    r"audio.*fail": ("audio_failure", "warning", "hardware"),
    r"microphone.*fail": ("audio_failure", "warning", "hardware"),
    
    # Network patterns
    r"IP conflict": ("ip_conflict", "major", "network"),
    r"duplicate IP": ("ip_conflict", "major", "network"),
    r"DNS.*fail": ("dns_failure", "warning", "network"),
    
    # Security patterns
    r"login.*fail": ("unauthorized_access", "major", "security"),
    r"authentication.*fail": ("unauthorized_access", "major", "security"),
    
    # Storage patterns
    r"disk.*fail": ("storage_failure", "critical", "hardware"),
    r"SD card.*fail": ("storage_failure", "critical", "hardware"),
    r"storage.*error": ("storage_failure", "critical", "hardware"),
}
```

---

## Fingerprint Generation

Alert fingerprints are generated to enable deduplication and reconciliation:

```python
def generate_fingerprint(camera_ip: str, alert_type: str) -> str:
    """
    Generate unique fingerprint for Axis camera alert.
    
    Format: SHA256("axis:{camera_ip}:{alert_type}")
    
    Note: Does NOT include timestamp - same alert type from same camera
    should deduplicate regardless of when it occurred.
    """
    fingerprint_str = f"axis:{camera_ip}:{alert_type}"
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()
```

---

## Reconciliation Logic

When polling cameras, the connector implements reconciliation to auto-resolve alerts:

1. **Poll all cameras** and collect current alert conditions
2. **Compare with active alerts** in database for source_system="axis"
3. **Auto-resolve** any active alerts whose fingerprint is NOT in current poll results
4. **Set resolved_at** timestamp and change status to "resolved"
5. **Publish WebSocket event** for real-time UI updates

```python
# Reconciliation runs after each poll cycle
# Alerts are resolved with:
#   - status: "resolved"
#   - resolved_at: current timestamp
#   - resolved_by: "system"
#   - notes: "Alert condition no longer detected by Axis connector"
```

---

## Example Normalized Alerts

### Camera Offline

```python
NormalizedAlert(
    source_system="axis",
    source_alert_id="10.1.1.100_camera_offline_a1b2c3d4",
    severity="critical",
    category="availability",
    status="active",
    title="Camera Offline: Lobby Cam 1",
    description="Camera at 10.1.1.100 is not responding. Connection timeout after 10 seconds.",
    device_ip="10.1.1.100",
    device_name="Lobby Cam 1",
    alert_type="camera_offline",
    occurred_at="2026-01-07T19:00:00Z",
    raw_data={
        "camera_ip": "10.1.1.100",
        "camera_name": "Lobby Cam 1",
        "camera_model": "AXIS P3245-V",
        "firmware_version": "10.12.114",
        "vapix_endpoint": "/axis-cgi/basicdeviceinfo.cgi",
        "event_type": "camera_offline",
        "error": "Connection timeout",
        "timeout_seconds": 10
    }
)
```

### PTZ Power Insufficient

```python
NormalizedAlert(
    source_system="axis",
    source_alert_id="10.1.1.105_ptz_power_insufficient_e5f6g7h8",
    severity="major",
    category="hardware",
    status="active",
    title="PTZ Power Insufficient: Parking Cam 5",
    description="Camera reports insufficient power for PTZ operations. Check PoE switch power budget.",
    device_ip="10.1.1.105",
    device_name="Parking Cam 5",
    alert_type="ptz_power_insufficient",
    occurred_at="2026-01-07T19:05:00Z",
    raw_data={
        "camera_ip": "10.1.1.105",
        "camera_name": "Parking Cam 5",
        "camera_model": "AXIS Q6135-LE",
        "firmware_version": "10.11.65",
        "vapix_endpoint": "/axis-cgi/systemlog.cgi",
        "event_type": "ptz_power_insufficient",
        "log_entry": "Jan 7 19:05:00 axis-camera PTZ: not enough power for pan/tilt operation",
        "log_timestamp": "2026-01-07T19:05:00Z"
    }
)
```

### Storage Warning

```python
NormalizedAlert(
    source_system="axis",
    source_alert_id="10.1.1.110_storage_warning_i9j0k1l2",
    severity="warning",
    category="hardware",
    status="active",
    title="Storage Warning: Entrance Cam 10",
    description="SD card storage at 85% capacity. Recording may stop when full.",
    device_ip="10.1.1.110",
    device_name="Entrance Cam 10",
    alert_type="storage_warning",
    occurred_at="2026-01-07T19:10:00Z",
    raw_data={
        "camera_ip": "10.1.1.110",
        "camera_name": "Entrance Cam 10",
        "camera_model": "AXIS M3106-L Mk II",
        "firmware_version": "10.12.114",
        "vapix_endpoint": "/axis-cgi/disks/list.cgi",
        "event_type": "storage_warning",
        "disk_name": "SD_DISK",
        "disk_size_gb": 128,
        "disk_used_gb": 109,
        "disk_usage_percent": 85
    }
)
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-07 | OpsConductor | Initial mapping documentation |
