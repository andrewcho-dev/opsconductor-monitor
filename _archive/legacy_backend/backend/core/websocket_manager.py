"""
WebSocket Manager for Real-Time Alert Updates

Manages WebSocket connections and broadcasts alert events to all connected clients.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time alert updates.
    
    Supports:
    - Multiple concurrent connections
    - Broadcasting to all clients
    - Topic-based subscriptions (alerts, connectors, etc.)
    """
    
    def __init__(self):
        # All active connections
        self.active_connections: Set[WebSocket] = set()
        # Connections by topic for targeted broadcasts
        self.topic_connections: Dict[str, Set[WebSocket]] = {
            "alerts": set(),
            "connectors": set(),
            "system": set(),
        }
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, topics: Optional[list] = None):
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            topics: Optional list of topics to subscribe to (default: all)
        """
        await websocket.accept()
        
        async with self._lock:
            self.active_connections.add(websocket)
            
            # Subscribe to topics
            subscribe_topics = topics or ["alerts", "connectors", "system"]
            for topic in subscribe_topics:
                if topic in self.topic_connections:
                    self.topic_connections[topic].add(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial connection confirmation
        await self._send_json(websocket, {
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "topics": subscribe_topics,
        })
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
            
            # Remove from all topic subscriptions
            for topic_set in self.topic_connections.values():
                topic_set.discard(websocket)
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def _send_json(self, websocket: WebSocket, data: dict):
        """Send JSON data to a single connection."""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: dict, topic: Optional[str] = None):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast
            topic: Optional topic to target specific subscribers
        """
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Get target connections
        if topic and topic in self.topic_connections:
            connections = self.topic_connections[topic].copy()
        else:
            connections = self.active_connections.copy()
        
        if not connections:
            return
        
        # Broadcast to all connections
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)
        
        if connections:
            logger.debug(f"Broadcast to {len(connections) - len(disconnected)} clients: {message.get('type', 'unknown')}")
    
    async def broadcast_alert_event(self, event_type: str, alert_data: dict):
        """
        Broadcast an alert event to all subscribers.
        
        Args:
            event_type: Type of event (created, updated, cleared, deleted)
            alert_data: The alert data to broadcast
        """
        message = {
            "type": "alert_event",
            "event": event_type,
            "alert": alert_data,
        }
        await self.broadcast(message, topic="alerts")
    
    async def broadcast_connector_event(self, event_type: str, connector_data: dict):
        """
        Broadcast a connector event to all subscribers.
        
        Args:
            event_type: Type of event (connected, disconnected, polling, error)
            connector_data: The connector data to broadcast
        """
        message = {
            "type": "connector_event",
            "event": event_type,
            "connector": connector_data,
        }
        await self.broadcast(message, topic="connectors")
    
    async def broadcast_system_event(self, event_type: str, data: dict):
        """
        Broadcast a system event to all subscribers.
        
        Args:
            event_type: Type of event (poll_complete, error, etc.)
            data: Event data
        """
        message = {
            "type": "system_event",
            "event": event_type,
            "data": data,
        }
        await self.broadcast(message, topic="system")
    
    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


# Per-process connection manager instances (keyed by PID for forked workers)
_manager_instances: dict = {}


def get_websocket_manager() -> ConnectionManager:
    """
    Get the WebSocket connection manager for this worker process.
    
    Each Uvicorn worker (forked process) gets its own instance.
    This ensures each worker manages its own WebSocket connections.
    """
    import os
    pid = os.getpid()
    if pid not in _manager_instances:
        _manager_instances[pid] = ConnectionManager()
        logger.info(f"Created ConnectionManager for worker PID {pid}")
    return _manager_instances[pid]


# Convenience functions for broadcasting from anywhere in the app
async def broadcast_alert_created(alert_data: dict):
    """Broadcast that a new alert was created."""
    manager = get_websocket_manager()
    await manager.broadcast_alert_event("created", alert_data)


async def broadcast_alert_updated(alert_data: dict):
    """Broadcast that an alert was updated."""
    manager = get_websocket_manager()
    await manager.broadcast_alert_event("updated", alert_data)


