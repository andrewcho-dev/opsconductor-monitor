#!/usr/bin/env python3
"""
OpsConductor Main Entry Point.

This is the new modular entry point that uses the backend package.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env if present
from dotenv import load_dotenv
load_dotenv()

from backend.app import create_app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"Starting OpsConductor on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
