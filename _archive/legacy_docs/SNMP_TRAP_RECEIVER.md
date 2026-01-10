# Universal SNMP Trap Receiver

## Overview

This document describes the architecture and implementation of a universal SNMP trap receiver for OpsConductor Monitor. The receiver is designed to handle traps from **all infrastructure** (not just Ciena switches), providing real-time event notification for the entire network.

## Design Goals

1. **Universal**: Handle traps from any vendor (Ciena, Cisco, Juniper, Linux, etc.)
2. **Robust**: Never crash, gracefully handle malformed traps
3. **Reliable**: No trap loss under high load, persistent logging
4. **Efficient**: Async processing, minimal latency
5. **Extensible**: Easy to add new vendor handlers
6. **Observable**: Metrics, health checks, logging

---

## Architecture

### High-Level Design

```
                                    ┌─────────────────────────────────────┐
                                    │         Network Devices             │
                                    │  (Switches, Routers, Servers, etc.) │
                                    └──────────────┬──────────────────────┘
                                                   │
                                          UDP Port 162
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SNMP Trap Receiver                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         UDP Listener (asyncio)                          │ │
│  │  - Binds to 0.0.0.0:162                                                 │ │
│  │  - Non-blocking receive                                                 │ │
│  │  - Source IP validation (optional)                                      │ │
│  └────────────────────────────────────┬────────────────────────────────────┘ │
│                                       │                                      │
│                                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Trap Decoder (pysnmp)                           │ │
│  │  - SNMPv1, SNMPv2c, SNMPv3 support                                      │ │
│  │  - OID resolution                                                       │ │
│  │  - Varbind extraction                                                   │ │
│  └────────────────────────────────────┬────────────────────────────────────┘ │
│                                       │                                      │
│                                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Event Queue (asyncio.Queue)                     │ │
│  │  - Decouples receiving from processing                                  │ │
│  │  - Configurable max size (default 10,000)                               │ │
│  │  - Overflow protection with logging                                     │ │
│  └────────────────────────────────────┬────────────────────────────────────┘ │
│                                       │                                      │
│                                       ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Trap Router                                     │ │
│  │  - Routes traps to appropriate handler based on:                        │ │
│  │    - Enterprise OID (vendor identification)                             │ │
│  │    - Trap OID (event type)                                              │ │
│  │    - Source IP (device lookup)                                          │ │
│  └────────────────────────────────────┬────────────────────────────────────┘ │
│                                       │                                      │
│         ┌─────────────┬───────────────┼───────────────┬─────────────┐        │
│         ▼             ▼               ▼               ▼             ▼        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐      │
│  │  Ciena    │ │  Cisco    │ │  Juniper  │ │  Linux    │ │  Generic  │      │
│  │  Handler  │ │  Handler  │ │  Handler  │ │  Handler  │ │  Handler  │      │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘      │
│        │             │             │             │             │             │
│        └─────────────┴─────────────┴─────────────┴─────────────┘             │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Event Processor                                 │ │
│  │  - Database writer (trap_log, active_alarms)                            │ │
│  │  - Alert trigger (email, webhook, etc.)                                 │ │
│  │  - Metric updater                                                       │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. UDP Listener

**Purpose**: Receive raw SNMP trap packets from the network

**Implementation**:
```python
class TrapListener:
    """Async UDP listener for SNMP traps."""
    
    def __init__(self, host='0.0.0.0', port=162):
        self.host = host
        self.port = port
        self.transport = None
        self.protocol = None
    
    async def start(self):
        """Start listening for traps."""
        loop = asyncio.get_event_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: TrapProtocol(self.on_trap_received),
            local_addr=(self.host, self.port)
        )
    
    async def on_trap_received(self, data: bytes, addr: tuple):
        """Called when a trap packet is received."""
        # Queue for processing
        await self.queue.put((data, addr, time.time()))
