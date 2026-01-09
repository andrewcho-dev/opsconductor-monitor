"""
Redis Pub/Sub for Cross-Process Event Broadcasting

Enables real-time event communication between Celery workers and FastAPI backend.
Celery workers publish events to Redis, FastAPI subscribes and broadcasts to WebSockets.
"""

import asyncio
import json
import logging
import os
from typing import Optional, Callable, Any
from datetime import datetime

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ALERT_CHANNEL = "opsconductor:alerts"
SYSTEM_CHANNEL = "opsconductor:system"


class RedisPubSub:
    """
    Redis Pub/Sub manager for cross-process event broadcasting.
    
    Each Uvicorn worker process gets its own instance with its own Redis connection.
    This is intentional - each worker needs to subscribe to Redis independently
    so it can broadcast to its own WebSocket clients.
    """
    
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._handlers: dict = {
            ALERT_CHANNEL: [],
            SYSTEM_CHANNEL: [],
        }
        self._pid = os.getpid()
        logger.info(f"RedisPubSub initialized for worker PID {self._pid}")
    
    async def connect(self):
        """Connect to Redis."""
        if self._redis is None:
            self._redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            logger.info(f"Connected to Redis: {REDIS_URL}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        self._redis = None
        self._pubsub = None
        self._listener_task = None
        logger.info("Disconnected from Redis")
    
    async def publish(self, channel: str, message: dict):
        """
        Publish a message to a Redis channel.
        
        Args:
            channel: Channel name
            message: Message dict (will be JSON serialized)
        """
        await self.connect()
        
        # Add timestamp
        message["timestamp"] = datetime.utcnow().isoformat()
        
        try:
            await self._redis.publish(channel, json.dumps(message))
            logger.debug(f"Published to {channel}: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
    
    async def subscribe(self, channel: str, handler: Callable):
        """
        Subscribe to a Redis channel.
        
        Args:
            channel: Channel name
            handler: Async function to call with message dict
        """
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        logger.info(f"Subscribed handler to {channel}")
    
    async def start_listener(self):
        """Start the Redis pub/sub listener."""
        await self.connect()
        
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(ALERT_CHANNEL, SYSTEM_CHANNEL)
        
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("Redis pub/sub listener started")
    
    async def _listen(self):
        """Listen for messages and dispatch to handlers."""
        logger.info(f"Redis listener started for PID {self._pid}")
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    logger.info(f"Received Redis message on {channel}")
                    try:
                        data = json.loads(message["data"])
                        handlers = self._handlers.get(channel, [])
                        logger.info(f"Dispatching to {len(handlers)} handlers")
                        for handler in handlers:
                            try:
                                await handler(data)
                            except Exception as e:
                                logger.error(f"Handler error for {channel}: {e}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON from {channel}: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")


# Per-process instance (keyed by PID to handle forked workers)
_pubsub_instances: dict = {}


def get_redis_pubsub() -> RedisPubSub:
    """
    Get the Redis pub/sub instance for this worker process.
    
    Each Uvicorn worker (forked process) gets its own instance.
    This ensures each worker has its own Redis subscription and
    can broadcast to its own WebSocket clients.
    """
    pid = os.getpid()
    if pid not in _pubsub_instances:
        _pubsub_instances[pid] = RedisPubSub()
        logger.info(f"Created RedisPubSub instance for worker PID {pid}")
    return _pubsub_instances[pid]


# Synchronous publish for use in Celery workers
def publish_alert_event_sync(event_type: str, alert_data: dict):
    """
    Synchronously publish an alert event to Redis.
    
    Use this from Celery workers where async is not available.
    """
    import redis
    
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        message = {
            "type": "alert_event",
            "event": event_type,
            "alert": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        result = r.publish(ALERT_CHANNEL, json.dumps(message))
        logger.info(f"Published alert event '{event_type}' to {result} subscribers")
    except Exception as e:
        logger.error(f"Failed to publish alert event: {e}")


def publish_system_event_sync(event_type: str, data: dict):
    """
    Synchronously publish a system event to Redis.
    
    Use this from Celery workers where async is not available.
    """
    import redis
    
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        message = {
            "type": "system_event",
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        result = r.publish(SYSTEM_CHANNEL, json.dumps(message))
        logger.info(f"Published system event '{event_type}' to {result} subscribers")
    except Exception as e:
        logger.error(f"Failed to publish system event: {e}")
