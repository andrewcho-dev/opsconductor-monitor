#!/usr/bin/env python3
"""
Universal SNMP Trap Receiver for OpsConductor Monitor.

Handles SNMP traps from all network devices (Ciena, Cisco, Juniper, Linux, etc.)
with async processing, vendor-specific handlers, and alarm correlation.
"""

import asyncio
import logging
import os
import signal
import sys
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

# pysnmp imports
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.smi import builder, view, compiler, rfc1902
from pysnmp.proto.api import v2c

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('snmp_trap_receiver')


@dataclass
class DecodedTrap:
    """Structured representation of a decoded SNMP trap."""
    received_at: datetime
    source_ip: str
    source_port: int
    snmp_version: str
    community: str
    enterprise_oid: str
    trap_oid: str
    generic_trap: int
    specific_trap: int
    uptime: int
    varbinds: Dict[str, Any]
    raw_hex: str = ""


@dataclass
class TrapEvent:
    """Normalized event extracted from a trap."""
    event_type: str
    source_ip: str
    device_name: Optional[str]
    severity: str
    object_type: Optional[str]
    object_id: Optional[str]
    description: str
    details: Dict[str, Any]
    alarm_id: Optional[str] = None
    is_clear: bool = False


class TrapRouter:
    """Routes traps to appropriate vendor handlers based on OID."""
    
    # Enterprise OID prefixes for vendor identification
    VENDOR_OIDS = {
        '1.3.6.1.4.1.6141': 'ciena',      # Ciena WWP (SAOS)
        '1.3.6.1.4.1.1271': 'ciena',      # Ciena CES
        '1.3.6.1.4.1.9': 'cisco',          # Cisco
        '1.3.6.1.4.1.2636': 'juniper',     # Juniper
        '1.3.6.1.4.1.8072': 'linux',       # Net-SNMP (Linux)
        '1.3.6.1.4.1.2021': 'linux',       # UCD-SNMP (Linux)
        '1.3.6.1.4.1.11': 'hp',            # HP
        '1.3.6.1.4.1.674': 'dell',         # Dell
    }
    
    # Standard trap OIDs (RFC 1157, RFC 3418)
    STANDARD_TRAPS = {
        '1.3.6.1.6.3.1.1.5.1': 'coldStart',
        '1.3.6.1.6.3.1.1.5.2': 'warmStart',
        '1.3.6.1.6.3.1.1.5.3': 'linkDown',
        '1.3.6.1.6.3.1.1.5.4': 'linkUp',
        '1.3.6.1.6.3.1.1.5.5': 'authenticationFailure',
        '1.3.6.1.6.3.1.1.5.6': 'egpNeighborLoss',
    }
    
    def route(self, trap: DecodedTrap) -> str:
        """Determine which handler should process this trap."""
        # Check enterprise OID for vendor
        for prefix, vendor in self.VENDOR_OIDS.items():
            if trap.enterprise_oid and trap.enterprise_oid.startswith(prefix):
                return vendor
            if trap.trap_oid and trap.trap_oid.startswith(prefix):
                return vendor
        
        # Check trap OID for standard traps
        if trap.trap_oid in self.STANDARD_TRAPS:
            return 'standard'
        
        return 'generic'


