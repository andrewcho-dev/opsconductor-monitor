# Ciena SNMP MIB Reference for 3942/5160 Switches

## Overview

This document provides the definitive SNMP MIB reference for Ciena 3942 and 5160 switches running SAOS software. These switches use the **WWP-LEOS MIB family** (Enterprise OID 6141), NOT the CIENA-CES MIB (1271) which does not exist on these platforms.

## Critical Configuration

### SNMP Community String

**The switches are configured with community string `public`, NOT `0psc0nduct0r`.**

```bash
# Correct
snmpget -v2c -c public <switch_ip> <oid>

# WRONG - will timeout
snmpget -v2c -c 0psc0nduct0r <switch_ip> <oid>
```

### MIB Enterprise OIDs

| Enterprise | OID | Status on 3942/5160 |
|------------|-----|---------------------|
| WWP (World Wide Packets) | 1.3.6.1.4.1.**6141** | ✅ **WORKS** |
| CIENA-CES | 1.3.6.1.4.1.**1271** | ❌ Does NOT exist |

---

## WWP-LEOS MIB Structure

Base OID: `1.3.6.1.4.1.6141.2.60`

| Subtree | MIB Name | OIDs | Description |
|---------|----------|------|-------------|
| .1 | WWP-LEOS-SYSTEM-CONFIG-MIB | 18 | System configuration |
| .2 | WWP-LEOS-PORT-MIB | 1780 | Port configuration |
| .3 | WWP-LEOS-VLAN-MIB | 5953 | VLAN configuration |
| **.4** | **WWP-LEOS-PORT-XCVR-MIB** | 2184 | **Transceiver DOM (optical power)** |
| .5 | WWP-LEOS-ALARM-MIB | 188 | Alarms |
| .6 | WWP-LEOS-CFM-MIB | 5363 | Connectivity Fault Management |
| .8 | WWP-LEOS-CHASSIS-MIB | 7 | Chassis health |
| .11 | WWP-LEOS-RSTP-MIB | 266 | Spanning Tree |
| **.47** | **WWP-LEOS-RAPS-MIB** | 4 | **G.8032 Ring Protection** |

---

## 1. Optical Power (DOM) - WWP-LEOS-PORT-XCVR-MIB

**Base OID:** `1.3.6.1.4.1.6141.2.60.4.1.1.1.1`

### Key OIDs for Optical Diagnostics

| Column | OID Suffix | Name | Unit | Conversion |
|--------|------------|------|------|------------|
| 105 | .105.{port} | **RX Power** | dBm × 10000 | Divide by 10000 |
| 106 | .106.{port} | **TX Power** | dBm × 10000 | Divide by 10000 |
| 107 | .107.{port} | TX High Alarm Threshold | dBm × 10000 | Divide by 10000 |
| 108 | .108.{port} | TX Low Alarm Threshold | dBm × 10000 | Divide by 10000 |
| 109 | .109.{port} | RX High Alarm Threshold | dBm × 10000 | Divide by 10000 |
| 110 | .110.{port} | RX Low Alarm Threshold | dBm × 10000 | Divide by 10000 |
| 104 | .104.{port} | Temperature | Raw (needs decode) | TBD |

### Transceiver Identification

| Column | OID Suffix | Name | Type |
|--------|------------|------|------|
| 1 | .1.{port} | Port Index | INTEGER |
| 2 | .2.{port} | Oper State | INTEGER (1=disabled, 2=enabled) |
| 3 | .3.{port} | ID Type | INTEGER (4=SFP+) |
| 7 | .7.{port} | Vendor Name | STRING |
| 9 | .9.{port} | Part Number | STRING |
| 11 | .11.{port} | Serial Number | STRING |
| 13 | .13.{port} | Date Code | STRING |
| 15 | .15.{port} | Wavelength (nm) | INTEGER |
| 111 | .111.{port} | Model | STRING |

### Threshold Settings (mW)

| Column | OID Suffix | Name | Unit |
|--------|------------|------|------|
| 40 | .40.{port} | TX High Alarm (µW) | micro-watts |
| 41 | .41.{port} | TX Low Alarm (µW) | micro-watts |
| 42 | .42.{port} | RX High Alarm (µW) | micro-watts |
| 43 | .43.{port} | RX Low Alarm (µW) | micro-watts |

