"""
SNMP Trap Receiver Connector

Listens for SNMP traps on UDP port 162.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from backend.connectors.base import BaseConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

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
            # Create UDP server with SO_REUSEPORT for multi-worker support
            # This allows multiple uvicorn workers to share the same UDP port
            # The kernel load-balances incoming packets across workers using a hash
            loop = asyncio.get_event_loop()
            
            self._transport, self._protocol = await loop.create_datagram_endpoint(
                lambda: SNMPTrapProtocol(self),
                local_addr=(self.bind_address, self.port),
                reuse_port=True  # Enable SO_REUSEPORT for multi-worker load balancing
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
        """Decode trap using pysnmp library (v7 API with snake_case methods)."""
        from pysnmp.proto.api import v1, v2c, decodeMessageVersion
        from pyasn1.codec.ber import decoder as ber_decoder
        
        try:
            # Determine SNMP version
            version = decodeMessageVersion(data)
            
            trap_oid = ""
            enterprise_oid = ""
            varbinds = {}
            community = ""
            
            if version == 1:  # SNMPv2c
                msg, _ = ber_decoder.decode(data, asn1Spec=v2c.Message())
                community = str(msg["community"])
                pdu = v2c.apiMessage.get_pdu(msg)
                
                for oid, val in v2c.apiPDU.get_varbinds(pdu):
                    oid_str = str(oid)
                    val_str = val.prettyPrint() if hasattr(val, 'prettyPrint') else str(val)
                    
                    # snmpTrapOID.0
                    if oid_str == "1.3.6.1.6.3.1.1.4.1.0":
                        trap_oid = val_str
                    else:
                        varbinds[oid_str] = val_str
                
                return {
                    "source_ip": source_ip,
                    "trap_oid": trap_oid,
                    "enterprise_oid": enterprise_oid,
                    "varbinds": varbinds,
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "v2c",
                    "community": community
                }
            
            elif version == 0:  # SNMPv1
                msg, _ = ber_decoder.decode(data, asn1Spec=v1.Message())
                community = str(msg["community"])
                pdu = v1.apiMessage.get_pdu(msg)
                
                # Get trap-specific fields
                enterprise_oid = str(v1.apiTrapPDU.get_enterprise(pdu))
                generic_trap = int(v1.apiTrapPDU.get_generic_trap(pdu))
                specific_trap = int(v1.apiTrapPDU.get_specific_trap(pdu))
                
                # Build trap OID
                if generic_trap < 6:
                    trap_oid = f"1.3.6.1.6.3.1.1.5.{generic_trap + 1}"
                else:
                    trap_oid = f"{enterprise_oid}.0.{specific_trap}"
                
                for oid, val in v1.apiTrapPDU.get_varbinds(pdu):
                    oid_str = str(oid)
                    val_str = val.prettyPrint() if hasattr(val, 'prettyPrint') else str(val)
                    varbinds[oid_str] = val_str
                
                return {
                    "source_ip": source_ip,
                    "trap_oid": trap_oid,
                    "enterprise_oid": enterprise_oid,
                    "varbinds": varbinds,
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "v1",
                    "community": community
                }
            
        except Exception as e:
            logger.debug(f"pysnmp decode failed: {e}")
        
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