```

**Considerations**:
- Port 162 requires root/sudo or CAP_NET_BIND_SERVICE capability
- Use `setcap cap_net_bind_service=+ep /path/to/python` or run as root
- Alternative: Use port 1162 and configure devices accordingly

### 2. Trap Decoder

**Purpose**: Parse SNMP trap packets into structured data

**Supported Formats**:
- SNMPv1 Trap PDU
- SNMPv2c Trap PDU (NOTIFICATION)
- SNMPv3 (with USM authentication)

**Output Structure**:
```python
@dataclass
class DecodedTrap:
    received_at: datetime
    source_ip: str
    source_port: int
    snmp_version: str  # 'v1', 'v2c', 'v3'
    community: str  # For v1/v2c
    enterprise_oid: str  # Vendor identifier
    trap_oid: str  # Specific trap type
    generic_trap: int  # For v1: 0-6
    specific_trap: int  # For v1: vendor-specific
    uptime: int  # sysUpTime
    varbinds: Dict[str, Any]  # OID -> value mapping
    raw_data: bytes  # Original packet for debugging
```

### 3. Event Queue

**Purpose**: Decouple trap receiving from processing to prevent packet loss

**Design**:
- Async queue (asyncio.Queue)
- Configurable max size (default 10,000 traps)
- Overflow handling: log warning, drop oldest if full
- Multiple consumers for parallel processing

**Monitoring**:
- Queue depth metric
- Overflow counter
- Processing latency histogram

### 4. Trap Router

**Purpose**: Route traps to appropriate vendor handler

**Routing Logic**:
```python
class TrapRouter:
    """Routes traps to appropriate handlers based on OID."""
    
    # Enterprise OID prefixes for vendor identification
    VENDOR_OIDS = {
        '1.3.6.1.4.1.6141': 'ciena_wwp',    # Ciena WWP (SAOS)
        '1.3.6.1.4.1.1271': 'ciena_ces',    # Ciena CES
        '1.3.6.1.4.1.9': 'cisco',           # Cisco
        '1.3.6.1.4.1.2636': 'juniper',      # Juniper
        '1.3.6.1.4.1.8072': 'net_snmp',     # Net-SNMP (Linux)
        '1.3.6.1.4.1.2021': 'ucd_snmp',     # UCD-SNMP (Linux)
    }
    
    # Standard trap OIDs (RFC 1157, RFC 3418)
    STANDARD_TRAPS = {
        '1.3.6.1.6.3.1.1.5.1': 'coldStart',
        '1.3.6.1.6.3.1.1.5.2': 'warmStart',
        '1.3.6.1.6.3.1.1.5.3': 'linkDown',
        '1.3.6.1.6.3.1.1.5.4': 'linkUp',
        '1.3.6.1.6.3.1.1.5.5': 'authenticationFailure',
    }
    
    def route(self, trap: DecodedTrap) -> str:
        """Determine which handler should process this trap."""
        # Check enterprise OID for vendor
        for prefix, vendor in self.VENDOR_OIDS.items():
            if trap.enterprise_oid.startswith(prefix):
                return vendor
        
        # Check trap OID for standard traps
        if trap.trap_oid in self.STANDARD_TRAPS:
            return 'standard'
        
        return 'generic'
