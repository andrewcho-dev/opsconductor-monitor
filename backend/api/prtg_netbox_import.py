"""
PRTG to NetBox Import API Blueprint

REST API endpoints for importing devices from PRTG to NetBox.
"""

from flask import Blueprint, request, jsonify
import logging

from backend.services.prtg_netbox_importer import PRTGNetBoxImporter

logger = logging.getLogger(__name__)

prtg_netbox_import_bp = Blueprint('prtg_netbox_import', __name__, url_prefix='/api/import')


@prtg_netbox_import_bp.route('/netbox-options', methods=['GET'])
def get_netbox_options():
    """Get NetBox sites, device types, and roles for selection dropdowns."""
    try:
        importer = PRTGNetBoxImporter()
        options = importer.get_netbox_options()
        return jsonify({'success': True, 'data': options})
    except Exception as e:
        logger.error(f"Error getting NetBox options: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/prtg-groups', methods=['GET'])
def get_prtg_groups():
    """Get all PRTG groups for filtering."""
    try:
        importer = PRTGNetBoxImporter()
        groups = importer.get_prtg_groups()
        return jsonify({'success': True, 'groups': groups})
    except Exception as e:
        logger.error(f"Error getting PRTG groups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/prtg-devices', methods=['GET', 'POST'])
def get_prtg_devices():
    """
    Get PRTG devices with filtering.
    
    Query params (GET) or JSON body (POST):
        ip_range: CIDR range (e.g., '10.120.0.0/16')
        ip_addresses: List of specific IPs
        name_filter: Device name substring
        group_filter: PRTG group substring
        status_filter: Status (up, down, warning, paused)
    """
    try:
        importer = PRTGNetBoxImporter()
        
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = {
                'ip_range': request.args.get('ip_range'),
                'name_filter': request.args.get('name_filter'),
                'group_filter': request.args.get('group_filter'),
                'status_filter': request.args.get('status_filter'),
            }
            # Handle ip_addresses as comma-separated
            ip_list = request.args.get('ip_addresses')
            if ip_list:
                data['ip_addresses'] = [ip.strip() for ip in ip_list.split(',')]
        
        result = importer.get_prtg_devices(
            ip_range=data.get('ip_range'),
            ip_addresses=data.get('ip_addresses'),
            name_filter=data.get('name_filter'),
            group_filter=data.get('group_filter'),
            status_filter=data.get('status_filter'),
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting PRTG devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/preview', methods=['POST'])
def preview_import():
    """
    Preview import without making changes.
    
    JSON body:
        devices: List of devices from /prtg-devices
        site_id: NetBox site ID
        device_type_id: NetBox device type ID
        role_id: NetBox device role ID
    """
    try:
        importer = PRTGNetBoxImporter()
        data = request.get_json() or {}
        
        devices = data.get('devices', [])
        site_id = data.get('site_id')
        device_type_id = data.get('device_type_id')
        role_id = data.get('role_id')
        
        if not all([site_id, device_type_id, role_id]):
            return jsonify({
                'success': False, 
                'error': 'site_id, device_type_id, and role_id are required'
            }), 400
        
        result = importer.preview_import(
            devices=devices,
            site_id=site_id,
            device_type_id=device_type_id,
            role_id=role_id,
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error previewing import: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/execute', methods=['POST'])
def execute_import():
    """
    Execute the import from PRTG to NetBox.
    
    JSON body:
        devices: List of devices to import
        site_id: NetBox site ID
        device_type_id: NetBox device type ID
        role_id: NetBox device role ID
        update_existing: Whether to update existing devices (default: false)
        dry_run: Preview only, don't make changes (default: false)
    """
    try:
        importer = PRTGNetBoxImporter()
        data = request.get_json() or {}
        
        devices = data.get('devices', [])
        site_id = data.get('site_id')
        device_type_id = data.get('device_type_id')
        role_id = data.get('role_id')
        update_existing = data.get('update_existing', False)
        dry_run = data.get('dry_run', False)
        
        if not all([site_id, device_type_id, role_id]):
            return jsonify({
                'success': False,
                'error': 'site_id, device_type_id, and role_id are required'
            }), 400
        
        if not devices:
            return jsonify({
                'success': False,
                'error': 'No devices provided for import'
            }), 400
        
        result = importer.import_devices(
            devices=devices,
            site_id=site_id,
            device_type_id=device_type_id,
            role_id=role_id,
            update_existing=update_existing,
            dry_run=dry_run,
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing import: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/field-mapping', methods=['GET'])
def get_field_mapping():
    """Get the PRTG to NetBox field mapping documentation."""
    return jsonify({
        'success': True,
        'mapping': {
            'prtg_field': 'netbox_field',
            'host (IP)': 'primary_ip4 (identifier)',
            'device': 'name',
            'group': 'comments',
            'tags': 'tags',
            'message': 'description',
            'status': 'status (mapped: Up→active, Down→failed, Paused→offline)',
        },
        'required_selections': {
            'site_id': 'NetBox Site - where the device is located',
            'device_type_id': 'NetBox Device Type - hardware model',
            'role_id': 'NetBox Device Role - function (router, switch, server, etc.)',
        }
    })


@prtg_netbox_import_bp.route('/create-site', methods=['POST'])
def create_site():
    """Create a new NetBox site."""
    try:
        importer = PRTGNetBoxImporter()
        data = request.get_json() or {}
        
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'error': 'Site name is required'}), 400
        
        # Generate slug from name
        slug = name.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        result = importer.netbox.create_site(
            name=name,
            slug=slug,
            status='active',
            description=data.get('description', '')
        )
        
        return jsonify({
            'success': True,
            'site': {'id': result['id'], 'name': result['name'], 'slug': result['slug']}
        })
    except Exception as e:
        logger.error(f"Error creating site: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/create-device-type', methods=['POST'])
def create_device_type():
    """Create a new NetBox device type."""
    try:
        importer = PRTGNetBoxImporter()
        data = request.get_json() or {}
        
        model = data.get('model')
        manufacturer_id = data.get('manufacturer_id')
        
        if not model:
            return jsonify({'success': False, 'error': 'Model name is required'}), 400
        
        # If no manufacturer provided, try to get or create a generic one
        if not manufacturer_id:
            # Try to find "Generic" manufacturer or create one
            try:
                manufacturers = importer.netbox._request('GET', 'dcim/manufacturers/', params={'name': 'Generic'})
                if manufacturers.get('results'):
                    manufacturer_id = manufacturers['results'][0]['id']
                else:
                    # Create Generic manufacturer
                    new_mfr = importer.netbox._request('POST', 'dcim/manufacturers/', json={
                        'name': 'Generic',
                        'slug': 'generic'
                    })
                    manufacturer_id = new_mfr['id']
            except Exception as e:
                logger.warning(f"Could not get/create Generic manufacturer: {e}")
                return jsonify({'success': False, 'error': 'manufacturer_id is required'}), 400
        
        # Generate slug from model
        slug = model.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        result = importer.netbox.create_device_type(
            manufacturer_id=manufacturer_id,
            model=model,
            slug=slug
        )
        
        return jsonify({
            'success': True,
            'device_type': {
                'id': result['id'],
                'model': result['model'],
                'display': f"{result.get('manufacturer', {}).get('name', '')} {result['model']}"
            }
        })
    except Exception as e:
        logger.error(f"Error creating device type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/create-device-role', methods=['POST'])
def create_device_role():
    """Create a new NetBox device role."""
    try:
        importer = PRTGNetBoxImporter()
        data = request.get_json() or {}
        
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'error': 'Role name is required'}), 400
        
        # Generate slug from name
        slug = name.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        # Default color (gray)
        color = data.get('color', '9e9e9e')
        
        result = importer.netbox.create_device_role(
            name=name,
            slug=slug,
            color=color
        )
        
        return jsonify({
            'success': True,
            'device_role': {'id': result['id'], 'name': result['name'], 'slug': result['slug']}
        })
    except Exception as e:
        logger.error(f"Error creating device role: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@prtg_netbox_import_bp.route('/manufacturers', methods=['GET'])
def get_manufacturers():
    """Get NetBox manufacturers for device type creation."""
    try:
        importer = PRTGNetBoxImporter()
        result = importer.netbox._request('GET', 'dcim/manufacturers/', params={'limit': 1000})
        manufacturers = [{'id': m['id'], 'name': m['name']} for m in result.get('results', [])]
        return jsonify({'success': True, 'manufacturers': manufacturers})
    except Exception as e:
        logger.error(f"Error getting manufacturers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
