"""
SNMP Trap Receiver

Listen for SNMP traps on UDP 162, dispatch to parser based on OID → addon mapping.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SNMPTrap:
    """Parsed SNMP trap data."""
    source_ip: str
    source_port: int
    trap_oid: str
    enterprise_oid: str
    varbinds: Dict[str, Any]
    timestamp: datetime
    raw_data: bytes


class TrapReceiver:
    """
    SNMP Trap Receiver.
    
    Listens on UDP port 162 for incoming traps, parses them,
    looks up the addon by enterprise OID, and processes through alert engine.
    
    Usage:
        receiver = TrapReceiver(port=162)
        await receiver.start()
        # ... runs until stopped
        await receiver.stop()
    """
    
    def __init__(self, port: int = 162, community: str = 'public'):
        self.port = port
        self.community = community
        self._transport = None
        self._protocol = None
        self._running = False
        self._stats = {
            'traps_received': 0,
            'traps_processed': 0,
            'traps_dropped': 0,
            'errors': 0,
        }
    
    async def start(self) -> None:
        """Start the trap receiver."""
        if self._running:
            logger.warning("Trap receiver already running")
            return
        
        loop = asyncio.get_event_loop()
        
        # Create UDP endpoint
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: TrapProtocol(self),
            local_addr=('0.0.0.0', self.port)
        )
        
        self._running = True
        logger.info(f"SNMP trap receiver started on UDP port {self.port}")
    
    async def stop(self) -> None:
        """Stop the trap receiver."""
        if self._transport:
            self._transport.close()
            self._transport = None
            self._protocol = None
        
        self._running = False
        logger.info("SNMP trap receiver stopped")
    
    async def handle_trap(self, trap: SNMPTrap) -> None:
        """
        Handle incoming trap - lookup addon, parse, process.
        """
        from .addon_registry import get_registry
        from .parser import get_parser
        from .alert_engine import get_engine
        
        self._stats['traps_received'] += 1
        
        try:
            # Find addon by enterprise OID
            registry = get_registry()
            addon = registry.find_by_oid(trap.enterprise_oid)
            
            if not addon:
                # Try matching by full trap OID
                addon = registry.find_by_oid(trap.trap_oid)
            
            if not addon:
                logger.debug(f"No addon for OID {trap.enterprise_oid}, dropping trap")
                self._stats['traps_dropped'] += 1
                return
            
            # Prepare data for parser
            trap_data = {
                'source_ip': trap.source_ip,
                'trap_oid': trap.trap_oid,
                'enterprise_oid': trap.enterprise_oid,
                'varbinds': trap.varbinds,
                'timestamp': trap.timestamp.isoformat(),
            }
            
            # Check if this is a clear OID
            trap_definitions = addon.manifest.get('snmp_trap', {}).get('trap_definitions', {})
            is_clear = False
            for oid, defn in trap_definitions.items():
                clear_oid = defn.get('clear_oid')
                if clear_oid and trap.trap_oid == clear_oid:
                    is_clear = True
                    break
            
            trap_data['_is_clear'] = is_clear
            
            # Parse through addon rules
            parser = get_parser()
            parsed = parser.parse(trap_data, addon.manifest, addon.id)
            
            if not parsed:
                logger.warning(f"Failed to parse trap from {trap.source_ip}")
                self._stats['errors'] += 1
                return
            
            # Process through alert engine
            engine = get_engine()
            alert = await engine.process(parsed, addon)
            
            self._stats['traps_processed'] += 1
            logger.debug(f"Processed trap → alert {alert.id}")
            
        except Exception as e:
            logger.error(f"Error handling trap: {e}")
            self._stats['errors'] += 1
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get receiver statistics."""
        return self._stats.copy()
    
    @property
    def is_running(self) -> bool:
        """Check if receiver is running."""
        return self._running


class TrapProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for SNMP traps."""
    
    def __init__(self, receiver: TrapReceiver):
        self.receiver = receiver
    
    def datagram_received(self, data: bytes, addr: tuple) -> None:
        """Handle incoming UDP datagram."""
        source_ip, source_port = addr
        
        try:
            trap = self._parse_trap(data, source_ip, source_port)
            if trap:
                asyncio.create_task(self.receiver.handle_trap(trap))
        except Exception as e:
            logger.error(f"Error parsing trap from {source_ip}: {e}")
    
    def _parse_trap(self, data: bytes, source_ip: str, source_port: int) -> Optional[SNMPTrap]:
        """Parse SNMP trap from raw bytes using pysnmp."""
        try:
            from pysnmp.hlapi import SnmpEngine
            from pysnmp.proto import api
            from pyasn1.codec.ber import decoder
            
            # Decode the message
            msg_version = api.decodeMessageVersion(data)
            
            if msg_version in api.protoModules:
                proto_module = api.protoModules[msg_version]
            else:
                logger.warning(f"Unsupported SNMP version: {msg_version}")
                return None
            
            req_msg, _ = decoder.decode(data, asn1Spec=proto_module.Message())
            req_pdu = proto_module.apiMessage.getPDU(req_msg)
            
            # Extract trap info
            if req_pdu.isSameTypeWith(proto_module.TrapPDU()):
                # SNMPv1 trap
                enterprise = proto_module.apiTrapPDU.getEnterprise(req_pdu).prettyPrint()
                trap_type = proto_module.apiTrapPDU.getGenericTrap(req_pdu)
                specific_trap = proto_module.apiTrapPDU.getSpecificTrap(req_pdu)
                
                # Build trap OID
                if trap_type == 6:  # Enterprise specific
                    trap_oid = f"{enterprise}.0.{specific_trap}"
                else:
                    trap_oid = f"1.3.6.1.6.3.1.1.5.{trap_type + 1}"
                
                # Extract varbinds
                varbinds = {}
                for oid, val in proto_module.apiTrapPDU.getVarBinds(req_pdu):
                    varbinds[oid.prettyPrint()] = val.prettyPrint()
                
                return SNMPTrap(
                    source_ip=source_ip,
                    source_port=source_port,
                    trap_oid=trap_oid,
                    enterprise_oid=enterprise,
                    varbinds=varbinds,
                    timestamp=datetime.utcnow(),
                    raw_data=data
                )
            
            elif hasattr(proto_module, 'SNMPv2TrapPDU') and req_pdu.isSameTypeWith(proto_module.SNMPv2TrapPDU()):
                # SNMPv2c trap
                varbinds = {}
                trap_oid = ''
                
                for oid, val in proto_module.apiPDU.getVarBinds(req_pdu):
                    oid_str = oid.prettyPrint()
                    val_str = val.prettyPrint()
                    varbinds[oid_str] = val_str
                    
                    # snmpTrapOID.0
                    if oid_str == '1.3.6.1.6.3.1.1.4.1.0':
                        trap_oid = val_str
                
                # Extract enterprise OID (first part of trap OID)
                enterprise_oid = '.'.join(trap_oid.split('.')[:-2]) if trap_oid else ''
                
                return SNMPTrap(
                    source_ip=source_ip,
                    source_port=source_port,
                    trap_oid=trap_oid,
                    enterprise_oid=enterprise_oid,
                    varbinds=varbinds,
                    timestamp=datetime.utcnow(),
                    raw_data=data
                )
            
        except ImportError:
            logger.error("pysnmp not installed - cannot parse SNMP traps")
            return None
        except Exception as e:
            logger.error(f"Trap parse error: {e}")
            return None
        
        return None


# Global receiver instance
_receiver: Optional[TrapReceiver] = None


def get_receiver() -> TrapReceiver:
    """Get global trap receiver instance."""
    global _receiver
    if _receiver is None:
        _receiver = TrapReceiver()
    return _receiver


async def start_receiver(port: int = 162) -> TrapReceiver:
    """Start the global trap receiver."""
    receiver = get_receiver()
    receiver.port = port
    await receiver.start()
    return receiver


async def stop_receiver() -> None:
    """Stop the global trap receiver."""
    if _receiver:
        await _receiver.stop()
