"""
Device Importer API Blueprint

REST API endpoints for importing devices from PRTG to NetBox and OpsConductor.
"""

from flask import Blueprint, request, jsonify
import logging

from backend.services.device_importer_service import DeviceImporterService

logger = logging.getLogger(__name__)

device_importer_bp = Blueprint('device_importer', __name__, url_prefix='/api/import')


@device_importer_bp.route('/discover', methods=['GET'])
def discover_devices():
    """Discover devices from PRTG."""
    try:
        service = DeviceImporterService()
        
        group = request.args.get('group')
        status = request.args.get('status')
        include_sensors = request.args.get('include_sensors', 'false').lower() == 'true'
        
        result = service.discover_prtg_devices(
            group=group,
            status=status,
            include_sensors=include_sensors,
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error discovering devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@device_importer_bp.route('/preview', methods=['GET'])
def preview_import():
    """Preview import operations without making changes."""
    try:
        service = DeviceImporterService()
        
        target = request.args.get('target', 'all')  # 'netbox', 'opsconductor', 'all'
        
        result = service.preview_import(target=target)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error previewing import: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@device_importer_bp.route('/networks', methods=['GET'])
def get_networks():
    """Get discovered networks from PRTG devices."""
    try:
        service = DeviceImporterService()
        result = service.get_discovered_networks()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting networks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@device_importer_bp.route('/opsconductor', methods=['POST'])
def import_to_opsconductor():
    """Import devices from PRTG to OpsConductor."""
    try:
        service = DeviceImporterService()
        data = request.get_json() or {}
        
        device_ids = data.get('device_ids')  # List of PRTG device IDs
        update_existing = data.get('update_existing', True)
        create_missing = data.get('create_missing', True)
        dry_run = data.get('dry_run', False)
        
        result = service.import_to_opsconductor(
            device_ids=device_ids,
            update_existing=update_existing,
            create_missing=create_missing,
            dry_run=dry_run,
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error importing to OpsConductor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@device_importer_bp.route('/netbox', methods=['POST'])
def import_to_netbox():
    """Import devices from PRTG to NetBox."""
    try:
        service = DeviceImporterService()
        data = request.get_json() or {}
        
        device_ids = data.get('device_ids')
        default_site_id = data.get('site_id')
        default_role_id = data.get('role_id')
        default_device_type_id = data.get('device_type_id')
        update_existing = data.get('update_existing', False)
        create_missing = data.get('create_missing', True)
        dry_run = data.get('dry_run', False)
        
        result = service.import_to_netbox(
            device_ids=device_ids,
            default_site_id=default_site_id,
            default_role_id=default_role_id,
            default_device_type_id=default_device_type_id,
            update_existing=update_existing,
            create_missing=create_missing,
            dry_run=dry_run,
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error importing to NetBox: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@device_importer_bp.route('/all', methods=['POST'])
def import_to_all():
    """Import devices from PRTG to both NetBox and OpsConductor."""
    try:
        service = DeviceImporterService()
        data = request.get_json() or {}
        
        device_ids = data.get('device_ids')
        netbox_site_id = data.get('netbox_site_id')
        netbox_role_id = data.get('netbox_role_id')
        netbox_device_type_id = data.get('netbox_device_type_id')
        update_existing = data.get('update_existing', False)
        dry_run = data.get('dry_run', False)
        
        result = service.import_to_all(
            device_ids=device_ids,
            netbox_site_id=netbox_site_id,
            netbox_role_id=netbox_role_id,
            netbox_device_type_id=netbox_device_type_id,
            update_existing=update_existing,
            dry_run=dry_run,
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error importing to all: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
