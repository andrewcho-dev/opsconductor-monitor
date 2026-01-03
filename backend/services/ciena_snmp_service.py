"""
Ciena SNMP Service.

Provides SNMP polling for Ciena 3942/5160 switches running SAOS 6.
Uses official Ciena MIBs for real-time monitoring of:
- Active alarms
- G.8032 Ring (RAPS) status
- Port status and statistics
- Chassis/system information
"""

import logging
from typing import Dict, List, Optional, Any
from pysnmp.hlapi import (
    getCmd, nextCmd, bulkCmd,
    SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity,
    Integer, OctetString
)

logger = logging.getLogger(__name__)


# WWP (World Wide Packets) Enterprise OID: 1.3.6.1.4.1.6141
# Ciena 3942/5160 running SAOS use WWP LEOS MIBs
WWP_ENTERPRISE = '1.3.6.1.4.1.6141'
WWP_MODULES_LEOS = f'{WWP_ENTERPRISE}.2.60'

# Key OIDs from official WWP LEOS MIBs
WWP_OIDS = {
    # WWP-LEOS-RAPS-MIB (wwpModulesLeos.47 = 1.3.6.1.4.1.6141.2.60.47)
    'raps': {
        'base': f'{WWP_MODULES_LEOS}.47',
        'global_state': f'{WWP_MODULES_LEOS}.47.1.1.1.1.0',  # wwpLeosRapsState (1=disabled, 2=enabled)
        'node_id': f'{WWP_MODULES_LEOS}.47.1.1.1.2.0',  # wwpLeosRapsNodeId
        'num_rings': f'{WWP_MODULES_LEOS}.47.1.1.1.4.0',  # wwpLeosRapsNumberOfRings
        'logical_ring_table': f'{WWP_MODULES_LEOS}.47.1.2.1',  # wwpLeosRapsLogicalRingTable
        'virtual_ring_table': f'{WWP_MODULES_LEOS}.47.1.3.1',  # wwpLeosRapsVirtualRingTable
    },
    
    # Virtual Ring Table entries (wwpLeosRapsVirtualRingEntry)
    'virtual_ring': {
        'name': f'{WWP_MODULES_LEOS}.47.1.3.1.1.2',  # wwpLeosRapsVirtualRingName
        'vid': f'{WWP_MODULES_LEOS}.47.1.3.1.1.3',  # wwpLeosRapsVirtualRingVid
        'logical_ring_id': f'{WWP_MODULES_LEOS}.47.1.3.1.1.4',  # wwpLeosRapsVirtualRingLogicalRingId
        'revertive': f'{WWP_MODULES_LEOS}.47.1.3.1.1.6',  # wwpLeosRapsVirtualRingRevertive
        'state': f'{WWP_MODULES_LEOS}.47.1.3.1.1.7',  # wwpLeosRapsVirtualRingState
        'status': f'{WWP_MODULES_LEOS}.47.1.3.1.1.8',  # wwpLeosRapsVirtualRingStatus
        'alarm': f'{WWP_MODULES_LEOS}.47.1.3.1.1.9',  # wwpLeosRapsVirtualRingAlarm
        'switchovers': f'{WWP_MODULES_LEOS}.47.1.3.1.1.10',  # wwpLeosRapsVirtualRingNumOfSwitchOvers
        'uptime_last_failure': f'{WWP_MODULES_LEOS}.47.1.3.1.1.11',  # wwpLeosRapsVirtualRingUptimeFromLastFailure
        'total_downtime': f'{WWP_MODULES_LEOS}.47.1.3.1.1.12',  # wwpLeosRapsVirtualRingTotalDownTime
        'west_port_rpl': f'{WWP_MODULES_LEOS}.47.1.3.1.1.13',  # wwpLeosRapsVirtualRingWestPortRpl
        'west_port_state': f'{WWP_MODULES_LEOS}.47.1.3.1.1.14',  # wwpLeosRapsVirtualRingWestPortState
        'west_port_status': f'{WWP_MODULES_LEOS}.47.1.3.1.1.15',  # wwpLeosRapsVirtualRingWestPortStatus
        'east_port_rpl': f'{WWP_MODULES_LEOS}.47.1.3.1.1.24',  # wwpLeosRapsVirtualRingEastPortRpl
        'east_port_state': f'{WWP_MODULES_LEOS}.47.1.3.1.1.25',  # wwpLeosRapsVirtualRingEastPortState
        'east_port_status': f'{WWP_MODULES_LEOS}.47.1.3.1.1.26',  # wwpLeosRapsVirtualRingEastPortStatus
        'ring_type': f'{WWP_MODULES_LEOS}.47.1.3.1.1.35',  # wwpLeosRapsVirtualRingType
    },
    
    # WWP-LEOS-CHASSIS-MIB (wwpModulesLeos.1)
    'chassis': {
        'base': f'{WWP_MODULES_LEOS}.1',
        'model': f'{WWP_MODULES_LEOS}.1.1.1.2.1.7.1',  # wwpLeosChassisDeviceType
        'serial': f'{WWP_MODULES_LEOS}.1.1.1.2.1.3.1',  # wwpLeosChassisMfgSerialNum
    },
    
    # WWP-LEOS-PORT-MIB (wwpModulesLeos.2)
    'port': {
        'base': f'{WWP_MODULES_LEOS}.2',
        'table': f'{WWP_MODULES_LEOS}.2.1.1.1',  # wwpLeosPortTable
        'id': f'{WWP_MODULES_LEOS}.2.1.1.1.1.1',  # wwpLeosPortId
        'type': f'{WWP_MODULES_LEOS}.2.1.1.1.1.2',  # wwpLeosPortType
        'name': f'{WWP_MODULES_LEOS}.2.1.1.1.1.3',  # wwpLeosPortName
        'desc': f'{WWP_MODULES_LEOS}.2.1.1.1.1.4',  # wwpLeosPortDesc
        'admin_state': f'{WWP_MODULES_LEOS}.2.1.1.1.1.5',  # wwpLeosPortAdminStatus
        'oper_state': f'{WWP_MODULES_LEOS}.2.1.1.1.1.6',  # wwpLeosPortOperStatus
    },
    
    # WWP-LEOS-PORT-XCVR-MIB (wwpModulesLeos.4) - SFP/DOM data
    'xcvr': {
        'base': f'{WWP_MODULES_LEOS}.4',
        'table': f'{WWP_MODULES_LEOS}.4.1.1.1',  # wwpLeosPortXcvrTable
        'id': f'{WWP_MODULES_LEOS}.4.1.1.1.1.1',  # wwpLeosPortXcvrId
        'oper_state': f'{WWP_MODULES_LEOS}.4.1.1.1.1.2',  # wwpLeosPortXcvrOperState
        'identifier_type': f'{WWP_MODULES_LEOS}.4.1.1.1.1.3',  # wwpLeosPortXcvrIdentiferType (SFP/XFP/etc)
        'connector_type': f'{WWP_MODULES_LEOS}.4.1.1.1.1.5',  # wwpLeosPortXcvrConnectorType
        'xcvr_type': f'{WWP_MODULES_LEOS}.4.1.1.1.1.6',  # wwpLeosPortXcvrType (speed/reach)
        'vendor_name': f'{WWP_MODULES_LEOS}.4.1.1.1.1.7',  # wwpLeosPortXcvrVendorName
        'vendor_pn': f'{WWP_MODULES_LEOS}.4.1.1.1.1.9',  # wwpLeosPortXcvrVendorPN
        'serial_num': f'{WWP_MODULES_LEOS}.4.1.1.1.1.11',  # wwpLeosPortXcvrSerialNum
        'wavelength': f'{WWP_MODULES_LEOS}.4.1.1.1.1.15',  # wwpLeosPortXcvrWaveLength (nm)
        'temperature': f'{WWP_MODULES_LEOS}.4.1.1.1.1.16',  # wwpLeosPortXcvrTemperature (degrees C)
        'vcc': f'{WWP_MODULES_LEOS}.4.1.1.1.1.17',  # wwpLeosPortXcvrVcc
        'bias': f'{WWP_MODULES_LEOS}.4.1.1.1.1.18',  # wwpLeosPortXcvrBias
        'rx_power_uw': f'{WWP_MODULES_LEOS}.4.1.1.1.1.19',  # wwpLeosPortXcvrRxPower (uW)
        'tx_power_uw': f'{WWP_MODULES_LEOS}.4.1.1.1.1.27',  # wwpLeosPortXcvrTxOutputPw (uW)
        'rx_dbm': f'{WWP_MODULES_LEOS}.4.1.1.1.1.105',  # wwpLeosPortXcvrRxDbmPower (dBm * 10000)
        'tx_dbm': f'{WWP_MODULES_LEOS}.4.1.1.1.1.106',  # wwpLeosPortXcvrTxDbmPower (dBm * 10000)
        'los_state': f'{WWP_MODULES_LEOS}.4.1.1.1.1.28',  # wwpLeosPortXcvrLosState
        'diag_supported': f'{WWP_MODULES_LEOS}.4.1.1.1.1.29',  # wwpLeosPortXcvrDiagSupported
    },
    
    # Standard MIB-II OIDs
    'system': {
        'descr': '1.3.6.1.2.1.1.1.0',  # sysDescr
        'object_id': '1.3.6.1.2.1.1.2.0',  # sysObjectID
        'uptime': '1.3.6.1.2.1.1.3.0',  # sysUpTime
        'contact': '1.3.6.1.2.1.1.4.0',  # sysContact
        'name': '1.3.6.1.2.1.1.5.0',  # sysName
        'location': '1.3.6.1.2.1.1.6.0',  # sysLocation
    },
    
    # WWP-LEOS-PORT-STATS-MIB (wwpModulesLeos.3)
    'port_stats': {
        'base': f'{WWP_MODULES_LEOS}.3',
        'table': f'{WWP_MODULES_LEOS}.3.1.1.2',  # wwpLeosPortStatsTable
        'rx_bytes': f'{WWP_MODULES_LEOS}.3.1.1.2.1.2',  # wwpLeosPortStatsRxBytes (col 2)
        'rx_pkts': f'{WWP_MODULES_LEOS}.3.1.1.2.1.3',  # wwpLeosPortStatsRxPkts (col 3)
        'rx_crc_errors': f'{WWP_MODULES_LEOS}.3.1.1.2.1.4',  # wwpLeosPortStatsRxCrcErrorPkts (col 4)
        'rx_bcast': f'{WWP_MODULES_LEOS}.3.1.1.2.1.5',  # wwpLeosPortStatsRxBcastPkts (col 5)
        'tx_bytes': f'{WWP_MODULES_LEOS}.3.1.1.2.1.16',  # wwpLeosPortStatsTxBytes (col 16)
        'tx_pkts': f'{WWP_MODULES_LEOS}.3.1.1.2.1.18',  # wwpLeosPortStatsTxPkts (col 18)
        'rx_discard': f'{WWP_MODULES_LEOS}.3.1.1.2.1.62',  # wwpLeosPortStatsRxDiscardPkts
        'rx_errors': f'{WWP_MODULES_LEOS}.3.1.1.2.1.70',  # wwpLeosPortStatsRxInErrorPkts
        'link_up_count': f'{WWP_MODULES_LEOS}.3.1.1.2.1.56',  # wwpLeosPortStatsPortLinkUp
        'link_down_count': f'{WWP_MODULES_LEOS}.3.1.1.2.1.57',  # wwpLeosPortStatsPortLinkDown
        'link_flap_count': f'{WWP_MODULES_LEOS}.3.1.1.2.1.58',  # wwpLeosPortStatsPortLinkFlap
    },
    
    # WWP-LEOS-CHASSIS-MIB - Power Supply (wwpModulesLeos.1.1.1.3)
    'power_supply': {
        'table': f'{WWP_MODULES_LEOS}.1.1.1.3.1',  # wwpLeosChassisPowerTable
        'num': f'{WWP_MODULES_LEOS}.1.1.1.3.1.1.1',  # wwpLeosChassisPowerSupplyNum
        'state': f'{WWP_MODULES_LEOS}.1.1.1.3.1.1.2',  # wwpLeosChassisPowerSupplyState
        'type': f'{WWP_MODULES_LEOS}.1.1.1.3.1.1.3',  # wwpLeosChassisPowerSupplyType
        'redundant_state': f'{WWP_MODULES_LEOS}.1.1.1.3.1.1.4',  # wwpLeosChassisPowerSupplyRedundantState
    },
    
    # WWP-LEOS-CHASSIS-MIB - Fan Module (wwpModulesLeos.1.1.1.4)
    'fan': {
        'table': f'{WWP_MODULES_LEOS}.1.1.1.4.1',  # wwpLeosChassisFanModuleTable
        'num': f'{WWP_MODULES_LEOS}.1.1.1.4.1.1.1',  # wwpLeosChassisFanModuleNum
        'type': f'{WWP_MODULES_LEOS}.1.1.1.4.1.1.2',  # wwpLeosChassisFanModuleType
        'status': f'{WWP_MODULES_LEOS}.1.1.1.4.1.1.3',  # wwpLeosChassisFanModuleStatus
        'avg_speed': f'{WWP_MODULES_LEOS}.1.1.1.4.1.1.4',  # wwpLeosChassisFanAvgSpeed
        'current_speed': f'{WWP_MODULES_LEOS}.1.1.1.4.1.1.5',  # wwpLeosChassisFanCurrentSpeed
    },
    
    # WWP-LEOS-CHASSIS-MIB - Temperature Sensor (wwpModulesLeos.1.1.1.5)
    'temp_sensor': {
        'table': f'{WWP_MODULES_LEOS}.1.1.1.5.1',  # wwpLeosChassisTempSensorTable
        'num': f'{WWP_MODULES_LEOS}.1.1.1.5.1.1.1',  # wwpLeosChassisTempSensorNum
        'value': f'{WWP_MODULES_LEOS}.1.1.1.5.1.1.2',  # wwpLeosChassisTempSensorValue
        'high_threshold': f'{WWP_MODULES_LEOS}.1.1.1.5.1.1.3',  # wwpLeosChassisTempSensorHighThreshold
        'low_threshold': f'{WWP_MODULES_LEOS}.1.1.1.5.1.1.4',  # wwpLeosChassisTempSensorLowThreshold
        'state': f'{WWP_MODULES_LEOS}.1.1.1.5.1.1.5',  # wwpLeosChassisTempSensorState
    },
    
    # WWP-LEOS-EXT-LAG-MIB (wwpModulesLeos.14)
    'lag': {
        'base': f'{WWP_MODULES_LEOS}.14',
        'max_lags': f'{WWP_MODULES_LEOS}.14.1.1.1.0',  # wwpLeosMaxLags
        'num_lags': f'{WWP_MODULES_LEOS}.14.1.1.2.0',  # wwpLeosNumLags
        'table': f'{WWP_MODULES_LEOS}.14.1.1.3',  # wwpExtLagTable
        'id': f'{WWP_MODULES_LEOS}.14.1.1.3.1.1',  # wwpLeosExtAggId
        'name': f'{WWP_MODULES_LEOS}.14.1.1.3.1.2',  # wwpLeosExtAggName
        'mode': f'{WWP_MODULES_LEOS}.14.1.1.3.1.4',  # wwpLeosExtAggMode
        'admin_state': f'{WWP_MODULES_LEOS}.14.1.1.3.1.5',  # wwpLeosExtAggAdminState
        'oper_state': f'{WWP_MODULES_LEOS}.14.1.1.3.1.6',  # wwpLeosExtAggOperState
        'member_count': f'{WWP_MODULES_LEOS}.14.1.1.3.1.7',  # wwpLeosExtAggMemberCount
    },
    
    # WWP-LEOS-MSTP-MIB (wwpModulesLeos.37)
    'mstp': {
        'base': f'{WWP_MODULES_LEOS}.37',
        'enabled': f'{WWP_MODULES_LEOS}.37.1.1.1.0',  # wwpLeosMstpBridgeEnable
        'force_version': f'{WWP_MODULES_LEOS}.37.1.1.2.0',  # wwpLeosMstpForceVersion
        'bridge_priority': f'{WWP_MODULES_LEOS}.37.1.1.3.0',  # wwpLeosMstpBridgePriority
        'port_table': f'{WWP_MODULES_LEOS}.37.1.3.1',  # wwpLeosMstpXstPortTable
        'port_state': f'{WWP_MODULES_LEOS}.37.1.3.1.1.4',  # wwpLeosMstpXstPortState
        'port_role': f'{WWP_MODULES_LEOS}.37.1.3.1.1.5',  # wwpLeosMstpXstPortRole
    },
    
    # WWP-LEOS-NTP-CLIENT-MIB (wwpModulesLeos.18)
    'ntp': {
        'base': f'{WWP_MODULES_LEOS}.18',
        'admin_state': f'{WWP_MODULES_LEOS}.18.1.1.1.0',  # wwpLeosNtpClientAdminState
        'oper_state': f'{WWP_MODULES_LEOS}.18.1.1.2.0',  # wwpLeosNtpClientOperState
        'sync_status': f'{WWP_MODULES_LEOS}.18.1.1.3.0',  # wwpLeosNtpClientSyncStatus
        'server_table': f'{WWP_MODULES_LEOS}.18.1.1.5',  # wwpLeosNtpClientServerTable
    },
    
    # WWP-LEOS-CFM-MIB (wwpModulesLeos.6)
    'cfm': {
        'base': f'{WWP_MODULES_LEOS}.6',
        'global_state': f'{WWP_MODULES_LEOS}.6.1.1.1.0',  # wwpLeosCfmGlobalAdminState
        'service_table': f'{WWP_MODULES_LEOS}.6.1.2.1',  # wwpLeosCfmServiceTable
        'mep_table': f'{WWP_MODULES_LEOS}.6.1.4.1',  # wwpLeosCfmExtMEPTable
        'mep_oper_state': f'{WWP_MODULES_LEOS}.6.1.4.1.1.3',  # wwpLeosCfmExtMEPOperState
        'mep_ccm_state': f'{WWP_MODULES_LEOS}.6.1.4.1.1.7',  # wwpLeosCfmExtMEPCcmState
        'mep_remote_mep_state': f'{WWP_MODULES_LEOS}.6.1.4.1.1.11',  # wwpLeosCfmExtMEPRemoteMEPState
        'mep_defects': f'{WWP_MODULES_LEOS}.6.1.4.1.1.15',  # wwpLeosCfmExtMEPDefects
    },
}

