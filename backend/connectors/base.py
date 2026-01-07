"""
OpsConductor Connector Base Classes

Abstract base classes that all connectors must implement.
"""

import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.models import NormalizedAlert, Severity, Category, ConnectorStatus

logger = logging.getLogger(__name__)


class BaseNormalizer(ABC):
    """
    Base class for alert normalizers.
    
    Each connector has a normalizer that transforms raw alert data
    from the source system into the standard NormalizedAlert format.
    """
    
    @property
    @abstractmethod
    def source_system(self) -> str:
        """Return the source system identifier (e.g., 'prtg', 'snmp')."""
        pass
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Transform raw alert data to standard NormalizedAlert.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            NormalizedAlert conforming to standard schema
        """
        pass
    
    @abstractmethod
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """
        Determine severity from raw data.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            Mapped Severity enum value
        """
        pass
    
    @abstractmethod
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """
        Determine category from raw data.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            Mapped Category enum value
        """
        pass
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """
        Generate deduplication fingerprint for alert.
        
        Default implementation creates hash from source system,
        source alert ID, device, and alert type. Override for
        custom deduplication logic.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            SHA256 hash string for deduplication
        """
        # Extract key fields for fingerprint
        source_id = str(raw_data.get("source_alert_id", ""))
        device = str(raw_data.get("device_ip") or raw_data.get("device_name") or "")
        alert_type = str(raw_data.get("alert_type", ""))
        
        # Create fingerprint string
        fingerprint_str = f"{self.source_system}:{source_id}:{device}:{alert_type}"
        
        # Return SHA256 hash
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """
        Determine if this is a clear/recovery event.
        
        Override in subclass for source-specific logic.
        
        Args:
            raw_data: Raw alert data from source system
            
        Returns:
            True if this is a clear/recovery event
        """
        return False


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
        from core.event_bus import get_event_bus, EventType
        
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