```

### 5. Vendor Handlers

Each vendor handler is responsible for:
1. Parsing vendor-specific varbinds
2. Extracting meaningful event data
3. Creating normalized event records

#### Ciena Handler

```python
class CienaTrapHandler:
    """Handler for Ciena SAOS traps."""
    
    # Ciena-specific trap OIDs
    TRAP_TYPES = {
        # WWP-LEOS-ALARM-MIB
        '1.3.6.1.4.1.6141.2.60.5.0.1': 'alarmRaised',
        '1.3.6.1.4.1.6141.2.60.5.0.2': 'alarmCleared',
        # WWP-LEOS-RAPS-MIB
        '1.3.6.1.4.1.6141.2.60.47.0.1': 'rapsStateChange',
        '1.3.6.1.4.1.6141.2.60.47.0.2': 'rapsSwitchover',
        # WWP-LEOS-PORT-MIB
        '1.3.6.1.4.1.6141.2.60.2.0.1': 'portLinkUp',
        '1.3.6.1.4.1.6141.2.60.2.0.2': 'portLinkDown',
        # WWP-LEOS-CFM-MIB
        '1.3.6.1.4.1.6141.2.60.6.0.1': 'cfmDefect',
    }
    
    def handle(self, trap: DecodedTrap) -> Event:
        """Process Ciena trap and return normalized event."""
        trap_type = self.TRAP_TYPES.get(trap.trap_oid, 'unknown')
        
        if trap_type == 'alarmRaised':
            return self._handle_alarm_raised(trap)
        elif trap_type == 'alarmCleared':
            return self._handle_alarm_cleared(trap)
        elif trap_type in ('portLinkUp', 'portLinkDown'):
            return self._handle_link_event(trap, trap_type)
        elif trap_type.startswith('raps'):
            return self._handle_raps_event(trap, trap_type)
        else:
            return self._handle_generic(trap)
```

#### Generic Handler

```python
class GenericTrapHandler:
    """Handler for unknown/generic traps."""
    
    def handle(self, trap: DecodedTrap) -> Event:
        """Log and store unknown trap for analysis."""
        return Event(
            event_type='unknown_trap',
            source_ip=trap.source_ip,
            severity='info',
            description=f"Unknown trap: {trap.trap_oid}",
            raw_data=trap.varbinds
        )
```

### 6. Event Processor

**Purpose**: Take action on processed events

**Actions**:
1. **Database Storage**: Write to trap_log and active_alarms tables
2. **Alert Triggering**: Send notifications for critical events
3. **Metric Updates**: Update Prometheus/StatsD metrics
4. **State Updates**: Update in-memory device state

---

## Database Schema

### trap_log

Stores all received traps for audit and analysis:

```sql
CREATE TABLE trap_log (
    id BIGSERIAL PRIMARY KEY,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    source_ip INET NOT NULL,
    source_port INTEGER,
    snmp_version VARCHAR(10),
    community VARCHAR(100),
    enterprise_oid VARCHAR(255),
    trap_oid VARCHAR(255) NOT NULL,
    trap_type VARCHAR(100),  -- Resolved trap name
    vendor VARCHAR(50),  -- Identified vendor
    uptime BIGINT,
    varbinds JSONB,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    handler VARCHAR(50),  -- Which handler processed it
    event_id BIGINT,  -- Reference to created event
    
    -- Indexes for common queries
    INDEX idx_trap_log_source (source_ip),
    INDEX idx_trap_log_received (received_at),
    INDEX idx_trap_log_oid (trap_oid),
    INDEX idx_trap_log_vendor (vendor),
    INDEX idx_trap_log_unprocessed (processed) WHERE processed = FALSE
);

-- Partition by month for efficient cleanup
-- CREATE TABLE trap_log_2026_01 PARTITION OF trap_log
--     FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### trap_events

Normalized events extracted from traps:

```sql
CREATE TABLE trap_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    source_ip INET NOT NULL,
    device_name VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,  -- alarm, link, ring, cfm, etc.
    severity VARCHAR(20) NOT NULL,  -- critical, major, minor, warning, info
    object_type VARCHAR(50),  -- port, chassis, ring, etc.
    object_id VARCHAR(100),  -- port 21, ring VR100, etc.
    description TEXT,
    details JSONB,  -- Event-specific details
    trap_log_id BIGINT REFERENCES trap_log(id),
    
    -- For alarm correlation
    alarm_id VARCHAR(100),  -- Unique alarm identifier
    is_clear BOOLEAN DEFAULT FALSE,  -- True if this clears an alarm
    cleared_event_id BIGINT,  -- Reference to clearing event
    
    INDEX idx_events_source (source_ip),
    INDEX idx_events_type (event_type),
    INDEX idx_events_severity (severity),
    INDEX idx_events_created (created_at)
);
```

