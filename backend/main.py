"""
OpsConductor API - Main Application Entry Point

Slim application setup with modular router architecture.
All endpoint logic is in backend/routers/ modules.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.logging_service import logging_service, get_logger, LogSource

logger = get_logger(__name__, LogSource.SYSTEM)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("OpsConductor API starting up...")
    
    # Setup WebSocket event subscriptions (in-process events)
    from backend.core.websocket_manager import setup_event_subscriptions, setup_redis_subscriptions
    setup_event_subscriptions()
    logger.info("WebSocket event subscriptions configured")
    
    # Setup Redis pub/sub for cross-process events (from Celery workers)
    try:
        await setup_redis_subscriptions()
        logger.info("Redis pub/sub subscriptions configured")
    except Exception as e:
        logger.error(f"Failed to setup Redis subscriptions: {e}")
    
    # Start SNMP trap receiver if enabled
    snmp_trap_connector = None
    try:
        from backend.core.connector_manager import start_snmp_trap_receiver
        snmp_trap_connector = await start_snmp_trap_receiver()
        if snmp_trap_connector:
            logger.info("SNMP trap receiver started")
    except Exception as e:
        logger.warning(f"Failed to start SNMP trap receiver: {e}")
    
    yield
    
    # Stop SNMP trap receiver
    if snmp_trap_connector:
        try:
            await snmp_trap_connector.stop()
            logger.info("SNMP trap receiver stopped")
        except Exception as e:
            logger.warning(f"Error stopping SNMP trap receiver: {e}")
    
    logger.info("OpsConductor API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="OpsConductor API",
    description="Network monitoring and automation platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Skip logging for static files and health checks
    if not request.url.path.startswith(('/assets', '/static', '/favicon')):
        if request.url.path != '/system/v1/health':
            logger.debug(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
    
    return response


# Import and include routers
from backend.routers import (
    system_router,
    identity_router,
    auth_router,
    inventory_router,
    monitoring_router,
    automation_router,
    integrations_router,
    credentials_router,
    notifications_router,
    alerts_router,
    dependencies_router,
    connectors_router,
    normalization_router,
)
from backend.routers.websocket import router as websocket_router
from backend.routers.addons import router as addons_router

# Include all routers
app.include_router(system_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(identity_router)
app.include_router(inventory_router)
app.include_router(monitoring_router)
app.include_router(automation_router)
app.include_router(integrations_router)
app.include_router(credentials_router)
app.include_router(notifications_router)

# MVP Alert Aggregation routers
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(dependencies_router, prefix="/api/v1/dependencies", tags=["dependencies"])
app.include_router(connectors_router, prefix="/api/v1/connectors", tags=["connectors"])
app.include_router(normalization_router, prefix="/api/v1/normalization", tags=["normalization"])
app.include_router(addons_router)

# WebSocket router for real-time updates
app.include_router(websocket_router)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to docs or serve frontend"""
    return {"message": "OpsConductor API", "docs": "/docs", "version": "2.0.0"}


# API info endpoint
@app.get("/api/info", include_in_schema=False)
async def api_info():
    """API information"""
    return {
        "name": "OpsConductor API",
        "version": "2.0.0",
        "description": "Network monitoring and automation platform",
        "endpoints": {
            "system": "/system/v1",
            "identity": "/identity/v1",
            "inventory": "/inventory/v1",
            "monitoring": "/monitoring/v1",
            "automation": "/automation/v1",
            "integrations": "/integrations/v1",
            "credentials": "/credentials/v1",
            "notifications": "/notifications/v1"
        }
    }


# Static file serving for frontend (production)
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve SPA frontend for non-API routes"""
        # Skip API routes
        if full_path.startswith(('api/', 'system/', 'identity/', 'inventory/', 
                                  'monitoring/', 'automation/', 'integrations/',
                                  'credentials/', 'notifications/', 'auth/', 'docs', 'redoc', 'openapi')):
            return JSONResponse({"error": "Not found"}, status_code=404)
        
        # Serve index.html for SPA routing
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse({"error": "Frontend not built"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
