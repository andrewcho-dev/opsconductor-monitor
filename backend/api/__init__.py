"""Backend API package - Flask Blueprints."""

from .devices import devices_bp
from .groups import groups_bp
from .jobs import jobs_bp
from .scheduler import scheduler_bp
from .scans import scans_bp

__all__ = [
    'devices_bp',
    'groups_bp',
    'jobs_bp',
    'scheduler_bp',
    'scans_bp',
]


def register_blueprints(app):
    """
    Register all API blueprints with the Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(devices_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(scans_bp)
