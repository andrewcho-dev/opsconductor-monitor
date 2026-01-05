"""FastAPI routers for OpsConductor API."""

from fastapi import FastAPI

from .health import router as health_router
from .ciena_snmp import router as ciena_snmp_router
from .legacy import router as legacy_router
from .devices import router as devices_router
from .polling import router as polling_router
from .traps import router as traps_router
from .auth import router as auth_router
from .settings import router as settings_router
from .metrics import router as metrics_router
from .netbox import router as netbox_router
from .notifications import router as notifications_router
from .logs import router as logs_router
from .system import router as system_router
from .credentials import router as credentials_router
from .workflows import router as workflows_router
from .jobs import router as jobs_router
from .scheduler import router as scheduler_router
from .groups import router as groups_router
from .scans import router as scans_router
from .alerts import router as alerts_router
from .prtg import router as prtg_router
from .mib_mappings import router as mib_router
from .ciena_ssh import router as ciena_ssh_router
from .ciena_mcp import router as ciena_mcp_router
from .winrm import router as winrm_router
from .eaton_snmp import router as eaton_snmp_router
from .device_importer import router as device_importer_router
from .prtg_netbox_import import router as prtg_netbox_import_router


def register_routers(app: FastAPI):
    """
    Register all API routers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Health check (no prefix for /api/health)
    app.include_router(health_router, prefix="/api", tags=["health"])
    
    # Authentication
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    
    # Core API routers
    app.include_router(devices_router, prefix="/api/devices", tags=["devices"])
    app.include_router(groups_router, prefix="/api/groups", tags=["groups"])
    app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(scheduler_router, prefix="/api/scheduler", tags=["scheduler"])
    app.include_router(scans_router, prefix="/api/scans", tags=["scans"])
    
    # Workflow builder
    app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows"])
    
    # Settings and system
    app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
    app.include_router(system_router, prefix="/api/system", tags=["system"])
    
    # Logging and alerts
    app.include_router(logs_router, prefix="/api/logs", tags=["logs"])
    app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])
    
    # Notifications
    app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
    
    # Credentials
    app.include_router(credentials_router, prefix="/api/credentials", tags=["credentials"])
    
    # Metrics and polling
    app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
    app.include_router(polling_router, prefix="/api/polling", tags=["polling"])
    
    # SNMP Traps
    app.include_router(traps_router, prefix="/api/traps", tags=["traps"])
    
    # MIB mappings
    app.include_router(mib_router, prefix="/api/mib", tags=["mib"])
    
    # External integrations
    app.include_router(netbox_router, prefix="/api/netbox", tags=["netbox"])
    app.include_router(prtg_router, prefix="/api/prtg", tags=["prtg"])
    app.include_router(prtg_netbox_import_router, prefix="/api/import", tags=["import"])
    app.include_router(device_importer_router, prefix="/api/device-importer", tags=["import"])
    
    # Device-specific SNMP/SSH
    app.include_router(ciena_snmp_router, prefix="/api/ciena/snmp", tags=["ciena", "snmp"])
    app.include_router(ciena_ssh_router, prefix="/api/ciena/ssh", tags=["ciena", "ssh"])
    app.include_router(ciena_mcp_router, prefix="/api/ciena/mcp", tags=["ciena", "mcp"])
    app.include_router(ciena_mcp_router, prefix="/api/mcp", tags=["mcp"])  # Alias for frontend
    app.include_router(eaton_snmp_router, prefix="/api/eaton/snmp", tags=["eaton", "snmp"])
    
    # WinRM
    app.include_router(winrm_router, prefix="/api/winrm", tags=["winrm"])
    
    # Legacy routes (for backward compatibility)
    app.include_router(legacy_router, tags=["legacy"])


__all__ = [
    'register_routers',
    'health_router',
    'ciena_snmp_router',
    'legacy_router',
    'devices_router',
    'polling_router',
    'traps_router',
    'auth_router',
    'settings_router',
    'metrics_router',
    'netbox_router',
    'notifications_router',
    'logs_router',
    'system_router',
    'credentials_router',
    'workflows_router',
    'jobs_router',
    'scheduler_router',
    'groups_router',
    'scans_router',
    'alerts_router',
    'prtg_router',
    'mib_router',
    'ciena_ssh_router',
    'ciena_mcp_router',
    'winrm_router',
    'eaton_snmp_router',
    'device_importer_router',
    'prtg_netbox_import_router',
]
