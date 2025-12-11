"""
Scans API Blueprint.

Routes for interface scans and optical power data.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, NotFoundError, ValidationError


scans_bp = Blueprint('scans', __name__, url_prefix='/api/scans')


def get_scan_service():
    """Get scan service instance."""
    from database import DatabaseManager
    from ..repositories.scan_repo import ScanRepository, OpticalPowerRepository
    from ..repositories.device_repo import DeviceRepository
    from ..services.scan_service import ScanService
    
    db = DatabaseManager()
    scan_repo = ScanRepository(db)
    optical_repo = OpticalPowerRepository(db)
    device_repo = DeviceRepository(db)
    return ScanService(scan_repo, optical_repo, device_repo)


@scans_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@scans_bp.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected errors."""
    return jsonify(error_response('INTERNAL_ERROR', str(error))), 500


@scans_bp.route('/interfaces/<ip_address>', methods=['GET'])
def get_device_interfaces(ip_address):
    """
    Get latest interface scan data for a device.
    
    Args:
        ip_address: Device IP address
    
    Returns:
        List of interface records
    """
    service = get_scan_service()
    interfaces = service.get_device_interfaces(ip_address)
    
    return jsonify(list_response(interfaces))


@scans_bp.route('/optical', methods=['GET'])
def get_optical_interfaces():
    """
    Get all optical interfaces.
    
    Query params:
        ip_address: Optional device filter
    
    Returns:
        List of optical interfaces
    """
    service = get_scan_service()
    
    ip_address = request.args.get('ip_address')
    interfaces = service.get_optical_interfaces(ip_address)
    
    return jsonify(list_response(interfaces))


@scans_bp.route('/optical/power-history', methods=['GET'])
def get_optical_power_history():
    """
    Get optical power history for a device/interface.
    
    Query params:
        ip_address: Device IP address (required)
        interface_index: Optional interface filter
        hours: Time window in hours (default: 24)
    
    Returns:
        List of power readings
    """
    service = get_scan_service()
    
    ip_address = request.args.get('ip_address')
    if not ip_address:
        raise ValidationError('ip_address is required', field='ip_address')
    
    interface_index = request.args.get('interface_index')
    if interface_index:
        interface_index = int(interface_index)
    
    hours = int(request.args.get('hours', '24'))
    
    history = service.get_optical_power_history(ip_address, interface_index, hours)
    
    return jsonify(list_response(history))


@scans_bp.route('/optical/power-history', methods=['POST'])
def get_optical_power_history_bulk():
    """
    Get optical power history for multiple devices.
    
    Body:
        ip_addresses: List of device IP addresses
        interface_index: Optional interface filter
        hours: Time window in hours (default: 24)
    
    Returns:
        Dictionary mapping IP to power readings
    """
    service = get_scan_service()
    data = request.get_json() or {}
    
    ip_addresses = data.get('ip_addresses', [])
    if not ip_addresses:
        raise ValidationError('ip_addresses is required', field='ip_addresses')
    
    interface_index = data.get('interface_index')
    hours = data.get('hours', 24)
    
    history = service.get_power_history_for_devices(ip_addresses, interface_index, hours)
    
    return jsonify(success_response(history))


@scans_bp.route('/optical/trends', methods=['GET'])
def get_optical_power_trends():
    """
    Get optical power trend statistics.
    
    Query params:
        ip_address: Device IP address (required)
        interface_index: Interface index (required)
        days: Time window in days (default: 7)
    
    Returns:
        Trend statistics
    """
    service = get_scan_service()
    
    ip_address = request.args.get('ip_address')
    interface_index = request.args.get('interface_index')
    
    if not ip_address:
        raise ValidationError('ip_address is required', field='ip_address')
    if not interface_index:
        raise ValidationError('interface_index is required', field='interface_index')
    
    days = int(request.args.get('days', '7'))
    
    trends = service.get_optical_power_trends(ip_address, int(interface_index), days)
    
    return jsonify(success_response(trends))


@scans_bp.route('/cleanup', methods=['POST'])
def cleanup_old_data():
    """
    Clean up old scan and power data.
    
    Body:
        optical_days: Age threshold for optical data (default: 90)
    
    Returns:
        Cleanup statistics
    """
    service = get_scan_service()
    data = request.get_json() or {}
    
    optical_days = data.get('optical_days', 90)
    
    result = service.cleanup_old_data(optical_days)
    
    return jsonify(success_response(result, message='Cleanup completed'))
