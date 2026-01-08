"""
Axis Camera Connector

Polls Axis cameras via VAPIX API for status and events.
See docs/mappings/AXIS_ALERT_MAPPING.md for alert mapping documentation.
"""

import re
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from base64 import b64encode

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import AxisNormalizer

logger = logging.getLogger(__name__)

# System log patterns for detecting issues - see AXIS_ALERT_MAPPING.md
SYSTEM_LOG_PATTERNS: List[Tuple[str, str, str]] = [
    # (regex_pattern, alert_type, description)
    # Power
    (r"insufficient power", "power_insufficient", "Insufficient power detected"),
    (r"PoE budget", "power_insufficient", "PoE budget exceeded"),
    (r"power limit", "power_insufficient", "Power limit reached"),
    (r"power supply", "power_supply_error", "Power supply error"),
    # PTZ
    (r"not enough power for PTZ", "ptz_power_insufficient", "Insufficient power for PTZ"),
    (r"PTZ.*error", "ptz_error", "PTZ error detected"),
    (r"PTZ.*fail", "ptz_error", "PTZ failure"),
    (r"motor.*fail", "ptz_motor_failure", "PTZ motor failure"),
    (r"pan.*fail", "ptz_motor_failure", "Pan motor failure"),
    (r"tilt.*fail", "ptz_motor_failure", "Tilt motor failure"),
    # Hardware
    (r"fan.*fail", "fan_failure", "Fan failure detected"),
    (r"heater.*fail", "heater_failure", "Heater failure"),
    (r"lens.*error", "lens_error", "Lens error"),
    (r"focus.*fail", "focus_failure", "Auto-focus failure"),
    (r"IR.*fail", "ir_failure", "IR illuminator failure"),
    (r"illuminator.*fail", "ir_failure", "Illuminator failure"),
    (r"sensor.*fail", "sensor_failure", "Image sensor failure"),
    (r"imager.*fail", "sensor_failure", "Imager failure"),
    (r"audio.*fail", "audio_failure", "Audio system failure"),
    (r"microphone.*fail", "audio_failure", "Microphone failure"),
    # Network
    (r"IP conflict", "ip_conflict", "IP address conflict"),
    (r"duplicate IP", "ip_conflict", "Duplicate IP detected"),
    (r"DNS.*fail", "dns_failure", "DNS resolution failure"),
    # Security
    (r"login.*fail", "unauthorized_access", "Failed login attempt"),
    (r"authentication.*fail", "unauthorized_access", "Authentication failure"),
    # Storage
    (r"disk.*fail", "storage_failure", "Disk failure"),
    (r"SD card.*fail", "storage_failure", "SD card failure"),
    (r"storage.*error", "storage_failure", "Storage error"),
]


