"""
OpsConductor Connector Base Classes

Abstract base classes that all connectors must implement.
Provides database-driven alert mapping with standard methods.
"""

import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.core.models import NormalizedAlert, Severity, Category, ConnectorStatus

logger = logging.getLogger(__name__)


class BaseNormalizer(ABC):
    """
    Base class for alert normalizers with database-driven mappings.
    
    Each connector has a normalizer that transforms raw alert data
    from the source system into the standard NormalizedAlert format.
    
    Subclasses should set:
        - connector_type: str (e.g., "prtg", "axis")
        - default_category: Category (fallback when no mapping found)
    
    Standard methods provided:
        - _load_mappings(): Load severity/category mappings from database
        - is_event_enabled(): Check if event type is enabled
        - _get_severity(): Get severity from database mapping
        - _get_category(): Get category from database mapping
        - is_clear_event(): Standard clear event detection
    """
    
    # Subclasses must set these
    connector_type: str = None
    default_category: Category = Category.UNKNOWN
    
    # Clear event suffixes (standard across all connectors)
    CLEAR_SUFFIXES = ('_restored', '_up', '_online', '_ok', '_normal', '_cleared', '_clear')
    
    def __init__(self):
        """Initialize normalizer with empty caches."""
        self._severity_cache: Dict[str, Dict] = {}
        self._category_cache: Dict[str, Dict] = {}
        self._cache_loaded = False
    
    @property
    def source_system(self) -> str:
        """Return the source system identifier."""
        return self.connector_type
    
    def _load_mappings(self) -> None:
        """
        Load severity and category mappings from database.
        
        Caches mappings for performance. Call refresh_mappings() to reload.
        """
        if self._cache_loaded:
            return
        
        try:
            from backend.utils.db import db_query
            
            # Load severity mappings
            severity_rows = db_query(
                "SELECT source_value, target_severity, enabled, description "
                "FROM severity_mappings WHERE connector_type = %s",
                (self.connector_type,)
            )
            for row in severity_rows:
                self._severity_cache[row["source_value"]] = {
                    "severity": row["target_severity"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            # Load category mappings
            category_rows = db_query(
                "SELECT source_value, target_category, enabled, description "
                "FROM category_mappings WHERE connector_type = %s",
                (self.connector_type,)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(
                f"Loaded {self.connector_type} mappings: "
                f"{len(self._severity_cache)} severity, {len(self._category_cache)} category"
            )
            
        except Exception as e:
            logger.error(f"Failed to load {self.connector_type} mappings: {e}")
            self._cache_loaded = True  # Don't retry on every call
    
    def refresh_mappings(self) -> None:
        """Force reload of mappings from database."""
        self._severity_cache.clear()
        self._category_cache.clear()
        self._cache_loaded = False
        self._load_mappings()
    
    def is_event_enabled(self, event_type: str) -> bool:
        """
        Check if this event type is enabled in mappings.
        
        Returns False if:
        - Event type is not in any mapping (unknown events are ignored)
        - Event type is explicitly disabled in mappings
        
        Args:
            event_type: The event/alert type string
            
        Returns:
            True if event should be processed
        """
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(event_type)
        category_mapping = self._category_cache.get(event_type)
        
        # If not in ANY mapping, treat as disabled (unknown event type)
        if not severity_mapping and not category_mapping:
            logger.debug(f"Event type '{event_type}' not in {self.connector_type} mappings - ignoring")
            return False
        
        # Check if explicitly disabled
        if severity_mapping and not severity_mapping.get("enabled", True):
            return False
        if category_mapping and not category_mapping.get("enabled", True):
            return False
        
        return True
    
    def _get_severity(self, event_type: str) -> Severity:
        """
        Get severity from database mapping.
        
        Args:
            event_type: The event/alert type string
            
        Returns:
            Mapped Severity enum value, or WARNING as fallback
        """
        self._load_mappings()
        
        mapping = self._severity_cache.get(event_type)
        if mapping:
            try:
                return Severity(mapping["severity"])
            except ValueError:
                logger.warning(f"Invalid severity value in mapping: {mapping['severity']}")
        
        return Severity.WARNING
    
    def _get_category(self, event_type: str) -> Category:
        """
        Get category from database mapping.
        
        Args:
            event_type: The event/alert type string
            
        Returns:
            Mapped Category enum value, or default_category as fallback
        """
        self._load_mappings()
        
        mapping = self._category_cache.get(event_type)
        if mapping:
            try:
                return Category(mapping["category"])
            except ValueError:
                logger.warning(f"Invalid category value in mapping: {mapping['category']}")
        
        return self.default_category
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """
        Determine severity from raw data.
        
        Default implementation extracts event_type/alert_type and looks up mapping.
        Override for connector-specific logic.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            Mapped Severity enum value
        """
        event_type = raw_data.get("alert_type") or raw_data.get("event_type", "")
        return self._get_severity(event_type)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """
        Determine category from raw data.
        
        Default implementation extracts event_type/alert_type and looks up mapping.
        Override for connector-specific logic.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            Mapped Category enum value
        """
        event_type = raw_data.get("alert_type") or raw_data.get("event_type", "")
        return self._get_category(event_type)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """
        Generate deduplication fingerprint for alert.
        
        Default implementation creates hash from source system,
        device IP, and alert type. Override for custom logic.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            SHA256 hash string for deduplication
        """
        device = str(raw_data.get("device_ip") or raw_data.get("device_name") or "")
        alert_type = str(raw_data.get("alert_type") or raw_data.get("event_type", ""))
        
        fingerprint_str = f"{self.connector_type}:{device}:{alert_type}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, event_type: str, raw_data: Dict[str, Any] = None) -> bool:
        """
        Determine if this is a clear/recovery event.
        
        Standard logic:
        1. Check if severity mapping returns 'clear'
        2. Check if event_type ends with clear suffixes
        
        Args:
            event_type: The event/alert type string
            raw_data: Optional raw data for additional context
            
        Returns:
            True if this is a clear/recovery event
        """
        # Check if database mapping says this is a clear event
        severity = self._get_severity(event_type)
        if severity == Severity.CLEAR:
            return True
        
        # Check standard clear suffixes
        return event_type.lower().endswith(self.CLEAR_SUFFIXES)
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform raw alert data to standard NormalizedAlert.
        
        Returns None if event is disabled or should be filtered.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            NormalizedAlert conforming to standard schema, or None
        """
        pass


class BaseConnector(ABC):
    """
    Base class for all alert source connectors.
    
    Connectors are responsible for:
    - Connecting to external systems
    - Receiving or polling for alerts
    - Passing raw data to normalizer
    - Managing connection state
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration.
        
        Args:
            config: Connector configuration from database
        """
        self.config = config
        self.enabled = False
        self.status = ConnectorStatus.UNKNOWN
        self.error_message: Optional[str] = None
        self.last_poll_at: Optional[datetime] = None
        self.alerts_received: int = 0
        self._normalizer: Optional[BaseNormalizer] = None
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """
        Return connector type identifier.
        
        Returns:
            Type string (e.g., 'prtg', 'snmp_trap', 'eaton')
        """
        pass
    
    @property
    def normalizer(self) -> BaseNormalizer:
        """Get the normalizer for this connector."""
        if self._normalizer is None:
            self._normalizer = self._create_normalizer()
        return self._normalizer
    
    @abstractmethod
    def _create_normalizer(self) -> BaseNormalizer:
        """
        Create and return the normalizer instance.
        
        Returns:
            Normalizer instance for this connector
        """
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the connector.
        
        For poll-based connectors: Start polling loop
        For push-based connectors: Start listening
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the connector and cleanup resources.
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connectivity to external system.
        
        Returns:
            Dict with:
                success: bool
                message: str
                details: Optional[Dict] - Additional info
        """
        pass
    
    async def poll(self) -> List[NormalizedAlert]:
        """
        Poll for alerts (for poll-based connectors).
        
        Default implementation raises NotImplementedError.
        Override in subclass for poll-based connectors.
        
        Returns:
            List of normalized alerts
        """
        raise NotImplementedError(f"{self.connector_type} does not support polling")
    
    async def handle_webhook(self, data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Handle incoming webhook data (for push-based connectors).
        
        Default implementation raises NotImplementedError.
        Override in subclass for webhook-based connectors.
        
        Args:
            data: Webhook payload
            
        Returns:
            Normalized alert or None if invalid
        """
        raise NotImplementedError(f"{self.connector_type} does not support webhooks")
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Normalize raw data using this connector's normalizer.
        
        Args:
            raw_data: Raw alert data
            
        Returns:
            NormalizedAlert
        """
        return self.normalizer.normalize(raw_data)
    
    def set_status(self, status: ConnectorStatus, error: str = None) -> None:
        """Update connector status."""
        self.status = status
        self.error_message = error
        if status == ConnectorStatus.ERROR:
            logger.error(f"Connector {self.connector_type} error: {error}")
        else:
            logger.info(f"Connector {self.connector_type} status: {status.value}")
    
    def increment_alerts(self, count: int = 1) -> None:
        """Increment received alert counter."""
        self.alerts_received += count
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default."""
        return self.config.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connector state to dictionary."""
        return {
            "type": self.connector_type,
            "enabled": self.enabled,
            "status": self.status.value,
            "error_message": self.error_message,
            "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
            "alerts_received": self.alerts_received,
        }


class PollingConnector(BaseConnector):
    """
    Base class for poll-based connectors.
    
    Adds polling loop infrastructure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.poll_interval = config.get("poll_interval", 60)
        self._polling = False
        self._poll_task = None
    
    async def start(self) -> None:
        """Start polling loop."""
        if self._polling:
            return
        
        self._polling = True
        self.enabled = True
        logger.info(f"Starting {self.connector_type} polling (interval: {self.poll_interval}s)")
        
        # Start poll loop as background task
        import asyncio
        self._poll_task = asyncio.create_task(self._poll_loop())
    
    async def stop(self) -> None:
        """Stop polling loop."""
        self._polling = False
        self.enabled = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        
        logger.info(f"Stopped {self.connector_type} polling")
    
    async def _poll_loop(self) -> None:
        """Internal polling loop."""
        import asyncio
        
        while self._polling:
            try:
                alerts = await self.poll()
                self.last_poll_at = datetime.utcnow()
                
                if alerts:
                    self.increment_alerts(len(alerts))
                    await self._process_alerts(alerts)
                
                self.set_status(ConnectorStatus.CONNECTED)
                
            except Exception as e:
                self.set_status(ConnectorStatus.ERROR, str(e))
                logger.exception(f"Error in {self.connector_type} poll loop")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        """
        Process received alerts.
        
        Override to customize processing, or leave default
        to publish to event bus.
        """
        from backend.core.event_bus import get_event_bus, EventType
        
        bus = get_event_bus()
        for alert in alerts:
            await bus.publish(
                EventType.ALERT_CREATED,
                alert,
                source=self.connector_type
            )


class WebhookConnector(BaseConnector):
    """
    Base class for webhook-based connectors.
    
    These connectors receive alerts via HTTP webhooks rather than polling.
    """
    
    async def start(self) -> None:
        """Mark connector as enabled (webhook endpoint handles receiving)."""
        self.enabled = True
        self.set_status(ConnectorStatus.CONNECTED)
        logger.info(f"Started {self.connector_type} webhook connector")
    
    async def stop(self) -> None:
        """Mark connector as disabled."""
        self.enabled = False
        self.set_status(ConnectorStatus.DISCONNECTED)
        logger.info(f"Stopped {self.connector_type} webhook connector")
    
    async def receive_webhook(self, data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Process incoming webhook and return normalized alert.
        
        Args:
            data: Webhook payload
            
        Returns:
            NormalizedAlert or None if invalid/filtered
        """
        try:
            alert = await self.handle_webhook(data)
            if alert:
                self.increment_alerts()
                self.last_poll_at = datetime.utcnow()
            return alert
        except Exception as e:
            logger.exception(f"Error processing {self.connector_type} webhook")
            raise
