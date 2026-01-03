"""
OpsConductor Backend Application.

Flask application factory with modular blueprint registration.
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import register_blueprints
from backend.utils.errors import AppError
from backend.utils.responses import error_response
from backend.services.logging_service import logging_service, get_logger, LogSource
from backend.middleware import init_request_logging
from backend.middleware.user_audit import init_audit_middleware
from backend.database import get_db


def create_app(config=None):
    """
    Application factory for creating Flask app.
    
    Args:
        config: Optional configuration dictionary
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
    
    # Load configuration
    app.config['JSON_SORT_KEYS'] = False
    if config:
        app.config.update(config)
    
    # Initialize logging service with database connection
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    db = get_db()
    logging_service.initialize(db_connection=db, log_level=log_level)
    
    logger = get_logger(__name__, LogSource.SYSTEM)
    logger.info("OpsConductor backend starting up", category='startup')
    
    # Enable CORS for all origins (including legacy routes without /api prefix)
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/data": {"origins": "*"},
        r"/get_combined_interfaces": {"origins": "*"},
        r"/*": {"origins": "*"}
    })
    
    # Initialize request logging middleware
    init_request_logging(app)
    
    # Initialize user action audit middleware (logs all user-initiated actions)
    init_audit_middleware(app)
    
    # Register all blueprints (includes settings, system, legacy)
    register_blueprints(app)
    
    logger.info("All blueprints registered", category='startup')
    
    # Global error handlers
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify(error_response(error.code, error.message, error.details)), error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify(error_response('NOT_FOUND', 'Resource not found')), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return jsonify(error_response('INTERNAL_ERROR', str(error))), 500
    
    # Serve frontend
    @app.route('/')
    def serve_frontend():
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')
    
    return app


# Create default app instance
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
