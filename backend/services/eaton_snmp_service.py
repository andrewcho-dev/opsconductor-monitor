"""
Eaton UPS SNMP Service
Provides SNMP polling for Eaton UPS devices using the XUPS-MIB (PowerMIB)
"""

import logging
from typing import Dict, List, Optional, Any
from pysnmp.hlapi import (
    getCmd, nextCmd, SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity
)

logger = logging.getLogger(__name__)

# Eaton Enterprise OID: 1.3.6.1.4.1.534
EATON_ENTERPRISE = '1.3.6.1.4.1.534'
XUPS_MIB = f'{EATON_ENTERPRISE}.1'

# XUPS-MIB OID Mappings
EATON_OIDS = {
    # Identity (xupsMIB.1)
    'ident': {
        'manufacturer': f'{XUPS_MIB}.1.1.0',
        'model': f'{XUPS_MIB}.1.2.0',
        'software_version': f'{XUPS_MIB}.1.3.0',
        'oem_code': f'{XUPS_MIB}.1.4.0',
    },
    
    # Battery (xupsMIB.2)
    'battery': {
        'time_remaining': f'{XUPS_MIB}.2.1.0',  # seconds
        'voltage': f'{XUPS_MIB}.2.2.0',  # VDC
        'current': f'{XUPS_MIB}.2.3.0',  # Amps DC
        'capacity': f'{XUPS_MIB}.2.4.0',  # percent 0-100
        'abm_status': f'{XUPS_MIB}.2.5.0',  # battery status enum
        'last_replaced': f'{XUPS_MIB}.2.6.0',
    },
    
    # Input (xupsMIB.3)
    'input': {
        'frequency': f'{XUPS_MIB}.3.1.0',  # 0.1 Hz
        'line_bads': f'{XUPS_MIB}.3.2.0',  # count
        'num_phases': f'{XUPS_MIB}.3.3.0',
        'table': f'{XUPS_MIB}.3.4',  # xupsInputTable
        'voltage': f'{XUPS_MIB}.3.4.1.2',  # xupsInputVoltage (indexed by phase)
        'current': f'{XUPS_MIB}.3.4.1.3',  # xupsInputCurrent
        'watts': f'{XUPS_MIB}.3.4.1.4',  # xupsInputWatts
    },
    
    # Output (xupsMIB.4)
    'output': {
        'load': f'{XUPS_MIB}.4.1.0',  # percent
        'frequency': f'{XUPS_MIB}.4.2.0',  # 0.1 Hz
        'num_phases': f'{XUPS_MIB}.4.3.0',
        'table': f'{XUPS_MIB}.4.4',  # xupsOutputTable
        'voltage': f'{XUPS_MIB}.4.4.1.2',  # xupsOutputVoltage (indexed by phase)
        'current': f'{XUPS_MIB}.4.4.1.3',  # xupsOutputCurrent
        'watts': f'{XUPS_MIB}.4.4.1.4',  # xupsOutputWatts
        'source': f'{XUPS_MIB}.4.5.0',  # output source enum
    },
    
    # Bypass (xupsMIB.5)
    'bypass': {
        'frequency': f'{XUPS_MIB}.5.1.0',
        'num_phases': f'{XUPS_MIB}.5.2.0',
        'table': f'{XUPS_MIB}.5.3',
        'voltage': f'{XUPS_MIB}.5.3.1.2',
        'current': f'{XUPS_MIB}.5.3.1.3',
        'watts': f'{XUPS_MIB}.5.3.1.4',
    },
    
    # Environment (xupsMIB.6)
    'environment': {
        'ambient_temp': f'{XUPS_MIB}.6.1.0',  # Celsius
        'ambient_lower_limit': f'{XUPS_MIB}.6.2.0',
        'ambient_upper_limit': f'{XUPS_MIB}.6.3.0',
        'ambient_humidity': f'{XUPS_MIB}.6.6.0',  # percent
        'humidity_lower_limit': f'{XUPS_MIB}.6.7.0',
        'humidity_upper_limit': f'{XUPS_MIB}.6.8.0',
    },
    
    # Alarms (xupsMIB.7)
    'alarm': {
        'count': f'{XUPS_MIB}.7.1.0',
        'table': f'{XUPS_MIB}.7.2',
        'on_battery': f'{XUPS_MIB}.7.3.0',
        'low_battery': f'{XUPS_MIB}.7.4.0',
        'utility_restored': f'{XUPS_MIB}.7.5.0',
        'return_from_low_battery': f'{XUPS_MIB}.7.6.0',
        'battery_bad': f'{XUPS_MIB}.7.7.0',
        'output_overload': f'{XUPS_MIB}.7.8.0',
        'on_bypass': f'{XUPS_MIB}.7.9.0',
        'bypass_not_available': f'{XUPS_MIB}.7.10.0',
        'output_off': f'{XUPS_MIB}.7.11.0',
        'ups_shutdown': f'{XUPS_MIB}.7.12.0',
        'charger_failure': f'{XUPS_MIB}.7.13.0',
        'ups_off': f'{XUPS_MIB}.7.15.0',
        'fan_failure': f'{XUPS_MIB}.7.20.0',
        'fuse_failure': f'{XUPS_MIB}.7.21.0',
        'general_fault': f'{XUPS_MIB}.7.23.0',
        'awaiting_power': f'{XUPS_MIB}.7.25.0',
        'shutdown_pending': f'{XUPS_MIB}.7.26.0',
        'shutdown_imminent': f'{XUPS_MIB}.7.27.0',
    },
    
    # Test (xupsMIB.8)
    'test': {
        'battery_test': f'{XUPS_MIB}.8.1.0',
        'battery_test_results': f'{XUPS_MIB}.8.2.0',
    },
    
    # Config (xupsMIB.10)
    'config': {
        'input_voltage': f'{XUPS_MIB}.10.1.0',
        'input_freq': f'{XUPS_MIB}.10.2.0',
        'output_voltage': f'{XUPS_MIB}.10.3.0',
        'output_freq': f'{XUPS_MIB}.10.4.0',
        'output_va': f'{XUPS_MIB}.10.5.0',
        'output_power': f'{XUPS_MIB}.10.6.0',
        'low_battery_time': f'{XUPS_MIB}.10.7.0',
        'audible_alarm': f'{XUPS_MIB}.10.8.0',
    },
}

