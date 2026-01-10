# Ciena Data Collection Architecture

## Overview

This document outlines the data collection strategy for Ciena switches (3942, 5160, and other SAOS-based devices) in OpsConductor Monitor. The architecture prioritizes **SNMP as the primary data source**, with **SNMP traps for real-time alerts**, and **MCP for inventory/topology**.

## Background

### Why SNMP as Primary?

1. **Fast**: SNMP bulk walks complete in ~1-2 seconds vs 8+ seconds for SSH
2. **Standard**: Industry-standard protocol with well-defined MIBs
3. **Efficient**: Can poll multiple OIDs in single request
4. **Complete**: WWP-LEOS MIB provides optical power, thresholds, and alarms

### Previous Issue: Wrong Community String

SNMP was previously thought to be "unreliable" because we were using the wrong community string (`0psc0nduct0r`). The switches are configured with community `public`. Once corrected, SNMP works perfectly.

### Why Keep SNMP Traps?

1. **Real-time**: Traps are push-based, providing immediate notification
2. **Low overhead**: No polling required for alerts
3. **Universal**: Works with all infrastructure, not just Ciena

### Why Keep MCP?

1. **Inventory**: Best source for device discovery and equipment details
2. **Topology**: Network link discovery between devices
3. **Services**: Circuit/service provisioning information
4. **Already integrated**: NetBox sync already uses MCP

### SSH as Backup

SSH remains available as a backup method if SNMP fails, or for data not available via SNMP.

---

## Data Source Tiers

### Tier 1: SNMP Polling (Primary)

**Frequency**: Every 5 minutes (configurable)
**Method**: SNMP v2c bulk walks
**Community**: `public` (CRITICAL: not `0psc0nduct0r`)

#### MIB Reference

See **[CIENA_SNMP_MIB_REFERENCE.md](CIENA_SNMP_MIB_REFERENCE.md)** for complete OID documentation.

#### Key OIDs

| Data Type | MIB | OID | Notes |
|-----------|-----|-----|-------|
| **RX Power** | WWP-LEOS-PORT-XCVR | `6141.2.60.4.1.1.1.1.105.{port}` | dBm × 10000 |
| **TX Power** | WWP-LEOS-PORT-XCVR | `6141.2.60.4.1.1.1.1.106.{port}` | dBm × 10000 |
| **RX Bytes** | IF-MIB (ifXTable) | `1.3.6.1.2.1.31.1.1.1.6.{10000+port}` | 64-bit counter |
| **TX Bytes** | IF-MIB (ifXTable) | `1.3.6.1.2.1.31.1.1.1.10.{10000+port}` | 64-bit counter |
| **Port Speed** | IF-MIB (ifXTable) | `1.3.6.1.2.1.31.1.1.1.15.{10000+port}` | Mbps |
| **Hostname** | MIB-II | `1.3.6.1.2.1.1.5.0` | String |
| **Uptime** | MIB-II | `1.3.6.1.2.1.1.3.0` | Timeticks |

#### SNMP Polling Flow

```
1. Bulk walk optical power OIDs (all ports in one request)
2. Bulk walk interface counters (all ports in one request)
3. Get system info (single requests)
4. Parse responses into structured data
5. Store in database
```

#### Estimated Performance

- **Per switch**: ~1-2 seconds
- **10 switches parallel**: ~2 seconds total
- **50 switches (5 batches)**: ~10 seconds total

---

### Tier 2: SNMP Trap Receiver (Real-Time Alerts)

**Purpose**: Receive push notifications for critical events
**Port**: UDP 162 (standard SNMP trap port)
**Scope**: All infrastructure (not just Ciena)

#### Trap Types to Handle

| Vendor | Trap Type | OID Pattern | Action |
|--------|-----------|-------------|--------|
| **Ciena** | Alarm (threshold violation) | `1.3.6.1.4.1.1271.*` | Create/update alarm record |
| **Ciena** | Link Up/Down | `1.3.6.1.6.3.1.1.5.3/4` | Update port status |
| **Ciena** | G.8032 Switchover | `1.3.6.1.4.1.6141.2.60.47.*` | Update ring status, alert |
| **Ciena** | CFM Defect | `1.3.6.1.4.1.6141.2.60.6.*` | Update CFM state |
| **Generic** | Cold/Warm Start | `1.3.6.1.6.3.1.1.5.1/2` | Log device restart |
| **Generic** | Authentication Failure | `1.3.6.1.6.3.1.1.5.5` | Security alert |
| **Any** | Unknown | `*` | Log for analysis |

