"""
System API Blueprint.

Routes for system health, progress, and scan operations.
"""

import threading
from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..utils.errors import AppError


system_bp = Blueprint('system', __name__)

# Scan state (shared with legacy routes)
_scan_state = {
    'status': 'idle',
    'scanned': 0,
    'total': 0,
    'online': 0,
    'cancel_requested': False,
}
_scan_lock = threading.Lock()


def get_scan_state():
    """Get current scan state."""
    with _scan_lock:
        return dict(_scan_state)


def update_scan_state(**kwargs):
    """Update scan state."""
    with _scan_lock:
        _scan_state.update(kwargs)


@system_bp.errorhandler(AppError)
def handle_app_error(error):
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@system_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify(success_response({
        'status': 'healthy',
        'service': 'opsconductor-backend'
    }))


@system_bp.route('/progress', methods=['GET'])
def get_progress():
    """Get scan progress."""
    state = get_scan_state()
    return jsonify(state)


@system_bp.route('/cancel_scan', methods=['POST'])
def cancel_scan():
    """Cancel running scan."""
    update_scan_state(cancel_requested=True)
    return jsonify(success_response(message='Scan cancellation requested'))


@system_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint."""
    return jsonify(success_response({'message': 'Backend is running'}))
