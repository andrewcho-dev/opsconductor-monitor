"""
OpsConductor Application - Main Entry Point.

This is the main entry point that uses the FastAPI backend.
Run with: uvicorn app:app --host 0.0.0.0 --port 5000 --reload
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.app import create_app, app

# Re-export the app for backward compatibility
__all__ = ['app', 'create_app']

if __name__ == '__main__':
    import uvicorn
    
    # Get configuration from environment
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', 5000))
    reload = os.environ.get('API_RELOAD', 'true').lower() == 'true'
    
    print(f"Starting OpsConductor FastAPI on {host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=reload)