#### Trap Receiver Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SNMP Trap Receiver                        │
│                     (UDP Port 162)                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Listener   │───▶│   Decoder    │───▶│   Router     │   │
│  │  (asyncio)   │    │  (pysnmp)    │    │  (by OID)    │   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘   │
│                                                  │           │
│         ┌────────────────┬───────────────┬──────┴─────┐     │
│         ▼                ▼               ▼            ▼     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────┐  │
│  │   Ciena    │  │   Cisco    │  │   Linux    │  │Generic│  │
│  │  Handler   │  │  Handler   │  │  Handler   │  │Handler│  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └───┬───┘  │
│        │               │               │             │       │
│        └───────────────┴───────────────┴─────────────┘       │
│                              │                               │
│                              ▼                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Event Queue                          │ │
│  │  (Redis or in-memory for high throughput)               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                               │
│         ┌────────────────────┴────────────────────┐          │
│         ▼                                         ▼          │
│  ┌─────────────┐                          ┌─────────────┐    │
│  │  Database   │                          │   Alerting  │    │
│  │   Writer    │                          │   Engine    │    │
│  └─────────────┘                          └─────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Switch Configuration Required

Each switch needs to be configured to send traps to our receiver:

```
# Ciena SAOS example
snmp-server host add <our-server-ip> version v2c community <community> trap-port 162
```

---

### Tier 3: MCP (Fallback/Inventory)

**Purpose**: Device discovery, inventory sync, topology
**Frequency**: On-demand or daily sync

#### MCP Data Usage

| Data Type | MCP Endpoint | Usage |
|-----------|--------------|-------|
| Device Inventory | `/nsi/api/search/networkConstructs` | NetBox device sync |
| Equipment/SFPs | `/nsi/api/search/equipment` | NetBox module sync |
| Network Links | `/nsi/api/search/fres` | Topology discovery |
| Services | `/nsi/api/search/services` | Circuit tracking |

#### When to Use MCP

- Initial device discovery
- Daily inventory sync to NetBox
- Topology/link discovery
- Service/circuit information
- Historical PM data (if needed beyond current bin)

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       OpsConductor Monitor                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │  SSH Poller    │  │  SNMP Trap     │  │  MCP Client    │         │
│  │  Service       │  │  Receiver      │  │  Service       │         │
│  │                │  │                │  │                │         │
│  │  - Optical     │  │  - Alarms      │  │  - Inventory   │         │
│  │  - Port status │  │  - Link events │  │  - Equipment   │         │
│  │  - Traffic     │  │  - Ring events │  │  - Topology    │         │
│  │  - Alarms      │  │  - CFM events  │  │  - Services    │         │
│  │  - Chassis     │  │                │  │                │         │
│  │  - Rings       │  │                │  │                │         │
│  │                │  │                │  │                │         │
│  │  Every 5 min   │  │  Real-time     │  │  On-demand     │         │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘         │
│          │                   │                   │                   │
│          └───────────────────┴───────────────────┘                   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    PostgreSQL Database                       │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  Tables:                                                     │    │
│  │  - device_metrics (optical, traffic, chassis)                │    │
│  │  - active_alarms (from SSH + traps)                          │    │
│  │  - alarm_history (historical record)                         │    │
│  │  - port_status (link state, speed)                           │    │
│  │  - ring_status (G.8032 state)                                │    │
│  │  - trap_log (raw trap archive)                               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│          ┌───────────────────┼───────────────────┐                   │
│          ▼                   ▼                   ▼                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐            │
│  │  NetBox     │     │  Alerting   │     │  Dashboard  │            │
│  │  Sync       │     │  Engine     │     │  API        │            │
│  └─────────────┘     └─────────────┘     └─────────────┘            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### device_metrics

```sql
CREATE TABLE device_metrics (
    id SERIAL PRIMARY KEY,
    device_ip VARCHAR(45) NOT NULL,
    device_name VARCHAR(255),
    port_id INTEGER NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- 'optical', 'traffic', 'chassis'
    
    -- Optical metrics
    tx_power_dbm DECIMAL(8,4),
    rx_power_dbm DECIMAL(8,4),
    temperature_c DECIMAL(6,2),
    voltage_v DECIMAL(6,3),
    bias_ma DECIMAL(8,3),
    tx_power_alarm BOOLEAN DEFAULT FALSE,
    rx_power_alarm BOOLEAN DEFAULT FALSE,
    
    -- Traffic metrics
    tx_bytes_per_sec BIGINT,
    rx_bytes_per_sec BIGINT,
    tx_frames_per_sec BIGINT,
    rx_frames_per_sec BIGINT,
    
    -- Timestamps
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_device_port (device_ip, port_id),
    INDEX idx_collected_at (collected_at)
);
```

### active_alarms

```sql
CREATE TABLE active_alarms (
    id SERIAL PRIMARY KEY,
    device_ip VARCHAR(45) NOT NULL,
    device_name VARCHAR(255),
    alarm_id VARCHAR(100),  -- Unique ID from device
    severity VARCHAR(20) NOT NULL,  -- critical, major, minor, warning
    source VARCHAR(50) NOT NULL,  -- 'ssh', 'trap', 'mcp'
    object_type VARCHAR(50),  -- port, chassis, ring, etc.
    object_instance VARCHAR(100),  -- port 21, PSU 1, etc.
    description TEXT,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    cleared BOOLEAN DEFAULT FALSE,
    cleared_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE (device_ip, alarm_id),
    INDEX idx_severity (severity),
    INDEX idx_cleared (cleared)
);
```

### trap_log