# Ciena CES Enterprise OID: 1.3.6.1.4.1.1271
# Used for alarm MIBs on SAOS devices
CIENA_CES_ENTERPRISE = '1.3.6.1.4.1.1271'
CIENA_CES_CONFIG = f'{CIENA_CES_ENTERPRISE}.2.1'

# Ciena CES Alarm MIB OIDs (works on 3942/5160)
CES_ALARM_OIDS = {
    'base': f'{CIENA_CES_CONFIG}.24',
    'cutoff': f'{CIENA_CES_CONFIG}.24.1.1.1.0',  # cienaCesAlarmCutOff
    'alarm_table': f'{CIENA_CES_CONFIG}.24.1.2.1',  # cienaCesAlarmTable (alarm definitions)
    'active_table': f'{CIENA_CES_CONFIG}.24.1.3.1',  # cienaCesAlarmActiveTable
    # Active alarm entry fields
    'active_severity': f'{CIENA_CES_CONFIG}.24.1.3.1.1.1',  # cienaCesAlarmActiveSeverity
    'active_invoke_id': f'{CIENA_CES_CONFIG}.24.1.3.1.1.2',  # cienaCesAlarmActiveInvokeId
    'active_object_class': f'{CIENA_CES_CONFIG}.24.1.3.1.1.3',  # cienaCesAlarmActiveManagedObjectClass
    'active_object_interpret': f'{CIENA_CES_CONFIG}.24.1.3.1.1.4',  # cienaCesAlarmActiveManagedObjectInterpret
    'active_object_instance': f'{CIENA_CES_CONFIG}.24.1.3.1.1.5',  # cienaCesAlarmActiveManagedObjectInstance
    'active_acknowledged': f'{CIENA_CES_CONFIG}.24.1.3.1.1.6',  # cienaCesAlarmActiveAck
    'active_description': f'{CIENA_CES_CONFIG}.24.1.3.1.1.7',  # cienaCesAlarmActiveDescription
    'active_timestamp': f'{CIENA_CES_CONFIG}.24.1.3.1.1.8',  # cienaCesAlarmActiveTimeStamp
}

