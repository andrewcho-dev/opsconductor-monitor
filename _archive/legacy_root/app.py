"""
OpsConductor Application - Main Entry Point.

OpenAPI 3.x compliant API with domain-based routing:
- /identity/v1/* - Authentication, users, roles
- /inventory/v1/* - Devices, interfaces, topology
- /monitoring/v1/* - Metrics, alerts, polling
- /automation/v1/* - Workflows, jobs, scheduling
- /integrations/v1/* - NetBox, PRTG, MCP
- /system/v1/* - Settings, logs, health
- /credentials/v1/* - Credential vault
- /notifications/v1/* - Notification channels

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

# Import the OpenAPI 3.x application from backend.main
from backend.main import app

# Re-export the app
__all__ = ['app']

if __name__ == '__main__':
    import uvicorn
    
    # Get configuration from environment
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', 5000))
    reload = os.environ.get('API_RELOAD', 'true').lower() == 'true'
    
    print(f"Starting OpsConductor OpenAPI 3.x on {host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=reload)
