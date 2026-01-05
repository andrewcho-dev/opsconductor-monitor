"""
OpsConductor Backend Application.

FastAPI application with modular router registration.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routers import register_routers
from backend.utils.errors import AppError
from backend.utils.responses import error_response
from backend.services.logging_service import logging_service, get_logger, LogSource
from backend.database import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown."""
    # Startup
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    db = get_db()
    logging_service.initialize(db_connection=db, log_level=log_level)
    logger = get_logger(__name__, LogSource.SYSTEM)
    logger.info("OpsConductor FastAPI backend starting up", category='startup')
    
    yield
    
    # Shutdown
    logger = get_logger(__name__, LogSource.SYSTEM)
    logger.info("OpsConductor FastAPI backend shutting down", category='shutdown')


def create_app() -> FastAPI:
    """
    Application factory for creating FastAPI app.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="OpsConductor API",
        description="Network monitoring and automation platform",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # Enable CORS for all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register all routers
    register_routers(app)
    
    # Global exception handler for AppError
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, exc.details)
        )
    
    # Global 404 handler
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        # Check if this is an API route
        if request.url.path.startswith('/api/'):
            return JSONResponse(
                status_code=404,
                content=error_response('NOT_FOUND', 'Resource not found')
            )
        # For non-API routes, serve the frontend
        frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist')
        index_path = os.path.join(frontend_dist, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse(
            status_code=404,
            content=error_response('NOT_FOUND', 'Resource not found')
        )
    
    # Serve frontend static files
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist')
    if os.path.exists(frontend_dist):
        # Mount assets directory
        assets_dir = os.path.join(frontend_dist, 'assets')
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        
        # Serve index.html for root
        @app.get("/")
        async def serve_frontend():
            return FileResponse(os.path.join(frontend_dist, 'index.html'))
        
        # Note: SPA catch-all is handled by the 404 handler above
        # All non-API routes that don't match registered routes will serve index.html
    
    return app


# Create default app instance
app = create_app()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend.app:app", host='0.0.0.0', port=5000, reload=True)