```sql
CREATE TABLE trap_log (
    id SERIAL PRIMARY KEY,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_ip VARCHAR(45) NOT NULL,
    trap_oid VARCHAR(255) NOT NULL,
    trap_type VARCHAR(100),
    community VARCHAR(100),
    varbinds JSONB,  -- All trap variables as JSON
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_source_ip (source_ip),
    INDEX idx_received_at (received_at),
    INDEX idx_trap_oid (trap_oid)
);
```

---

## Implementation Plan

### Phase 1: SSH Polling Service

1. Create `CienaSSHService` class with paramiko
2. Implement command execution with interactive shell
3. Create parsers for each command output format
4. Add parallel polling with ThreadPoolExecutor
5. Integrate with existing poller infrastructure
6. Add database storage for metrics

### Phase 2: SNMP Trap Receiver

1. Create `SNMPTrapReceiver` class with pysnmp
2. Implement asyncio-based UDP listener
3. Create trap decoder and OID router
4. Implement vendor-specific handlers (Ciena, Cisco, generic)
5. Add event queue for high-throughput handling
6. Integrate with alerting engine
7. Add trap logging to database

### Phase 3: Integration & Migration

1. Update polling tasks to use SSH instead of SNMP
2. Configure switches to send traps to our receiver
3. Deprecate SNMP polling for Ciena devices
4. Update frontend to display new data sources
5. Add monitoring for SSH/trap receiver health

---

## Configuration

### Environment Variables

```bash
# SSH Polling
CIENA_SSH_USERNAME=su
CIENA_SSH_PASSWORD=wwp
CIENA_SSH_TIMEOUT=10
CIENA_SSH_MAX_CONCURRENT=10
CIENA_SSH_POLL_INTERVAL=300  # 5 minutes

# SNMP Trap Receiver
SNMP_TRAP_PORT=162
SNMP_TRAP_COMMUNITY=public
SNMP_TRAP_QUEUE_SIZE=10000

# MCP (existing)
MCP_URL=https://10.127.0.15
MCP_USERNAME=admin
MCP_PASSWORD=...
```

### Switch Configuration

Each Ciena switch needs SNMP trap destination configured:

```
# Add trap receiver (run on each switch)
snmp-server host add <opsconductor-ip> version v2c community 0psc0nduct0r trap-port 162
```

---

## Monitoring & Observability

### Health Checks

- SSH poller: Track success/failure rate per device
- Trap receiver: Monitor queue depth, processing latency
- MCP client: Track API response times

### Metrics to Expose

- `ssh_poll_duration_seconds` - Time to poll each device
- `ssh_poll_success_total` - Successful polls counter
- `ssh_poll_failure_total` - Failed polls counter
- `trap_received_total` - Traps received counter
- `trap_processed_total` - Traps processed counter
- `trap_queue_depth` - Current queue size

### Alerts

- SSH poll failure rate > 10%
- Trap receiver queue depth > 1000
- No traps received in 1 hour (if devices configured)

---

## Security Considerations

1. **SSH Credentials**: Store encrypted, use secrets management
2. **SNMP Community**: Use non-default community strings
3. **Trap Receiver**: Validate source IPs against known devices
4. **Network Segmentation**: Trap receiver should be in management VLAN

---

## Appendix: Ciena SSH Command Output Formats

### port xcvr show port X diagnostics

```
+--------------------- XCVR DIAGNOSTICS - Port 21       -----------------+
|               |          |         Alarm        |        Warning       |
| Output        | Value    | Threshold     | Flag | Threshold     | Flag |
+---------------+----------+---------------+------+---------------+------+
| Temp    (degC)|  46.315  | HIGH 100.000  | 0    | HIGH  95.000  | 0    |
|               |          | LOW  -10.000  | 0    | LOW   -5.000  | 0    |
+---------------+----------+---------------+------+---------------+------+
| Tx Power (dBm)|  +1.9318 | HIGH  +5.0000 | 0    | HIGH  +4.0000 | 0    |
|               |          | LOW   -1.9997 | 0    | LOW   -1.0002 | 0    |
+---------------+----------+---------------+------+---------------+------+
| Rx Power (dBm)|  -5.4516 | HIGH  -5.9998 | 1    | HIGH  -7.0006 | 1    |
|               |          | LOW  -23.9794 | 0    | LOW  -23.0103 | 0    |
+---------------+----------+---------------+------+---------------+------+
```

### pm show pm-instance X bin-number 1

```
| Instance Name                   | 21                                         |
|   TX Bytes per Second           |                                  2,185,588 |
|   TX Frames per Second          |                                      2,394 |
|   RX Bytes per Second           |                                  1,637,196 |
|   RX Frames per Second          |                                      2,397 |
```

### alarm show

```
+------ ACTIVE ALARM TABLE ------+
| Idx | Sev  | SA | Cond | Obj   | Time                | Desc                    |
+-----+------+----+------+-------+---------------------+-------------------------+
| 1   | MN   | N  | SET  | 21    | 2025-10-13 23:05:11 | xcvrRxPower: High       |
```

---

*Document Version: 1.0*
*Created: 2026-01-03*
*Author: OpsConductor Team*
