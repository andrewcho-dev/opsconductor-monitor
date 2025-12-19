"""
Ciena MCP API Blueprint.

Routes for Ciena MCP integration configuration and data retrieval.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..utils.errors import AppError, ValidationError
from ..services.ciena_mcp_service import CienaMCPService, CienaMCPError, reset_mcp_service

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')


def get_mcp_settings():
    """Get MCP settings from database."""
    from database import DatabaseManager
    db = DatabaseManager()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT key, value FROM system_settings 
            WHERE key LIKE 'mcp_%'
        """)
        rows = cursor.fetchall()
    
    settings = {}
    for row in rows:
        key = row['key'].replace('mcp_', '')
        settings[key] = row['value']
    
    return settings


def save_mcp_settings(settings: dict):
    """Save MCP settings to database."""
    from database import DatabaseManager
    db = DatabaseManager()
    
    with db.cursor() as cursor:
        for key, value in settings.items():
            cursor.execute("""
                INSERT INTO system_settings (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()
            """, (f'mcp_{key}', value, value))
        db.get_connection().commit()
    
    # Reset the global service instance to pick up new settings
    reset_mcp_service()


def get_mcp_service():
    """Get configured MCP service instance."""
    settings = get_mcp_settings()
    return CienaMCPService(
        url=settings.get('url', ''),
        username=settings.get('username', ''),
        password=settings.get('password', ''),
        verify_ssl=settings.get('verify_ssl', 'false').lower() == 'true'
    )


@mcp_bp.errorhandler(CienaMCPError)
def handle_mcp_error(error):
    """Handle MCP errors."""
    return jsonify(error_response('MCP_ERROR', error.message)), 502


@mcp_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


# ==================== CONFIGURATION ====================

