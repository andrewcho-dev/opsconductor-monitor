"""
OpsConductor API - Main Application

Clean, minimal FastAPI application for alert processing.
Uses Socket.IO for rock-solid real-time updates.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend_v2.api.routes import alerts, addons, system, targets, users
from backend_v2.api.socketio_manager import sio, socket_app, setup_alert_broadcasts
from backend_v2.api.auth import decode_token
from backend_v2.core.addon_registry import get_registry
from backend_v2.core.trap_receiver import start_receiver, stop_receiver
from backend_v2.core.db import close_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Redis subscriber task for cross-process alert events
_redis_subscriber_task = None

async def redis_alert_subscriber():
    """Subscribe to Redis alert_events channel and forward to Socket.IO."""
    import redis
    import json
    from backend_v2.api.socketio_manager import broadcast_event
    
    r = redis.Redis(host='localhost', port=6379, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe('alert_events')
    
    logger.info("Redis alert subscriber started")
    
    while True:
        try:
            message = pubsub.get_message(timeout=1.0)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                event_type = data.get('event_type')
                alert_data = data.get('alert')
                if event_type and alert_data:
                    await broadcast_event(event_type, alert_data)
                    logger.debug(f"Forwarded {event_type} to Socket.IO")
        except Exception as e:
            logger.warning(f"Redis subscriber error: {e}")
        await asyncio.sleep(0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global _redis_subscriber_task
    logger.info("OpsConductor v2 starting...")
    
    # Load addons
    registry = get_registry()
    logger.info(f"Loaded {len(registry.get_enabled())} addons")
    
    # Setup Socket.IO broadcasts from alert engine (for in-process events)
    setup_alert_broadcasts()
    
    # Start Redis subscriber for cross-process events (Celery -> FastAPI)
    _redis_subscriber_task = asyncio.create_task(redis_alert_subscriber())
    
    # Start SNMP trap receiver
    try:
        await start_receiver(port=162)
    except Exception as e:
        logger.warning(f"Could not start trap receiver: {e}")
    
    logger.info("OpsConductor v2 ready")
    
    yield
    
    # Shutdown
    logger.info("OpsConductor v2 shutting down...")
    if _redis_subscriber_task:
        _redis_subscriber_task.cancel()
    await stop_receiver()
    close_pool()
    logger.info("OpsConductor v2 stopped")


# Create application
app = FastAPI(
    title="OpsConductor API",
    description="Alert processing and addon management",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log API requests."""
    import time
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    # Skip health checks and static files
    if request.url.path not in ['/health', '/docs', '/redoc', '/openapi.json']:
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
    
    return response


# Include routers
app.include_router(system.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(addons.router, prefix="/api/v1")
app.include_router(targets.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


# Mount Socket.IO at /socket.io
app.mount("/socket.io", socket_app)


# Webhook endpoint (dynamic based on addon config)
@app.post("/webhooks/{path:path}")
async def webhook_handler(path: str, request: Request):
    """
    Handle incoming webhooks from external systems.
    
    Path should match addon's webhook.endpoint_path configuration.
    """
    from backend_v2.core.webhook_receiver import handle_webhook
    
    try:
        data = await request.json()
    except:
        data = dict(await request.form())
    
    source_ip = request.client.host if request.client else None
    result = await handle_webhook(path, data, source_ip)
    
    return JSONResponse(result)


# Root endpoint
@app.get("/")
async def root():
    """API information."""
    return {
        "name": "OpsConductor API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
