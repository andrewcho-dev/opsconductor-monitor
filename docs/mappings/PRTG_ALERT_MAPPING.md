# PRTG Alert Mapping

This document defines the complete mapping between PRTG Network Monitor alerts and OpsConductor's normalized alert structure.

**Connector Type:** `prtg`  
**Source System:** `prtg`  
**Last Updated:** 2026-01-07  
**Version:** 1.0

---

## Table of Contents

1. [Normalized Alert Structure](#normalized-alert-structure)
2. [Severity Definitions](#severity-definitions)
3. [Category Definitions](#category-definitions)
4. [Status Definitions](#status-definitions)
5. [PRTG Status ID Mapping](#prtg-status-id-mapping)
6. [Alert Mappings by PRTG Status](#alert-mappings-by-prtg-status)
7. [Sensor Type to Category Mapping](#sensor-type-to-category-mapping)
8. [Fingerprint Generation](#fingerprint-generation)
9. [Reconciliation Logic](#reconciliation-logic)
10. [Example Normalized Alerts](#example-normalized-alerts)

---

## Normalized Alert Structure

All PRTG alerts are normalized to the following structure:

```python
NormalizedAlert(
    source_system="prtg",
    source_alert_id="prtg_{sensor_id}",
    severity=<Severity>,           # critical, major, minor, warning, info
    category=<Category>,           # availability, hardware, application, network, etc.
    status="active",               # active, acknowledged, suppressed, resolved
    title="{Sensor Name} - {Status}",
    description="{PRTG message}",
    device_ip="{host}",
    device_name="{device_name}",
    alert_type="{sensor_type}_{status}",
    occurred_at=<timestamp>,
    raw_data={
        "sensor_id": "{sensorid}",
        "device_id": "{deviceid}",
        "device_name": "{device}",
        "sensor_name": "{sensor}",
        "host": "{host}",
        "status": "{status}",
        "status_id": "{statusid}",
        "message": "{message}",
        "priority": "{priority}",
        "group": "{group}",
        "probe": "{probe}",
        "tags": "{tags}",
        "last_value": "{lastvalue}",
        "duration": "{duration}"
    }
)
```

---

## Severity Definitions

| Severity | Code | PRTG Status IDs | Usage |
|----------|------|-----------------|-------|
| **Critical** | `critical` | 5 (Down) | Sensor is down, service unavailable |
| **Major** | `major` | 4 (Warning), 14 (Down Acknowledged) | Warning state or acknowledged down |
| **Minor** | `minor` | 10 (Unusual) | Unusual readings detected |
| **Warning** | `warning` | 4 (Warning) | Threshold exceeded but not critical |
| **Info** | `info` | 7 (Paused), 8 (Paused by Dependency) | Informational states |

---

## Category Definitions

| Category | Code | Sensor Types |
|----------|------|--------------|
| **Availability** | `availability` | Ping, HTTP, Port, Service |
| **Hardware** | `hardware` | SNMP Hardware, Disk, Memory, CPU |
| **Application** | `application` | Process, Windows Service, Database |
| **Network** | `network` | Bandwidth, Traffic, SNMP Traffic |
| **Environmental** | `environmental` | Temperature, Humidity sensors |
| **Security** | `security` | Firewall, Antivirus, Security sensors |
| **Performance** | `performance` | Response time, Load, Queue sensors |

---

## Status Definitions

| Status | Code | Description |
|--------|------|-------------|
| **Active** | `active` | Alert condition currently exists |
| **Acknowledged** | `acknowledged` | Operator has seen and acknowledged the alert |
| **Suppressed** | `suppressed` | Alert is temporarily suppressed (maintenance/paused) |
| **Resolved** | `resolved` | Alert condition no longer exists (Up status received) |

---

## PRTG Status ID Mapping

| PRTG Status ID | PRTG Status Text | Normalized Severity | Normalized Status | Notes |
|----------------|------------------|---------------------|-------------------|-------|
| 1 | Unknown | `warning` | `active` | Sensor state unknown |
| 2 | Scanning | `info` | `suppressed` | Sensor is scanning |
| 3 | Up | - | `resolved` | Resolves any active alert |
| 4 | Warning | `warning` | `active` | Threshold warning |
| 5 | Down | `critical` | `active` | Sensor/service down |
| 6 | No Probe | `major` | `active` | Probe not responding |
| 7 | Paused by User | `info` | `suppressed` | Manually paused |
| 8 | Paused by Dependency | `info` | `suppressed` | Paused due to parent |
| 9 | Paused by Schedule | `info` | `suppressed` | Scheduled pause |
| 10 | Unusual | `minor` | `active` | Unusual readings |
| 11 | Not Licensed | `warning` | `active` | License issue |
| 12 | Paused Until | `info` | `suppressed` | Paused until time |
| 13 | Down Acknowledged | `major` | `acknowledged` | Down but acknowledged |
| 14 | Down Partial | `major` | `active` | Partially down |

---

## Alert Mappings by PRTG Status

### Down Alerts (Status ID: 5)

| Alert Type Code | Alert Name | Severity | Category | Trigger Condition |
|-----------------|------------|----------|----------|-------------------|
| `ping_down` | **Device Unreachable** | `critical` | `availability` | Ping sensor status = Down |
| `http_down` | **HTTP Service Down** | `critical` | `availability` | HTTP sensor status = Down |
| `port_down` | **Port Unreachable** | `critical` | `availability` | Port sensor status = Down |
| `service_down` | **Service Down** | `critical` | `application` | Windows Service sensor = Down |
| `snmp_down` | **SNMP Unreachable** | `critical` | `availability` | SNMP sensor status = Down |
| `bandwidth_down` | **Interface Down** | `critical` | `network` | Bandwidth sensor = Down |
| `disk_down` | **Disk Failure** | `critical` | `hardware` | Disk sensor = Down |
| `database_down` | **Database Unreachable** | `critical` | `application` | Database sensor = Down |

### Warning Alerts (Status ID: 4)

| Alert Type Code | Alert Name | Severity | Category | Trigger Condition |
|-----------------|------------|----------|----------|-------------------|
| `ping_warning` | **High Latency** | `warning` | `availability` | Ping latency exceeds threshold |
| `cpu_warning` | **High CPU Usage** | `warning` | `hardware` | CPU usage exceeds threshold |
| `memory_warning` | **High Memory Usage** | `warning` | `hardware` | Memory usage exceeds threshold |
| `disk_warning` | **Low Disk Space** | `warning` | `hardware` | Disk space below threshold |
| `bandwidth_warning` | **High Bandwidth Usage** | `warning` | `network` | Bandwidth exceeds threshold |
| `temperature_warning` | **Temperature Warning** | `warning` | `environmental` | Temperature exceeds threshold |
| `response_warning` | **Slow Response** | `warning` | `performance` | Response time exceeds threshold |

### Unusual Alerts (Status ID: 10)

| Alert Type Code | Alert Name | Severity | Category | Trigger Condition |
|-----------------|------------|----------|----------|-------------------|
| `traffic_unusual` | **Unusual Traffic** | `minor` | `network` | Traffic pattern anomaly detected |
| `value_unusual` | **Unusual Value** | `minor` | `performance` | Sensor value outside normal range |

### Paused States (Status IDs: 7, 8, 9, 12)

| Alert Type Code | Alert Name | Severity | Category | Trigger Condition |
|-----------------|------------|----------|----------|-------------------|
| `sensor_paused` | **Sensor Paused** | `info` | `maintenance` | Sensor manually paused |
| `sensor_paused_dependency` | **Paused by Dependency** | `info` | `maintenance` | Parent device/sensor down |
| `sensor_paused_schedule` | **Paused by Schedule** | `info` | `maintenance` | Scheduled maintenance window |

### Resolution (Status ID: 3)

| Alert Type Code | Alert Name | Severity | Category | Trigger Condition |
|-----------------|------------|----------|----------|-------------------|
| - | - | (original) | (original) | Status changes to "Up" - resolves active alert |

---

## Sensor Type to Category Mapping

| PRTG Sensor Type | Category | Notes |
|------------------|----------|-------|
| Ping | `availability` | Basic reachability |
| HTTP, HTTPS | `availability` | Web service availability |
| Port | `availability` | TCP/UDP port availability |
| DNS | `availability` | DNS resolution |
| FTP | `availability` | FTP service |
| SNMP System Uptime | `availability` | Device uptime |
| SNMP Traffic | `network` | Interface traffic |
| Bandwidth | `network` | Network bandwidth |
| Packet Sniffer | `network` | Network analysis |
| NetFlow | `network` | Flow data |
| SNMP Disk Free | `hardware` | Disk space |
| SNMP Memory | `hardware` | Memory usage |
| SNMP CPU Load | `hardware` | CPU utilization |
| WMI Disk | `hardware` | Windows disk |
| WMI Memory | `hardware` | Windows memory |
| WMI CPU | `hardware` | Windows CPU |
| Windows Service | `application` | Service status |
| Process | `application` | Process monitoring |
| SQL Server | `application` | Database |
| MySQL | `application` | Database |
| Oracle | `application` | Database |
| Exchange | `application` | Mail server |
| IIS | `application` | Web server |
| VMware | `application` | Virtualization |
| Hyper-V | `application` | Virtualization |
| SNMP Custom | `performance` | Custom metrics |
| Sensor Factory | `performance` | Calculated metrics |

---

## Fingerprint Generation

Alert fingerprints are generated to enable deduplication and reconciliation:

```python
def generate_fingerprint(source_system: str, source_alert_id: str, device_identifier: str, alert_type: str) -> str:
    """
    Generate unique fingerprint for PRTG alert.
    
    Format: SHA256("prtg:{sensor_id}:{device_ip}:{sensor_type}")
    
    Note: Uses sensor_id as primary identifier since each sensor
    represents a unique monitoring point.
    """
    fingerprint_str = f"{source_system}:{source_alert_id}:{device_identifier}:{alert_type}"
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()
```

---

## Reconciliation Logic

When polling PRTG, the connector implements reconciliation to auto-resolve alerts:

1. **Poll PRTG API** for all sensors in alert state (Down, Warning, Unusual)
2. **Compare with active alerts** in database for source_system="prtg"
3. **Auto-resolve** any active alerts whose sensor is no longer in alert state
4. **Set resolved_at** timestamp and change status to "resolved"
5. **Publish WebSocket event** for real-time UI updates

```python
# Reconciliation runs after each poll cycle
# Alerts are resolved with:
#   - status: "resolved"
#   - resolved_at: current timestamp
#   - resolved_by: "system"
#   - notes: "Sensor returned to Up state in PRTG"
```

### Paused Sensor Handling

When a sensor is paused in PRTG:
- **Existing active alerts** are changed to status `suppressed`
- **No new alerts** are generated for paused sensors
- **When unpaused**, if sensor is in alert state, alert becomes `active` again

---

## Example Normalized Alerts

### Device Down (Ping)

```python
NormalizedAlert(
    source_system="prtg",
    source_alert_id="prtg_12345",
    severity="critical",
    category="availability",
    status="active",
    title="Ping - Down",
    description="Device is not responding to ping requests. 100% packet loss.",
    device_ip="10.1.1.50",
    device_name="Core-Switch-01",
    alert_type="ping_down",
    occurred_at="2026-01-07T19:00:00Z",
    raw_data={
        "sensor_id": "12345",
        "device_id": "1001",
        "device_name": "Core-Switch-01",
        "sensor_name": "Ping",
        "host": "10.1.1.50",
        "status": "Down",
        "status_id": "5",
        "message": "100% packet loss",
        "priority": "5",
        "group": "Network Infrastructure",
        "probe": "Local Probe",
        "tags": "core,switch,critical",
        "last_value": "100% packet loss",
        "duration": "0:05:30"
    }
)
```

### High CPU Warning

```python
NormalizedAlert(
    source_system="prtg",
    source_alert_id="prtg_23456",
    severity="warning",
    category="hardware",
    status="active",
    title="CPU Load - Warning",
    description="CPU usage is at 95%, exceeding the 90% warning threshold.",
    device_ip="10.1.2.100",
    device_name="Web-Server-01",
    alert_type="cpu_warning",
    occurred_at="2026-01-07T19:05:00Z",
    raw_data={
        "sensor_id": "23456",
        "device_id": "2001",
        "device_name": "Web-Server-01",
        "sensor_name": "CPU Load",
        "host": "10.1.2.100",
        "status": "Warning",
        "status_id": "4",
        "message": "CPU at 95% (Warning threshold: 90%)",
        "priority": "3",
        "group": "Web Servers",
        "probe": "Local Probe",
        "tags": "web,production",
        "last_value": "95 %",
        "duration": "0:02:15"
    }
)
```

### Low Disk Space Warning

```python
NormalizedAlert(
    source_system="prtg",
    source_alert_id="prtg_34567",
    severity="warning",
    category="hardware",
    status="active",
    title="Disk Free: C:\\ - Warning",
    description="Disk C:\\ has only 8% free space remaining.",
    device_ip="10.1.2.101",
    device_name="File-Server-01",
    alert_type="disk_warning",
    occurred_at="2026-01-07T19:10:00Z",
    raw_data={
        "sensor_id": "34567",
        "device_id": "2002",
        "device_name": "File-Server-01",
        "sensor_name": "Disk Free: C:\\",
        "host": "10.1.2.101",
        "status": "Warning",
        "status_id": "4",
        "message": "8% free (Warning threshold: 10%)",
        "priority": "4",
        "group": "File Servers",
        "probe": "Local Probe",
        "tags": "storage,production",
        "last_value": "8 % free",
        "duration": "0:15:00"
    }
)
```

### Sensor Paused

```python
NormalizedAlert(
    source_system="prtg",
    source_alert_id="prtg_45678",
    severity="info",
    category="maintenance",
    status="suppressed",
    title="HTTP - Paused",
    description="Sensor paused by user for maintenance.",
    device_ip="10.1.3.50",
    device_name="App-Server-01",
    alert_type="sensor_paused",
    occurred_at="2026-01-07T19:15:00Z",
    raw_data={
        "sensor_id": "45678",
        "device_id": "3001",
        "device_name": "App-Server-01",
        "sensor_name": "HTTP",
        "host": "10.1.3.50",
        "status": "Paused by User",
        "status_id": "7",
        "message": "Paused for scheduled maintenance",
        "priority": "3",
        "group": "Application Servers",
        "probe": "Local Probe",
        "tags": "app,maintenance",
        "last_value": "-",
        "duration": "-"
    }
)
```

---

## Priority Mapping

PRTG priority levels map to alert handling:

| PRTG Priority | Value | Handling |
|---------------|-------|----------|
| Highest | 5 | Immediate notification, critical alerts |
| High | 4 | High priority notification |
| Normal | 3 | Standard notification |
| Low | 2 | Low priority, batch notifications |
| Lowest | 1 | Informational only |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-07 | OpsConductor | Initial mapping documentation |