class CienaTrapHandler:
    """Handler for Ciena SAOS traps with alarm correlation."""
    
    # Ciena-specific trap OIDs (WWP-LEOS MIBs)
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
        '1.3.6.1.4.1.6141.2.60.6.0.2': 'cfmDefectCleared',
        # Standard link traps
        '1.3.6.1.6.3.1.1.5.3': 'linkDown',
        '1.3.6.1.6.3.1.1.5.4': 'linkUp',
    }
    
    # Severity mapping from Ciena alarm severity values
    SEVERITY_MAP = {
        1: 'critical',
        2: 'major', 
        3: 'minor',
        4: 'warning',
        5: 'info',
        6: 'cleared',
    }
    
    # Varbind OIDs for alarm details
    ALARM_VARBINDS = {
        '1.3.6.1.4.1.6141.2.60.5.1.1.1': 'alarm_object',
        '1.3.6.1.4.1.6141.2.60.5.1.1.2': 'alarm_severity',
        '1.3.6.1.4.1.6141.2.60.5.1.1.3': 'alarm_description',
        '1.3.6.1.4.1.6141.2.60.5.1.1.4': 'alarm_time',
        '1.3.6.1.4.1.6141.2.60.5.1.1.5': 'alarm_id',
    }
    
    def handle(self, trap: DecodedTrap) -> Optional[TrapEvent]:
        """Process Ciena trap and return normalized event."""
        trap_type = self._get_trap_type(trap.trap_oid)
        
        if trap_type in ('alarmRaised', 'alarmCleared'):
            return self._handle_alarm(trap, trap_type)
        elif trap_type in ('portLinkUp', 'portLinkDown', 'linkUp', 'linkDown'):
            return self._handle_link_event(trap, trap_type)
        elif trap_type.startswith('raps'):
            return self._handle_raps_event(trap, trap_type)
        elif trap_type.startswith('cfm'):
            return self._handle_cfm_event(trap, trap_type)
        else:
            return self._handle_generic(trap)
    
    def _get_trap_type(self, trap_oid: str) -> str:
        """Get trap type name from OID."""
        # Check exact match first
        if trap_oid in self.TRAP_TYPES:
            return self.TRAP_TYPES[trap_oid]
        
        # Check prefix match for enterprise traps
        for oid, name in self.TRAP_TYPES.items():
            if trap_oid.startswith(oid):
                return name
        
        return 'unknown'
    
    def _handle_alarm(self, trap: DecodedTrap, trap_type: str) -> TrapEvent:
        """Handle Ciena alarm raised/cleared traps."""
        is_clear = trap_type == 'alarmCleared'
        
        # Extract alarm details from varbinds
        alarm_object = None
        alarm_severity = 'warning'
        alarm_description = 'Unknown alarm'
        alarm_id = None
        
        for oid, value in trap.varbinds.items():
            # Match by OID suffix
            if '6141.2.60.5.1.1.1' in oid or oid.endswith('.1'):
                alarm_object = str(value)
            elif '6141.2.60.5.1.1.2' in oid or oid.endswith('.2'):
                try:
                    sev_val = int(value)
                    alarm_severity = self.SEVERITY_MAP.get(sev_val, 'warning')
                except (ValueError, TypeError):
                    pass
            elif '6141.2.60.5.1.1.3' in oid or oid.endswith('.3'):
                alarm_description = str(value)
            elif '6141.2.60.5.1.1.5' in oid:
                alarm_id = str(value)
        
        # Generate alarm_id if not provided (for correlation)
        if not alarm_id:
            # Create unique ID from source IP + object + description
            alarm_id = f"{trap.source_ip}:{alarm_object or 'unknown'}:{alarm_description[:50]}"
        
        # Parse object type and ID from alarm_object
        object_type = 'unknown'
        object_id = alarm_object
        if alarm_object:
            if 'Port' in alarm_object or 'port' in alarm_object:
                object_type = 'port'
                # Extract port number
                import re
                match = re.search(r'(\d+)', alarm_object)
                if match:
                    object_id = match.group(1)
            elif 'Ring' in alarm_object or 'RAPS' in alarm_object:
                object_type = 'ring'
            elif 'Chassis' in alarm_object or 'chassis' in alarm_object:
                object_type = 'chassis'
        
        return TrapEvent(
            event_type='alarm',
            source_ip=trap.source_ip,
            device_name=None,  # Will be resolved later
            severity='cleared' if is_clear else alarm_severity,
            object_type=object_type,
            object_id=object_id,
            description=alarm_description,
            details={
                'alarm_object': alarm_object,
                'trap_type': trap_type,
                'varbinds': trap.varbinds,
            },
            alarm_id=alarm_id,
            is_clear=is_clear,
        )
    
    def _handle_link_event(self, trap: DecodedTrap, trap_type: str) -> TrapEvent:
        """Handle port link up/down traps."""
        is_up = 'Up' in trap_type or 'up' in trap_type
        
        # Extract interface info from varbinds
        if_index = None
        if_name = None
        if_descr = None
        
        for oid, value in trap.varbinds.items():
            if '.2.2.1.1.' in oid:  # ifIndex
                if_index = str(value)
            elif '.2.2.1.2.' in oid:  # ifDescr
                if_descr = str(value)
            elif '.31.1.1.1.1.' in oid:  # ifName
                if_name = str(value)
        
        port_id = if_name or if_descr or if_index or 'unknown'
        
        return TrapEvent(
            event_type='link',
            source_ip=trap.source_ip,
            device_name=None,
            severity='warning' if not is_up else 'info',
            object_type='port',
            object_id=port_id,
            description=f"Port {port_id} {'up' if is_up else 'down'}",
            details={
                'if_index': if_index,
                'if_name': if_name,
                'if_descr': if_descr,
                'link_state': 'up' if is_up else 'down',
            },
            alarm_id=f"{trap.source_ip}:link:{port_id}",
            is_clear=is_up,  # Link up clears link down alarm
        )
    
    def _handle_raps_event(self, trap: DecodedTrap, trap_type: str) -> TrapEvent:
        """Handle G.8032 RAPS ring events."""
        ring_id = None
        ring_state = None
        
        for oid, value in trap.varbinds.items():
            if 'ringId' in oid.lower() or '.47.' in oid:
                ring_id = str(value)
            if 'state' in oid.lower():
                ring_state = str(value)
        
        return TrapEvent(
            event_type='raps',
            source_ip=trap.source_ip,
            device_name=None,
            severity='warning' if 'Switchover' in trap_type else 'info',
            object_type='ring',
            object_id=ring_id or 'unknown',
            description=f"RAPS {trap_type}: Ring {ring_id or 'unknown'}",
            details={
                'ring_id': ring_id,
                'ring_state': ring_state,
                'trap_type': trap_type,
                'varbinds': trap.varbinds,
            },
            alarm_id=f"{trap.source_ip}:raps:{ring_id}" if ring_id else None,
            is_clear=False,
        )
    
    def _handle_cfm_event(self, trap: DecodedTrap, trap_type: str) -> TrapEvent:
        """Handle CFM (Connectivity Fault Management) events."""
        is_clear = 'Cleared' in trap_type
        
        return TrapEvent(
            event_type='cfm',
            source_ip=trap.source_ip,
            device_name=None,
            severity='cleared' if is_clear else 'minor',
            object_type='cfm',
            object_id=None,
            description=f"CFM {trap_type}",
            details={
                'trap_type': trap_type,
                'varbinds': trap.varbinds,
            },
            alarm_id=f"{trap.source_ip}:cfm:{hash(str(trap.varbinds))}",
            is_clear=is_clear,
        )
    
    def _handle_generic(self, trap: DecodedTrap) -> TrapEvent:
        """Handle unknown Ciena traps."""
        return TrapEvent(
            event_type='unknown',
            source_ip=trap.source_ip,
            device_name=None,
            severity='info',
            object_type=None,
            object_id=None,
            description=f"Unknown Ciena trap: {trap.trap_oid}",
            details={
                'trap_oid': trap.trap_oid,
                'enterprise_oid': trap.enterprise_oid,
                'varbinds': trap.varbinds,
            },
            alarm_id=None,
            is_clear=False,
        )


