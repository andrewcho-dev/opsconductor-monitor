"""
Socket.IO Manager for Real-Time Updates

Rock-solid real-time communication with:
- Automatic reconnection
- Fallback to polling
- Room support
- Event namespacing
"""

import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime

import socketio

logger = logging.getLogger(__name__)

# Create Socket.IO server with CORS support
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
)

# Track connected clients
_clients: Dict[str, Dict[str, Any]] = {}  # sid -> {user_id, connected_at, subscriptions}


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection."""
    user_id = None
    
    # Extract user_id from auth token
    if auth and 'token' in auth:
        from backend.api.auth import decode_token
        payload = decode_token(auth['token'])
        if payload:
            user_id = int(payload.get('sub', 0))
    
    _clients[sid] = {
        'user_id': user_id,
        'connected_at': datetime.utcnow(),
        'subscriptions': {'alert_created', 'alert_updated', 'alert_resolved'}
    }
    
    logger.info(f"Socket.IO client connected: {sid} (user: {user_id})")
    
    # Send welcome message
    await sio.emit('connected', {
        'sid': sid,
        'user_id': user_id,
        'subscriptions': list(_clients[sid]['subscriptions'])
    }, to=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    if sid in _clients:
        user_id = _clients[sid].get('user_id')
        del _clients[sid]
        logger.info(f"Socket.IO client disconnected: {sid} (user: {user_id})")


@sio.event
async def subscribe(sid, data):
    """Subscribe to event types."""
    if sid in _clients:
        event_types = data.get('event_types', [])
        _clients[sid]['subscriptions'].update(event_types)
        await sio.emit('subscribed', {'event_types': event_types}, to=sid)


@sio.event
async def unsubscribe(sid, data):
    """Unsubscribe from event types."""
    if sid in _clients:
        event_types = set(data.get('event_types', []))
        _clients[sid]['subscriptions'] -= event_types
        await sio.emit('unsubscribed', {'event_types': list(event_types)}, to=sid)


@sio.event
async def ping(sid):
    """Handle ping from client."""
    await sio.emit('pong', to=sid)


async def broadcast_event(event_type: str, data: Dict[str, Any]) -> int:
    """
    Broadcast event to all subscribed clients.
    
    Returns number of clients that received the message.
    """
    sent_count = 0
    
    for sid, client in _clients.items():
        if event_type in client.get('subscriptions', set()):
            try:
                await sio.emit(event_type, {
                    'type': event_type,
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=sid)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to {sid}: {e}")
    
    return sent_count


async def send_to_user(user_id: int, event_type: str, data: Dict) -> bool:
    """Send event to specific user's connections."""
    sent = False
    
    for sid, client in _clients.items():
        if client.get('user_id') == user_id:
            try:
                await sio.emit(event_type, {
                    'type': event_type,
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=sid)
                sent = True
            except:
                pass
    
    return sent


def get_client_count() -> int:
    """Get number of connected clients."""
    return len(_clients)


def get_stats() -> Dict[str, Any]:
    """Get connection statistics."""
    return {
        'connected_clients': len(_clients),
        'clients': [
            {
                'sid': sid,
                'user_id': c.get('user_id'),
                'subscriptions': list(c.get('subscriptions', [])),
                'connected_at': c.get('connected_at').isoformat() if c.get('connected_at') else None
            }
            for sid, c in _clients.items()
        ]
    }


def setup_alert_broadcasts():
    """Register callback with alert engine for automatic Socket.IO broadcasts."""
    from backend.core.alert_engine import register_event_callback
    
    async def broadcast_alert_event(event_type: str, alert_data: Dict):
        await broadcast_event(event_type, alert_data)
    
    register_event_callback(broadcast_alert_event)
    logger.info("Alert event broadcasts registered with Socket.IO")


# Create ASGI app for Socket.IO
socket_app = socketio.ASGIApp(sio)