# Backward compatibility alias
CIENA_OIDS = WWP_OIDS

# Enum mappings from MIBs
XCVR_IDENTIFIER_TYPE = {
    1: 'Unknown',
    2: 'GBIC',
    3: 'Soldered',
    4: 'SFP',
    5: 'Reserved',
    6: 'Vendor',
    7: 'XBI',
    8: 'XENPAK',
    9: 'XFP',
    10: 'XFF',
    11: 'XFP-E',
    12: 'XPAK',
    13: 'X2',
}

RAPS_STATE = {
    1: 'adminDisabled',
    2: 'ok',
    3: 'protecting',
    4: 'recovering',
    5: 'init',
    6: 'none',
}

RAPS_STATUS = {
    1: 'clear',
    2: 'localSignalFail',
    3: 'localForceSwitch',
    4: 'remoteOrOtherPortSignalFail',
    5: 'remoteOrOtherPortForceSwitch',
    6: 'provisioningMismatch',
    7: 'noRapsPduReceived',
    8: 'noRplOwnerDetected',
}

RAPS_ALARM = {
    1: 'clear',
    2: 'protectionSwitching',
    3: 'provisionMismatch',
    4: 'noRapsPduReceived',
    5: 'noRplOwnerDetected',
}

ALARM_SEVERITY = {
    1: 'cleared',
    2: 'indeterminate',
    3: 'critical',
    4: 'major',
    5: 'minor',
    6: 'warning',
}

