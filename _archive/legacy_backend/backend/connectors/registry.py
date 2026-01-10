"""
OpsConductor Connector Registry

Registry of all available connector types.
"""

import logging
from typing import Dict, Type, Optional

from .base import BaseConnector

logger = logging.getLogger(__name__)

# Import connector classes
from .prtg import PRTGConnector
from .mcp import MCPConnector
from .snmp import SNMPTrapConnector
from .eaton import EatonConnector
from .eaton.rest_connector import EatonRESTConnector
from .axis import AxisConnector
from .milestone import MilestoneConnector
from .cradlepoint import CradlepointConnector
from .siklu import SikluConnector
from .ubiquiti import UbiquitiConnector
from .cisco_asa import CiscoASAConnector

# Registry of connector classes
_CONNECTOR_REGISTRY: Dict[str, Type[BaseConnector]] = {
    "prtg": PRTGConnector,
    "mcp": MCPConnector,
    "snmp_trap": SNMPTrapConnector,
    "snmp_poll": SNMPTrapConnector,  # Reuse for now
    "eaton": EatonConnector,
    "eaton_rest": EatonRESTConnector,
    "axis": AxisConnector,
    "milestone": MilestoneConnector,
    "cradlepoint": CradlepointConnector,
    "siklu": SikluConnector,
    "ubiquiti": UbiquitiConnector,
    "cisco_asa": CiscoASAConnector,
}

# List of all connector types (for UI display)
CONNECTOR_TYPES = [
    {
        "type": "prtg",
        "name": "PRTG Network Monitor",
        "description": "Paessler PRTG monitoring alerts via webhook and API",
        "supports_webhook": True,
        "supports_polling": True,
    },
    {
        "type": "mcp",
        "name": "Ciena MCP",
        "description": "Ciena Management Control Plane alarms",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "snmp_trap",
        "name": "SNMP Traps",
        "description": "Universal SNMP trap receiver (UDP 162)",
        "supports_webhook": False,
        "supports_polling": False,
    },
    {
        "type": "snmp_poll",
        "name": "SNMP Polling",
        "description": "Active SNMP polling for device status",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "eaton",
        "name": "Eaton UPS (SNMP)",
        "description": "Eaton UPS monitoring via SNMP (XUPS-MIB)",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "eaton_rest",
        "name": "Eaton UPS (REST API)",
        "description": "Eaton Network-M2 card alarms via REST API",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "axis",
        "name": "Axis Cameras",
        "description": "Axis camera events via VAPIX API",
        "supports_webhook": True,
        "supports_polling": True,
    },
    {
        "type": "milestone",
        "name": "Milestone VMS",
        "description": "Milestone XProtect VMS events",
        "supports_webhook": True,
        "supports_polling": True,
    },
    {
        "type": "cradlepoint",
        "name": "Cradlepoint",
        "description": "Cradlepoint router status via NCOS API",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "siklu",
        "name": "Siklu Radios",
        "description": "Siklu EtherHaul radio link monitoring",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "ubiquiti",
        "name": "Ubiquiti UISP",
        "description": "Ubiquiti device monitoring via UISP API",
        "supports_webhook": False,
        "supports_polling": True,
    },
    {
        "type": "cisco_asa",
        "name": "Cisco ASA",
        "description": "Cisco ASA firewall monitoring via SSH/CLI (IPSec VPN, system health)",
        "supports_webhook": False,
        "supports_polling": True,
    },
]


def register_connector(connector_type: str, connector_class: Type[BaseConnector]) -> None:
    """
    Register a connector class.
    
    Args:
        connector_type: Type identifier (e.g., 'prtg')
        connector_class: Connector class to register
    """
    _CONNECTOR_REGISTRY[connector_type] = connector_class
    logger.info(f"Registered connector: {connector_type}")


def get_connector_class(connector_type: str) -> Optional[Type[BaseConnector]]:
    """
    Get connector class by type.
    
    Args:
        connector_type: Type identifier
        
    Returns:
        Connector class or None if not found
    """
    return _CONNECTOR_REGISTRY.get(connector_type)


def get_connector_info(connector_type: str) -> Optional[Dict]:
    """
    Get connector type info.
    
    Args:
        connector_type: Type identifier
        
    Returns:
        Connector info dict or None
    """
    for info in CONNECTOR_TYPES:
        if info["type"] == connector_type:
            return info
    return None


def list_registered_connectors() -> list:
    """
    List all registered connector types.
    
    Returns:
        List of registered type identifiers
    """
    return list(_CONNECTOR_REGISTRY.keys())


def create_connector(connector_type: str, config: Dict) -> Optional[BaseConnector]:
    """
    Create a connector instance.
    
    Args:
        connector_type: Type identifier
        config: Connector configuration
        
    Returns:
        Connector instance or None if type not found
    """
    connector_class = get_connector_class(connector_type)
    if connector_class is None:
        logger.warning(f"Unknown connector type: {connector_type}")
        return None
    
    return connector_class(config)