# Enum mappings
BATTERY_STATUS = {
    1: 'charging',
    2: 'discharging',
    3: 'floating',
    4: 'resting',
    5: 'unknown',
    6: 'disconnected',
    7: 'under_test',
    8: 'check_battery',
}

OUTPUT_SOURCE = {
    1: 'other',
    2: 'none',
    3: 'normal',
    4: 'bypass',
    5: 'battery',
    6: 'booster',
    7: 'reducer',
    8: 'parallelCapacity',
    9: 'parallelRedundant',
    10: 'highEfficiencyMode',
}

TEST_RESULTS = {
    1: 'passed',
    2: 'failed',
    3: 'in_progress',
    4: 'not_supported',
    5: 'inhibited',
    6: 'scheduled',
}


class EatonSNMPError(Exception):
    """Custom exception for Eaton SNMP errors"""
    pass


class EatonSNMPService:
    """Service for polling Eaton UPS devices via SNMP"""
    
    def __init__(self, host: str, community: str = 'public', port: int = 161, timeout: int = 5, version: int = 1):
        self.host = host
        self.community = community
        self.port = port
        self.timeout = timeout
        self.version = version  # 1 = SNMPv1, 2 = SNMPv2c
        self.engine = SnmpEngine()
    
    def _snmp_get(self, oid: str) -> Optional[Any]:
        """Perform SNMP GET operation"""
        try:
            # mpModel: 0 = SNMPv1, 1 = SNMPv2c
            mp_model = 0 if self.version == 1 else 1
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    self.engine,
                    CommunityData(self.community, mpModel=mp_model),
                    UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
            )
            
            if error_indication:
                logger.warning(f"SNMP error for {self.host}: {error_indication}")
                return None
            if error_status:
                logger.warning(f"SNMP error status for {self.host}: {error_status.prettyPrint()}")
                return None
            
            for var_bind in var_binds:
                value = var_bind[1]
                # Check for noSuchObject or noSuchInstance
                if value.prettyPrint() in ['No Such Object currently exists at this OID',
                                           'No Such Instance currently exists at this OID']:
                    return None
                return value
            return None
        except Exception as e:
            logger.error(f"SNMP GET failed for {self.host} OID {oid}: {e}")
            return None
    
    def _snmp_walk(self, oid: str) -> List[tuple]:
        """Perform SNMP WALK operation"""
        results = []
        try:
            mp_model = 0 if self.version == 1 else 1
            for error_indication, error_status, error_index, var_binds in nextCmd(
                self.engine,
                CommunityData(self.community, mpModel=mp_model),
                UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if error_indication or error_status:
                    break
                for var_bind in var_binds:
                    results.append((str(var_bind[0]), var_bind[1]))
        except Exception as e:
            logger.error(f"SNMP WALK failed for {self.host} OID {oid}: {e}")
        return results
    
    def test_connection(self) -> Dict:
        """Test SNMP connectivity to UPS"""
        try:
            model = self._snmp_get(EATON_OIDS['ident']['model'])
            if model:
                return {
                    'success': True,
                    'host': self.host,
                    'model': str(model).strip(),
                }
            return {
                'success': False,
                'host': self.host,
                'error': 'No response from UPS',
            }
        except Exception as e:
            return {
                'success': False,
                'host': self.host,
                'error': str(e),
            }
    
    def get_identity(self) -> Dict:
        """Get UPS identity information"""
        try:
            return {
                'host': self.host,
                'manufacturer': str(self._snmp_get(EATON_OIDS['ident']['manufacturer']) or '').strip(),
                'model': str(self._snmp_get(EATON_OIDS['ident']['model']) or '').strip(),
                'software_version': str(self._snmp_get(EATON_OIDS['ident']['software_version']) or '').strip(),
            }
        except Exception as e:
            logger.error(f"Failed to get identity from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get identity: {e}")
    
    def get_battery_status(self) -> Dict:
        """Get battery status and metrics"""
        try:
            time_remaining = self._snmp_get(EATON_OIDS['battery']['time_remaining'])
            voltage = self._snmp_get(EATON_OIDS['battery']['voltage'])
            current = self._snmp_get(EATON_OIDS['battery']['current'])
            capacity = self._snmp_get(EATON_OIDS['battery']['capacity'])
            abm_status = self._snmp_get(EATON_OIDS['battery']['abm_status'])
            last_replaced = self._snmp_get(EATON_OIDS['battery']['last_replaced'])
            
            # Convert time remaining to minutes
            time_remaining_min = int(time_remaining) // 60 if time_remaining else None
            
            return {
                'host': self.host,
                'time_remaining_seconds': int(time_remaining) if time_remaining else None,
                'time_remaining_minutes': time_remaining_min,
                'voltage': int(voltage) if voltage else None,
                'current': int(current) if current else None,
                'capacity_percent': int(capacity) if capacity else None,
                'status': BATTERY_STATUS.get(int(abm_status), 'unknown') if abm_status else 'unknown',
                'status_code': int(abm_status) if abm_status else None,
                'last_replaced': str(last_replaced).strip() if last_replaced else None,
            }
        except Exception as e:
            logger.error(f"Failed to get battery status from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get battery status: {e}")
    
    def get_input_status(self) -> Dict:
        """Get input power status"""
        try:
            frequency = self._snmp_get(EATON_OIDS['input']['frequency'])
            line_bads = self._snmp_get(EATON_OIDS['input']['line_bads'])
            num_phases = self._snmp_get(EATON_OIDS['input']['num_phases'])
            
            # Get per-phase data
            phases = []
            phase_count = int(num_phases) if num_phases else 1
            for phase in range(1, phase_count + 1):
                voltage = self._snmp_get(f"{EATON_OIDS['input']['voltage']}.{phase}")
                current = self._snmp_get(f"{EATON_OIDS['input']['current']}.{phase}")
                watts = self._snmp_get(f"{EATON_OIDS['input']['watts']}.{phase}")
                phases.append({
                    'phase': phase,
                    'voltage': int(voltage) if voltage else None,
                    'current': int(current) if current else None,
                    'watts': int(watts) if watts else None,
                })
            
            return {
                'host': self.host,
                'frequency_hz': int(frequency) / 10.0 if frequency else None,
                'line_bads': int(line_bads) if line_bads else 0,
                'num_phases': phase_count,
                'phases': phases,
            }
        except Exception as e:
            logger.error(f"Failed to get input status from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get input status: {e}")
    
    def get_output_status(self) -> Dict:
        """Get output power status"""
        try:
            load = self._snmp_get(EATON_OIDS['output']['load'])
            frequency = self._snmp_get(EATON_OIDS['output']['frequency'])
            num_phases = self._snmp_get(EATON_OIDS['output']['num_phases'])
            source = self._snmp_get(EATON_OIDS['output']['source'])
            
            # Get per-phase data
            phases = []
            phase_count = int(num_phases) if num_phases else 1
            for phase in range(1, phase_count + 1):
                voltage = self._snmp_get(f"{EATON_OIDS['output']['voltage']}.{phase}")
                current = self._snmp_get(f"{EATON_OIDS['output']['current']}.{phase}")
                watts = self._snmp_get(f"{EATON_OIDS['output']['watts']}.{phase}")
                phases.append({
                    'phase': phase,
                    'voltage': int(voltage) if voltage else None,
                    'current': int(current) if current else None,
                    'watts': int(watts) if watts else None,
                })
            
            return {
                'host': self.host,
                'load_percent': int(load) if load else None,
                'frequency_hz': int(frequency) / 10.0 if frequency else None,
                'source': OUTPUT_SOURCE.get(int(source), 'unknown') if source else 'unknown',
                'source_code': int(source) if source else None,
                'num_phases': phase_count,
                'phases': phases,
            }
        except Exception as e:
            logger.error(f"Failed to get output status from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get output status: {e}")
    
    def get_environment(self) -> Dict:
        """Get environmental data (temperature, humidity)"""
        try:
            temp = self._snmp_get(EATON_OIDS['environment']['ambient_temp'])
            temp_lower = self._snmp_get(EATON_OIDS['environment']['ambient_lower_limit'])
            temp_upper = self._snmp_get(EATON_OIDS['environment']['ambient_upper_limit'])
            humidity = self._snmp_get(EATON_OIDS['environment']['ambient_humidity'])
            humidity_lower = self._snmp_get(EATON_OIDS['environment']['humidity_lower_limit'])
            humidity_upper = self._snmp_get(EATON_OIDS['environment']['humidity_upper_limit'])
            
            return {
                'host': self.host,
                'temperature_c': int(temp) if temp else None,
                'temperature_lower_limit': int(temp_lower) if temp_lower else None,
                'temperature_upper_limit': int(temp_upper) if temp_upper else None,
                'humidity_percent': int(humidity) if humidity else None,
                'humidity_lower_limit': int(humidity_lower) if humidity_lower else None,
                'humidity_upper_limit': int(humidity_upper) if humidity_upper else None,
            }
        except Exception as e:
            logger.error(f"Failed to get environment from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get environment: {e}")
    
    def get_alarms(self) -> Dict:
        """Get active alarms"""
        try:
            alarm_count = self._snmp_get(EATON_OIDS['alarm']['count'])
            
            # Check individual alarm flags
            alarms = []
            alarm_checks = [
                ('on_battery', 'On Battery'),
                ('low_battery', 'Low Battery'),
                ('battery_bad', 'Battery Bad'),
                ('output_overload', 'Output Overload'),
                ('on_bypass', 'On Bypass'),
                ('bypass_not_available', 'Bypass Not Available'),
                ('output_off', 'Output Off'),
                ('ups_shutdown', 'UPS Shutdown'),
                ('charger_failure', 'Charger Failure'),
                ('ups_off', 'UPS Off'),
                ('fan_failure', 'Fan Failure'),
                ('fuse_failure', 'Fuse Failure'),
                ('general_fault', 'General Fault'),
                ('awaiting_power', 'Awaiting Power'),
                ('shutdown_pending', 'Shutdown Pending'),
                ('shutdown_imminent', 'Shutdown Imminent'),
            ]
            
            for key, description in alarm_checks:
                if key in EATON_OIDS['alarm']:
                    value = self._snmp_get(EATON_OIDS['alarm'][key])
                    if value and int(value) == 1:
                        alarms.append({
                            'type': key,
                            'description': description,
                            'active': True,
                        })
            
            return {
                'host': self.host,
                'alarm_count': int(alarm_count) if alarm_count else 0,
                'alarms': alarms,
            }
        except Exception as e:
            logger.error(f"Failed to get alarms from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get alarms: {e}")
    
    def _safe_int(self, value, default=0):
        """Safely convert value to int, returning default if not possible"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_config(self) -> Dict:
        """Get UPS configuration"""
        try:
            return {
                'host': self.host,
                'input_voltage': self._safe_int(self._snmp_get(EATON_OIDS['config']['input_voltage'])),
                'input_freq': self._safe_int(self._snmp_get(EATON_OIDS['config']['input_freq'])) / 10.0,
                'output_voltage': self._safe_int(self._snmp_get(EATON_OIDS['config']['output_voltage'])),
                'output_freq': self._safe_int(self._snmp_get(EATON_OIDS['config']['output_freq'])) / 10.0,
                'output_va': self._safe_int(self._snmp_get(EATON_OIDS['config']['output_va'])),
                'output_power': self._safe_int(self._snmp_get(EATON_OIDS['config']['output_power'])),
                'low_battery_time': self._safe_int(self._snmp_get(EATON_OIDS['config']['low_battery_time'])),
            }
        except Exception as e:
            logger.error(f"Failed to get config from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to get config: {e}")
    
    def poll_all(self) -> Dict:
        """Poll all UPS data in one call"""
        try:
            identity = self.get_identity()
            battery = self.get_battery_status()
            input_status = self.get_input_status()
            output = self.get_output_status()
            environment = self.get_environment()
            alarms = self.get_alarms()
            config = self.get_config()
            
            return {
                'host': self.host,
                'identity': identity,
                'battery': battery,
                'input': input_status,
                'output': output,
                'environment': environment,
                'alarms': alarms,
                'config': config,
            }
        except Exception as e:
            logger.error(f"Failed to poll all data from {self.host}: {e}")
            raise EatonSNMPError(f"Failed to poll all data: {e}")