ALARM_OBJECT_CLASS = {
    1: 'unknown',
    2: 'chassis',
    3: 'slot',
    4: 'port',
}

# Power supply state
POWER_SUPPLY_STATE = {
    1: 'online',
    2: 'offline',
    3: 'faulted',
}

# Fan status
FAN_STATUS = {
    1: 'ok',
    2: 'pending',
    3: 'failure',
}

# Temperature sensor state
TEMP_SENSOR_STATE = {
    0: 'high',
    1: 'normal',
    2: 'low',
}

# LAG mode
LAG_MODE = {
    1: 'static',
    2: 'lacp',
}

# MSTP port state
MSTP_PORT_STATE = {
    1: 'disabled',
    2: 'blocking',
    3: 'listening',
    4: 'learning',
    5: 'forwarding',
}

# MSTP port role
MSTP_PORT_ROLE = {
    1: 'disabled',
    2: 'root',
    3: 'designated',
    4: 'alternate',
    5: 'backup',
}

# NTP sync status
NTP_SYNC_STATUS = {
    1: 'notSynchronized',
    2: 'synchronized',
}

# CFM MEP operational state
CFM_MEP_OPER_STATE = {
    1: 'disabled',
    2: 'enabled',
}


class CienaSNMPError(Exception):
    """Exception for Ciena SNMP errors."""
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(message)


