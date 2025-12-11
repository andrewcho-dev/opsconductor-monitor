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
    
    # Enable CORS
    CORS(app)
    
    # Register all blueprints (includes settings, system, legacy)
    register_blueprints(app)
    
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
