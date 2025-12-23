# Eaton UPS SNMP MIB Files

This folder contains MIB files for monitoring Eaton UPS devices via SNMP.

## Enterprise OID
- **Eaton**: `1.3.6.1.4.1.534` (enterprises.534)

## MIB Files

| File | Description |
|------|-------------|
| `EATON-OIDS.my` | Root OID definitions for Eaton enterprise |
| `XUPS-MIB.my` | Main UPS MIB (PowerMIB) - battery, input, output, alarms |
| `EATON-EMP-MIB.my` | Environmental Monitoring Probe (temperature, humidity, contacts) |
| `EATON-EPDU-MIB.my` | ePDU (Power Distribution Unit) MIB |
| `EATON-ATS2-MIB.my` | Automatic Transfer Switch MIB |

## Key OIDs for UPS Monitoring

### Identity (1.3.6.1.4.1.534.1.1)
| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.4.1.534.1.1.1.0 | xupsIdentManufacturer | Manufacturer name |
| .1.3.6.1.4.1.534.1.1.2.0 | xupsIdentModel | UPS model |
| .1.3.6.1.4.1.534.1.1.3.0 | xupsIdentSoftwareVersion | Firmware version |

### Battery (1.3.6.1.4.1.534.1.2)
| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.4.1.534.1.2.1.0 | xupsBatTimeRemaining | Runtime remaining (seconds) |
| .1.3.6.1.4.1.534.1.2.2.0 | xupsBatVoltage | Battery voltage (VDC) |
| .1.3.6.1.4.1.534.1.2.3.0 | xupsBatCurrent | Battery current (Amps) |
| .1.3.6.1.4.1.534.1.2.4.0 | xupsBatCapacity | Battery charge (0-100%) |
| .1.3.6.1.4.1.534.1.2.5.0 | xupsBatteryAbmStatus | Battery status (1=charging, 2=discharging, 3=floating, 4=resting, 5=unknown, 6=disconnected, 7=underTest, 8=checkBattery) |

### Input (1.3.6.1.4.1.534.1.3)
| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.4.1.534.1.3.1.0 | xupsInputFrequency | Input frequency (0.1 Hz) |
| .1.3.6.1.4.1.534.1.3.2.0 | xupsInputLineBads | Count of input out-of-tolerance events |
| .1.3.6.1.4.1.534.1.3.3.0 | xupsInputNumPhases | Number of input phases |
| .1.3.6.1.4.1.534.1.3.4.1.2.1 | xupsInputVoltage.1 | Phase 1 input voltage (V) |
| .1.3.6.1.4.1.534.1.3.4.1.3.1 | xupsInputCurrent.1 | Phase 1 input current (A) |
| .1.3.6.1.4.1.534.1.3.4.1.4.1 | xupsInputWatts.1 | Phase 1 input power (W) |

### Output (1.3.6.1.4.1.534.1.4)
| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.4.1.534.1.4.1.0 | xupsOutputLoad | Output load (%) |
| .1.3.6.1.4.1.534.1.4.2.0 | xupsOutputFrequency | Output frequency (0.1 Hz) |
| .1.3.6.1.4.1.534.1.4.3.0 | xupsOutputNumPhases | Number of output phases |
| .1.3.6.1.4.1.534.1.4.4.1.2.1 | xupsOutputVoltage.1 | Phase 1 output voltage (V) |
| .1.3.6.1.4.1.534.1.4.4.1.3.1 | xupsOutputCurrent.1 | Phase 1 output current (A) |
| .1.3.6.1.4.1.534.1.4.4.1.4.1 | xupsOutputWatts.1 | Phase 1 output power (W) |
| .1.3.6.1.4.1.534.1.4.5.0 | xupsOutputSource | Output source (1=other, 2=none, 3=normal, 4=bypass, 5=battery, 6=booster, 7=reducer) |

### Environment (1.3.6.1.4.1.534.1.6)
| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.4.1.534.1.6.1.0 | xupsEnvAmbientTemp | Ambient temperature (°C) |
| .1.3.6.1.4.1.534.1.6.2.0 | xupsEnvAmbientLowerLimit | Low temp threshold |
| .1.3.6.1.4.1.534.1.6.3.0 | xupsEnvAmbientUpperLimit | High temp threshold |
| .1.3.6.1.4.1.534.1.6.6.0 | xupsEnvAmbientHumidity | Ambient humidity (%) |

### Alarms (1.3.6.1.4.1.534.1.7)
| OID | Name | Description |
|-----|------|-------------|
| .1.3.6.1.4.1.534.1.7.1.0 | xupsAlarms | Number of active alarms |
| .1.3.6.1.4.1.534.1.7.2 | xupsAlarmTable | Table of active alarms |
| .1.3.6.1.4.1.534.1.7.3.0 | xupsOnBattery | 1 if on battery |
| .1.3.6.1.4.1.534.1.7.4.0 | xupsLowBattery | 1 if low battery |
| .1.3.6.1.4.1.534.1.7.5.0 | xupsUtilityPowerRestored | 1 if utility restored |
| .1.3.6.1.4.1.534.1.7.7.0 | xupsAlarmBatteryBad | 1 if battery bad |
| .1.3.6.1.4.1.534.1.7.8.0 | xupsOutputOverload | 1 if output overloaded |

## Testing SNMP Connectivity

```bash
# Test basic connectivity
snmpget -v2c -c public <UPS_IP> 1.3.6.1.4.1.534.1.1.2.0

# Get battery status
snmpget -v2c -c public <UPS_IP> 1.3.6.1.4.1.534.1.2.4.0

# Walk all UPS data
snmpwalk -v2c -c public <UPS_IP> 1.3.6.1.4.1.534.1
```

## Network Card Compatibility

These MIBs work with Eaton network management cards including:
- Network-MS (Gigabit Network Card)
- ConnectUPS-BD Web/SNMP Card
- ConnectUPS-X Web/SNMP Card
- Network-M2 Card
