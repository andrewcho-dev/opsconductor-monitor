"""
FastAPI Routers Package

Modular router architecture for OpsConductor API.
Each router handles a specific API domain and should be under 500 lines.
"""

from .system import router as system_router
from .identity import router as identity_router, auth_router
from .inventory import router as inventory_router
from .monitoring import router as monitoring_router
from .automation import router as automation_router
from .integrations import router as integrations_router
from .credentials import router as credentials_router
from .notifications import router as notifications_router
from .alerts import router as alerts_router
from .dependencies import router as dependencies_router
from .connectors import router as connectors_router
from .normalization import router as normalization_router

__all__ = [
    'system_router',
    'identity_router',
    'auth_router',
    'inventory_router',
    'monitoring_router',
    'automation_router',
    'integrations_router',
    'credentials_router',
    'notifications_router',
    'alerts_router',
    'dependencies_router',
    'connectors_router',
    'normalization_router',
]
