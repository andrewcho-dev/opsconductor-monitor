#!/usr/bin/env python3
"""
OpsConductor Main Entry Point.

FastAPI application using OpenAPI 3.x specification.
Use: uvicorn run:app --host 0.0.0.0 --port 5000 --reload
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env if present
from dotenv import load_dotenv
load_dotenv()

# Import the FastAPI application from app.py (which imports from backend.main)
from app import app

if __name__ == '__main__':
    import uvicorn
    
    # Get configuration from environment
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', 5000))
    reload = os.environ.get('API_RELOAD', 'true').lower() == 'true'
    
    print(f"Starting OpsConductor on {host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=reload)