@mcp_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get MCP configuration settings."""
    settings = get_mcp_settings()
    # Don't expose password
    if settings.get('password'):
        settings['password_configured'] = True
        settings['password'] = '••••••••'
    else:
        settings['password_configured'] = False
    
    return jsonify(success_response(settings))


@mcp_bp.route('/settings', methods=['PUT'])
def update_settings():
    """Update MCP configuration settings."""
    data = request.get_json() or {}
    
    settings_to_save = {}
    
    if 'url' in data:
        url = data['url'].rstrip('/')
        if url and not url.startswith(('http://', 'https://')):
            raise ValidationError('URL must start with http:// or https://')
        settings_to_save['url'] = url
    
    if 'username' in data:
        settings_to_save['username'] = data['username']
    
    if 'password' in data and data['password'] != '••••••••':
        settings_to_save['password'] = data['password']
    
    if 'verify_ssl' in data:
        settings_to_save['verify_ssl'] = 'true' if data['verify_ssl'] else 'false'
    
    if settings_to_save:
        save_mcp_settings(settings_to_save)
    
    return jsonify(success_response({'message': 'Settings updated successfully'}))


@mcp_bp.route('/test', methods=['POST'])
def test_connection():
    """Test MCP connection with current or provided settings."""
    data = request.get_json() or {}
    
    # Use provided settings or fall back to saved settings
    saved_settings = get_mcp_settings()
    
    url = data.get('url') or saved_settings.get('url', '')
    username = data.get('username') or saved_settings.get('username', '')
    password = data.get('password') if data.get('password') and data['password'] != '••••••••' else saved_settings.get('password', '')
    verify_ssl = data.get('verify_ssl', saved_settings.get('verify_ssl', 'false').lower() == 'true')
    
    service = CienaMCPService(url=url, username=username, password=password, verify_ssl=verify_ssl)
    result = service.test_connection()
    
    if result['success']:
        # Also get summary counts
        try:
            summary = service.get_device_summary()
            result['summary'] = summary
        except:
            pass
    
    return jsonify(success_response(result))


# ==================== DEVICES ====================

@mcp_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get devices from MCP."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    service = get_mcp_service()
    result = service.get_devices(limit=limit, offset=offset)
    
    # Transform to simpler format
    devices = []
    for device in result.get('data', []):
        attrs = device.get('attributes', {})
        display = attrs.get('displayData', {})
        devices.append({
            'id': device.get('id'),
            'name': attrs.get('name') or display.get('displayName'),
            'ip_address': attrs.get('ipAddress') or display.get('displayIpAddress'),
            'mac_address': attrs.get('macAddress') or display.get('displayMACAddress'),
            'serial_number': attrs.get('serialNumber'),
            'device_type': attrs.get('deviceType'),
            'software_version': attrs.get('softwareVersion'),
            'vendor': attrs.get('vendor', 'Ciena'),
            'sync_state': display.get('displaySyncState'),
            'association_state': display.get('displayAssociationState'),
        })
    
    return jsonify(success_response({
        'devices': devices,
        'total': result.get('meta', {}).get('total', len(devices)),
        'limit': limit,
        'offset': offset,
    }))


@mcp_bp.route('/devices/all', methods=['GET'])
def get_all_devices():
    """Get all devices from MCP (with pagination handling)."""
    service = get_mcp_service()
    devices = service.get_all_devices()
    
    # Transform to simpler format
    device_list = []
    for device in devices:
        attrs = device.get('attributes', {})
        display = attrs.get('displayData', {})
        device_list.append({
            'id': device.get('id'),
            'name': attrs.get('name') or display.get('displayName'),
            'ip_address': attrs.get('ipAddress') or display.get('displayIpAddress'),
            'mac_address': attrs.get('macAddress') or display.get('displayMACAddress'),
            'serial_number': attrs.get('serialNumber'),
            'device_type': attrs.get('deviceType'),
            'software_version': attrs.get('softwareVersion'),
            'vendor': attrs.get('vendor', 'Ciena'),
            'sync_state': display.get('displaySyncState'),
            'association_state': display.get('displayAssociationState'),
        })
    
    return jsonify(success_response({
        'devices': device_list,
        'total': len(device_list),
    }))


# ==================== EQUIPMENT ====================

@mcp_bp.route('/equipment', methods=['GET'])
def get_equipment():
    """Get equipment from MCP."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    device_id = request.args.get('device_id')
    
    service = get_mcp_service()
    result = service.get_equipment(limit=limit, offset=offset, device_id=device_id)
    
    # Transform to simpler format
    equipment = []
    for item in result.get('data', []):
        attrs = item.get('attributes', {})
        display = attrs.get('displayData', {})
        installed = attrs.get('installedSpec', {})
        locations = attrs.get('locations', [{}])
        location = locations[0] if locations else {}
        
        equipment.append({
            'id': item.get('id'),
            'name': display.get('displayName'),
            'type': installed.get('type') or attrs.get('cardType'),
            'serial_number': installed.get('serialNumber'),
            'part_number': installed.get('partNumber'),
            'manufacturer': installed.get('manufacturer'),
            'slot': location.get('subslot'),
            'device_name': location.get('neName'),
            'state': attrs.get('state'),
        })
    
    return jsonify(success_response({
        'equipment': equipment,
        'total': result.get('meta', {}).get('total', len(equipment)),
        'limit': limit,
        'offset': offset,
    }))


# ==================== LINKS/TOPOLOGY ====================