### Example: Get Optical Power for Port 21

```bash
# RX Power (dBm)
snmpget -v2c -c public 10.127.0.222 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.105.21
# Returns: INTEGER: -57839  → -5.7839 dBm

# TX Power (dBm)
snmpget -v2c -c public 10.127.0.222 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.106.21
# Returns: INTEGER: 19312  → 1.9312 dBm

# Bulk walk all optical data
snmpbulkwalk -v2c -c public 10.127.0.222 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.105
snmpbulkwalk -v2c -c public 10.127.0.222 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.106
```

### Python Conversion

```python
def snmp_to_dbm(snmp_value: int) -> float:
    """Convert SNMP optical power value to dBm."""
    return snmp_value / 10000.0

# Example
rx_power_snmp = -57839
rx_power_dbm = snmp_to_dbm(rx_power_snmp)  # -5.7839 dBm
```

---

## 2. Interface Statistics - Standard IF-MIB

**Base OID:** `1.3.6.1.2.1.2.2.1` (ifTable) and `1.3.6.1.2.1.31.1.1.1` (ifXTable)

### Interface Index Mapping

**Physical ports 1-24 are indexed as 10001-10024**

| Physical Port | ifIndex |
|---------------|---------|
| Port 1 | 10001 |
| Port 2 | 10002 |
| ... | ... |
| Port 21 | 10021 |
| Port 22 | 10022 |
| Port 24 | 10024 |

### Key OIDs (ifXTable - 64-bit counters)

| Column | OID | Name | Type |
|--------|-----|------|------|
| 1 | .1.3.6.1.2.1.31.1.1.1.1.{ifIndex} | ifName | STRING |
| 6 | .1.3.6.1.2.1.31.1.1.1.6.{ifIndex} | **ifHCInOctets** | Counter64 (RX bytes) |
| 10 | .1.3.6.1.2.1.31.1.1.1.10.{ifIndex} | **ifHCOutOctets** | Counter64 (TX bytes) |
| 7 | .1.3.6.1.2.1.31.1.1.1.7.{ifIndex} | ifHCInUcastPkts | Counter64 |
| 11 | .1.3.6.1.2.1.31.1.1.1.11.{ifIndex} | ifHCOutUcastPkts | Counter64 |
| 15 | .1.3.6.1.2.1.31.1.1.1.15.{ifIndex} | ifHighSpeed | Gauge32 (Mbps) |

### Key OIDs (ifTable - 32-bit counters)

| Column | OID | Name | Type |
|--------|-----|------|------|
| 2 | .1.3.6.1.2.1.2.2.1.2.{ifIndex} | ifDescr | STRING |
| 5 | .1.3.6.1.2.1.2.2.1.5.{ifIndex} | ifSpeed | Gauge32 (bps) |
| 7 | .1.3.6.1.2.1.2.2.1.7.{ifIndex} | ifAdminStatus | INTEGER |
| 8 | .1.3.6.1.2.1.2.2.1.8.{ifIndex} | ifOperStatus | INTEGER |
| 10 | .1.3.6.1.2.1.2.2.1.10.{ifIndex} | ifInOctets | Counter32 |
| 14 | .1.3.6.1.2.1.2.2.1.14.{ifIndex} | ifInErrors | Counter32 |
| 16 | .1.3.6.1.2.1.2.2.1.16.{ifIndex} | ifOutOctets | Counter32 |
| 20 | .1.3.6.1.2.1.2.2.1.20.{ifIndex} | ifOutErrors | Counter32 |

### Example: Get Traffic Stats for Port 21

```bash
# Interface name
snmpget -v2c -c public 10.127.0.222 1.3.6.1.2.1.31.1.1.1.1.10021
# Returns: STRING: "21"

# RX bytes (64-bit)
snmpget -v2c -c public 10.127.0.222 1.3.6.1.2.1.31.1.1.1.6.10021
# Returns: Counter64: 120092100141789

# TX bytes (64-bit)
snmpget -v2c -c public 10.127.0.222 1.3.6.1.2.1.31.1.1.1.10.10021
# Returns: Counter64: 22117762850897

# Speed (Mbps)
snmpget -v2c -c public 10.127.0.222 1.3.6.1.2.1.31.1.1.1.15.10021
# Returns: Gauge32: 10000 (10 Gbps)
```

