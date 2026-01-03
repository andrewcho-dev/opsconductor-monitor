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

@mcp_bp.route('/services/raw', methods=['GET'])
def get_services_raw():
    """Get raw services data from MCP for debugging."""
    limit = request.args.get('limit', 5, type=int)
    service = get_mcp_service()
    result = service.get_services(limit=limit, offset=0)
    return jsonify(success_response(result))


@mcp_bp.route('/services', methods=['GET'])
def get_services():
    """Get services/circuits from MCP."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    service_class = request.args.get('class')
    
    service = get_mcp_service()
    result = service.get_services(limit=limit, offset=offset)
    
    # Build endpoint -> (device ID, port) lookup from included data
    endpoint_to_info = {}
    for item in result.get('included', []):
        if item.get('type') == 'endPoints':
            ep_id = item.get('id')
            nc_data = item.get('relationships', {}).get('networkConstructs', {}).get('data', [])
            tpe_data = item.get('relationships', {}).get('tpes', {}).get('data', [])
            
            device_id = nc_data[0].get('id') if nc_data else None
            
            # Extract port from TPE ID (format: device_id::TPE_4_PTP -> port 4)
            port_name = None
            if tpe_data:
                tpe_id = tpe_data[0].get('id', '')
                if '::TPE_' in tpe_id:
                    port_part = tpe_id.split('::TPE_')[1].replace('_PTP', '').replace('_CTP', '')
                    # Clean up complex port names - extract just the number if present
                    import re
                    match = re.match(r'^(\d+)', port_part)
                    if match:
                        port_name = match.group(1)
                    elif port_part.startswith('FTP_G8032_'):
                        # Ring FTP port - simplify display
                        port_name = 'FTP'
                    else:
                        port_name = port_part
            
            endpoint_to_info[ep_id] = {'device_id': device_id, 'port': port_name}
    
    # Get device lookup (cached)
    device_lookup = _get_device_lookup(service)
    
    # Transform to simpler format
    services = []
    for svc in result.get('data', []):
        attrs = svc.get('attributes', {})
        display = attrs.get('displayData', {})
        utilization = attrs.get('utilizationData', {})
        add_attrs = attrs.get('additionalAttributes', {})
        
        # Extract endpoint device and port names
        endpoints = svc.get('relationships', {}).get('endPoints', {}).get('data', [])
        a_end_device = None
        a_end_port = None
        z_end_device = None
        z_end_port = None
        
        if len(endpoints) >= 1:
            ep_id = endpoints[0].get('id')
            ep_info = endpoint_to_info.get(ep_id, {})
            device_id = ep_info.get('device_id')
            a_end_device = device_lookup.get(device_id) if device_id else None
            a_end_port = ep_info.get('port')
        if len(endpoints) >= 2:
            ep_id = endpoints[1].get('id')
            ep_info = endpoint_to_info.get(ep_id, {})
            device_id = ep_info.get('device_id')
            z_end_device = device_lookup.get(device_id) if device_id else None
            z_end_port = ep_info.get('port')
        
        # Build display name: prefer userLabel, then construct from endpoints
        user_label = attrs.get('userLabel') or ''
        mgmt_name = attrs.get('mgmtName') or ''
        if user_label.strip():
            display_name = user_label
        elif mgmt_name.strip():
            display_name = mgmt_name
        elif a_end_device and z_end_device:
            display_name = f"{a_end_device} ↔ {z_end_device}"
        elif a_end_device:
            display_name = f"{a_end_device} ↔ ?"
        else:
            display_name = svc.get('id')
        
        services.append({
            'id': svc.get('id'),
            'name': display_name,
            'service_class': attrs.get('serviceClass'),
            'layer_rate': attrs.get('layerRate'),
            'admin_state': display.get('adminState') or attrs.get('adminState'),
            'operation_state': display.get('operationState') or attrs.get('operationState'),
            'deployment_state': display.get('displayDeploymentState') or attrs.get('deploymentState'),
            'total_capacity': utilization.get('totalCapacity'),
            'used_capacity': utilization.get('usedCapacity'),
            'utilization_percent': utilization.get('utilizationPercent'),
            'capacity_units': utilization.get('capacityUnits'),
            'a_end': a_end_device,
            'a_end_port': a_end_port,
            'z_end': z_end_device,
            'z_end_port': z_end_port,
            # Ring-specific fields
            'ring_id': add_attrs.get('ringId'),
            'ring_state': add_attrs.get('ringState'),
            'ring_status': add_attrs.get('ringStatus'),
            'ring_type': add_attrs.get('ringType'),
            'ring_members': add_attrs.get('ringMembers'),
            'logical_ring': add_attrs.get('logicalRingName'),
            'virtual_ring': add_attrs.get('virtualRingName'),
        })
    
    # Group services by name into folders
    from collections import defaultdict
    grouped = defaultdict(list)
    for svc in services:
        grouped[svc['name']].append(svc)
    
    # Build folder structure
    service_folders = []
    for name, links in sorted(grouped.items()):
        # Aggregate state - if any link is down, folder is down
        states = [(l.get('operation_state') or '').lower() for l in links]
        if 'down' in states:
            folder_state = 'down'
        elif all(s == 'up' for s in states):
            folder_state = 'up'
        else:
            folder_state = 'partial'
        
        # Get service class from first link
        svc_class = links[0].get('service_class') if links else None
        
        service_folders.append({
            'name': name,
            'service_class': svc_class,
            'link_count': len(links),
            'state': folder_state,
            'links': links,
        })
    
    return jsonify(success_response({
        'services': services,  # Keep flat list for backward compatibility
        'service_folders': service_folders,  # New grouped structure
        'total_links': len(services),
        'total_services': len(service_folders),
        'limit': limit,
        'offset': offset,
    }))


# Cache for device lookup
_device_lookup_cache = None
_device_lookup_time = 0

def _get_device_lookup(service):
    """Get cached device ID -> name lookup."""
    import time
    global _device_lookup_cache, _device_lookup_time
    
    # Cache for 5 minutes
    if _device_lookup_cache and (time.time() - _device_lookup_time) < 300:
        return _device_lookup_cache
    
    devices = service.get_all_devices()
    lookup = {}
    for d in devices:
        attrs = d.get('attributes', {})
        display = attrs.get('displayData', {})
        name = attrs.get('name') or display.get('displayName') or d.get('id')
        lookup[d.get('id')] = name
    
    _device_lookup_cache = lookup
    _device_lookup_time = time.time()
    return lookup


@mcp_bp.route('/services/rings', methods=['GET'])
def get_rings():
    """Get G.8032 ring services from MCP with member services."""
    service = get_mcp_service()
    rings_raw = service.get_rings()
    
    # Also get all services to find ring members
    all_services_result = service.get_services(limit=500, offset=0)
    
    # Build endpoint -> (device ID, port) lookup from included data
    endpoint_to_info = {}
    for item in all_services_result.get('included', []):
        if item.get('type') == 'endPoints':
            ep_id = item.get('id')
            nc_data = item.get('relationships', {}).get('networkConstructs', {}).get('data', [])
            tpe_data = item.get('relationships', {}).get('tpes', {}).get('data', [])
            
            device_id = nc_data[0].get('id') if nc_data else None
            
            port_name = None
            if tpe_data:
                tpe_id = tpe_data[0].get('id', '')
                if '::TPE_' in tpe_id:
                    port_part = tpe_id.split('::TPE_')[1].replace('_PTP', '').replace('_CTP', '')
                    import re
                    match = re.match(r'^(\d+)', port_part)
                    if match:
                        port_name = match.group(1)
                    elif port_part.startswith('FTP_G8032_'):
                        # Ring FTP port - extract ring name for display
                        port_name = 'FTP'
                    else:
                        port_name = port_part
            
            endpoint_to_info[ep_id] = {'device_id': device_id, 'port': port_name}
    
    # Get device lookup
    device_lookup = _get_device_lookup(service)
    
    # Build services list with endpoint info
    services_by_ring = {}
    for svc in all_services_result.get('data', []):
        attrs = svc.get('attributes', {})
        add_attrs = attrs.get('additionalAttributes', {})
        virtual_ring = add_attrs.get('virtualRingName')
        
        if not virtual_ring:
            continue
        
        # Extract endpoint info
        endpoints = svc.get('relationships', {}).get('endPoints', {}).get('data', [])
        a_end_device = None
        a_end_port = None
        z_end_device = None
        z_end_port = None
        
        if len(endpoints) >= 1:
            ep_id = endpoints[0].get('id')
            ep_info = endpoint_to_info.get(ep_id, {})
            device_id = ep_info.get('device_id')
            a_end_device = device_lookup.get(device_id) if device_id else None
            a_end_port = ep_info.get('port')
        if len(endpoints) >= 2:
            ep_id = endpoints[1].get('id')
            ep_info = endpoint_to_info.get(ep_id, {})
            device_id = ep_info.get('device_id')
            z_end_device = device_lookup.get(device_id) if device_id else None
            z_end_port = ep_info.get('port')
        
        display = attrs.get('displayData', {})
        utilization = attrs.get('utilizationData', {})
        
        svc_data = {
            'id': svc.get('id'),
            'name': attrs.get('userLabel') or attrs.get('mgmtName') or svc.get('id'),
            'a_end': a_end_device,
            'a_end_port': a_end_port,
            'z_end': z_end_device,
            'z_end_port': z_end_port,
            'operation_state': display.get('operationState') or attrs.get('operationState'),
            'admin_state': display.get('adminState') or attrs.get('adminState'),
            'total_capacity': utilization.get('totalCapacity'),
            'capacity_units': utilization.get('capacityUnits'),
        }
        
        if virtual_ring not in services_by_ring:
            services_by_ring[virtual_ring] = []
        services_by_ring[virtual_ring].append(svc_data)
    
    # Build ring data with member services
    rings = []
    for ring in rings_raw:
        attrs = ring.get('attributes', {})
        display = attrs.get('displayData', {})
        add_attrs = attrs.get('additionalAttributes', {})
        
        virtual_ring = add_attrs.get('virtualRingName')
        
        # Parse g8032Edges to get actual ring segments (inter-switch links)
        ring_segments_raw = []
        g8032_edges = add_attrs.get('g8032Edges') or ''
        if g8032_edges:
            # Format: device1::TPE_port1_...,device2::TPE_port2_...;device3::TPE_port3_...,device4::TPE_port4_...
            segments = g8032_edges.split(';')
            for seg in segments:
                parts = seg.split(',')
                if len(parts) == 2:
                    ep1, ep2 = parts
                    # Parse endpoint 1
                    dev1_id = ep1.split('::')[0] if '::' in ep1 else None
                    port1 = None
                    if '::TPE_' in ep1:
                        port_part = ep1.split('::TPE_')[1]
                        import re
                        match = re.match(r'^(\d+)', port_part)
                        port1 = match.group(1) if match else port_part.split('_')[0]
                    
                    # Parse endpoint 2
                    dev2_id = ep2.split('::')[0] if '::' in ep2 else None
                    port2 = None
                    if '::TPE_' in ep2:
                        port_part = ep2.split('::TPE_')[1]
                        match = re.match(r'^(\d+)', port_part)
                        port2 = match.group(1) if match else port_part.split('_')[0]
                    
                    dev1_name = device_lookup.get(dev1_id, dev1_id[:8] + '...' if dev1_id else None)
                    dev2_name = device_lookup.get(dev2_id, dev2_id[:8] + '...' if dev2_id else None)
                    
                    ring_segments_raw.append({
                        'a_end': dev1_name,
                        'a_end_port': port1,
                        'z_end': dev2_name,
                        'z_end_port': port2,
                    })
        
        # Get RPL owner info first (needed for ordering)
        rpl_owner_ctp = add_attrs.get('rplOwnerCtpId') or ''
        rpl_device_id = rpl_owner_ctp.split('::')[0] if '::' in rpl_owner_ctp else None
        rpl_owner_device = device_lookup.get(rpl_device_id, rpl_device_id[:8] + '...' if rpl_device_id else None)
        rpl_owner_port = None
        if '::TPE_' in rpl_owner_ctp:
            port_part = rpl_owner_ctp.split('::TPE_')[1]
            match = re.match(r'^(\d+)', port_part)
            rpl_owner_port = match.group(1) if match else port_part.split('_')[0]
        
        # Order segments starting from RPL block and following the ring path
        ring_segments = []
        if ring_segments_raw and rpl_owner_device:
            # Build adjacency: device -> list of (port, connected_device, connected_port, segment_index)
            adjacency = {}
            for idx, seg in enumerate(ring_segments_raw):
                a_dev, a_port = seg['a_end'], seg['a_end_port']
                z_dev, z_port = seg['z_end'], seg['z_end_port']
                
                if a_dev not in adjacency:
                    adjacency[a_dev] = []
                adjacency[a_dev].append((a_port, z_dev, z_port, idx))
                
                if z_dev not in adjacency:
                    adjacency[z_dev] = []
                adjacency[z_dev].append((z_port, a_dev, a_port, idx))
            
            # Start from RPL owner device/port and traverse the ring
            visited_segments = set()
            current_device = rpl_owner_device
            current_port = rpl_owner_port
            
            # Find the segment that starts from RPL block
            for _ in range(len(ring_segments_raw) + 1):
                if current_device not in adjacency:
                    break
                
                found_next = False
                for port, next_dev, next_port, seg_idx in adjacency.get(current_device, []):
                    if seg_idx in visited_segments:
                        continue
                    if port == current_port or current_port is None:
                        # Add this segment
                        seg = ring_segments_raw[seg_idx]
                        # Check if this segment contains the RPL block
                        is_rpl_segment = (len(ring_segments) == 0)  # First segment from RPL
                        
                        # Orient segment so current_device is A-end
                        if seg['a_end'] == current_device:
                            new_seg = dict(seg)
                            new_seg['is_rpl_block'] = is_rpl_segment
                            new_seg['rpl_blocked_port'] = 'a_end' if is_rpl_segment else None
                            ring_segments.append(new_seg)
                            current_device = seg['z_end']
                            current_port = None  # Find any unvisited port on next device
                        else:
                            ring_segments.append({
                                'a_end': seg['z_end'],
                                'a_end_port': seg['z_end_port'],
                                'z_end': seg['a_end'],
                                'z_end_port': seg['a_end_port'],
                                'is_rpl_block': is_rpl_segment,
                                'rpl_blocked_port': 'a_end' if is_rpl_segment else None,
                            })
                            current_device = seg['a_end']
                            current_port = None
                        visited_segments.add(seg_idx)
                        found_next = True
                        break
                
                if not found_next:
                    # Try any unvisited segment from current device
                    for port, next_dev, next_port, seg_idx in adjacency.get(current_device, []):
                        if seg_idx not in visited_segments:
                            seg = ring_segments_raw[seg_idx]
                            if seg['a_end'] == current_device:
                                new_seg = dict(seg)
                                new_seg['is_rpl_block'] = False
                                new_seg['rpl_blocked_port'] = None
                                ring_segments.append(new_seg)
                                current_device = seg['z_end']
                            else:
                                ring_segments.append({
                                    'a_end': seg['z_end'],
                                    'a_end_port': seg['z_end_port'],
                                    'z_end': seg['a_end'],
                                    'z_end_port': seg['a_end_port'],
                                    'is_rpl_block': False,
                                    'rpl_blocked_port': None,
                                })
                                current_device = seg['a_end']
                            visited_segments.add(seg_idx)
                            found_next = True
                            break
                
                if not found_next:
                    break
            
            # Add any remaining unvisited segments
            for idx, seg in enumerate(ring_segments_raw):
                if idx not in visited_segments:
                    new_seg = dict(seg)
                    new_seg['is_rpl_block'] = False
                    new_seg['rpl_blocked_port'] = None
                    ring_segments.append(new_seg)
        else:
            # No RPL owner, just add flags to raw segments
            ring_segments = []
            for seg in ring_segments_raw:
                new_seg = dict(seg)
                new_seg['is_rpl_block'] = False
                new_seg['rpl_blocked_port'] = None
                ring_segments.append(new_seg)
        
        # Calculate ring health based on ring state (not member services)
        ring_state = add_attrs.get('ringState')
        ring_status = add_attrs.get('ringStatus')
        if ring_state == 'OK' and ring_status == 'OK':
            members_state = 'up'
        else:
            members_state = 'down'
        
        # Determine protection state
        # If ring_state is not OK or ring_status is not OK, protection may have switched
        protection_active = ring_state != 'OK' or ring_status != 'OK'
        
        rings.append({
            'id': ring.get('id'),
            'name': attrs.get('mgmtName') or attrs.get('userLabel') or ring.get('id'),
            'ring_id': add_attrs.get('ringId'),
            'ring_state': ring_state,
            'ring_status': ring_status,
            'ring_type': add_attrs.get('ringType'),
            'ring_members': add_attrs.get('ringMembers'),
            'logical_ring': add_attrs.get('logicalRingName'),
            'virtual_ring': virtual_ring,
            'rpl_owner': add_attrs.get('rplOwnerCtpId'),
            'rpl_owner_device': rpl_owner_device,
            'rpl_owner_port': rpl_owner_port,
            'protection_active': protection_active,
            'revertive': add_attrs.get('revertive'),
            'wait_to_restore': add_attrs.get('waitToRestore'),
            'guard_time': add_attrs.get('guardTime'),
            'hold_off_time': add_attrs.get('holdOffTime'),
            'raps_vid': add_attrs.get('rapsVid'),
            'ring_segments': ring_segments,
            'segment_count': len(ring_segments),
            'members_state': members_state,
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


# ==================== PERFORMANCE METRICS ====================

@mcp_bp.route('/pm/<device_id>/port/<port_number>', methods=['GET'])
def get_port_realtime_pm(device_id, port_number):
    """
    Get real-time performance metrics for a specific port from MCP.
    
    Args:
        device_id: MCP network construct ID
        port_number: Port number (e.g., '21', '22')
    
    Returns traffic stats including rx/tx bytes, packets, errors.
    """
    service = get_mcp_service()
    
    if not service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    try:
        stats = service.get_realtime_pm(device_id, port_number)
        
        if not stats:
            return jsonify(error_response('NOT_FOUND', f'No PM data for port {port_number}')), 404
        
        return jsonify(success_response(stats))
    except Exception as e:
        return jsonify(error_response('MCP_ERROR', str(e))), 500


@mcp_bp.route('/pm/<device_id>/ports', methods=['GET'])
def get_all_ports_pm(device_id):
    """
    Get real-time PM stats for all ports on a device.
    
    Args:
        device_id: MCP network construct ID
    
    Query params:
        ports: Comma-separated list of port numbers (default: 1-24)
    """
    ports_param = request.args.get('ports')
    port_numbers = ports_param.split(',') if ports_param else None
    
    service = get_mcp_service()
    
    if not service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    try:
        stats = service.get_all_port_stats(device_id, port_numbers)
        
        return jsonify(success_response({
            'device_id': device_id,
            'ports': stats,
            'count': len(stats),
        }))
    except Exception as e:
        return jsonify(error_response('MCP_ERROR', str(e))), 500


@mcp_bp.route('/pm/by-ip/<device_ip>/port/<port_number>', methods=['GET'])
def get_port_pm_by_ip(device_ip, port_number):
    """
    Get real-time PM for a port by device IP address.
    
    This is a convenience endpoint that looks up the MCP device ID by IP.
    """
    service = get_mcp_service()
    
    if not service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    try:
        # Find device by IP
        all_devices = service.get_all_devices()
        device_id = None
        
        for device in all_devices:
            attrs = device.get('attributes', {})
            if attrs.get('ipAddress') == device_ip:
                device_id = device.get('id')
                break
        
        if not device_id:
            return jsonify(error_response('NOT_FOUND', f'Device with IP {device_ip} not found in MCP')), 404
        
        stats = service.get_realtime_pm(device_id, port_number)
        
        if not stats:
            return jsonify(error_response('NOT_FOUND', f'No PM data for port {port_number}')), 404
        
        return jsonify(success_response(stats))
    except Exception as e:
        return jsonify(error_response('MCP_ERROR', str(e))), 500


@mcp_bp.route('/ports/<device_id>/status', methods=['GET'])
def get_ethernet_port_status(device_id):
    """
    Get real-time Ethernet port operational status for a device.
    
    Returns operLink (Up/Down), operMode, operSTP, adminLink, etc. for all ports.
    """
    service = get_mcp_service()
    
    if not service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    try:
        ports = service.get_ethernet_port_status(device_id)
        
        return jsonify(success_response({
            'device_id': device_id,
            'ports': ports,
            'count': len(ports),
        }))
    except Exception as e:
        return jsonify(error_response('MCP_ERROR', str(e))), 500


@mcp_bp.route('/ports/by-ip/<device_ip>/status', methods=['GET'])
def get_ethernet_port_status_by_ip(device_ip):
    """
    Get real-time Ethernet port status by device IP address.
    """
    service = get_mcp_service()
    
    if not service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    try:
        # Find device by IP
        all_devices = service.get_all_devices()
        device_id = None
        
        for device in all_devices:
            attrs = device.get('attributes', {})
            if attrs.get('ipAddress') == device_ip:
                device_id = device.get('id')
                break
        
        if not device_id:
            return jsonify(error_response('NOT_FOUND', f'Device with IP {device_ip} not found in MCP')), 404
        
        ports = service.get_ethernet_port_status(device_id)
        
        return jsonify(success_response({
            'device_ip': device_ip,
            'device_id': device_id,
            'ports': ports,
            'count': len(ports),
        }))
    except Exception as e:
        return jsonify(error_response('MCP_ERROR', str(e))), 500


# ==================== NETBOX SYNC ====================

@mcp_bp.route('/sync/interfaces', methods=['POST'])
def sync_ciena_interfaces():
    """
    Sync Ciena switch interfaces to NetBox with correct types, speeds, and SFP modules.
    
    This updates:
    - Interface types based on MCP port_type (10/100/G -> 1000base-t, 10Gig -> 10gbase-x-sfpp)
    - Interface speeds based on operational mode
    - SFP modules in module bays
    
    Query params:
        device_ip: Optional - sync only this device
    """
    from ..services.ciena_mcp_service import sync_ciena_interfaces_to_netbox
    
    device_ip = request.args.get('device_ip')
    
    mcp_service = get_mcp_service()
    if not mcp_service.is_configured:
        return jsonify(error_response('NOT_CONFIGURED', 'MCP is not configured')), 400
    
    from .netbox import get_netbox_service
    netbox_service = get_netbox_service()
    
    if not netbox_service.is_configured:
        return jsonify(error_response('NETBOX_ERROR', 'NetBox is not configured')), 400
    
    try:
        stats = sync_ciena_interfaces_to_netbox(mcp_service, netbox_service, device_ip=device_ip)
        return jsonify(success_response(stats))
    except Exception as e:
        return jsonify(error_response('SYNC_ERROR', str(e))), 500