@mcp_bp.route('/links', methods=['GET'])
def get_links():
    """Get network links from MCP."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    service = get_mcp_service()
    result = service.get_links(limit=limit, offset=offset)
    
    # Transform to simpler format
    links = []
    for link in result.get('data', []):
        attrs = link.get('attributes', {})
        utilization = attrs.get('utilizationData', {})
        
        links.append({
            'id': link.get('id'),
            'service_class': attrs.get('serviceClass'),
            'layer_rate': attrs.get('layerRate'),
            'protocol': attrs.get('protocol'),
            'admin_state': attrs.get('adminState'),
            'operation_state': attrs.get('operationState'),
            'total_capacity': utilization.get('totalCapacity'),
            'used_capacity': utilization.get('usedCapacity'),
            'utilization_percent': utilization.get('utilizationPercent'),
        })
    
    return jsonify(success_response({
        'links': links,
        'total': result.get('meta', {}).get('total', len(links)),
        'limit': limit,
        'offset': offset,
    }))


# ==================== DEVICE BY IP ====================

@mcp_bp.route('/device/<ip>', methods=['GET'])
def get_device_by_ip(ip):
    """Get MCP device info by IP address, including equipment."""
    service = get_mcp_service()
    
    if not service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    # Get all devices and find by IP
    all_devices = service.get_all_devices()
    
    device_data = None
    for device in all_devices:
        attrs = device.get('attributes', {})
        device_ip = attrs.get('ipAddress') or attrs.get('displayData', {}).get('displayIpAddress')
        if device_ip == ip:
            display = attrs.get('displayData', {})
            device_data = {
                'id': device.get('id'),
                'name': attrs.get('name') or display.get('displayName'),
                'ip_address': device_ip,
                'mac_address': attrs.get('macAddress') or display.get('displayMACAddress'),
                'serial_number': attrs.get('serialNumber'),
                'device_type': attrs.get('deviceType'),
                'software_version': attrs.get('softwareVersion'),
                'vendor': attrs.get('vendor', 'Ciena'),
                'sync_state': display.get('displaySyncState'),
                'association_state': display.get('displayAssociationState'),
                'model': attrs.get('model'),
                'hardware_version': attrs.get('hardwareVersion'),
                'network_construct_type': attrs.get('networkConstructType'),
            }
            break
    
    if not device_data:
        return jsonify(success_response({
            'found': False,
            'device': None,
            'equipment': []
        }))
    
    # Get equipment for this device by filtering by device name
    device_name = device_data['name']
    all_equipment = service.get_all_equipment()
    
    # Filter equipment to only this device
    all_equipment = [e for e in all_equipment if e.get('attributes', {}).get('locations', [{}])[0].get('neName') == device_name]
    
    equipment_list = []
    for item in all_equipment:
        attrs = item.get('attributes', {})
        display = attrs.get('displayData', {})
        installed = attrs.get('installedSpec', {})
        locations = attrs.get('locations', [{}])
        location = locations[0] if locations else {}
        
        equipment_list.append({
            'id': item.get('id'),
            'name': display.get('displayName'),
            'type': installed.get('type') or attrs.get('cardType'),
            'serial_number': installed.get('serialNumber'),
            'part_number': installed.get('partNumber'),
            'manufacturer': installed.get('manufacturer'),
            'hardware_version': installed.get('hardwareVersion'),
            'slot': location.get('subslot'),
            'state': attrs.get('state'),
            'category': attrs.get('category'),
        })
    
    # Get ports for this device
    device_id = device_data['id']
    all_ports = service.get_all_ports(device_id)
    
    port_list = []
    for port in all_ports:
        attrs = port.get('attributes', {})
        display = attrs.get('displayData', {})
        state_data = attrs.get('stateData', {})
        planned_spec = attrs.get('plannedSpec', {})
        
        port_list.append({
            'id': port.get('id'),
            'name': display.get('displayName') or attrs.get('name'),
            'type': attrs.get('type'),
            'layer_rate': attrs.get('layerRate'),
            'admin_state': state_data.get('adminState'),
            'operational_state': state_data.get('operationalState'),
            'speed': planned_spec.get('rate') or attrs.get('rate'),
            'mtu': planned_spec.get('mtu'),
            'mac_address': attrs.get('macAddress'),
            'description': attrs.get('description'),
            'direction': attrs.get('direction'),
        })
    
    return jsonify(success_response({
        'found': True,
        'device': device_data,
        'equipment': equipment_list,
        'equipment_count': len(equipment_list),
        'ports': port_list,
        'port_count': len(port_list),
    }))


# ==================== SERVICES (FREs) ====================

@mcp_bp.route('/services', methods=['GET'])
def get_services():
    """Get services/circuits from MCP."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    service_class = request.args.get('class')
    
    service = get_mcp_service()
    result = service.get_services(limit=limit, offset=offset, service_class=service_class)
    
    # Transform to simpler format
    services = []
    for svc in result.get('data', []):
        attrs = svc.get('attributes', {})
        display = attrs.get('displayData', {})
        utilization = attrs.get('utilizationData', {})
        add_attrs = attrs.get('additionalAttributes', {})
        
        services.append({
            'id': svc.get('id'),
            'name': attrs.get('userLabel') or attrs.get('mgmtName') or svc.get('id'),
            'service_class': attrs.get('serviceClass'),
            'layer_rate': attrs.get('layerRate'),
            'admin_state': display.get('adminState') or attrs.get('adminState'),
            'operation_state': display.get('operationState') or attrs.get('operationState'),
            'deployment_state': display.get('displayDeploymentState') or attrs.get('deploymentState'),
            'total_capacity': utilization.get('totalCapacity'),
            'used_capacity': utilization.get('usedCapacity'),
            'utilization_percent': utilization.get('utilizationPercent'),
            'capacity_units': utilization.get('capacityUnits'),
            # Ring-specific fields
            'ring_id': add_attrs.get('ringId'),
            'ring_state': add_attrs.get('ringState'),
            'ring_status': add_attrs.get('ringStatus'),
            'ring_type': add_attrs.get('ringType'),
            'ring_members': add_attrs.get('ringMembers'),
            'logical_ring': add_attrs.get('logicalRingName'),
            'virtual_ring': add_attrs.get('virtualRingName'),
        })
    
    return jsonify(success_response({
        'services': services,
        'total': result.get('meta', {}).get('total', len(services)),
        'limit': limit,
        'offset': offset,
    }))