class CienaSNMPService:
    """Service for SNMP polling of Ciena switches."""
    
    def __init__(self, host: str, community: str = 'public', port: int = 161, timeout: int = 5, retries: int = 2):
        """
        Initialize Ciena SNMP client.
        
        Args:
            host: Switch IP address or hostname
            community: SNMP community string
            port: SNMP port (default 161)
            timeout: Request timeout in seconds
            retries: Number of retries on failure
        """
        self.host = host
        self.community = community
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self._engine = SnmpEngine()
    
    def _get_transport(self) -> UdpTransportTarget:
        """Get UDP transport target."""
        return UdpTransportTarget(
            (self.host, self.port),
            timeout=self.timeout,
            retries=self.retries
        )
    
    def _get_community(self) -> CommunityData:
        """Get community data for SNMPv2c."""
        return CommunityData(self.community, mpModel=1)  # mpModel=1 for SNMPv2c
    
    def _snmp_get(self, oid: str) -> Any:
        """
        Perform SNMP GET request.
        
        Args:
            oid: OID to query
            
        Returns:
            Value from SNMP response
        """
        error_indication, error_status, error_index, var_binds = next(
            getCmd(
                self._engine,
                self._get_community(),
                self._get_transport(),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
        )
        
        if error_indication:
            raise CienaSNMPError(f"SNMP error: {error_indication}")
        elif error_status:
            raise CienaSNMPError(f"SNMP error: {error_status.prettyPrint()} at {error_index}")
        
        for var_bind in var_binds:
            return var_bind[1]
        
        return None
    
    def _snmp_walk(self, oid: str) -> List[tuple]:
        """
        Perform SNMP WALK (GETNEXT) request.
        
        Args:
            oid: Base OID to walk
            
        Returns:
            List of (oid, value) tuples
        """
        results = []
        
        for error_indication, error_status, error_index, var_binds in nextCmd(
            self._engine,
            self._get_community(),
            self._get_transport(),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        ):
            if error_indication:
                logger.warning(f"SNMP walk error: {error_indication}")
                break
            elif error_status:
                logger.warning(f"SNMP walk error: {error_status.prettyPrint()}")
                break
            else:
                for var_bind in var_binds:
                    results.append((str(var_bind[0]), var_bind[1]))
        
        return results
    
    def _snmp_bulk(self, oid: str, max_repetitions: int = 25) -> List[tuple]:
        """
        Perform SNMP BULK request for efficient table retrieval.
        
        Args:
            oid: Base OID to query
            max_repetitions: Max rows to retrieve per request
            
        Returns:
            List of (oid, value) tuples
        """
        results = []
        
        for error_indication, error_status, error_index, var_binds in bulkCmd(
            self._engine,
            self._get_community(),
            self._get_transport(),
            ContextData(),
            0, max_repetitions,
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        ):
            if error_indication:
                logger.warning(f"SNMP bulk error: {error_indication}")
                break
            elif error_status:
                logger.warning(f"SNMP bulk error: {error_status.prettyPrint()}")
                break
            else:
                for var_bind in var_binds:
                    results.append((str(var_bind[0]), var_bind[1]))
        
        return results
    
    def get_system_info(self) -> Dict:
        """Get basic system information via SNMP."""
        try:
            return {
                'host': self.host,
                'name': str(self._snmp_get(CIENA_OIDS['system']['name']) or ''),
                'description': str(self._snmp_get(CIENA_OIDS['system']['descr']) or ''),
                'uptime': int(self._snmp_get(CIENA_OIDS['system']['uptime']) or 0),
                'location': str(self._snmp_get(CIENA_OIDS['system']['location']) or ''),
                'contact': str(self._snmp_get(CIENA_OIDS['system']['contact']) or ''),
            }
        except Exception as e:
            logger.error(f"Failed to get system info from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get system info: {e}")
    
    def get_raps_global(self) -> Dict:
        """Get global RAPS (G.8032) status."""
        try:
            state = self._snmp_get(WWP_OIDS['raps']['global_state'])
            num_rings = self._snmp_get(WWP_OIDS['raps']['num_rings'])
            node_id = self._snmp_get(WWP_OIDS['raps']['node_id'])
            
            # WWP LEOS: 1=disabled, 2=enabled
            state_str = 'enabled' if state and int(state) == 2 else 'disabled'
            
            return {
                'host': self.host,
                'state': state_str,
                'num_rings': int(num_rings) if num_rings else 0,
                'node_id': str(node_id) if node_id else None,
            }
        except Exception as e:
            logger.error(f"Failed to get RAPS global from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get RAPS global: {e}")
    
    def get_virtual_rings(self) -> List[Dict]:
        """Get all virtual ring status via SNMP."""
        rings = []
        
        try:
            # Walk the virtual ring table
            name_results = self._snmp_walk(WWP_OIDS['virtual_ring']['name'])
            
            for oid, name in name_results:
                # Extract ring index from OID
                ring_index = oid.split('.')[-1]
                
                try:
                    ring = {
                        'index': int(ring_index),
                        'name': str(name),
                        'host': self.host,
                    }
                    
                    # Get additional ring attributes
                    for attr, base_oid in WWP_OIDS['virtual_ring'].items():
                        if attr == 'name':
                            continue
                        try:
                            value = self._snmp_get(f"{base_oid}.{ring_index}")
                            if value is not None:
                                # Convert enum values
                                if attr == 'state':
                                    ring[attr] = RAPS_STATE.get(int(value), str(value))
                                elif attr == 'status':
                                    ring[attr] = RAPS_STATUS.get(int(value), str(value))
                                elif attr == 'alarm':
                                    ring[attr] = RAPS_ALARM.get(int(value), str(value))
                                elif attr in ('revertive', 'west_port_rpl', 'east_port_rpl'):
                                    ring[attr] = int(value) == 2  # 2 = on/true
                                else:
                                    ring[attr] = int(value) if isinstance(value, Integer) else str(value)
                        except Exception as e:
                            logger.debug(f"Could not get {attr} for ring {ring_index}: {e}")
                    
                    rings.append(ring)
                    
                except Exception as e:
                    logger.warning(f"Error processing ring {ring_index}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to get virtual rings from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get virtual rings: {e}")
        
        return rings
    
    def get_active_alarms(self) -> List[Dict]:
        """Get active alarms via SNMP using Ciena CES Alarm MIB."""
        alarms = {}
        
        try:
            # Walk each column and build alarm dict by index
            # Column 1: Severity
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_severity']):
                idx = oid.replace(CES_ALARM_OIDS['active_severity'] + '.', '')
                if idx not in alarms:
                    alarms[idx] = {'index': idx, 'host': self.host}
                alarms[idx]['severity'] = ALARM_SEVERITY.get(int(val), 'unknown') if val else 'unknown'
            
            # Column 3: Object Class
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_object_class']):
                idx = oid.replace(CES_ALARM_OIDS['active_object_class'] + '.', '')
                if idx in alarms:
                    alarms[idx]['object_class'] = ALARM_OBJECT_CLASS.get(int(val), 'unknown') if val else 'unknown'
            
            # Column 4: Object Interpret (e.g. "Port ID", "Virt Ring")
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_object_interpret']):
                idx = oid.replace(CES_ALARM_OIDS['active_object_interpret'] + '.', '')
                if idx in alarms:
                    alarms[idx]['object_type'] = str(val).strip() if val else None
            
            # Column 5: Object Instance (e.g. "17", "VR100")
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_object_instance']):
                idx = oid.replace(CES_ALARM_OIDS['active_object_instance'] + '.', '')
                if idx in alarms:
                    alarms[idx]['object_instance'] = str(val).strip() if val else None
            
            # Column 6: Acknowledged
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_acknowledged']):
                idx = oid.replace(CES_ALARM_OIDS['active_acknowledged'] + '.', '')
                if idx in alarms:
                    alarms[idx]['acknowledged'] = (int(val) == 1) if val else False
            
            # Column 7: Description
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_description']):
                idx = oid.replace(CES_ALARM_OIDS['active_description'] + '.', '')
                if idx in alarms:
                    alarms[idx]['description'] = str(val).strip() if val else 'Unknown'
            
            # Column 8: Timestamp
            for oid, val in self._snmp_walk(CES_ALARM_OIDS['active_timestamp']):
                idx = oid.replace(CES_ALARM_OIDS['active_timestamp'] + '.', '')
                if idx in alarms:
                    alarms[idx]['timestamp'] = str(val).strip() if val else None
            
        except Exception as e:
            logger.error(f"Failed to get active alarms from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get active alarms: {e}")
        
        return list(alarms.values())
    
    def get_ports(self) -> List[Dict]:
        """Get port status via SNMP."""
        ports = []
        
        try:
            # Walk port names
            name_results = self._snmp_walk(WWP_OIDS['port']['name'])
            
            for oid, name in name_results:
                port_index = oid.split('.')[-1]
                
                try:
                    port = {
                        'index': int(port_index),
                        'name': str(name),
                        'host': self.host,
                    }
                    
                    # Get admin state
                    try:
                        admin = self._snmp_get(f"{WWP_OIDS['port']['admin_state']}.{port_index}")
                        port['admin_state'] = 'enabled' if admin and int(admin) == 1 else 'disabled'
                    except:
                        port['admin_state'] = 'unknown'
                    
                    # Get oper state
                    try:
                        oper = self._snmp_get(f"{WWP_OIDS['port']['oper_state']}.{port_index}")
                        port['oper_state'] = 'up' if oper and int(oper) == 1 else 'down'
                    except:
                        port['oper_state'] = 'unknown'
                    
                    ports.append(port)
                    
                except Exception as e:
                    logger.debug(f"Error processing port {port_index}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to get ports from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get ports: {e}")
        
        return ports
    
    def get_transceivers(self) -> List[Dict]:
        """Get SFP/transceiver DOM data via SNMP."""
        xcvrs = []
        
        try:
            # Walk transceiver vendor names to find populated ports
            vendor_results = self._snmp_walk(WWP_OIDS['xcvr']['vendor_name'])
            
            for oid, vendor in vendor_results:
                xcvr_index = oid.split('.')[-1]
                vendor_str = str(vendor).strip()
                
                # Skip empty/not present
                if not vendor_str:
                    continue
                
                try:
                    xcvr = {
                        'port_id': int(xcvr_index),
                        'vendor': vendor_str,
                        'host': self.host,
                    }
                    
                    # Get oper state
                    try:
                        oper = self._snmp_get(f"{WWP_OIDS['xcvr']['oper_state']}.{xcvr_index}")
                        oper_map = {1: 'disabled', 2: 'enabled', 3: 'loopback', 4: 'notPresent', 5: 'faulted'}
                        xcvr['oper_state'] = oper_map.get(int(oper), str(oper)) if oper else 'unknown'
                    except:
                        xcvr['oper_state'] = 'unknown'
                    
                    # Get identifier type (SFP, XFP, etc)
                    try:
                        id_type = self._snmp_get(f"{WWP_OIDS['xcvr']['identifier_type']}.{xcvr_index}")
                        xcvr['sfp_type'] = XCVR_IDENTIFIER_TYPE.get(int(id_type), 'Unknown') if id_type else 'Unknown'
                    except:
                        xcvr['sfp_type'] = 'Unknown'
                    
                    # Get part number
                    try:
                        pn = self._snmp_get(f"{WWP_OIDS['xcvr']['vendor_pn']}.{xcvr_index}")
                        xcvr['part_number'] = str(pn).strip() if pn else None
                    except:
                        xcvr['part_number'] = None
                    
                    # Get serial number
                    try:
                        sn = self._snmp_get(f"{WWP_OIDS['xcvr']['serial_num']}.{xcvr_index}")
                        xcvr['serial_number'] = str(sn).strip() if sn else None
                    except:
                        xcvr['serial_number'] = None
                    
                    # Get wavelength
                    try:
                        wl = self._snmp_get(f"{WWP_OIDS['xcvr']['wavelength']}.{xcvr_index}")
                        xcvr['wavelength_nm'] = int(wl) if wl else None
                    except:
                        xcvr['wavelength_nm'] = None
                    
                    # Get temperature (degrees C - raw value)
                    try:
                        temp = self._snmp_get(f"{WWP_OIDS['xcvr']['temperature']}.{xcvr_index}")
                        xcvr['temperature_c'] = int(temp) if temp else None
                    except:
                        xcvr['temperature_c'] = None
                    
                    # Get Rx power in dBm (value / 10000)
                    try:
                        rx_dbm = self._snmp_get(f"{WWP_OIDS['xcvr']['rx_dbm']}.{xcvr_index}")
                        xcvr['rx_power_dbm'] = round(int(rx_dbm) / 10000.0, 2) if rx_dbm else None
                    except:
                        xcvr['rx_power_dbm'] = None
                    
                    # Get Tx power in dBm (value / 10000)
                    try:
                        tx_dbm = self._snmp_get(f"{WWP_OIDS['xcvr']['tx_dbm']}.{xcvr_index}")
                        xcvr['tx_power_dbm'] = round(int(tx_dbm) / 10000.0, 2) if tx_dbm else None
                    except:
                        xcvr['tx_power_dbm'] = None
                    
                    # Get LOS state (1=true, 2=false for TruthValue)
                    try:
                        los = self._snmp_get(f"{WWP_OIDS['xcvr']['los_state']}.{xcvr_index}")
                        xcvr['los'] = (int(los) == 1) if los else False
                    except:
                        xcvr['los'] = None
                    
                    xcvrs.append(xcvr)
                    
                except Exception as e:
                    logger.debug(f"Error processing transceiver {xcvr_index}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to get transceivers from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get transceivers: {e}")
        
        return xcvrs
    
    def get_port_stats(self) -> List[Dict]:
        """Get port traffic statistics via SNMP."""
        stats = {}
        
        try:
            # Walk rx_bytes to get all port indices
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['rx_bytes']):
                idx = oid.split('.')[-1]
                if idx not in stats:
                    stats[idx] = {'port_id': int(idx), 'host': self.host}
                stats[idx]['rx_bytes'] = int(val) if val else 0
            
            # Walk other stats
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['rx_pkts']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['rx_pkts'] = int(val) if val else 0
            
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['tx_bytes']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['tx_bytes'] = int(val) if val else 0
            
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['tx_pkts']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['tx_pkts'] = int(val) if val else 0
            
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['rx_crc_errors']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['rx_crc_errors'] = int(val) if val else 0
            
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['rx_errors']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['rx_errors'] = int(val) if val else 0
            
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['rx_discard']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['rx_discards'] = int(val) if val else 0
            
            for oid, val in self._snmp_walk(WWP_OIDS['port_stats']['link_flap_count']):
                idx = oid.split('.')[-1]
                if idx in stats:
                    stats[idx]['link_flaps'] = int(val) if val else 0
                    
        except Exception as e:
            logger.error(f"Failed to get port stats from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get port stats: {e}")
        
        return list(stats.values())
    
    def get_chassis_health(self) -> Dict:
        """Get chassis health info (power, fans, temperature)."""
        health = {
            'host': self.host,
            'power_supplies': [],
            'fans': [],
            'temperatures': [],
        }
        
        try:
            # Power supplies
            psu_states = {}
            for oid, val in self._snmp_walk(WWP_OIDS['power_supply']['state']):
                idx = oid.split('.')[-1]
                psu_states[idx] = {
                    'id': int(idx),
                    'state': POWER_SUPPLY_STATE.get(int(val), 'unknown') if val else 'unknown'
                }
            health['power_supplies'] = list(psu_states.values())
            
            # Fans
            fan_data = {}
            for oid, val in self._snmp_walk(WWP_OIDS['fan']['status']):
                idx = oid.split('.')[-1]
                fan_data[idx] = {
                    'id': int(idx),
                    'status': FAN_STATUS.get(int(val), 'unknown') if val else 'unknown'
                }
            for oid, val in self._snmp_walk(WWP_OIDS['fan']['current_speed']):
                idx = oid.split('.')[-1]
                if idx in fan_data:
                    fan_data[idx]['speed_rpm'] = int(val) if val else 0
            health['fans'] = list(fan_data.values())
            
            # Temperature sensors
            temp_data = {}
            for oid, val in self._snmp_walk(WWP_OIDS['temp_sensor']['value']):
                idx = oid.split('.')[-1]
                temp_data[idx] = {
                    'id': int(idx),
                    'temperature_c': int(val) if val else None
                }
            for oid, val in self._snmp_walk(WWP_OIDS['temp_sensor']['state']):
                idx = oid.split('.')[-1]
                if idx in temp_data:
                    temp_data[idx]['state'] = TEMP_SENSOR_STATE.get(int(val), 'unknown') if val else 'unknown'
            for oid, val in self._snmp_walk(WWP_OIDS['temp_sensor']['high_threshold']):
                idx = oid.split('.')[-1]
                if idx in temp_data:
                    temp_data[idx]['high_threshold'] = int(val) if val else None
            health['temperatures'] = list(temp_data.values())
            
        except Exception as e:
            logger.error(f"Failed to get chassis health from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get chassis health: {e}")
        
        return health
    
    def get_lag_status(self) -> List[Dict]:
        """Get LAG/Link Aggregation status via SNMP."""
        lags = {}
        
        try:
            # Walk LAG names
            for oid, val in self._snmp_walk(WWP_OIDS['lag']['name']):
                idx = oid.split('.')[-1]
                lags[idx] = {
                    'id': int(idx),
                    'name': str(val).strip() if val else f'LAG-{idx}',
                    'host': self.host
                }
            
            # Get oper state
            for oid, val in self._snmp_walk(WWP_OIDS['lag']['oper_state']):
                idx = oid.split('.')[-1]
                if idx in lags:
                    lags[idx]['oper_state'] = 'up' if val and int(val) == 1 else 'down'
            
            # Get admin state
            for oid, val in self._snmp_walk(WWP_OIDS['lag']['admin_state']):
                idx = oid.split('.')[-1]
                if idx in lags:
                    lags[idx]['admin_state'] = 'enabled' if val and int(val) == 1 else 'disabled'
            
            # Get mode
            for oid, val in self._snmp_walk(WWP_OIDS['lag']['mode']):
                idx = oid.split('.')[-1]
                if idx in lags:
                    lags[idx]['mode'] = LAG_MODE.get(int(val), 'unknown') if val else 'unknown'
            
            # Get member count
            for oid, val in self._snmp_walk(WWP_OIDS['lag']['member_count']):
                idx = oid.split('.')[-1]
                if idx in lags:
                    lags[idx]['member_count'] = int(val) if val else 0
                    
        except Exception as e:
            logger.error(f"Failed to get LAG status from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get LAG status: {e}")
        
        return list(lags.values())
    
    def get_mstp_status(self) -> Dict:
        """Get MSTP/Spanning Tree status via SNMP."""
        mstp = {
            'host': self.host,
            'enabled': False,
            'version': 'unknown',
            'ports': []
        }
        
        try:
            # Get global MSTP state
            try:
                enabled = self._snmp_get(WWP_OIDS['mstp']['enabled'])
                mstp['enabled'] = bool(int(enabled)) if enabled else False
            except:
                pass
            
            # Get force version
            try:
                version = self._snmp_get(WWP_OIDS['mstp']['force_version'])
                version_map = {0: 'STP', 2: 'RSTP', 3: 'MSTP'}
                mstp['version'] = version_map.get(int(version), 'unknown') if version else 'unknown'
            except:
                pass
            
            # Get port states
            port_data = {}
            for oid, val in self._snmp_walk(WWP_OIDS['mstp']['port_state']):
                parts = oid.split('.')
                port_idx = parts[-1]
                port_data[port_idx] = {
                    'port_id': int(port_idx),
                    'state': MSTP_PORT_STATE.get(int(val), 'unknown') if val else 'unknown'
                }
            
            for oid, val in self._snmp_walk(WWP_OIDS['mstp']['port_role']):
                parts = oid.split('.')
                port_idx = parts[-1]
                if port_idx in port_data:
                    port_data[port_idx]['role'] = MSTP_PORT_ROLE.get(int(val), 'unknown') if val else 'unknown'
            
            mstp['ports'] = list(port_data.values())
            
        except Exception as e:
            logger.error(f"Failed to get MSTP status from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get MSTP status: {e}")
        
        return mstp
    
    def get_ntp_status(self) -> Dict:
        """Get NTP synchronization status via SNMP."""
        ntp = {
            'host': self.host,
            'admin_state': 'unknown',
            'oper_state': 'unknown',
            'sync_status': 'unknown'
        }
        
        try:
            try:
                admin = self._snmp_get(WWP_OIDS['ntp']['admin_state'])
                ntp['admin_state'] = 'enabled' if admin and int(admin) == 1 else 'disabled'
            except:
                pass
            
            try:
                oper = self._snmp_get(WWP_OIDS['ntp']['oper_state'])
                ntp['oper_state'] = 'enabled' if oper and int(oper) == 1 else 'disabled'
            except:
                pass
            
            try:
                sync = self._snmp_get(WWP_OIDS['ntp']['sync_status'])
                ntp['sync_status'] = NTP_SYNC_STATUS.get(int(sync), 'unknown') if sync else 'unknown'
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to get NTP status from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get NTP status: {e}")
        
        return ntp
    
    def get_cfm_status(self) -> Dict:
        """Get CFM/Ethernet OAM status via SNMP."""
        cfm = {
            'host': self.host,
            'global_state': 'unknown',
            'meps': []
        }
        
        try:
            # Get global CFM state
            try:
                state = self._snmp_get(WWP_OIDS['cfm']['global_state'])
                cfm['global_state'] = 'enabled' if state and int(state) == 1 else 'disabled'
            except:
                pass
            
            # Get MEP operational states
            mep_data = {}
            for oid, val in self._snmp_walk(WWP_OIDS['cfm']['mep_oper_state']):
                idx = oid.replace(WWP_OIDS['cfm']['mep_oper_state'] + '.', '')
                mep_data[idx] = {
                    'index': idx,
                    'oper_state': CFM_MEP_OPER_STATE.get(int(val), 'unknown') if val else 'unknown'
                }
            
            # Get MEP CCM state
            for oid, val in self._snmp_walk(WWP_OIDS['cfm']['mep_ccm_state']):
                idx = oid.replace(WWP_OIDS['cfm']['mep_ccm_state'] + '.', '')
                if idx in mep_data:
                    mep_data[idx]['ccm_state'] = 'enabled' if val and int(val) == 1 else 'disabled'
            
            # Get MEP defects
            for oid, val in self._snmp_walk(WWP_OIDS['cfm']['mep_defects']):
                idx = oid.replace(WWP_OIDS['cfm']['mep_defects'] + '.', '')
                if idx in mep_data:
                    mep_data[idx]['defects'] = int(val) if val else 0
            
            cfm['meps'] = list(mep_data.values())
            
        except Exception as e:
            logger.error(f"Failed to get CFM status from {self.host}: {e}")
            raise CienaSNMPError(f"Failed to get CFM status: {e}")
        
        return cfm
    
    def test_connection(self) -> Dict:
        """Test SNMP connectivity to the switch."""
        try:
            sys_name = self._snmp_get(CIENA_OIDS['system']['name'])
            sys_descr = self._snmp_get(CIENA_OIDS['system']['descr'])
            
            return {
                'success': True,
                'host': self.host,
                'name': str(sys_name) if sys_name else None,
                'description': str(sys_descr) if sys_descr else None,
            }
        except Exception as e:
            return {
                'success': False,
                'host': self.host,
                'error': str(e),
            }


