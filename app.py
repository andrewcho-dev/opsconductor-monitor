"""
OpsConductor Application - Main Entry Point.

This is the main entry point that uses the new modular backend.
For backward compatibility, this file delegates to backend.app.
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
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"Starting OpsConductor on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
