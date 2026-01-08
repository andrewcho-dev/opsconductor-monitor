"""
WebSocket Router for Real-Time Updates

Provides WebSocket endpoints for real-time alert and system updates.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional, List

from core.websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    topics: Optional[str] = Query(None, description="Comma-separated topics to subscribe to")
):
    """
    WebSocket endpoint for real-time updates.
    
    Connect to receive real-time alert and system events.
    
    Query Parameters:
        topics: Comma-separated list of topics (alerts, connectors, system)
                Default: all topics
    
    Message Types Received:
        - connected: Initial connection confirmation
        - alert_event: Alert created/updated/cleared/deleted
        - connector_event: Connector status changes
        - system_event: System events like poll_complete
    
    Example connection:
        ws://host:port/ws?topics=alerts,system
    """
    manager = get_websocket_manager()
    
    # Parse topics
    topic_list = None
    if topics:
        topic_list = [t.strip() for t in topics.split(",")]
    
    await manager.connect(websocket, topic_list)
    
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
            
            # Could handle other client commands here (subscribe, unsubscribe, etc.)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint specifically for alert updates.
    
    Convenience endpoint that only subscribes to alert events.
    """
    manager = get_websocket_manager()
    await manager.connect(websocket, ["alerts"])
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Alerts WebSocket error: {e}")
        await manager.disconnect(websocket)
