"""
NetBox API Blueprint.

Routes for NetBox integration configuration and proxy endpoints.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, ValidationError
from ..services.netbox_service import NetBoxService, NetBoxError

netbox_bp = Blueprint('netbox', __name__, url_prefix='/api/netbox')


def get_netbox_settings():
    """Get NetBox settings from database."""
    from database import DatabaseManager
    db = DatabaseManager()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT key, value FROM system_settings 
            WHERE key LIKE 'netbox_%'
        """)
        rows = cursor.fetchall()
    
    settings = {}
    for row in rows:
        key = row['key'].replace('netbox_', '')
        settings[key] = row['value']
    
    return settings


def save_netbox_settings(settings: dict):
    """Save NetBox settings to database."""
    from database import DatabaseManager
    db = DatabaseManager()
    
    with db.cursor() as cursor:
        for key, value in settings.items():
            cursor.execute("""
                INSERT INTO system_settings (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()
            """, (f'netbox_{key}', value, value))
        db.get_connection().commit()


def get_netbox_service():
    """Get configured NetBox service instance."""
    settings = get_netbox_settings()
    return NetBoxService(
        url=settings.get('url', ''),
        token=settings.get('token', ''),
        verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
    )


@netbox_bp.errorhandler(NetBoxError)
def handle_netbox_error(error):
    """Handle NetBox errors."""
    return jsonify(error_response('NETBOX_ERROR', error.message, error.details)), 502


@netbox_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


# ==================== CONFIGURATION ====================