@mcp_bp.route('/services/rings', methods=['GET'])
def get_rings():
    """Get G.8032 ring services from MCP."""
    service = get_mcp_service()
    rings_raw = service.get_rings()
    
    rings = []
    for ring in rings_raw:
        attrs = ring.get('attributes', {})
        display = attrs.get('displayData', {})
        add_attrs = attrs.get('additionalAttributes', {})
        
        rings.append({
            'id': ring.get('id'),
            'name': attrs.get('mgmtName') or attrs.get('userLabel') or ring.get('id'),
            'ring_id': add_attrs.get('ringId'),
            'ring_state': add_attrs.get('ringState'),
            'ring_status': add_attrs.get('ringStatus'),
            'ring_type': add_attrs.get('ringType'),
            'ring_members': add_attrs.get('ringMembers'),
            'logical_ring': add_attrs.get('logicalRingName'),
            'virtual_ring': add_attrs.get('virtualRingName'),
            'rpl_owner': add_attrs.get('rplOwnerCtpId'),
            'revertive': add_attrs.get('revertive'),
            'wait_to_restore': add_attrs.get('waitToRestore'),
            'guard_time': add_attrs.get('guardTime'),
            'hold_off_time': add_attrs.get('holdOffTime'),
            'raps_vid': add_attrs.get('rapsVid'),
        })
    
    return jsonify(success_response({
        'rings': rings,
        'total': len(rings),
    }))


@mcp_bp.route('/services/summary', methods=['GET'])
def get_services_summary():
    """Get summary of all MCP services."""
    service = get_mcp_service()
    summary = service.get_service_summary()
    
    return jsonify(success_response(summary))


# ==================== SUMMARY ====================

@mcp_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get MCP inventory summary."""
    service = get_mcp_service()
    summary = service.get_device_summary()
    
    return jsonify(success_response(summary))


# ==================== SYNC TO NETBOX ====================

@mcp_bp.route('/sync/netbox', methods=['POST'])
def sync_to_netbox():
    """Sync MCP devices to NetBox."""
    data = request.get_json() or {}
    
    create_missing = data.get('create_missing', True)
    site_id = data.get('site_id')
    device_role_id = data.get('device_role_id')
    
    mcp_service = get_mcp_service()
    
    from .netbox import get_netbox_service
    netbox_service = get_netbox_service()
    
    if not netbox_service.is_configured:
        return jsonify(error_response('NETBOX_ERROR', 'NetBox is not configured')), 400
    
    stats = mcp_service.sync_devices_to_netbox(
        netbox_service,
        site_id=site_id,
        device_role_id=device_role_id,
        create_missing=create_missing
    )
    
    return jsonify(success_response(stats))


@mcp_bp.route('/sync/equipment', methods=['POST'])
def sync_equipment_to_netbox():
    """Sync MCP equipment (SFPs, cards) to NetBox as inventory items."""
    mcp_service = get_mcp_service()
    
    from .netbox import get_netbox_service
    netbox_service = get_netbox_service()
    
    if not netbox_service.is_configured:
        return jsonify(error_response('NETBOX_ERROR', 'NetBox is not configured')), 400
    
    stats = mcp_service.sync_equipment_to_netbox(netbox_service)
    
    return jsonify(success_response(stats))
