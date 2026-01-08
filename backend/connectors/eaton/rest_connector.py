"""
Eaton UPS REST API Connector

Polls Eaton Network-M2 cards via REST API for alarms.
"""

import logging
import aiohttp
import ssl
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus, Severity, Category
from backend.core.alert_manager import get_alert_manager
from backend.utils.ip_utils import validate_device_ip
from backend.db import db_query

logger = logging.getLogger(__name__)


# Alarm code to description mapping (common Eaton alarm codes)
ALARM_CODES = {
    "1001": "UPS on battery",
    "1002": "Low battery",
    "1003": "Battery depleted",
    "1004": "Battery fault",
    "1005": "Battery needs replacement",
    "1006": "Overload",
    "1007": "Over temperature",
    "1008": "Output short circuit",
    "1009": "UPS fault",
    "1010": "Input power failure",
    "1011": "Bypass active",
    "1012": "UPS shutdown imminent",
    "1013": "Charger failure",
    "1014": "Fan failure",
    "1015": "Fuse failure",
    "1016": "Sequential shutdown canceled",
    "1017": "General alarm",
    "1018": "Awaiting power",
    "1019": "Shutdown pending",
    "1020": "Shutdown in progress",
    "1101": "Communication lost",
    "1102": "Communication restored",
    "1201": "Test in progress",
    "1202": "Test passed",
    "1203": "Test failed",
    "1301": "Configuration changed",
    "1302": "System event",
    "5001": "Informational event",
}

# Level to severity mapping (fallback)
LEVEL_SEVERITY = {
    "critical": Severity.CRITICAL,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
}


class EatonRESTNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Eaton REST API alarms.
    
    All mappings come from severity_mappings and category_mappings tables.
    """
    
    def __init__(self):
        self._severity_cache = {}
        self._category_cache = {}
        self._cache_loaded = False
    
    def _load_mappings(self):
        """Load mappings from database."""
        if self._cache_loaded:
            return
        
        try:
            # Load severity mappings
            severity_rows = db_query(
                "SELECT source_value, target_severity, enabled, description FROM severity_mappings WHERE connector_type = %s",
                ("eaton_rest",)
            )
            for row in severity_rows:
                self._severity_cache[row['source_value']] = {
                    'severity': row['target_severity'],
                    'enabled': row['enabled'],
                    'description': row.get('description', '')
                }
            
            # Load category mappings
            category_rows = db_query(
                "SELECT source_value, target_category, enabled, description FROM category_mappings WHERE connector_type = %s",
                ("eaton_rest",)
            )
            for row in category_rows:
                self._category_cache[row['source_value']] = {
                    'category': row['target_category'],
                    'enabled': row['enabled'],
                    'description': row.get('description', '')
                }
            
            logger.info(f"Loaded eaton_rest mappings: {len(self._severity_cache)} severity, {len(self._category_cache)} category")
            self._cache_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load eaton_rest mappings: {e}")
            self._cache_loaded = True  # Don't retry on every call
    
    def is_alarm_enabled(self, alarm_code: str) -> bool:
        """Check if this alarm code is enabled in mappings."""
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(alarm_code)
        if severity_mapping and not severity_mapping.get('enabled', True):
            return False
        
        return True
    
    @property
    def source_system(self) -> str:
        return "eaton"
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Normalize Eaton REST API alarm to standard format."""
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alarm = raw_data.get("alarm", {})
        
        # Validate device IP
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping Eaton alarm - no valid device_ip: {e}")
            return None
        
        alarm_id = alarm.get("id", "")
        alarm_code = alarm.get("code", "")
        level = alarm.get("level", "info").lower()
        description = alarm.get("description", "")
        state = alarm.get("state", "open")
        timestamp = alarm.get("timestamp", "")
        lifecycle = alarm.get("lifeCycle", {})
        alarm_device = alarm.get("device", {})
        alarm_device_name = alarm_device.get("name", "")
        
        # Check if this alarm code is enabled in mappings
        if not self.is_alarm_enabled(alarm_code):
            logger.debug(f"Skipping disabled Eaton alarm code: {alarm_code}")
            return None
        
        # Get human-readable description
        if description.isdigit():
            # Description is a code, look up the actual description
            description = ALARM_CODES.get(description, f"Alarm code {description}")
        
        alarm_description = ALARM_CODES.get(alarm_code, description or f"Alarm {alarm_code}")
        
        # Determine severity from database mapping first, then fallback
        self._load_mappings()
        severity_mapping = self._severity_cache.get(alarm_code)
        if severity_mapping:
            severity = Severity(severity_mapping['severity'])
        else:
            severity = LEVEL_SEVERITY.get(level, Severity.WARNING)
        
        # Is this a clear event?
        is_clear = state == "closed" or not lifecycle.get("active", True)
        if is_clear:
            severity = Severity.CLEAR
        
        # Build title
        title = f"Eaton UPS {alarm_description}"
        if alarm_device_name:
            title = f"{title} - {alarm_device_name}"
        
        # Build message
        message_parts = []
        if device_name:
            message_parts.append(f"UPS: {device_name}")
        elif device_ip:
            message_parts.append(f"UPS: {device_ip}")
        message_parts.append(f"Alarm: {alarm_description}")
        if alarm_code:
            message_parts.append(f"Code: {alarm_code}")
        if alarm_device_name and alarm_device_name != device_name:
            message_parts.append(f"Component: {alarm_device_name}")
        if lifecycle.get("openAt"):
            message_parts.append(f"Started: {lifecycle['openAt']}")
        if is_clear and lifecycle.get("closeAt"):
            message_parts.append(f"Cleared: {lifecycle['closeAt']}")
        
        message = " | ".join(message_parts)
        
        # Parse timestamp
        try:
            occurred_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            occurred_at = datetime.utcnow()
        
        # source_alert_id must be STABLE for deduplication
        source_alert_id = f"{validated_ip}:{alarm_code}:{alarm_id}"
        
        # Determine category from database mapping first, then fallback
        category_mapping = self._category_cache.get(alarm_code)
        if category_mapping:
            category = Category(category_mapping['category'])
        else:
            category = Category.POWER
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=source_alert_id,
            device_ip=validated_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"eaton_{alarm_code}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        alarm = raw_data.get("alarm", {})
        level = alarm.get("level", "info").lower()
        return LEVEL_SEVERITY.get(level, Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        return Category.POWER


class EatonRESTConnector(PollingConnector):
    """
    Eaton UPS connector using REST API (Network-M2 cards).
    
    Polls active alarms from Eaton Network-M2 cards.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.username = config.get("username", "admin")
        self.password = config.get("password", "")
        self.verify_ssl = config.get("verify_ssl", False)
        self._tokens: Dict[str, Dict[str, Any]] = {}  # IP -> {token, expires_at}
    
    @property
    def connector_type(self) -> str:
        return "eaton_rest"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return EatonRESTNormalizer()
    
    async def start(self) -> None:
        """Start the connector."""
        if not self.targets:
            logger.warning("No Eaton UPS targets configured")
        
        await super().start()
        logger.info(f"Eaton REST connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to configured UPS targets."""
        if not self.targets:
            return {
                "success": False,
                "message": "No targets configured",
                "details": None
            }
        
        results = []
        for target in self.targets:
            ip = target.get("ip")
            name = target.get("name", ip)
            username = target.get("username", self.username)
            password = target.get("password", self.password)
            
            try:
                token = await self._get_token(ip, username, password)
                if token:
                    # Try to get UPS info
                    info = await self._get_ups_info(ip, token)
                    results.append({
                        "ip": ip,
                        "name": name,
                        "success": True,
                        "model": info.get("identification", {}).get("model", "Unknown"),
                        "serial": info.get("identification", {}).get("serialNumber", ""),
                    })
                else:
                    results.append({
                        "ip": ip,
                        "name": name,
                        "success": False,
                        "error": "Failed to authenticate",
                    })
            except Exception as e:
                results.append({
                    "ip": ip,
                    "name": name,
                    "success": False,
                    "error": str(e),
                })
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "message": f"Connected to {success_count}/{len(self.targets)} UPS devices",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll all UPS targets for active alarms."""
        alerts = []
        
        for target in self.targets:
            try:
                target_alerts = await self._poll_target(target)
                alerts.extend(target_alerts)
            except Exception as e:
                logger.error(f"Error polling Eaton UPS {target.get('ip')}: {e}")
                
                # Generate communication lost alert
                raw_data = {
                    "device_ip": target.get("ip"),
                    "device_name": target.get("name"),
                    "alarm": {
                        "id": "comm_lost",
                        "code": "1101",
                        "level": "critical",
                        "description": "Communication lost",
                        "state": "open",
                        "timestamp": datetime.utcnow().isoformat(),
                        "lifeCycle": {"active": True, "openAt": datetime.utcnow().isoformat()},
                        "device": {"name": target.get("name", target.get("ip"))}
                    }
                }
                alert = self.normalizer.normalize(raw_data)
                if alert:
                    alerts.append(alert)
        
        logger.debug(f"Eaton REST poll: {len(alerts)} alerts from {len(self.targets)} targets")
        return alerts
    
    async def _poll_target(self, target: Dict) -> List[NormalizedAlert]:
        """Poll single UPS for active alarms."""
        alerts = []
        ip = target.get("ip")
        name = target.get("name", ip)
        username = target.get("username", self.username)
        password = target.get("password", self.password)
        
        # Get or refresh token
        token = await self._get_token(ip, username, password)
        if not token:
            raise Exception("Failed to authenticate")
        
        # Get active alarms from alarmService
        alarm_service = await self._api_get(ip, token, "/rest/mbdetnrs/1.0/alarmService")
        if not alarm_service:
            return alerts
        
        active_count = alarm_service.get("activeAlarmsCount", 0)
        
        if active_count > 0:
            # Get active alarms list
            active_alarms = await self._api_get(ip, token, "/rest/mbdetnrs/1.0/alarmService/activeAlarms")
            if active_alarms and active_alarms.get("members"):
                for member in active_alarms["members"]:
                    alarm_url = member.get("@id", "")
                    if alarm_url:
                        # Get full alarm details
                        alarm = await self._api_get(ip, token, alarm_url)
                        if alarm:
                            raw_data = {
                                "device_ip": ip,
                                "device_name": name,
                                "alarm": alarm,
                            }
                            alert = self.normalizer.normalize(raw_data)
                            if alert:
                                alerts.append(alert)
        
        return alerts
    
    async def _get_token(self, ip: str, username: str, password: str) -> Optional[str]:
        """Get OAuth2 token, using cache if valid."""
        cached = self._tokens.get(ip)
        if cached:
            # Check if token is still valid (with 60s buffer)
            if cached.get("expires_at", 0) > datetime.utcnow().timestamp() + 60:
                return cached.get("token")
        
        # Request new token
        ssl_context = ssl.create_default_context()
        if not self.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                url = f"https://{ip}/rest/mbdetnrs/1.0/oauth2/token"
                data = {
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                }
                
                async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        token = result.get("access_token")
                        expires_in = result.get("expires_in", 899)
                        
                        if token:
                            self._tokens[ip] = {
                                "token": token,
                                "expires_at": datetime.utcnow().timestamp() + expires_in,
                            }
                            return token
                    else:
                        logger.warning(f"Failed to get token from {ip}: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error getting token from {ip}: {e}")
        
        return None
    
    async def _api_get(self, ip: str, token: str, path: str) -> Optional[Dict]:
        """Make authenticated GET request to Eaton API."""
        ssl_context = ssl.create_default_context()
        if not self.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                # Handle both full URLs and relative paths
                if path.startswith("/"):
                    url = f"https://{ip}{path}"
                else:
                    url = f"https://{ip}/{path}"
                
                headers = {"Authorization": f"Bearer {token}"}
                
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.warning(f"API request to {url} failed: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error making API request to {ip}: {e}")
        
        return None
    
    async def _get_ups_info(self, ip: str, token: str) -> Dict:
        """Get UPS identification info."""
        return await self._api_get(ip, token, "/rest/mbdetnrs/1.0/powerDistributions/1") or {}
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        """Process polled alerts."""
        alert_manager = get_alert_manager()
        
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Eaton alert: {e}")