---

## Configuration

### Environment Variables

```bash
# Trap Receiver
SNMP_TRAP_ENABLED=true
SNMP_TRAP_HOST=0.0.0.0
SNMP_TRAP_PORT=162
SNMP_TRAP_QUEUE_SIZE=10000
SNMP_TRAP_WORKERS=4

# Community validation (optional)
SNMP_TRAP_COMMUNITIES=public,0psc0nduct0r
SNMP_TRAP_VALIDATE_COMMUNITY=true

# Source IP validation (optional)
SNMP_TRAP_ALLOWED_SOURCES=10.127.0.0/24,192.168.10.0/24
SNMP_TRAP_VALIDATE_SOURCE=false

# SNMPv3 (optional)
SNMP_TRAP_V3_ENABLED=false
SNMP_TRAP_V3_USER=trapuser
SNMP_TRAP_V3_AUTH_KEY=authpassword
SNMP_TRAP_V3_PRIV_KEY=privpassword

# Database
TRAP_DB_RETENTION_DAYS=90
TRAP_DB_BATCH_SIZE=100
```

### Device Configuration

#### Ciena SAOS

```
# Add trap receiver
snmp-server host add 192.168.10.50 version v2c community 0psc0nduct0r trap-port 162

# Enable specific traps
snmp-server enable traps alarm
snmp-server enable traps port
snmp-server enable traps raps
snmp-server enable traps cfm
```

#### Cisco IOS

```
snmp-server host 192.168.10.50 version 2c 0psc0nduct0r
snmp-server enable traps snmp linkdown linkup
snmp-server enable traps config
snmp-server enable traps entity
```

#### Linux (Net-SNMP)

```bash
# /etc/snmp/snmptrapd.conf
authCommunity log,execute,net 0psc0nduct0r
traphandle default /usr/bin/snmptrap -v 2c -c 0psc0nduct0r 192.168.10.50
```

---

## Deployment

### Running as a Service

```ini
# /etc/systemd/system/snmp-trap-receiver.service
[Unit]
Description=OpsConductor SNMP Trap Receiver
After=network.target postgresql.service

[Service]
Type=simple
User=opsconductor
Group=opsconductor
WorkingDirectory=/opt/opsconductor
ExecStart=/opt/opsconductor/venv/bin/python -m backend.services.snmp_trap_receiver
Restart=always
RestartSec=5

# Allow binding to port 162
AmbientCapabilities=CAP_NET_BIND_SERVICE

# Environment
EnvironmentFile=/opt/opsconductor/.env

[Install]
WantedBy=multi-user.target
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/

# Run as non-root but with NET_BIND_SERVICE capability
USER 1000
EXPOSE 162/udp

CMD ["python", "-m", "backend.services.snmp_trap_receiver"]
```

```yaml
# docker-compose.yml
services:
  trap-receiver:
    build: .
    ports:
      - "162:162/udp"
    cap_add:
      - NET_BIND_SERVICE
    environment:
      - SNMP_TRAP_PORT=162
      - DATABASE_URL=postgresql://...
    restart: always
```

---

## Monitoring

### Health Check Endpoint

```python
@app.route('/health/trap-receiver')
def trap_receiver_health():
    return {
        'status': 'healthy' if receiver.is_running else 'unhealthy',
        'uptime_seconds': receiver.uptime,
        'traps_received': receiver.traps_received,
        'traps_processed': receiver.traps_processed,
        'queue_depth': receiver.queue.qsize(),
        'last_trap_at': receiver.last_trap_at.isoformat() if receiver.last_trap_at else None,
    }
```

### Prometheus Metrics

