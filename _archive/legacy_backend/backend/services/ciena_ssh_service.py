"""
Ciena SSH Service.

Provides SSH-based data collection for Ciena SAOS switches (3942, 5160, etc.).
This is the primary data source for real-time monitoring, replacing unreliable SNMP polling.

Features:
- Interactive shell session for multiple commands in one connection
- Parallel polling across multiple switches
- Comprehensive data collection: optical, traffic, alarms, chassis, rings
- Structured output parsing
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import paramiko

logger = logging.getLogger(__name__)


class CienaSSHError(Exception):
    """Exception for Ciena SSH errors."""
    def __init__(self, message: str, host: str = None, details: Any = None):
        self.message = message
        self.host = host
        self.details = details
        super().__init__(message)


@dataclass
class OpticalDiagnostics:
    """Optical transceiver diagnostics for a single port."""
    port_id: int
    temperature_c: Optional[float] = None
    voltage_v: Optional[float] = None
    bias_ma: Optional[float] = None
    tx_power_mw: Optional[float] = None
    tx_power_dbm: Optional[float] = None
    rx_power_mw: Optional[float] = None
    rx_power_dbm: Optional[float] = None
    # Alarm flags
    temp_alarm_high: bool = False
    temp_alarm_low: bool = False
    voltage_alarm_high: bool = False
    voltage_alarm_low: bool = False
    tx_power_alarm_high: bool = False
    tx_power_alarm_low: bool = False
    rx_power_alarm_high: bool = False
    rx_power_alarm_low: bool = False
    # Thresholds
    tx_power_high_threshold: Optional[float] = None
    tx_power_low_threshold: Optional[float] = None
    rx_power_high_threshold: Optional[float] = None
    rx_power_low_threshold: Optional[float] = None


@dataclass
class PortStatus:
    """Port status information."""
    port_id: int
    name: str = ""
    admin_state: str = ""  # enabled/disabled
    oper_state: str = ""  # up/down
    link_state: str = ""  # up/down
    speed: str = ""  # 1G, 10G, etc.
    duplex: str = ""
    stp_state: str = ""
    description: str = ""


@dataclass
class TrafficStats:
    """Traffic statistics for a port."""
    port_id: int
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_discards: int = 0
    tx_discards: int = 0
    # Real-time rates (from PM)
    rx_bytes_per_sec: Optional[int] = None
    tx_bytes_per_sec: Optional[int] = None
    rx_frames_per_sec: Optional[int] = None
    tx_frames_per_sec: Optional[int] = None


@dataclass
class Alarm:
    """Active alarm on the switch."""
    index: int
    severity: str  # critical, major, minor, warning
    condition: str  # SET, CLEAR
    object_type: str  # port, chassis, etc.
    object_id: str  # port 21, PSU 1, etc.
    timestamp: str
    description: str
    acknowledged: bool = False


@dataclass
class ChassisHealth:
    """Chassis health information."""
    fans: List[Dict] = field(default_factory=list)
    power_supplies: List[Dict] = field(default_factory=list)
    temperatures: List[Dict] = field(default_factory=list)


@dataclass
class RingStatus:
    """G.8032 ring protection status."""
    name: str
    state: str  # ok, protecting, recovering, etc.
    west_port: int
    west_port_state: str
    east_port: int
    east_port_state: str
    switchovers: int = 0


@dataclass
class SystemInfo:
    """System information."""
    hostname: str = ""
    software_version: str = ""
    uptime: str = ""
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    serial_number: str = ""
    model: str = ""


@dataclass
class SwitchData:
    """Complete data collection from a switch."""
    host: str
    collected_at: datetime
    collection_time_ms: int
    success: bool
    error: Optional[str] = None
    
    system_info: Optional[SystemInfo] = None
    optical: List[OpticalDiagnostics] = field(default_factory=list)
    ports: List[PortStatus] = field(default_factory=list)
    traffic: List[TrafficStats] = field(default_factory=list)
    alarms: List[Alarm] = field(default_factory=list)
    chassis: Optional[ChassisHealth] = None
    rings: List[RingStatus] = field(default_factory=list)


class CienaSSHService:
    """Service for SSH-based data collection from Ciena switches."""
    
    # Default commands to execute
    # Note: PM command uses comma syntax, not range (1-24 doesn't work)
    DEFAULT_COMMANDS = [
        'port xcvr show port 1-24 diagnostics',  # Optical diagnostics
        'port show',  # Port status
        'pm show pm-instance 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24 bin-number 1',  # Traffic rates
        'alarm show',  # Active alarms
        'chassis show',  # Chassis health
        'ring-protection virtual-ring show',  # G.8032 rings
        'system show',  # System info
    ]
    
    def __init__(
        self,
        username: str = 'su',
        password: str = 'wwp',
        timeout: int = 10,
        max_concurrent: int = 10,
        command_delay: float = 0.5,
    ):
        """
        Initialize Ciena SSH service.
        
        Args:
            username: SSH username (default: su)
            password: SSH password (default: wwp)
            timeout: Connection timeout in seconds
            max_concurrent: Maximum concurrent SSH sessions
            command_delay: Delay between commands in seconds
        """
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.command_delay = command_delay
    
    def _connect(self, host: str) -> paramiko.SSHClient:
        """
        Establish SSH connection to a switch.
        
        Args:
            host: Switch IP address or hostname
            
        Returns:
            Connected SSHClient
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(
                host,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            return client
        except paramiko.AuthenticationException:
            raise CienaSSHError(f"Authentication failed for {host}", host=host)
        except paramiko.SSHException as e:
            raise CienaSSHError(f"SSH error connecting to {host}: {e}", host=host)
        except Exception as e:
            raise CienaSSHError(f"Failed to connect to {host}: {e}", host=host)
    
    def _execute_commands(
        self,
        client: paramiko.SSHClient,
        commands: List[str],
    ) -> Dict[str, str]:
        """
        Execute multiple commands in an interactive shell session.
        
        Args:
            client: Connected SSH client
            commands: List of commands to execute
            
        Returns:
            Dict mapping command to output
        """
        results = {}
        
        # Get interactive shell with larger terminal to avoid pagination
        shell = client.invoke_shell(width=200, height=1000)
        time.sleep(0.5)  # Wait for shell to initialize
        
        # Clear initial banner/prompt
        if shell.recv_ready():
            shell.recv(65535)
        
        for cmd in commands:
            # Send command
            shell.send(cmd + '\n')
            
            # Collect output with pagination handling
            output = ''
            max_iterations = 50  # Safety limit
            iterations = 0
            
            while iterations < max_iterations:
                time.sleep(self.command_delay)
                
                if not shell.recv_ready():
                    # Wait a bit more and check again
                    time.sleep(0.3)
                    if not shell.recv_ready():
                        break
                
                chunk = shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                
                # Handle --More-- pagination by sending space
                if '--More--' in chunk:
                    shell.send(' ')
                    iterations += 1
                    continue
                
                # Check if we've reached the prompt (command complete)
                if chunk.strip().endswith('>'):
                    break
                    
                iterations += 1
            
            # Clean up output - remove --More-- artifacts and ANSI codes
            output = re.sub(r'--More--\s*', '', output)
            output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)  # Remove ANSI escape codes
            
            results[cmd] = output
        
        shell.close()
        return results
    
    def poll_switch(self, host: str, commands: List[str] = None) -> SwitchData:
        """
        Poll a single switch for all data.
        
        Args:
            host: Switch IP address
            commands: Optional list of commands (uses DEFAULT_COMMANDS if not provided)
            
        Returns:
            SwitchData with all collected information
        """
        start_time = time.time()
        commands = commands or self.DEFAULT_COMMANDS
        
        try:
            client = self._connect(host)
            try:
                raw_output = self._execute_commands(client, commands)
            finally:
                client.close()
            
            # Parse all outputs
            data = SwitchData(
                host=host,
                collected_at=datetime.utcnow(),
                collection_time_ms=int((time.time() - start_time) * 1000),
                success=True,
            )
            
            # Parse each command output
            for cmd, output in raw_output.items():
                if 'port xcvr show' in cmd and 'diagnostics' in cmd:
                    data.optical = self._parse_optical_diagnostics(output)
                elif cmd == 'port show':
                    data.ports = self._parse_port_status(output)
                elif 'pm show pm-instance' in cmd:
                    data.traffic = self._parse_pm_stats(output)
                elif cmd == 'alarm show':
                    data.alarms = self._parse_alarms(output)
                elif cmd == 'chassis show':
                    data.chassis = self._parse_chassis(output)
                elif 'ring-protection' in cmd:
                    data.rings = self._parse_rings(output)
                elif cmd == 'system show':
                    data.system_info = self._parse_system_info(output)
            
            logger.info(f"Successfully polled {host} in {data.collection_time_ms}ms")
            return data
            
        except CienaSSHError as e:
            logger.error(f"SSH error polling {host}: {e.message}")
            return SwitchData(
                host=host,
                collected_at=datetime.utcnow(),
                collection_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error=e.message,
            )
        except Exception as e:
            logger.error(f"Unexpected error polling {host}: {e}")
            return SwitchData(
                host=host,
                collected_at=datetime.utcnow(),
                collection_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error=str(e),
            )
    
    def poll_switches(self, hosts: List[str], commands: List[str] = None) -> List[SwitchData]:
        """
        Poll multiple switches in parallel.
        
        Args:
            hosts: List of switch IP addresses
            commands: Optional list of commands
            
        Returns:
            List of SwitchData for each switch
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {
                executor.submit(self.poll_switch, host, commands): host
                for host in hosts
            }
            
            for future in as_completed(futures):
                host = futures[future]
                try:
                    data = future.result()
                    results.append(data)
                except Exception as e:
                    logger.error(f"Error polling {host}: {e}")
                    results.append(SwitchData(
                        host=host,
                        collected_at=datetime.utcnow(),
                        collection_time_ms=0,
                        success=False,
                        error=str(e),
                    ))
        
        return results
    
    # ==================== PARSERS ====================
    
    def _parse_optical_diagnostics(self, output: str) -> List[OpticalDiagnostics]:
        """Parse 'port xcvr show port X diagnostics' output."""
        diagnostics = []
        
        # Split by port sections - handle various spacing
        port_sections = re.split(r'\+-+\s*XCVR DIAGNOSTICS\s*-\s*Port\s+(\d+)\s*-+\+', output)
        
        # port_sections[0] is before first match, then alternating: port_num, content, port_num, content...
        for i in range(1, len(port_sections), 2):
            if i + 1 >= len(port_sections):
                break
                
            port_id = int(port_sections[i])
            content = port_sections[i + 1]
            
            diag = OpticalDiagnostics(port_id=port_id)
            
            # Parse line by line for more reliable extraction
            lines = content.split('\n')
            for j, line in enumerate(lines):
                # Parse temperature
                if 'Temp' in line and 'degC' in line:
                    match = re.search(r'\|\s*([\d.+-]+)\s*\|', line)
                    if match:
                        try:
                            diag.temperature_c = float(match.group(1))
                        except ValueError:
                            pass
                
                # Parse voltage
                elif 'Vcc' in line and 'volts' in line:
                    match = re.search(r'\|\s*([\d.+-]+)\s*\|', line)
                    if match:
                        try:
                            diag.voltage_v = float(match.group(1))
                        except ValueError:
                            pass
                
                # Parse bias
                elif 'Bias' in line and 'mA' in line:
                    match = re.search(r'\|\s*([\d.+-]+)\s*\|', line)
                    if match:
                        try:
                            diag.bias_ma = float(match.group(1))
                        except ValueError:
                            pass
                
                # Parse TX power (mW)
                elif 'Tx Power' in line and 'mW' in line and 'dBm' not in line:
                    match = re.search(r'\|\s*([\d.+-]+)\s*\|', line)
                    if match:
                        try:
                            diag.tx_power_mw = float(match.group(1))
                        except ValueError:
                            pass
                
                # Parse TX power (dBm) - format: | Tx Power (dBm)|  +1.9318 | HIGH  +5.0000 | 0    |
                elif 'Tx Power' in line and 'dBm' in line:
                    # Extract value and HIGH threshold/flag from this line
                    parts = line.split('|')
                    if len(parts) >= 5:
                        try:
                            diag.tx_power_dbm = float(parts[2].strip())
                            high_match = re.search(r'HIGH\s+([\d.+-]+)', parts[3])
                            if high_match:
                                diag.tx_power_high_threshold = float(high_match.group(1))
                            diag.tx_power_alarm_high = parts[4].strip() == '1'
                        except (ValueError, IndexError):
                            pass
                    # Check next line for LOW threshold
                    if j + 1 < len(lines) and 'LOW' in lines[j + 1]:
                        low_parts = lines[j + 1].split('|')
                        if len(low_parts) >= 5:
                            try:
                                low_match = re.search(r'LOW\s+([\d.+-]+)', low_parts[3])
                                if low_match:
                                    diag.tx_power_low_threshold = float(low_match.group(1))
                                diag.tx_power_alarm_low = low_parts[4].strip() == '1'
                            except (ValueError, IndexError):
                                pass
                
                # Parse RX power (mW)
                elif 'Rx Power' in line and 'mW' in line and 'dBm' not in line:
                    match = re.search(r'\|\s*([\d.+-]+)\s*\|', line)
                    if match:
                        try:
                            diag.rx_power_mw = float(match.group(1))
                        except ValueError:
                            pass
                
                # Parse RX power (dBm)
                elif 'Rx Power' in line and 'dBm' in line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        try:
                            diag.rx_power_dbm = float(parts[2].strip())
                            high_match = re.search(r'HIGH\s+([\d.+-]+)', parts[3])
                            if high_match:
                                diag.rx_power_high_threshold = float(high_match.group(1))
                            diag.rx_power_alarm_high = parts[4].strip() == '1'
                        except (ValueError, IndexError):
                            pass
                    # Check next line for LOW threshold
                    if j + 1 < len(lines) and 'LOW' in lines[j + 1]:
                        low_parts = lines[j + 1].split('|')
                        if len(low_parts) >= 5:
                            try:
                                low_match = re.search(r'LOW\s+([\d.+-]+)', low_parts[3])
                                if low_match:
                                    diag.rx_power_low_threshold = float(low_match.group(1))
                                diag.rx_power_alarm_low = low_parts[4].strip() == '1'
                            except (ValueError, IndexError):
                                pass
            
            diagnostics.append(diag)
        
        return diagnostics
    
    def _parse_port_status(self, output: str) -> List[PortStatus]:
        """Parse 'port show' output."""
        ports = []
        
        # Look for table rows with port data
        # Format: | Port | Name | Type | Admin | Oper | Speed | Duplex | STP |
        for line in output.split('\n'):
            # Skip header and separator lines
            if '|' not in line or 'Port' in line and 'Name' in line:
                continue
            if '---' in line or '===' in line:
                continue
            
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 6:
                continue
            
            try:
                # Try to parse port ID
                port_id_str = parts[1] if len(parts) > 1 else ''
                if not port_id_str or not port_id_str.isdigit():
                    continue
                
                port = PortStatus(
                    port_id=int(port_id_str),
                    name=parts[2] if len(parts) > 2 else '',
                    admin_state=parts[4] if len(parts) > 4 else '',
                    oper_state=parts[5] if len(parts) > 5 else '',
                    speed=parts[6] if len(parts) > 6 else '',
                    duplex=parts[7] if len(parts) > 7 else '',
                    stp_state=parts[8] if len(parts) > 8 else '',
                )
                ports.append(port)
            except (ValueError, IndexError):
                continue
        
        return ports
    
    def _parse_pm_stats(self, output: str) -> List[TrafficStats]:
        """Parse 'pm show pm-instance X bin-number 1' output."""
        # Use a dict to consolidate stats by port (PM output has multiple sections per port)
        stats_by_port: Dict[int, TrafficStats] = {}
        current_port = None
        
        for line in output.split('\n'):
            # Look for instance name (port ID)
            instance_match = re.search(r'Instance Name\s*\|\s*(\d+)', line)
            if instance_match:
                current_port = int(instance_match.group(1))
                if current_port not in stats_by_port:
                    stats_by_port[current_port] = TrafficStats(port_id=current_port)
                continue
            
            if current_port is None:
                continue
            
            current_stats = stats_by_port[current_port]
            
            # Parse traffic rates (these have leading spaces in the output)
            if 'TX Bytes per Second' in line:
                match = re.search(r'TX Bytes per Second\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.tx_bytes_per_sec = int(match.group(1).replace(',', ''))
            elif 'RX Bytes per Second' in line:
                match = re.search(r'RX Bytes per Second\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.rx_bytes_per_sec = int(match.group(1).replace(',', ''))
            elif 'TX Frames per Second' in line:
                match = re.search(r'TX Frames per Second\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.tx_frames_per_sec = int(match.group(1).replace(',', ''))
            elif 'RX Frames per Second' in line:
                match = re.search(r'RX Frames per Second\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.rx_frames_per_sec = int(match.group(1).replace(',', ''))
            # Parse cumulative counters (format: |   RxBytes   |   value   |)
            elif 'RxBytes' in line and '|' in line:
                match = re.search(r'RxBytes\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.rx_bytes = int(match.group(1).replace(',', ''))
            elif 'TxBytes' in line and '|' in line:
                match = re.search(r'TxBytes\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.tx_bytes = int(match.group(1).replace(',', ''))
            elif 'RxPkts' in line and '|' in line:
                match = re.search(r'RxPkts\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.rx_packets = int(match.group(1).replace(',', ''))
            elif 'TxPkts' in line and '|' in line:
                match = re.search(r'TxPkts\s*\|\s*([\d,]+)', line)
                if match:
                    current_stats.tx_packets = int(match.group(1).replace(',', ''))
        
        # Return sorted by port ID
        return sorted(stats_by_port.values(), key=lambda x: x.port_id)
    
    def _parse_alarms(self, output: str) -> List[Alarm]:
        """Parse 'alarm show' output."""
        alarms = []
        
        # Look for alarm table rows
        # Format varies, but typically: | Idx | Sev | SA | Cond | Obj | Time | Desc |
        for line in output.split('\n'):
            if '|' not in line:
                continue
            if 'Idx' in line or '---' in line or '===' in line:
                continue
            
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 7:
                continue
            
            try:
                idx_str = parts[1] if len(parts) > 1 else ''
                if not idx_str or not idx_str.isdigit():
                    continue
                
                # Map severity codes
                sev_code = parts[2] if len(parts) > 2 else ''
                severity_map = {
                    'CR': 'critical',
                    'MJ': 'major',
                    'MN': 'minor',
                    'WR': 'warning',
                    'CL': 'cleared',
                }
                severity = severity_map.get(sev_code.upper(), sev_code.lower())
                
                alarm = Alarm(
                    index=int(idx_str),
                    severity=severity,
                    condition=parts[4] if len(parts) > 4 else '',
                    object_type='port' if parts[5].isdigit() else 'other',
                    object_id=parts[5] if len(parts) > 5 else '',
                    timestamp=parts[6] if len(parts) > 6 else '',
                    description=parts[7] if len(parts) > 7 else '',
                    acknowledged=(parts[3] if len(parts) > 3 else '') == 'Y',
                )
                alarms.append(alarm)
            except (ValueError, IndexError):
                continue
        
        return alarms
    
    def _parse_chassis(self, output: str) -> ChassisHealth:
        """Parse 'chassis show' output."""
        health = ChassisHealth()
        
        # Parse fan information
        fan_section = False
        for line in output.split('\n'):
            if 'FAN' in line.upper() and 'MODULE' in line.upper():
                fan_section = True
                continue
            if fan_section and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    try:
                        fan_id = parts[1]
                        if fan_id.isdigit():
                            health.fans.append({
                                'id': int(fan_id),
                                'status': parts[2] if len(parts) > 2 else '',
                                'speed_rpm': int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None,
                            })
                    except (ValueError, IndexError):
                        pass
            elif fan_section and '---' not in line and line.strip() and '|' not in line:
                fan_section = False
        
        # Parse power supply information
        psu_section = False
        for line in output.split('\n'):
            if 'POWER' in line.upper() and 'SUPPLY' in line.upper():
                psu_section = True
                continue
            if psu_section and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    try:
                        psu_id = parts[1]
                        if psu_id.isdigit():
                            health.power_supplies.append({
                                'id': int(psu_id),
                                'state': parts[2] if len(parts) > 2 else '',
                                'type': parts[3] if len(parts) > 3 else '',
                            })
                    except (ValueError, IndexError):
                        pass
            elif psu_section and '---' not in line and line.strip() and '|' not in line:
                psu_section = False
        
        # Parse temperature sensors
        temp_section = False
        for line in output.split('\n'):
            if 'TEMP' in line.upper() and 'SENSOR' in line.upper():
                temp_section = True
                continue
            if temp_section and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    try:
                        temp_id = parts[1]
                        if temp_id.isdigit():
                            health.temperatures.append({
                                'id': int(temp_id),
                                'value_c': float(parts[2]) if len(parts) > 2 else None,
                                'state': parts[3] if len(parts) > 3 else '',
                            })
                    except (ValueError, IndexError):
                        pass
            elif temp_section and '---' not in line and line.strip() and '|' not in line:
                temp_section = False
        
        return health
    
    def _parse_rings(self, output: str) -> List[RingStatus]:
        """Parse 'ring-protection virtual-ring show' output."""
        rings = []
        
        if 'No Virtual Rings Found' in output:
            return rings
        
        # Parse ring information from table
        # This is a simplified parser - may need adjustment based on actual output format
        current_ring = None
        for line in output.split('\n'):
            if '|' not in line:
                continue
            
            parts = [p.strip() for p in line.split('|')]
            
            # Look for ring name
            name_match = re.search(r'Name\s*\|\s*(\S+)', line)
            if name_match:
                if current_ring:
                    rings.append(current_ring)
                current_ring = RingStatus(
                    name=name_match.group(1),
                    state='',
                    west_port=0,
                    west_port_state='',
                    east_port=0,
                    east_port_state='',
                )
            
            if current_ring:
                if 'State' in line and 'Port' not in line:
                    state_match = re.search(r'State\s*\|\s*(\S+)', line)
                    if state_match:
                        current_ring.state = state_match.group(1)
                elif 'West Port' in line:
                    west_match = re.search(r'West Port\s*\|\s*(\d+)', line)
                    if west_match:
                        current_ring.west_port = int(west_match.group(1))
                elif 'East Port' in line:
                    east_match = re.search(r'East Port\s*\|\s*(\d+)', line)
                    if east_match:
                        current_ring.east_port = int(east_match.group(1))
        
        if current_ring:
            rings.append(current_ring)
        
        return rings
    
    def _parse_system_info(self, output: str) -> SystemInfo:
        """Parse 'system show' output."""
        info = SystemInfo()
        
        for line in output.split('\n'):
            if 'Host Name' in line or 'Hostname' in line:
                match = re.search(r'(?:Host\s*Name|Hostname)\s*[:\|]\s*(\S+)', line, re.IGNORECASE)
                if match:
                    info.hostname = match.group(1)
            elif 'Uptime' in line:
                match = re.search(r'Uptime\s*[:\|]\s*(.+)', line, re.IGNORECASE)
                if match:
                    info.uptime = match.group(1).strip()
            elif 'CPU' in line and '%' in line:
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if match:
                    info.cpu_usage = float(match.group(1))
            elif 'Memory' in line and '%' in line:
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if match:
                    info.memory_usage = float(match.group(1))
            elif 'Serial' in line:
                match = re.search(r'Serial\s*(?:Number)?\s*[:\|]\s*(\S+)', line, re.IGNORECASE)
                if match:
                    info.serial_number = match.group(1)
            elif 'Model' in line or 'Device Type' in line:
                match = re.search(r'(?:Model|Device\s*Type)\s*[:\|]\s*(.+)', line, re.IGNORECASE)
                if match:
                    info.model = match.group(1).strip()
        
        return info
    
    # ==================== CONVENIENCE METHODS ====================
    
    def get_optical_diagnostics(self, host: str, ports: str = '1-24') -> List[OpticalDiagnostics]:
        """
        Get optical diagnostics for specific ports.
        
        Args:
            host: Switch IP address
            ports: Port range (e.g., '1-24', '21,22')
            
        Returns:
            List of OpticalDiagnostics
        """
        cmd = f'port xcvr show port {ports} diagnostics'
        data = self.poll_switch(host, commands=[cmd])
        return data.optical
    
    def get_alarms(self, host: str) -> List[Alarm]:
        """Get active alarms from a switch."""
        data = self.poll_switch(host, commands=['alarm show'])
        return data.alarms
    
    def get_traffic_rates(self, host: str, ports: str = '1-24') -> List[TrafficStats]:
        """Get real-time traffic rates for ports."""
        cmd = f'pm show pm-instance {ports} bin-number 1'
        data = self.poll_switch(host, commands=[cmd])
        return data.traffic
    
    def test_connection(self, host: str) -> Dict:
        """
        Test SSH connectivity to a switch.
        
        Returns:
            Dict with success status and details
        """
        try:
            client = self._connect(host)
            client.close()
            return {
                'success': True,
                'host': host,
                'message': 'SSH connection successful',
            }
        except CienaSSHError as e:
            return {
                'success': False,
                'host': host,
                'error': e.message,
            }
        except Exception as e:
            return {
                'success': False,
                'host': host,
                'error': str(e),
            }


# ==================== MODULE-LEVEL FUNCTIONS ====================

# Global service instance
_ssh_service: Optional[CienaSSHService] = None


def get_ssh_service() -> CienaSSHService:
    """Get or create the global SSH service instance."""
    global _ssh_service
    if _ssh_service is None:
        _ssh_service = CienaSSHService()
    return _ssh_service


def reset_ssh_service():
    """Reset the global SSH service instance."""
    global _ssh_service
    _ssh_service = None


def poll_switch(host: str, commands: List[str] = None) -> SwitchData:
    """Poll a single switch using the global service."""
    return get_ssh_service().poll_switch(host, commands)


def poll_switches(hosts: List[str], commands: List[str] = None) -> List[SwitchData]:
    """Poll multiple switches using the global service."""
    return get_ssh_service().poll_switches(hosts, commands)
