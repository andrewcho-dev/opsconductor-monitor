"""
SNMP Trap Receiver Connector

Listens for SNMP traps on UDP port 162.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from connectors.base import BaseConnector, BaseNormalizer
from core.models import NormalizedAlert, ConnectorStatus
from core.alert_manager import get_alert_manager

from .normalizer import SNMPNormalizer

logger = logging.getLogger(__name__)


class SNMPTrapConnector(BaseConnector):
    """
    SNMP Trap receiver connector.
    
    Listens on UDP 162 for incoming SNMP traps.
    Uses pysnmp for decoding trap PDUs.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bind_address = config.get("bind_address", "0.0.0.0")
        self.port = config.get("port", 162)
        self.community = config.get("community", "public")
        self._transport = None
        self._protocol = None
        self._running = False
    
    @property
    def connector_type(self) -> str:
        return "snmp_trap"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return SNMPNormalizer()
    
    async def start(self) -> None:
        """Start the SNMP trap receiver."""
        if self._running:
            return
        
        try:
            # Create UDP server
            loop = asyncio.get_event_loop()
            
            self._transport, self._protocol = await loop.create_datagram_endpoint(
                lambda: SNMPTrapProtocol(self),
                local_addr=(self.bind_address, self.port)
            )
            
            self._running = True
            self.enabled = True
            self.set_status(ConnectorStatus.CONNECTED)
            
            logger.info(f"SNMP trap receiver started on {self.bind_address}:{self.port}")
            
        except PermissionError:
            error = f"Permission denied for port {self.port}. Try running as root or use port > 1024."
            self.set_status(ConnectorStatus.ERROR, error)
            logger.error(error)
            raise
        except Exception as e:
            self.set_status(ConnectorStatus.ERROR, str(e))
            logger.exception("Failed to start SNMP trap receiver")
            raise
    
    async def stop(self) -> None:
        """Stop the SNMP trap receiver."""
        self._running = False
        self.enabled = False
        
        if self._transport:
            self._transport.close()
            self._transport = None
        
        self.set_status(ConnectorStatus.DISCONNECTED)
        logger.info("SNMP trap receiver stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test if we can bind to the port."""
        try:
            # Try to create a test socket
            import socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.bind((self.bind_address, self.port))
            test_socket.close()
            
            return {
                "success": True,
                "message": f"Can bind to {self.bind_address}:{self.port}",
                "details": {
                    "port": self.port,
                    "address": self.bind_address
                }
            }
        except PermissionError:
            return {
                "success": False,
                "message": f"Permission denied for port {self.port}",
                "details": None
            }
        except OSError as e:
            if "Address already in use" in str(e):
                # Port is in use, which might mean we're already running
                if self._running:
                    return {
                        "success": True,
                        "message": "Trap receiver is running",
                        "details": {"port": self.port}
                    }
                return {
                    "success": False,
                    "message": f"Port {self.port} already in use",
                    "details": None
                }
            return {
                "success": False,
                "message": str(e),
                "details": None
            }
    
    async def process_trap(self, source_addr: Tuple[str, int], data: bytes) -> None:
        """
        Process incoming SNMP trap.
        
        Args:
            source_addr: (IP, port) tuple
            data: Raw trap data
        """
        try:
            # Decode the trap
            trap_data = self._decode_trap(source_addr[0], data)
            
            if trap_data:
                # Normalize
                normalized = self.normalizer.normalize(trap_data)
                
                logger.info(f"SNMP trap from {source_addr[0]}: {normalized.alert_type}")
                
                # Process through alert manager
                alert_manager = get_alert_manager()
                await alert_manager.process_alert(normalized)
                
                self.increment_alerts()
                self.last_poll_at = datetime.utcnow()
                
        except Exception as e:
            logger.exception(f"Error processing SNMP trap from {source_addr[0]}")
    
    def _decode_trap(self, source_ip: str, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode SNMP trap PDU.
        
        Returns dict with trap_oid, enterprise_oid, varbinds.
        """
        try:
            # Try using pysnmp if available
            return self._decode_with_pysnmp(source_ip, data)
        except ImportError:
            # Fallback to basic decoding
            return self._decode_basic(source_ip, data)
        except Exception as e:
            logger.warning(f"Failed to decode trap: {e}")
            return None
    
    def _decode_with_pysnmp(self, source_ip: str, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode trap using pysnmp library."""
        from pysnmp.proto import api
        from pysnmp.proto.rfc1902 import ObjectName
        from pysnmp import debug
        
        # Try v2c first, then v1
        for version in [api.protoVersion2c, api.protoVersion1]:
            try:
                proto_module = api.protoModules[version]
                req_msg, _ = proto_module.apiMessage.getDecoder()(data)
                
                # Get PDU
                req_pdu = proto_module.apiMessage.getPDU(req_msg)
                
                if version == api.protoVersion2c:
                    # SNMPv2c trap
                    trap_oid = None
                    varbinds = {}
                    
                    for oid, val in proto_module.apiPDU.getVarBinds(req_pdu):
                        oid_str = str(oid)
                        val_str = str(val) if val else ""
                        
                        # snmpTrapOID
                        if oid_str == "1.3.6.1.6.3.1.1.4.1.0":
                            trap_oid = val_str
                        else:
                            varbinds[oid_str] = val_str
                    
                    return {
                        "source_ip": source_ip,
                        "trap_oid": trap_oid or "",
                        "enterprise_oid": "",
                        "varbinds": varbinds,
                        "timestamp": datetime.utcnow(),
                        "version": "v2c"
                    }
                else:
                    # SNMPv1 trap
                    enterprise = str(proto_module.apiTrapPDU.getEnterprise(req_pdu))
                    generic_trap = proto_module.apiTrapPDU.getGenericTrap(req_pdu)
                    specific_trap = proto_module.apiTrapPDU.getSpecificTrap(req_pdu)
                    
                    # Build trap OID
                    if generic_trap < 6:
                        # Standard trap
                        trap_oid = f"1.3.6.1.6.3.1.1.5.{generic_trap + 1}"
                    else:
                        # Enterprise-specific trap
                        trap_oid = f"{enterprise}.0.{specific_trap}"
                    
                    varbinds = {}
                    for oid, val in proto_module.apiTrapPDU.getVarBinds(req_pdu):
                        varbinds[str(oid)] = str(val) if val else ""
                    
                    return {
                        "source_ip": source_ip,
                        "trap_oid": trap_oid,
                        "enterprise_oid": enterprise,
                        "varbinds": varbinds,
                        "timestamp": datetime.utcnow(),
                        "version": "v1"
                    }
                    
            except Exception:
                continue
        
        return None
    
    def _decode_basic(self, source_ip: str, data: bytes) -> Optional[Dict[str, Any]]:
        """Basic trap decoding without pysnmp."""
        # Very basic - just capture that we got something
        return {
            "source_ip": source_ip,
            "trap_oid": "unknown",
            "enterprise_oid": "",
            "varbinds": {"raw_data": data.hex()[:200]},
            "timestamp": datetime.utcnow(),
            "version": "unknown"
        }


class SNMPTrapProtocol(asyncio.DatagramProtocol):
    """Asyncio protocol for receiving SNMP traps."""
    
    def __init__(self, connector: SNMPTrapConnector):
        self.connector = connector
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming UDP datagram."""
        # Schedule trap processing
        asyncio.create_task(self.connector.process_trap(addr, data))
    
    def error_received(self, exc):
        logger.error(f"SNMP trap receiver error: {exc}")


# Register the connector
from connectors.registry import register_connector
register_connector("snmp_trap", SNMPTrapConnector)
