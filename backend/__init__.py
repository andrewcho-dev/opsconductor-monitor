"""
OpsConductor Backend Package

This package contains the refactored backend with:
- api/: Flask Blueprints (routes only)
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