@netbox_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get NetBox configuration settings."""
    settings = get_netbox_settings()
    # Don't expose full token
    if settings.get('token'):
        settings['token_configured'] = True
        settings['token'] = '••••••••' + settings['token'][-8:] if len(settings.get('token', '')) > 8 else '••••••••'
    else:
        settings['token_configured'] = False
    
    return jsonify(success_response(settings))


@netbox_bp.route('/settings', methods=['PUT'])
def update_settings():
    """Update NetBox configuration settings."""
    data = request.get_json() or {}
    
    settings_to_save = {}
    
    if 'url' in data:
        url = data['url'].rstrip('/')
        if url and not url.startswith(('http://', 'https://')):
            raise ValidationError('URL must start with http:// or https://')
        settings_to_save['url'] = url
    
    if 'token' in data and not data['token'].startswith('••'):
        # Only update token if it's not masked
        settings_to_save['token'] = data['token']
    
    if 'verify_ssl' in data:
        settings_to_save['verify_ssl'] = 'true' if data['verify_ssl'] else 'false'
    
    if 'default_site_id' in data:
        settings_to_save['default_site_id'] = str(data['default_site_id']) if data['default_site_id'] else ''
    
    if 'default_role_id' in data:
        settings_to_save['default_role_id'] = str(data['default_role_id']) if data['default_role_id'] else ''
    
    if 'default_device_type_id' in data:
        settings_to_save['default_device_type_id'] = str(data['default_device_type_id']) if data['default_device_type_id'] else ''
    
    save_netbox_settings(settings_to_save)
    
    return jsonify(success_response(message='NetBox settings saved'))


@netbox_bp.route('/test', methods=['POST'])
def test_connection():
    """Test connection to NetBox."""
    data = request.get_json(silent=True) or {}
    
    # Use provided credentials or saved ones
    url = data.get('url')
    token = data.get('token')
    
    if not url or not token or token.startswith('••'):
        # Use saved settings
        settings = get_netbox_settings()
        url = url or settings.get('url')
        token = settings.get('token') if (not token or token.startswith('••')) else token
    
    if not url or not token:
        return jsonify(error_response('VALIDATION_ERROR', 'URL and token are required')), 400
    
    service = NetBoxService(
        url=url,
        token=token,
        verify_ssl=data.get('verify_ssl', True)
    )
    
    result = service.test_connection()
    
    if result.get('connected'):
        return jsonify(success_response(result, message='Connected to NetBox'))
    else:
        return jsonify(error_response('CONNECTION_FAILED', result.get('error', 'Connection failed'))), 502


# ==================== DEVICES ====================

@netbox_bp.route('/devices/cached', methods=['GET'])
def list_devices_cached():
    """List devices from local cache (fast) - use this for inventory page."""
    from database import DatabaseManager
    db = DatabaseManager()
    
    search = request.args.get('q') or request.args.get('search')
    site = request.args.get('site')
    role = request.args.get('role')
    
    query = """
        SELECT netbox_device_id, device_ip, device_name, device_type, manufacturer,
               site_id, site_name, role_name, cached_at
        FROM netbox_device_cache
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (device_name ILIKE %s OR device_ip::text ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    if site:
        query += " AND site_name = %s"
        params.append(site)
    if role:
        query += " AND role_name = %s"
        params.append(role)
    
    query += " ORDER BY device_name"
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    
    devices = []
    for row in rows:
        devices.append({
            'id': row['netbox_device_id'],
            'name': row['device_name'],
            'primary_ip4': {'address': f"{row['device_ip']}/32"} if row['device_ip'] else None,
            'device_type': {'model': row['device_type'], 'manufacturer': {'name': row['manufacturer']}},
            'site': {'id': row['site_id'], 'name': row['site_name']},
            'role': {'name': row['role_name']},
            'status': {'value': 'active', 'label': 'Active'},
            '_type': 'device',
        })
    
    return jsonify({
        'success': True,
        'data': devices,
        'count': len(devices),
        'cached': True,
    })


@netbox_bp.route('/devices/<int:device_id>/cached', methods=['GET'])
def get_device_cached(device_id):
    """Get a single device from local cache."""
    from database import DatabaseManager
    db = DatabaseManager()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT netbox_device_id, device_ip, device_name, device_type, manufacturer,
                   site_id, site_name, role_name, cached_at
            FROM netbox_device_cache
            WHERE netbox_device_id = %s
        """, (device_id,))
        row = cursor.fetchone()
    
    if not row:
        return jsonify(error_response('NOT_FOUND', 'Device not found in cache')), 404
    
    device = {
        'id': row['netbox_device_id'],
        'name': row['device_name'],
        'primary_ip4': {'address': f"{row['device_ip']}/32"} if row['device_ip'] else None,
        'device_type': {'model': row['device_type'], 'manufacturer': {'name': row['manufacturer']}},
        'site': {'id': row['site_id'], 'name': row['site_name']},
        'role': {'name': row['role_name']},
        'status': {'value': 'active', 'label': 'Active'},
        '_type': 'device',
    }
    
    return jsonify(success_response(device))


@netbox_bp.route('/devices', methods=['GET'])
def list_devices():
    """List devices from NetBox (includes VMs by default)."""
    service = get_netbox_service()
    
    params = {
        'site': request.args.get('site'),
        'role': request.args.get('role'),
        'manufacturer': request.args.get('manufacturer'),
        'status': request.args.get('status'),
        'tag': request.args.get('tag'),
        'q': request.args.get('q') or request.args.get('search'),
        'limit': int(request.args.get('limit', 100)),
        'offset': int(request.args.get('offset', 0)),
    }
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    result = service.get_devices(**params)
    devices = result.get('results', [])
    
    # Also include virtual machines unless explicitly excluded
    include_vms = request.args.get('include_vms', 'true').lower() != 'false'
    vms = []
    vm_count = 0
    
    if include_vms:
        vm_params = {
            'status': params.get('status'),
            'tag': params.get('tag'),
            'limit': params.get('limit', 100),
            'offset': params.get('offset', 0),
        }
        if request.args.get('site'):
            vm_params['site'] = request.args.get('site')
        if request.args.get('q') or request.args.get('search'):
            vm_params['q'] = request.args.get('q') or request.args.get('search')
        
        vm_params = {k: v for k, v in vm_params.items() if v is not None}
        
        try:
            vm_result = service._request('GET', 'virtualization/virtual-machines/', params=vm_params)
            vms = vm_result.get('results', [])
            vm_count = vm_result.get('count', 0)
            
            # Add a type field to distinguish devices from VMs
            for device in devices:
                device['_type'] = 'device'
            for vm in vms:
                vm['_type'] = 'virtual_machine'
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to fetch VMs: {e}")
    
    # Combine devices and VMs
    all_items = devices + vms
    total_count = result.get('count', 0) + vm_count
    
    return jsonify({
        'success': True,
        'data': all_items,
        'count': total_count,
        'device_count': result.get('count', 0),
        'vm_count': vm_count,
        'next': result.get('next'),
        'previous': result.get('previous'),
    })


@netbox_bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """Get a single device from NetBox."""
    service = get_netbox_service()
    device = service.get_device(device_id)
    return jsonify(success_response(device))


@netbox_bp.route('/devices', methods=['POST'])
def create_device():
    """Create a device in NetBox."""
    service = get_netbox_service()
    data = request.get_json() or {}
    
    required = ['name', 'device_type', 'role', 'site']
    for field in required:
        if field not in data:
            raise ValidationError(f'{field} is required')
    
    device = service.create_device(
        name=data['name'],
        device_type_id=data['device_type'],
        role_id=data['role'],
        site_id=data['site'],
        status=data.get('status', 'active'),
        serial=data.get('serial'),
        description=data.get('description'),
        tags=data.get('tags'),
        custom_fields=data.get('custom_fields'),
    )
    
    return jsonify(success_response(device, message='Device created')), 201


@netbox_bp.route('/devices/<int:device_id>', methods=['PATCH'])
def update_device(device_id):
    """Update a device in NetBox."""
    service = get_netbox_service()
    data = request.get_json() or {}
    
    device = service.update_device(device_id, **data)
    return jsonify(success_response(device, message='Device updated'))


@netbox_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Delete a device from NetBox."""
    service = get_netbox_service()
    service.delete_device(device_id)
    return jsonify(success_response(message='Device deleted'))


# ==================== IP ADDRESSES ====================

@netbox_bp.route('/ip-addresses', methods=['GET'])
def list_ip_addresses():
    """List IP addresses from NetBox."""
    service = get_netbox_service()
    
    params = {
        'address': request.args.get('address'),
        'device': request.args.get('device'),
        'status': request.args.get('status'),
        'limit': int(request.args.get('limit', 100)),
        'offset': int(request.args.get('offset', 0)),
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    result = service.get_ip_addresses(**params)
    
    return jsonify({
        'success': True,
        'data': result.get('results', []),
        'count': result.get('count', 0),
    })


# ==================== IP PREFIXES ====================

@netbox_bp.route('/prefixes', methods=['GET'])
def list_prefixes():
    """List IP prefixes from NetBox IPAM."""
    service = get_netbox_service()
    
    params = {
        'limit': int(request.args.get('limit', 500)),
        'offset': int(request.args.get('offset', 0)),
    }
    
    result = service._request('GET', 'ipam/prefixes/', params=params)
    
    return jsonify({
        'success': True,
        'data': result.get('results', []),
        'count': result.get('count', 0),
    })


# ==================== IP RANGES ====================

@netbox_bp.route('/ip-ranges', methods=['GET'])
def list_ip_ranges():
    """List IP ranges from NetBox IPAM."""
    service = get_netbox_service()
    
    params = {
        'limit': int(request.args.get('limit', 100)),
        'offset': int(request.args.get('offset', 0)),
    }
    
    result = service._request('GET', 'ipam/ip-ranges/', params=params)
    
    return jsonify({
        'success': True,
        'data': result.get('results', []),
        'count': result.get('count', 0),
    })


# ==================== LOOKUP DATA ====================

@netbox_bp.route('/sites', methods=['GET'])
def list_sites():
    """List sites from NetBox."""
    service = get_netbox_service()
    result = service.get_sites(limit=500)
    return jsonify(list_response(result.get('results', [])))


@netbox_bp.route('/device-roles', methods=['GET'])
def list_device_roles():
    """List device roles from NetBox."""
    service = get_netbox_service()
    result = service.get_device_roles(limit=500)
    return jsonify(list_response(result.get('results', [])))


@netbox_bp.route('/device-types', methods=['GET'])
def list_device_types():
    """List device types from NetBox."""
    service = get_netbox_service()
    manufacturer = request.args.get('manufacturer')
    result = service.get_device_types(manufacturer=manufacturer, limit=500)
    return jsonify(list_response(result.get('results', [])))


@netbox_bp.route('/manufacturers', methods=['GET'])
def list_manufacturers():
    """List manufacturers from NetBox."""
    service = get_netbox_service()
    result = service.get_manufacturers(limit=500)
    return jsonify(list_response(result.get('results', [])))


@netbox_bp.route('/tags', methods=['GET'])
def list_tags():
    """List tags from NetBox."""
    service = get_netbox_service()
    result = service._request('GET', 'extras/tags/', params={'limit': 500})
    return jsonify(list_response(result.get('results', [])))


# ==================== DISCOVERY INTEGRATION ====================

@netbox_bp.route('/discover', methods=['POST'])
def upsert_discovered_device():
    """
    Create or update a device from discovery results.
    
    This endpoint is called by discovery jobs to sync found devices to NetBox.
    """
    service = get_netbox_service()
    settings = get_netbox_settings()
    data = request.get_json() or {}
    
    if 'ip_address' not in data:
        raise ValidationError('ip_address is required')
    
    # Get defaults from settings
    default_site = int(settings.get('default_site_id', 0)) or None
    default_role = int(settings.get('default_role_id', 0)) or None
    default_type = int(settings.get('default_device_type_id', 0)) or None
    
    result = service.upsert_discovered_device(
        ip_address=data['ip_address'],
        hostname=data.get('hostname'),
        description=data.get('description'),
        vendor=data.get('vendor'),
        model=data.get('model'),
        serial=data.get('serial'),
        site_id=data.get('site_id') or default_site,
        role_id=data.get('role_id') or default_role,
        device_type_id=data.get('device_type_id') or default_type,
        status=data.get('status', 'active'),
        tags=data.get('tags'),
        custom_fields=data.get('custom_fields'),
    )
    
    return jsonify(success_response(result, message='Device synced to NetBox'))