def poll_switch(host: str, community: str = 'public') -> Dict:
    """
    Poll a single Ciena switch for all relevant data.
    
    Args:
        host: Switch IP address
        community: SNMP community string
        
    Returns:
        Dict with system info, rings, and alarms
    """
    service = CienaSNMPService(host, community)
    
    result = {
        'host': host,
        'success': False,
        'system': None,
        'raps_global': None,
        'virtual_rings': [],
        'active_alarms': [],
        'error': None,
    }
    
    try:
        result['system'] = service.get_system_info()
        result['success'] = True
    except Exception as e:
        result['error'] = f"System info failed: {e}"
        return result
    
    try:
        result['raps_global'] = service.get_raps_global()
    except Exception as e:
        logger.warning(f"RAPS global failed for {host}: {e}")
    
    try:
        result['virtual_rings'] = service.get_virtual_rings()
    except Exception as e:
        logger.warning(f"Virtual rings failed for {host}: {e}")
    
    try:
        result['active_alarms'] = service.get_active_alarms()
    except Exception as e:
        logger.warning(f"Active alarms failed for {host}: {e}")
    
    return result


def poll_multiple_switches(hosts: List[str], community: str = 'public') -> List[Dict]:
    """
    Poll multiple Ciena switches.
    
    Args:
        hosts: List of switch IP addresses
        community: SNMP community string
        
    Returns:
        List of poll results
    """
    results = []
    for host in hosts:
        try:
            result = poll_switch(host, community)
            results.append(result)
        except Exception as e:
            results.append({
                'host': host,
                'success': False,
                'error': str(e),
            })
    return results