class GenericTrapHandler:
    """Handler for unknown/generic traps."""
    
    STANDARD_TRAPS = {
        '1.3.6.1.6.3.1.1.5.1': ('coldStart', 'warning', 'Device cold start'),
        '1.3.6.1.6.3.1.1.5.2': ('warmStart', 'info', 'Device warm start'),
        '1.3.6.1.6.3.1.1.5.3': ('linkDown', 'warning', 'Interface link down'),
        '1.3.6.1.6.3.1.1.5.4': ('linkUp', 'info', 'Interface link up'),
        '1.3.6.1.6.3.1.1.5.5': ('authFailure', 'warning', 'SNMP authentication failure'),
    }
    
    def handle(self, trap: DecodedTrap) -> TrapEvent:
        """Process generic trap and return normalized event."""
        if trap.trap_oid in self.STANDARD_TRAPS:
            trap_name, severity, description = self.STANDARD_TRAPS[trap.trap_oid]
            is_clear = trap_name == 'linkUp'
            
            return TrapEvent(
                event_type=trap_name,
                source_ip=trap.source_ip,
                device_name=None,
                severity=severity,
                object_type=None,
                object_id=None,
                description=description,
                details={'varbinds': trap.varbinds},
                alarm_id=f"{trap.source_ip}:{trap_name}" if trap_name in ('linkDown', 'linkUp') else None,
                is_clear=is_clear,
            )
        
        return TrapEvent(
            event_type='unknown',
            source_ip=trap.source_ip,
            device_name=None,
            severity='info',
            object_type=None,
            object_id=None,
            description=f"Unknown trap: {trap.trap_oid}",
            details={
                'trap_oid': trap.trap_oid,
                'enterprise_oid': trap.enterprise_oid,
                'varbinds': trap.varbinds,
            },
            alarm_id=None,
            is_clear=False,
        )


