"""
OpsConductor Backend Package

FastAPI application using OpenAPI 3.x specification.

This package contains:
- main.py: FastAPI application with OpenAPI 3.x endpoints
- openapi/: Domain implementation modules (identity, inventory, monitoring, etc.)
- services/: Business logic layer
- repositories/: Data access layer
- models/: Data models/schemas
- parsers/: Output parsers with registry
- executors/: Command executors (SSH, SNMP, Ping)
- targeting/: Target resolution strategies
- utils/: Shared utilities
- config/: Configuration
- tasks/: Celery task wrappers
"""

__version__ = '2.0.0'
