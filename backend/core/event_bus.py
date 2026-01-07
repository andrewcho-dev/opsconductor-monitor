"""
OpsConductor Event Bus

Simple in-process async event bus for decoupling components.
Allows alert_manager to emit events that notification_service and
websocket handlers can subscribe to.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Coroutine
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types."""
    # Alert events
    ALERT_CREATED = "alert.created"
    ALERT_UPDATED = "alert.updated"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_SUPPRESSED = "alert.suppressed"
    ALERT_REOPENED = "alert.reopened"
    
    # Connector events
    CONNECTOR_CONNECTED = "connector.connected"
    CONNECTOR_DISCONNECTED = "connector.disconnected"
    CONNECTOR_ERROR = "connector.error"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"


@dataclass
class Event:
    """Event wrapper with metadata."""
    type: EventType
    data: Any
    timestamp: datetime = None
    source: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Simple async event bus for in-process event distribution.
    
    Usage:
        bus = EventBus()
        
        # Subscribe
        async def handle_alert(event: Event):
            print(f"Alert: {event.data}")
        
        bus.subscribe(EventType.ALERT_CREATED, handle_alert)
        
        # Publish
        await bus.publish(EventType.ALERT_CREATED, alert_data)
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._subscribers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._initialized = True
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async function to call when event occurs
        """
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
            
        Returns:
            True if handler was found and removed
        """
        try:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler from {event_type.value}")
            return True
        except ValueError:
            return False
    
    async def publish(
        self, 
        event_type: EventType, 
        data: Any, 
        source: str = None,
        wait: bool = False
    ) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Event payload
            source: Optional source identifier
            wait: If True, wait for all handlers to complete
        """
        event = Event(type=event_type, data=data, source=source)
        handlers = self._subscribers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"No subscribers for {event_type.value}")
            return
        
        logger.debug(f"Publishing {event_type.value} to {len(handlers)} handlers")
        
        if wait:
            # Wait for all handlers to complete
            await asyncio.gather(
                *[self._safe_call(handler, event) for handler in handlers],
                return_exceptions=True
            )
        else:
            # Fire and forget - don't block
            for handler in handlers:
                asyncio.create_task(self._safe_call(handler, event))
    
    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Call handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in event handler for {event.type.value}: {e}",
                exc_info=True
            )
    
    def clear(self) -> None:
        """Clear all subscriptions."""
        self._subscribers.clear()
        logger.info("EventBus cleared all subscriptions")
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))


# Global instance
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def publish_event(
    event_type: EventType, 
    data: Any, 
    source: str = None,
    wait: bool = False
) -> None:
    """Convenience function to publish event to global bus."""
    bus = get_event_bus()
    await bus.publish(event_type, data, source, wait)


def subscribe_event(event_type: EventType, handler: EventHandler) -> None:
    """Convenience function to subscribe to global bus."""
    bus = get_event_bus()
    bus.subscribe(event_type, handler)