class SNMPTrapReceiver:
    """Main SNMP trap receiver service."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 162):
        self.host = host
        self.port = port
        self.queue: asyncio.Queue = None
        self.running = False
        self.snmp_engine = None
        
        # Statistics
        self.traps_received = 0
        self.traps_processed = 0
        self.traps_errors = 0
        self.started_at = None
        self.last_trap_at = None
        
        # Handlers
        self.router = TrapRouter()
        self.handlers = {
            'ciena': CienaTrapHandler(),
            'generic': GenericTrapHandler(),
            'standard': GenericTrapHandler(),
            'cisco': GenericTrapHandler(),
            'juniper': GenericTrapHandler(),
            'linux': GenericTrapHandler(),
            'hp': GenericTrapHandler(),
            'dell': GenericTrapHandler(),
        }
        
        # Database connection
        self.db_conn = None
        
        # Configuration
        self.queue_size = int(os.environ.get('SNMP_TRAP_QUEUE_SIZE', 10000))
        self.num_workers = int(os.environ.get('SNMP_TRAP_WORKERS', 4))
        self.communities = os.environ.get('SNMP_TRAP_COMMUNITIES', 'public,0psc0nduct0r').split(',')
        self.validate_community = os.environ.get('SNMP_TRAP_VALIDATE_COMMUNITY', 'false').lower() == 'true'
    
    def _get_db_connection(self):
        """Get database connection."""
        if self.db_conn is None or self.db_conn.closed:
            self.db_conn = psycopg2.connect(
                host=os.environ.get('PG_HOST', 'localhost'),
                port=os.environ.get('PG_PORT', '5432'),
                database=os.environ.get('PG_DATABASE', 'network_scan'),
                user=os.environ.get('PG_USER', 'postgres'),
                password=os.environ.get('PG_PASSWORD', 'postgres'),
                cursor_factory=RealDictCursor
            )
            self.db_conn.autocommit = True
        return self.db_conn
    
    def _trap_callback(self, snmp_engine, state_reference, context_engine_id, context_name,
                       var_binds, cb_ctx):
        """Callback when trap is received by pysnmp."""
        try:
            # Get transport info (pysnmp 7.x API)
            transport_domain, transport_address = snmp_engine.message_dispatcher.get_transport_info(state_reference)
            source_ip = str(transport_address[0])
            source_port = int(transport_address[1])
            
            # Extract trap info
            trap_oid = ''
            enterprise_oid = ''
            uptime = 0
            varbinds = {}
            
            for oid, val in var_binds:
                oid_str = str(oid)
                
                # Convert value to Python type
                if hasattr(val, 'prettyPrint'):
                    val_str = val.prettyPrint()
                else:
                    val_str = str(val)
                
                # Identify special OIDs
                if oid_str == '1.3.6.1.2.1.1.3.0':  # sysUpTime
                    try:
                        uptime = int(val)
                    except:
                        uptime = 0
                elif oid_str == '1.3.6.1.6.3.1.1.4.1.0':  # snmpTrapOID
                    trap_oid = val_str
                elif oid_str.startswith('1.3.6.1.6.3.1.1.4.3'):  # snmpTrapEnterprise
                    enterprise_oid = val_str
                else:
                    varbinds[oid_str] = val_str
            
            # If no enterprise OID, try to extract from trap OID
            if not enterprise_oid and trap_oid:
                # Enterprise OID is usually the prefix of trap OID
                parts = trap_oid.rsplit('.', 2)
                if len(parts) > 1:
                    enterprise_oid = parts[0]
            
            # Create decoded trap
            decoded = DecodedTrap(
                received_at=datetime.now(timezone.utc),
                source_ip=source_ip,
                source_port=source_port,
                snmp_version='v2c',
                community='',  # Not available in callback
                enterprise_oid=enterprise_oid,
                trap_oid=trap_oid,
                generic_trap=0,
                specific_trap=0,
                uptime=uptime,
                varbinds=varbinds,
            )
            
            # Queue for processing
            self.traps_received += 1
            self.last_trap_at = datetime.now(timezone.utc)
            
            if self.queue and not self.queue.full():
                asyncio.get_event_loop().call_soon_threadsafe(
                    self.queue.put_nowait, decoded
                )
            else:
                logger.warning(f"Trap queue full, dropping trap from {source_ip}")
                self.traps_errors += 1
                
        except Exception as e:
            logger.error(f"Error in trap callback: {e}", exc_info=True)
            self.traps_errors += 1
    
    async def _process_trap(self, trap: DecodedTrap):
        """Process a single trap."""
        try:
            # Route to handler
            vendor = self.router.route(trap)
            handler = self.handlers.get(vendor, self.handlers['generic'])
            
            # Handle trap
            event = handler.handle(trap)
            
            # Store trap log
            trap_log_id = await self._store_trap_log(trap, vendor)
            
            # Store event if generated
            event_id = None
            if event:
                event_id = await self._store_event(event, trap_log_id)
                
                # Update trap log with event reference
                if event_id:
                    await self._update_trap_log(trap_log_id, event_id)
            
            self.traps_processed += 1
            logger.info(f"Processed trap from {trap.source_ip}: {trap.trap_oid} -> {vendor}/{event.event_type if event else 'no-event'}")
            
        except Exception as e:
            logger.error(f"Error processing trap: {e}", exc_info=True)
            self.traps_errors += 1
    
    async def _store_trap_log(self, trap: DecodedTrap, vendor: str) -> int:
        """Store raw trap in trap_log table."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trap_log 
                    (received_at, source_ip, source_port, snmp_version, community,
                     enterprise_oid, trap_oid, vendor, uptime, varbinds, processed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    RETURNING id
                """, (
                    trap.received_at,
                    trap.source_ip,
                    trap.source_port,
                    trap.snmp_version,
                    trap.community,
                    trap.enterprise_oid,
                    trap.trap_oid,
                    vendor,
                    trap.uptime,
                    json.dumps(trap.varbinds),
                ))
                result = cur.fetchone()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error storing trap log: {e}")
            return None
    
    async def _store_event(self, event: TrapEvent, trap_log_id: int) -> int:
        """Store normalized event in trap_events table."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                # Check for duplicate alarm (same alarm_id, not cleared)
                if event.alarm_id and not event.is_clear:
                    cur.execute("""
                        SELECT id FROM trap_events 
                        WHERE alarm_id = %s AND is_clear = FALSE
                        ORDER BY created_at DESC LIMIT 1
                    """, (event.alarm_id,))
                    existing = cur.fetchone()
                    if existing:
                        logger.debug(f"Duplicate alarm {event.alarm_id}, skipping")
                        return existing['id']
                
                # If this is a clear event, find the alarm to clear
                cleared_event_id = None
                if event.is_clear and event.alarm_id:
                    cur.execute("""
                        SELECT id FROM trap_events 
                        WHERE alarm_id = %s AND is_clear = FALSE
                        ORDER BY created_at DESC LIMIT 1
                    """, (event.alarm_id,))
                    alarm_to_clear = cur.fetchone()
                    if alarm_to_clear:
                        cleared_event_id = alarm_to_clear['id']
                
                # Resolve device name from source IP
                device_name = await self._resolve_device_name(event.source_ip)
                
                cur.execute("""
                    INSERT INTO trap_events 
                    (source_ip, device_name, event_type, severity, object_type, object_id,
                     description, details, trap_log_id, alarm_id, is_clear, cleared_event_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    event.source_ip,
                    device_name or event.device_name,
                    event.event_type,
                    event.severity,
                    event.object_type,
                    event.object_id,
                    event.description,
                    json.dumps(event.details),
                    trap_log_id,
                    event.alarm_id,
                    event.is_clear,
                    cleared_event_id,
                ))
                result = cur.fetchone()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error storing event: {e}")
            return None
    
    async def _update_trap_log(self, trap_log_id: int, event_id: int):
        """Update trap log with event reference."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trap_log SET event_id = %s, processed_at = NOW()
                    WHERE id = %s
                """, (event_id, trap_log_id))
        except Exception as e:
            logger.error(f"Error updating trap log: {e}")
    
    async def _resolve_device_name(self, ip: str) -> Optional[str]:
        """Resolve device name from IP address."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                # Check devices table
                cur.execute("""
                    SELECT hostname FROM devices WHERE ip_address = %s LIMIT 1
                """, (ip,))
                result = cur.fetchone()
                if result:
                    return result['hostname']
        except Exception as e:
            logger.debug(f"Could not resolve device name for {ip}: {e}")
        return None
    
    async def _worker(self, worker_id: int):
        """Worker coroutine to process traps from queue."""
        logger.info(f"Worker {worker_id} started")
        while self.running:
            try:
                trap = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_trap(trap)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
        logger.info(f"Worker {worker_id} stopped")
    
    async def _update_status(self):
        """Periodically update status in database."""
        while self.running:
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE trap_receiver_status SET
                            traps_received = %s,
                            traps_processed = %s,
                            traps_errors = %s,
                            queue_depth = %s,
                            is_running = %s,
                            last_trap_at = %s,
                            updated_at = NOW()
                        WHERE id = 1
                    """, (
                        self.traps_received,
                        self.traps_processed,
                        self.traps_errors,
                        self.queue.qsize() if self.queue else 0,
                        self.running,
                        self.last_trap_at,
                    ))
            except Exception as e:
                logger.error(f"Error updating status: {e}")
            
            await asyncio.sleep(10)
    
    def start(self):
        """Start the trap receiver (synchronous - pysnmp manages the event loop)."""
        logger.info(f"Starting SNMP Trap Receiver on {self.host}:{self.port}")
        
        self.running = True
        self.started_at = datetime.now(timezone.utc)
        
        # Create SNMP engine
        self.snmp_engine = engine.SnmpEngine()
        
        # Configure transport (pysnmp 7.x API)
        config.add_transport(
            self.snmp_engine,
            udp.DOMAIN_NAME,
            udp.UdpTransport().open_server_mode((self.host, self.port))
        )
        
        # Configure community strings (pysnmp 7.x API)
        for community in self.communities:
            config.add_v1_system(self.snmp_engine, community, community)
        
        # Register trap callback
        ntfrcv.NotificationReceiver(self.snmp_engine, self._trap_callback)
        
        # Get the event loop from pysnmp's dispatcher
        loop = self.snmp_engine.transport_dispatcher.loop
        
        # Create queue on this loop
        self.queue = asyncio.Queue(maxsize=self.queue_size)
        
        # Schedule workers and status updater on pysnmp's event loop
        for i in range(self.num_workers):
            loop.create_task(self._worker(i))
        loop.create_task(self._update_status())
        
        # Update initial status
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trap_receiver_status SET
                        started_at = %s,
                        is_running = TRUE,
                        traps_received = 0,
                        traps_processed = 0,
                        traps_errors = 0,
                        updated_at = NOW()
                    WHERE id = 1
                """, (self.started_at,))
        except Exception as e:
            logger.error(f"Error updating initial status: {e}")
        
        logger.info(f"SNMP Trap Receiver started with {self.num_workers} workers")
        
        # Run SNMP engine (pysnmp 7.x API) - this blocks
        try:
            self.snmp_engine.transport_dispatcher.job_started(1)
            self.snmp_engine.transport_dispatcher.run_dispatcher()
        except Exception as e:
            logger.error(f"Dispatcher error: {e}")
        finally:
            self.running = False
            
            # Update final status
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE trap_receiver_status SET
                            is_running = FALSE,
                            updated_at = NOW()
                        WHERE id = 1
                    """)
            except Exception as e:
                logger.error(f"Error updating final status: {e}")
            
            logger.info("SNMP Trap Receiver stopped")
    
    def stop(self):
        """Stop the trap receiver."""
        logger.info("Stopping SNMP Trap Receiver...")
        self.running = False
        if self.snmp_engine:
            self.snmp_engine.transport_dispatcher.job_finished(1)
            self.snmp_engine.close_dispatcher()


def main():
    """Main entry point."""
    host = os.environ.get('SNMP_TRAP_HOST', '0.0.0.0')
    port = int(os.environ.get('SNMP_TRAP_PORT', 162))
    
    receiver = SNMPTrapReceiver(host, port)
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        receiver.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run (synchronous - pysnmp manages the event loop)
    try:
        receiver.start()
    except KeyboardInterrupt:
        receiver.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
