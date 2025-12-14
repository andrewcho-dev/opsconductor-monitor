"""Backend API package - Flask Blueprints."""

from .devices import devices_bp
from .groups import groups_bp
from .jobs import jobs_bp
from .scheduler import scheduler_bp
from .scans import scans_bp
from .settings import settings_bp
from .system import system_bp
from .legacy import legacy_bp
from .workflows import workflows_bp, folders_bp, tags_bp, packages_bp
from .logs import logs_bp
from .alerts import alerts_bp
from .notifications import notifications_bp
from .credentials import credentials_bp
from .schema import schema_bp

__all__ = [
    'devices_bp',
    'groups_bp',
    'jobs_bp',
    'scheduler_bp',
    'scans_bp',
    'settings_bp',
    'system_bp',
    'legacy_bp',
    'workflows_bp',
    'folders_bp',
    'tags_bp',
    'packages_bp',
    'logs_bp',
    'alerts_bp',
    'notifications_bp',
    'credentials_bp',
    'schema_bp',
    'register_blueprints',
]


def register_blueprints(app):
    """
    Register all API blueprints with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Core API blueprints
    app.register_blueprint(devices_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(scans_bp)
    
    # Workflow builder blueprints
    app.register_blueprint(workflows_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(packages_bp)
    
    # Additional blueprints
    app.register_blueprint(settings_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(legacy_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(credentials_bp)
    app.register_blueprint(schema_bp)
