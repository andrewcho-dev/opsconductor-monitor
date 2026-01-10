"""
WebSocket Real-Time Updates

Broadcast alert events to connected clients for live dashboard updates.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class Client:
    """Connected WebSocket client."""
    websocket: WebSocket
    user_id: Optional[int]
    subscriptions: Set[str]
    connected_at: datetime


class WebSocketManager:
    """
    Manage WebSocket connections and broadcast events.
    
    Events:
    - alert_created: New alert
    - alert_updated: Alert status change
    - alert_resolved: Alert resolved
    - system_status: Health updates
    - addon_status: Addon enable/disable
    
    Usage:
        manager = WebSocketManager()
        
        # In route handler
        await manager.connect(websocket, user_id)
        
        # Broadcast from anywhere
        await manager.broadcast('alert_created', alert_data)
    """
    
    def __init__(self):
        self._clients: Dict[int, Client] = {}  # id -> Client
        self._client_counter = 0
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None) -> int:
        """
        Accept WebSocket connection and register client.
        
        Returns client ID for later reference.
        """
        await websocket.accept()
        
        async with self._lock:
            self._client_counter += 1
            client_id = self._client_counter
            
            self._clients[client_id] = Client(
                websocket=websocket,
                user_id=user_id,
                subscriptions={'alert_created', 'alert_updated', 'alert_resolved'},  # Default subscriptions
                connected_at=datetime.utcnow()
            )
        
        logger.info(f"WebSocket client {client_id} connected (user: {user_id})")
        
        # Send welcome message (ignore failures - client might not be ready)
        try:
            await self._clients[client_id].websocket.send_json({
                'type': 'connected',
                'client_id': client_id,
                'subscriptions': list(self._clients[client_id].subscriptions)
            })
        except Exception:
            pass  # Client not ready yet, that's ok
        
        return client_id
    
    async def disconnect(self, client_id: int) -> None:
        """Remove client from registry."""
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                logger.info(f"WebSocket client {client_id} disconnected")
    
    async def subscribe(self, client_id: int, event_types: Set[str]) -> None:
        """Subscribe client to event types."""
        if client_id in self._clients:
            self._clients[client_id].subscriptions.update(event_types)
            await self._send(client_id, {
                'type': 'subscribed',
                'event_types': list(event_types)
            })
    
    async def unsubscribe(self, client_id: int, event_types: Set[str]) -> None:
        """Unsubscribe client from event types."""
        if client_id in self._clients:
            self._clients[client_id].subscriptions -= event_types
            await self._send(client_id, {
                'type': 'unsubscribed',
                'event_types': list(event_types)
            })
    
    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> int:
        """
        Broadcast event to all subscribed clients.
        
        Returns number of clients that received the message.
        """
        message = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sent_count = 0
        disconnected = []
        
        for client_id, client in list(self._clients.items()):
            if event_type in client.subscriptions:
                try:
                    await client.websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to client {client_id}: {e}")
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)
        
        return sent_count
    
    async def send_to_user(self, user_id: int, event_type: str, data: Dict) -> bool:
        """Send event to specific user's connections."""
        message = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sent = False
        for client_id, client in list(self._clients.items()):
            if client.user_id == user_id:
                try:
                    await client.websocket.send_json(message)
                    sent = True
                except:
                    await self.disconnect(client_id)
        
        return sent
    
    async def _send(self, client_id: int, message: Dict) -> bool:
        """Send message to specific client."""
        if client_id not in self._clients:
            return False
        
        try:
            await self._clients[client_id].websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False
    
    async def handle_message(self, client_id: int, message: Dict) -> None:
        """Handle incoming message from client."""
        msg_type = message.get('type', '')
        
        if msg_type == 'subscribe':
            event_types = set(message.get('event_types', []))
            await self.subscribe(client_id, event_types)
        
        elif msg_type == 'unsubscribe':
            event_types = set(message.get('event_types', []))
            await self.unsubscribe(client_id, event_types)
        
        elif msg_type == 'ping':
            await self._send(client_id, {'type': 'pong'})
    
    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        return len(self._clients)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            'connected_clients': len(self._clients),
            'clients': [
                {
                    'id': cid,
                    'user_id': c.user_id,
                    'subscriptions': list(c.subscriptions),
                    'connected_at': c.connected_at.isoformat()
                }
                for cid, c in self._clients.items()
            ]
        }


# Global manager instance
_manager: Optional[WebSocketManager] = None


def get_manager() -> WebSocketManager:
    """Get global WebSocket manager."""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager


async def broadcast_event(event_type: str, data: Dict) -> int:
    """Convenience function to broadcast event."""
    return await get_manager().broadcast(event_type, data)


# Register with alert engine for automatic broadcasts
def setup_alert_broadcasts():
    """Register callback with alert engine for automatic WebSocket broadcasts."""
    from backend.core.alert_engine import register_event_callback
    
    async def broadcast_alert_event(event_type: str, alert_data: Dict):
        await broadcast_event(event_type, alert_data)
    
    register_event_callback(broadcast_alert_event)
    logger.info("Alert event broadcasts registered")