---

## 3. System Information - MIB-II

**Base OID:** `1.3.6.1.2.1.1`

| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.2.1.1.1.0 | sysDescr | System description |
| .1.3.6.1.2.1.1.3.0 | sysUpTime | Uptime in timeticks |
| .1.3.6.1.2.1.1.5.0 | sysName | Hostname |
| .1.3.6.1.2.1.1.6.0 | sysLocation | Location |

---

## 4. G.8032 Ring Protection - WWP-LEOS-RAPS-MIB

**Base OID:** `1.3.6.1.4.1.6141.2.60.47`

| OID | Name | Description |
|-----|------|-------------|
| .47.1.1.1.1.0 | rapsGlobalState | Global RAPS state (2=enabled) |
| .47.1.1.1.2.0 | rapsNodeId | Node MAC address |
| .47.1.1.1.4.0 | rapsLogicalRingCount | Number of logical rings |

---

## 5. Alarms - WWP-LEOS-ALARM-MIB

**Base OID:** `1.3.6.1.4.1.6141.2.60.5`

| OID | Name | Description |
|-----|------|-------------|
| .5.1.1.1.0 | alarmMaxEntries | Max alarm entries |
| .5.1.1.2.0 | alarmCurrentEntries | Current alarm count |
| .5.1.1.3.0 | alarmActiveCount | Active alarms |

---

## 6. Chassis Health - WWP-LEOS-CHASSIS-MIB

**Base OID:** `1.3.6.1.4.1.6141.2.60.8`

| OID | Name | Description |
|-----|------|-------------|
| .8.1.6.0 | chassisOperState | Operational state |
| .8.1.7.0 | chassisNumSlots | Number of slots |

---

## Quick Reference: Most Important OIDs

### Optical Power (per port)

```
RX Power (dBm×10000): 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.105.{port}
TX Power (dBm×10000): 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.106.{port}
```

### Traffic Counters (per port, ifIndex = 10000 + port)

```
RX Bytes (64-bit): 1.3.6.1.2.1.31.1.1.1.6.{10000+port}
TX Bytes (64-bit): 1.3.6.1.2.1.31.1.1.1.10.{10000+port}
Speed (Mbps):      1.3.6.1.2.1.31.1.1.1.15.{10000+port}
```

### System

```
Hostname:  1.3.6.1.2.1.1.5.0
Uptime:    1.3.6.1.2.1.1.3.0
```

---

## Polling Strategy

### Recommended Approach

1. **Bulk walk optical power** for all ports in one request:
   ```bash
   snmpbulkwalk -v2c -c public <ip> 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.105
   snmpbulkwalk -v2c -c public <ip> 1.3.6.1.4.1.6141.2.60.4.1.1.1.1.106
   ```

2. **Bulk walk interface counters** for all ports:
   ```bash
   snmpbulkwalk -v2c -c public <ip> 1.3.6.1.2.1.31.1.1.1.6
   snmpbulkwalk -v2c -c public <ip> 1.3.6.1.2.1.31.1.1.1.10
   ```

3. **Single gets for system info** (rarely changes):
   ```bash
   snmpget -v2c -c public <ip> 1.3.6.1.2.1.1.5.0
   ```

### Polling Frequency

| Data Type | Recommended Interval |
|-----------|---------------------|
| Optical Power | 5 minutes |
| Traffic Counters | 1-5 minutes |
| System Info | 1 hour |
| Alarms | 1 minute or use traps |

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Timeout | Wrong community | Use `public` not `0psc0nduct0r` |
| No Such Object | Wrong MIB | Use 6141 (WWP) not 1271 (CES) |
| Missing ports | Wrong ifIndex | Ports are 10001-10024, not 1-24 |
| Zero optical values | No SFP or copper port | Check port type first |

### Verify SNMP is Working

```bash
# Quick test - should return hostname
snmpget -v2c -c public <ip> 1.3.6.1.2.1.1.5.0
```

---

*Document Version: 1.0*
*Created: 2026-01-03*
*Tested on: Ciena 5160 (10.127.0.222), Ciena 3942*