```python
# Counters
snmp_traps_received_total = Counter(
    'snmp_traps_received_total',
    'Total SNMP traps received',
    ['source_ip', 'vendor']
)

snmp_traps_processed_total = Counter(
    'snmp_traps_processed_total',
    'Total SNMP traps processed',
    ['handler', 'event_type']
)

snmp_traps_errors_total = Counter(
    'snmp_traps_errors_total',
    'Total SNMP trap processing errors',
    ['error_type']
)

# Gauges
snmp_trap_queue_depth = Gauge(
    'snmp_trap_queue_depth',
    'Current trap queue depth'
)

# Histograms
snmp_trap_processing_seconds = Histogram(
    'snmp_trap_processing_seconds',
    'Trap processing duration',
    ['handler']
)
```

### Alerts

```yaml
# Prometheus alerting rules
groups:
  - name: snmp_trap_receiver
    rules:
      - alert: TrapReceiverDown
        expr: up{job="trap-receiver"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "SNMP trap receiver is down"
          
      - alert: TrapQueueBacklog
        expr: snmp_trap_queue_depth > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SNMP trap queue has backlog"
          
      - alert: NoTrapsReceived
        expr: increase(snmp_traps_received_total[1h]) == 0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "No SNMP traps received in 1 hour"
```

---

## Testing

### Manual Trap Generation

```bash
# Send test trap using snmptrap
snmptrap -v 2c -c public localhost '' \
    1.3.6.1.6.3.1.1.5.3 \
    1.3.6.1.2.1.2.2.1.1.1 i 1 \
    1.3.6.1.2.1.2.2.1.7.1 i 2 \
    1.3.6.1.2.1.2.2.1.8.1 i 2

# Send Ciena-style alarm trap
snmptrap -v 2c -c 0psc0nduct0r localhost '' \
    1.3.6.1.4.1.6141.2.60.5.0.1 \
    1.3.6.1.4.1.6141.2.60.5.1.1.1 s "Port 21" \
    1.3.6.1.4.1.6141.2.60.5.1.1.2 i 4 \
    1.3.6.1.4.1.6141.2.60.5.1.1.3 s "xcvrRxPower: High"
```

### Unit Tests

```python
class TestTrapDecoder:
    def test_decode_v2c_trap(self):
        raw_packet = b'...'  # Captured trap packet
        trap = decoder.decode(raw_packet, ('10.127.0.222', 161))
        assert trap.snmp_version == 'v2c'
        assert trap.trap_oid == '1.3.6.1.6.3.1.1.5.3'

class TestTrapRouter:
    def test_route_ciena_trap(self):
        trap = DecodedTrap(enterprise_oid='1.3.6.1.4.1.6141.2.60.5', ...)
        handler = router.route(trap)
        assert handler == 'ciena_wwp'

class TestCienaHandler:
    def test_handle_alarm_raised(self):
        trap = DecodedTrap(trap_oid='1.3.6.1.4.1.6141.2.60.5.0.1', ...)
        event = handler.handle(trap)
        assert event.event_type == 'alarm'
        assert event.severity == 'major'
```

---

## Security Considerations

1. **Community String Validation**: Reject traps with unknown community strings
2. **Source IP Filtering**: Only accept traps from known device IPs
3. **Rate Limiting**: Prevent DoS from trap floods
4. **SNMPv3**: Use authenticated/encrypted traps where possible
5. **Network Segmentation**: Trap receiver should be in management VLAN
6. **Input Validation**: Sanitize all trap data before database storage

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No traps received | Firewall blocking UDP 162 | Open firewall, check iptables |
| Permission denied on port 162 | Need root or CAP_NET_BIND_SERVICE | Use setcap or run as root |
| Traps not decoded | Wrong SNMP version | Check device config matches |
| Queue overflow | Processing too slow | Increase workers, optimize handlers |
| Unknown vendor | Missing OID mapping | Add to VENDOR_OIDS |

### Debug Mode

```bash
# Run with debug logging
SNMP_TRAP_DEBUG=true python -m backend.services.snmp_trap_receiver

# Capture raw packets
tcpdump -i any -n udp port 162 -w traps.pcap
```

---

*Document Version: 1.0*
*Created: 2026-01-03*
*Author: OpsConductor Team*