async def broadcast_alert_cleared(alert_data: dict):
    """Broadcast that an alert was cleared."""
    manager = get_websocket_manager()
    await manager.broadcast_alert_event("cleared", alert_data)


async def broadcast_alert_deleted(alert_id: str):
    """Broadcast that an alert was deleted."""
    manager = get_websocket_manager()
    await manager.broadcast_alert_event("deleted", {"id": alert_id})


async def broadcast_poll_complete(connector_name: str, alert_count: int):
    """Broadcast that a polling cycle completed."""
    manager = get_websocket_manager()
    await manager.broadcast_system_event("poll_complete", {
        "connector": connector_name,
        "alerts": alert_count,
    })


async def setup_redis_subscriptions():
    """
    Subscribe WebSocket broadcaster to Redis pub/sub events.
    
    This enables cross-process communication - Celery workers publish
    events to Redis, and this FastAPI process receives them and
    broadcasts to WebSocket clients.
    
    Call this during application startup.
    """
    from backend.core.redis_pubsub import get_redis_pubsub, ALERT_CHANNEL, SYSTEM_CHANNEL
    
    pubsub = get_redis_pubsub()
    manager = get_websocket_manager()
    
    async def handle_alert_message(message: dict):
        """Handle alert events from Redis."""
        if message.get("type") == "alert_event":
            await manager.broadcast(message, topic="alerts")
            logger.debug(f"Broadcast alert event: {message.get('event')}")
    
    async def handle_system_message(message: dict):
        """Handle system events from Redis."""
        if message.get("type") == "system_event":
            await manager.broadcast(message, topic="system")
            logger.debug(f"Broadcast system event: {message.get('event')}")
    
    # Subscribe to Redis channels
    await pubsub.subscribe(ALERT_CHANNEL, handle_alert_message)
    await pubsub.subscribe(SYSTEM_CHANNEL, handle_system_message)
    
    # Start the listener
    await pubsub.start_listener()
    
    logger.info("WebSocket Redis subscriptions configured")


def setup_event_subscriptions():
    """
    Subscribe WebSocket broadcaster to EventBus events.
    
    This handles events within the same process (e.g., from API endpoints).
    For cross-process events (from Celery), use setup_redis_subscriptions().
    """
    from backend.core.event_bus import get_event_bus, EventType, Event
    
    event_bus = get_event_bus()
    
    async def handle_alert_created(event: Event):
        """Handle alert created event."""
        alert = event.data
        await broadcast_alert_created(_alert_to_dict(alert))
    
    async def handle_alert_updated(event: Event):
        """Handle alert updated event."""
        alert = event.data
        await broadcast_alert_updated(_alert_to_dict(alert))
    
    async def handle_alert_resolved(event: Event):
        """Handle alert resolved/cleared event."""
        alert = event.data
        await broadcast_alert_cleared(_alert_to_dict(alert))
    
    async def handle_alert_acknowledged(event: Event):
        """Handle alert acknowledged event."""
        alert = event.data
        await broadcast_alert_updated(_alert_to_dict(alert))
    
    # Subscribe to all alert events
    event_bus.subscribe(EventType.ALERT_CREATED, handle_alert_created)
    event_bus.subscribe(EventType.ALERT_UPDATED, handle_alert_updated)
    event_bus.subscribe(EventType.ALERT_RESOLVED, handle_alert_resolved)
    event_bus.subscribe(EventType.ALERT_ACKNOWLEDGED, handle_alert_acknowledged)
    
    logger.info("WebSocket event subscriptions configured")


def _alert_to_dict(alert) -> dict:
    """Convert Alert object to dictionary for JSON serialization."""
    if hasattr(alert, 'dict'):
        return alert.dict()
    elif hasattr(alert, '__dict__'):
        data = {}
        for key, value in alert.__dict__.items():
            if key.startswith('_'):
                continue
            if hasattr(value, 'isoformat'):
                data[key] = value.isoformat()
            elif hasattr(value, 'value'):  # Enum
                data[key] = value.value
            elif isinstance(value, (str, int, float, bool, type(None))):
                data[key] = value
            else:
                data[key] = str(value)
        return data
    return {"id": str(alert)}