class AxisConnector(PollingConnector):
    """
    Axis camera connector using VAPIX API.
    
    Supports:
    - Manual camera list configuration
    - PRTG-based camera discovery (camera_source: "prtg")
    - System log parsing for hardware/power alerts
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.camera_source = config.get("camera_source", "manual")  # manual, prtg
        self.prtg_filter = config.get("prtg_filter", {})  # {tags: "camera"} or {group: "Cameras"}
        self.default_username = config.get("default_username", "root")
        self.default_password = config.get("default_password", "")
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._cached_targets: List[Dict] = []
        self._last_target_refresh: Optional[datetime] = None
    
    @property
    def connector_type(self) -> str:
        return "axis"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return AxisNormalizer()
    
    def _get_auth_header(self, username: str, password: str) -> str:
        """Create Basic auth header."""
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {credentials}"
    
    async def _get_session(self, target: Dict) -> aiohttp.ClientSession:
        """Get or create HTTP session for a target."""
        ip = target.get("ip")
        
        if ip not in self._sessions or self._sessions[ip].closed:
            auth_header = self._get_auth_header(
                target.get("username", "root"),
                target.get("password", "")
            )
            
            connector = aiohttp.TCPConnector(ssl=False)
            self._sessions[ip] = aiohttp.ClientSession(
                connector=connector,
                headers={"Authorization": auth_header}
            )
        
        return self._sessions[ip]
    
    async def start(self) -> None:
        """Start the connector."""
        if not self.targets:
            logger.warning("No Axis camera targets configured")
        
        await super().start()
        logger.info(f"Axis connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def stop(self) -> None:
        """Stop the connector."""
        # Close all sessions
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()
        
        await super().stop()
        logger.info("Axis connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to configured camera targets."""
        if not self.targets:
            return {
                "success": False,
                "message": "No targets configured",
                "details": None
            }
        
        results = []
        for target in self.targets:
            try:
                info = await self._get_device_info(target)
                results.append({
                    "ip": target.get("ip"),
                    "name": target.get("name"),
                    "success": True,
                    "model": info.get("model"),
                    "serial": info.get("serial"),
                })
            except Exception as e:
                results.append({
                    "ip": target.get("ip"),
                    "name": target.get("name"),
                    "success": False,
                    "error": str(e),
                })
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "message": f"Connected to {success_count}/{len(self.targets)} cameras",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll all camera targets for alerts."""
        alerts = []
        
        # Get targets (from manual list or PRTG)
        targets = await self._get_targets()
        
        # Poll cameras in batches - 200 concurrent is safe for most systems
        batch_size = 200
        for i in range(0, len(targets), batch_size):
            batch = targets[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self._poll_camera_safe(target) for target in batch],
                return_exceptions=True
            )
            for result in batch_results:
                if isinstance(result, list):
                    alerts.extend(result)
        
        logger.debug(f"Axis poll: {len(alerts)} alerts from {len(targets)} cameras")
        return alerts
    
    async def _poll_camera_safe(self, target: Dict) -> List[NormalizedAlert]:
        """Safely poll a camera, catching exceptions."""
        try:
            return await self._poll_camera(target)
        except Exception as e:
            logger.error(f"Error polling camera {target.get('ip')}: {e}")
            return [self._create_alert(target, "camera_offline", {"error": str(e)})]
    
    async def _get_targets(self) -> List[Dict]:
        """Get camera targets from configured source."""
        if self.camera_source == "prtg":
            # Refresh from PRTG every 5 minutes
            now = datetime.utcnow()
            if not self._cached_targets or not self._last_target_refresh or \
               (now - self._last_target_refresh).seconds > 300:
                self._cached_targets = await self._fetch_cameras_from_prtg()
                self._last_target_refresh = now
            return self._cached_targets
        return self.targets
    
    async def _fetch_cameras_from_prtg(self) -> List[Dict]:
        """Fetch camera list from PRTG based on filter."""
        try:
            from backend.database import DatabaseConnection
            db = DatabaseConnection()
            
            # Build query based on filter
            query = "SELECT device_name, host FROM prtg_devices WHERE 1=1"
            params = []
            
            if self.prtg_filter.get("tags"):
                query += " AND tags ILIKE %s"
                params.append(f"%{self.prtg_filter['tags']}%")
            if self.prtg_filter.get("group"):
                query += " AND device_group ILIKE %s"
                params.append(f"%{self.prtg_filter['group']}%")
            
            with db.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
            
            cameras = []
            for row in rows:
                if row.get("host"):
                    cameras.append({
                        "ip": row["host"],
                        "name": row.get("device_name", row["host"]),
                        "username": self.default_username,
                        "password": self.default_password,
                    })
            
            logger.info(f"Loaded {len(cameras)} cameras from PRTG")
            return cameras
        except Exception as e:
            logger.error(f"Failed to fetch cameras from PRTG: {e}")
            return self._cached_targets or []
    
    async def _poll_camera(self, target: Dict) -> List[NormalizedAlert]:
        """Poll single camera for status and events."""
        alerts = []
        ip = target.get("ip")
        
        try:
            # Check camera is reachable and get device info
            info = await self._get_device_info(target)
            target["_model"] = info.get("model", "")
            target["_firmware"] = info.get("firmware", "")
            
            # Check storage status
            try:
                storage = await self._get_storage_status(target)
                if storage:
                    alerts.extend(self._check_storage(target, storage))
            except Exception as e:
                logger.debug(f"Could not get storage status for {ip}: {e}")
            
            # Check system log for hardware/power issues
            try:
                log_alerts = await self._check_system_log(target)
                alerts.extend(log_alerts)
            except Exception as e:
                logger.debug(f"Could not get system log for {ip}: {e}")
            
            # Check temperature
            try:
                temp_alerts = await self._check_temperature(target)
                alerts.extend(temp_alerts)
            except Exception as e:
                logger.debug(f"Could not get temperature for {ip}: {e}")
            
        except aiohttp.ClientResponseError as e:
            if e.status in (401, 403):
                alerts.append(self._create_alert(target, "camera_auth_failed", {"error": str(e), "status": e.status}))
            else:
                alerts.append(self._create_alert(target, "camera_offline", {"error": str(e)}))
        except Exception as e:
            logger.warning(f"Camera {ip} appears offline: {e}")
            alerts.append(self._create_alert(target, "camera_offline", {"error": str(e)}))
        
        return alerts
    
    async def _get_device_info(self, target: Dict) -> Dict[str, Any]:
        """Get basic device info via VAPIX."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        async with session.get(
            f"http://{ip}/axis-cgi/basicdeviceinfo.cgi",
            timeout=aiohttp.ClientTimeout(total=3)
        ) as response:
            response.raise_for_status()
            text = await response.text()
            
            # Parse response (varies by firmware version)
            info = {}
            for line in text.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    info[key.strip().lower()] = value.strip()
            
            return {
                "model": info.get("prodshortname", info.get("brand", "Axis Camera")),
                "serial": info.get("serialnumber", ""),
                "firmware": info.get("version", ""),
            }
    
    async def _get_storage_status(self, target: Dict) -> Optional[Dict]:
        """Get storage/disk status."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        try:
            async with session.get(
                f"http://{ip}/axis-cgi/disks/list.cgi",
                timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    # Parse disk info (simplified)
                    return {"raw": text, "available": True}
        except Exception:
            pass
        
        return None
    
    async def _get_system_log(self, target: Dict) -> str:
        """Get system log via VAPIX."""
        ip = target.get("ip")
        session = await self._get_session(target)
        try:
            async with session.get(f"http://{ip}/axis-cgi/systemlog.cgi", timeout=aiohttp.ClientTimeout(total=3)) as response:
                if response.status == 200:
                    return await response.text()
        except Exception:
            pass
        return ""
    
    async def _check_system_log(self, target: Dict) -> List[NormalizedAlert]:
        """Parse system log for hardware/power alerts."""
        alerts = []
        log_text = await self._get_system_log(target)
        if not log_text:
            return alerts
        
        recent_lines = log_text.strip().split("\n")[-50:]
        detected_types = set()
        
        for line in recent_lines:
            for pattern, alert_type, description in SYSTEM_LOG_PATTERNS:
                if alert_type not in detected_types and re.search(pattern, line, re.IGNORECASE):
                    detected_types.add(alert_type)
                    alerts.append(self._create_alert(target, alert_type, {"log_entry": line, "description": description}))
        return alerts
    
    async def _check_temperature(self, target: Dict) -> List[NormalizedAlert]:
        """Check camera temperature via VAPIX."""
        alerts = []
        ip = target.get("ip")
        session = await self._get_session(target)
        try:
            async with session.get(f"http://{ip}/axis-cgi/param.cgi?action=list&group=Status.Temperature", timeout=aiohttp.ClientTimeout(total=3)) as response:
                if response.status == 200:
                    text = await response.text()
                    for line in text.split("\n"):
                        if "Temperature" in line and "=" in line:
                            try:
                                temp = float(re.sub(r"[^\d.]", "", line.split("=")[1]))
                                if temp > 70:
                                    alerts.append(self._create_alert(target, "temperature_critical", {"temperature": temp}))
                                elif temp > 60:
                                    alerts.append(self._create_alert(target, "temperature_warning", {"temperature": temp}))
                            except (ValueError, IndexError):
                                pass
        except Exception:
            pass
        return alerts
    
    def _check_storage(self, target: Dict, storage: Dict) -> List[NormalizedAlert]:
        """Check storage status and generate alerts if needed."""
        alerts = []
        
        raw = storage.get("raw", "")
        
        # Check for disk errors
        if "error" in raw.lower() or "fail" in raw.lower():
            alerts.append(self._create_alert(target, "storage_failure", storage))
        
        # Check for full disk
        if "full" in raw.lower() or "100%" in raw:
            alerts.append(self._create_alert(target, "storage_full", storage))
        
        return alerts
    
    def _create_alert(self, target: Dict, event_type: str, event_data: Dict) -> NormalizedAlert:
        """Create normalized alert from camera event."""
        raw_data = {
            "device_ip": target.get("ip"),
            "device_name": target.get("name"),
            "camera_model": target.get("_model", ""),
            "firmware_version": target.get("_firmware", ""),
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        """Process polled alerts."""
        alert_manager = get_alert_manager()
        
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Axis alert: {e}")
