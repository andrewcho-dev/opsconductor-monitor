"""
MIB OID Mapping API

Provides CRUD operations for SNMP MIB mappings:
- Profiles (vendor/device types)
- OID Groups (logical groupings of OIDs)
- OID Mappings (individual OID definitions)
- Enum Mappings (integer to string translations)
- Poll Types (which groups to poll together)
"""

import logging
from flask import Blueprint, request
from backend.database import DatabaseConnection
from backend.utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

mib_bp = Blueprint('mib', __name__, url_prefix='/api/mib')


# ============================================================================
# PROFILES
# ============================================================================

@mib_bp.route('/profiles', methods=['GET'])
def list_profiles():
    """List all SNMP profiles."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT p.*, 
                       COUNT(DISTINCT g.id) as group_count,
                       COUNT(DISTINCT pt.id) as poll_type_count
                FROM snmp_profiles p
                LEFT JOIN snmp_oid_groups g ON g.profile_id = p.id
                LEFT JOIN snmp_poll_types pt ON pt.profile_id = p.id
                GROUP BY p.id
                ORDER BY p.vendor, p.name
            """)
            profiles = cursor.fetchall()
        return success_response({'profiles': [dict(p) for p in profiles]})
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/profiles/<int:profile_id>', methods=['GET'])
def get_profile(profile_id):
    """Get a profile with all its groups, mappings, and poll types."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            # Get profile
            cursor.execute("SELECT * FROM snmp_profiles WHERE id = %s", (profile_id,))
            profile = cursor.fetchone()
            if not profile:
                return error_response("Profile not found", status=404)
            
            profile = dict(profile)
            
            # Get groups with their mappings
            cursor.execute("""
                SELECT * FROM snmp_oid_groups 
                WHERE profile_id = %s 
                ORDER BY name
            """, (profile_id,))
            groups = cursor.fetchall()
            
            profile['groups'] = []
            for group in groups:
                group_dict = dict(group)
                
                # Get mappings for this group
                cursor.execute("""
                    SELECT * FROM snmp_oid_mappings 
                    WHERE group_id = %s 
                    ORDER BY is_index DESC, name
                """, (group['id'],))
                mappings = cursor.fetchall()
                
                group_dict['mappings'] = []
                for mapping in mappings:
                    mapping_dict = dict(mapping)
                    
                    # Get enum values for this mapping
                    cursor.execute("""
                        SELECT * FROM snmp_enum_mappings 
                        WHERE mapping_id = %s 
                        ORDER BY int_value
                    """, (mapping['id'],))
                    enums = cursor.fetchall()
                    mapping_dict['enums'] = [dict(e) for e in enums]
                    
                    group_dict['mappings'].append(mapping_dict)
                
                profile['groups'].append(group_dict)
            
            # Get poll types
            cursor.execute("""
                SELECT pt.*, array_agg(ptg.group_id ORDER BY ptg.poll_order) as group_ids
                FROM snmp_poll_types pt
                LEFT JOIN snmp_poll_type_groups ptg ON ptg.poll_type_id = pt.id
                WHERE pt.profile_id = %s
                GROUP BY pt.id
                ORDER BY pt.name
            """, (profile_id,))
            poll_types = cursor.fetchall()
            profile['poll_types'] = [dict(pt) for pt in poll_types]
            
        return success_response({'profile': profile})
    except Exception as e:
        logger.error(f"Failed to get profile {profile_id}: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/profiles', methods=['POST'])
def create_profile():
    """Create a new SNMP profile."""
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('vendor'):
            return error_response("Name and vendor are required", status=400)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO snmp_profiles (name, vendor, description, enterprise_oid)
                VALUES (%s, %s, %s, %s)
                RETURNING *
            """, (data['name'], data['vendor'], data.get('description'), data.get('enterprise_oid')))
            profile = cursor.fetchone()
            db.get_connection().commit()
        
        return success_response({'profile': dict(profile)}, message="Profile created")
    except Exception as e:
        logger.error(f"Failed to create profile: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/profiles/<int:profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """Update a profile."""
    try:
        data = request.get_json()
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE snmp_profiles 
                SET name = COALESCE(%s, name),
                    vendor = COALESCE(%s, vendor),
                    description = COALESCE(%s, description),
                    enterprise_oid = COALESCE(%s, enterprise_oid),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """, (data.get('name'), data.get('vendor'), data.get('description'), 
                  data.get('enterprise_oid'), profile_id))
            profile = cursor.fetchone()
            if not profile:
                return error_response("Profile not found", status=404)
            db.get_connection().commit()
        
        return success_response({'profile': dict(profile)}, message="Profile updated")
    except Exception as e:
        logger.error(f"Failed to update profile {profile_id}: {e}")
        return error_response(str(e), status=500)


# ============================================================================
# OID GROUPS
# ============================================================================

@mib_bp.route('/profiles/<int:profile_id>/groups', methods=['POST'])
def create_group(profile_id):
    """Create a new OID group."""
    try:
        data = request.get_json()
        if not data.get('name'):
            return error_response("Name is required", status=400)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (profile_id, data['name'], data.get('description'), data.get('base_oid'),
                  data.get('mib_name'), data.get('is_table', False)))
            group = cursor.fetchone()
            db.get_connection().commit()
        
        return success_response({'group': dict(group)}, message="Group created")
    except Exception as e:
        logger.error(f"Failed to create group: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """Update an OID group."""
    try:
        data = request.get_json()
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE snmp_oid_groups 
                SET name = COALESCE(%s, name),
                    description = COALESCE(%s, description),
                    base_oid = COALESCE(%s, base_oid),
                    mib_name = COALESCE(%s, mib_name),
                    is_table = COALESCE(%s, is_table)
                WHERE id = %s
                RETURNING *
            """, (data.get('name'), data.get('description'), data.get('base_oid'),
                  data.get('mib_name'), data.get('is_table'), group_id))
            group = cursor.fetchone()
            if not group:
                return error_response("Group not found", status=404)
            db.get_connection().commit()
        
        return success_response({'group': dict(group)}, message="Group updated")
    except Exception as e:
        logger.error(f"Failed to update group {group_id}: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Delete an OID group and all its mappings."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM snmp_oid_groups WHERE id = %s RETURNING name", (group_id,))
            result = cursor.fetchone()
            if not result:
                return error_response("Group not found", status=404)
            db.get_connection().commit()
        
        return success_response({'id': group_id}, message=f"Group '{result['name']}' deleted")
    except Exception as e:
        logger.error(f"Failed to delete group {group_id}: {e}")
        return error_response(str(e), status=500)


# ============================================================================
# OID MAPPINGS
# ============================================================================

@mib_bp.route('/groups/<int:group_id>/mappings', methods=['POST'])
def create_mapping(group_id):
    """Create a new OID mapping."""
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('oid'):
            return error_response("Name and OID are required", status=400)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO snmp_oid_mappings 
                (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (group_id, data['name'], data['oid'], data.get('description'),
                  data.get('mib_object_name'), data.get('data_type', 'string'),
                  data.get('transform'), data.get('unit'), data.get('is_index', False)))
            mapping = cursor.fetchone()
            db.get_connection().commit()
        
        return success_response({'mapping': dict(mapping)}, message="Mapping created")
    except Exception as e:
        logger.error(f"Failed to create mapping: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/mappings/<int:mapping_id>', methods=['PUT'])
def update_mapping(mapping_id):
    """Update an OID mapping."""
    try:
        data = request.get_json()
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE snmp_oid_mappings 
                SET name = COALESCE(%s, name),
                    oid = COALESCE(%s, oid),
                    description = COALESCE(%s, description),
                    mib_object_name = COALESCE(%s, mib_object_name),
                    data_type = COALESCE(%s, data_type),
                    transform = COALESCE(%s, transform),
                    unit = COALESCE(%s, unit),
                    is_index = COALESCE(%s, is_index)
                WHERE id = %s
                RETURNING *
            """, (data.get('name'), data.get('oid'), data.get('description'),
                  data.get('mib_object_name'), data.get('data_type'),
                  data.get('transform'), data.get('unit'), data.get('is_index'), mapping_id))
            mapping = cursor.fetchone()
            if not mapping:
                return error_response("Mapping not found", status=404)
            db.get_connection().commit()
        
        return success_response({'mapping': dict(mapping)}, message="Mapping updated")
    except Exception as e:
        logger.error(f"Failed to update mapping {mapping_id}: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/mappings/<int:mapping_id>', methods=['DELETE'])
def delete_mapping(mapping_id):
    """Delete an OID mapping."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM snmp_oid_mappings WHERE id = %s RETURNING name", (mapping_id,))
            result = cursor.fetchone()
            if not result:
                return error_response("Mapping not found", status=404)
            db.get_connection().commit()
        
        return success_response({'id': mapping_id}, message=f"Mapping '{result['name']}' deleted")
    except Exception as e:
        logger.error(f"Failed to delete mapping {mapping_id}: {e}")
        return error_response(str(e), status=500)


# ============================================================================
# ENUM MAPPINGS
# ============================================================================

@mib_bp.route('/mappings/<int:mapping_id>/enums', methods=['POST'])
def create_enum(mapping_id):
    """Create a new enum value mapping."""
    try:
        data = request.get_json()
        if data.get('int_value') is None or not data.get('string_value'):
            return error_response("int_value and string_value are required", status=400)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO snmp_enum_mappings (mapping_id, int_value, string_value, severity)
                VALUES (%s, %s, %s, %s)
                RETURNING *
            """, (mapping_id, data['int_value'], data['string_value'], data.get('severity')))
            enum = cursor.fetchone()
            db.get_connection().commit()
        
        return success_response({'enum': dict(enum)}, message="Enum created")
    except Exception as e:
        logger.error(f"Failed to create enum: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/enums/<int:enum_id>', methods=['DELETE'])
def delete_enum(enum_id):
    """Delete an enum value mapping."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM snmp_enum_mappings WHERE id = %s RETURNING id", (enum_id,))
            result = cursor.fetchone()
            if not result:
                return error_response("Enum not found", status=404)
            db.get_connection().commit()
        
        return success_response({'id': enum_id}, message="Enum deleted")
    except Exception as e:
        logger.error(f"Failed to delete enum {enum_id}: {e}")
        return error_response(str(e), status=500)


# ============================================================================
# POLL TYPES
# ============================================================================

@mib_bp.route('/poll-types', methods=['GET'])
def list_poll_types():
    """List all poll types."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT pt.*, p.name as profile_name, p.vendor
                FROM snmp_poll_types pt
                JOIN snmp_profiles p ON p.id = pt.profile_id
                ORDER BY p.vendor, pt.name
            """)
            poll_types = cursor.fetchall()
        return success_response({'poll_types': [dict(pt) for pt in poll_types]})
    except Exception as e:
        logger.error(f"Failed to list poll types: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/profiles/<int:profile_id>/poll-types', methods=['POST'])
def create_poll_type(profile_id):
    """Create a new poll type."""
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('display_name'):
            return error_response("name and display_name are required", status=400)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO snmp_poll_types (name, display_name, description, profile_id, target_table, enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (data['name'], data['display_name'], data.get('description'),
                  profile_id, data.get('target_table'), data.get('enabled', True)))
            poll_type = cursor.fetchone()
            
            # Add groups if specified
            if data.get('group_ids'):
                for i, group_id in enumerate(data['group_ids']):
                    cursor.execute("""
                        INSERT INTO snmp_poll_type_groups (poll_type_id, group_id, poll_order)
                        VALUES (%s, %s, %s)
                    """, (poll_type['id'], group_id, i))
            
            db.get_connection().commit()
        
        return success_response({'poll_type': dict(poll_type)}, message="Poll type created")
    except Exception as e:
        logger.error(f"Failed to create poll type: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/poll-types/<int:poll_type_id>', methods=['PUT'])
def update_poll_type(poll_type_id):
    """Update a poll type."""
    try:
        data = request.get_json()
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE snmp_poll_types 
                SET name = COALESCE(%s, name),
                    display_name = COALESCE(%s, display_name),
                    description = COALESCE(%s, description),
                    target_table = COALESCE(%s, target_table),
                    enabled = COALESCE(%s, enabled)
                WHERE id = %s
                RETURNING *
            """, (data.get('name'), data.get('display_name'), data.get('description'),
                  data.get('target_table'), data.get('enabled'), poll_type_id))
            poll_type = cursor.fetchone()
            if not poll_type:
                return error_response("Poll type not found", status=404)
            
            # Update groups if specified
            if 'group_ids' in data:
                cursor.execute("DELETE FROM snmp_poll_type_groups WHERE poll_type_id = %s", (poll_type_id,))
                for i, group_id in enumerate(data['group_ids']):
                    cursor.execute("""
                        INSERT INTO snmp_poll_type_groups (poll_type_id, group_id, poll_order)
                        VALUES (%s, %s, %s)
                    """, (poll_type_id, group_id, i))
            
            db.get_connection().commit()
        
        return success_response({'poll_type': dict(poll_type)}, message="Poll type updated")
    except Exception as e:
        logger.error(f"Failed to update poll type {poll_type_id}: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/poll-types/<int:poll_type_id>', methods=['DELETE'])
def delete_poll_type(poll_type_id):
    """Delete a poll type."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM snmp_poll_types WHERE id = %s RETURNING name", (poll_type_id,))
            result = cursor.fetchone()
            if not result:
                return error_response("Poll type not found", status=404)
            db.get_connection().commit()
        
        return success_response({'id': poll_type_id}, message=f"Poll type '{result['name']}' deleted")
    except Exception as e:
        logger.error(f"Failed to delete poll type {poll_type_id}: {e}")
        return error_response(str(e), status=500)


# ============================================================================
# TEST SNMP POLL
# ============================================================================

@mib_bp.route('/test-poll', methods=['POST'])
def test_poll():
    """Test polling a single OID or group against a device."""
    try:
        data = request.get_json()
        host = data.get('host')
        community = data.get('community', 'public')
        oid = data.get('oid')
        group_id = data.get('group_id')
        
        if not host:
            return error_response("host is required", status=400)
        if not oid and not group_id:
            return error_response("oid or group_id is required", status=400)
        
        from pysnmp.hlapi import (
            getCmd, nextCmd, SnmpEngine, CommunityData, 
            UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
        )
        
        results = []
        
        if oid:
            # Single OID get
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((host, 161), timeout=5, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                return error_response(str(errorIndication), status=500)
            if errorStatus:
                return error_response(f"{errorStatus.prettyPrint()} at {errorIndex}", status=500)
            
            for varBind in varBinds:
                results.append({
                    'oid': str(varBind[0]),
                    'value': str(varBind[1]),
                    'type': varBind[1].__class__.__name__
                })
        
        elif group_id:
            # Walk a group's base OID
            db = DatabaseConnection()
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM snmp_oid_groups WHERE id = %s", (group_id,))
                group = cursor.fetchone()
                if not group:
                    return error_response("Group not found", status=404)
                
                cursor.execute("SELECT * FROM snmp_oid_mappings WHERE group_id = %s", (group_id,))
                mappings = cursor.fetchall()
            
            if group['is_table'] and group['base_oid']:
                # SNMP walk for tables
                for errorIndication, errorStatus, errorIndex, varBinds in nextCmd(
                    SnmpEngine(),
                    CommunityData(community),
                    UdpTransportTarget((host, 161), timeout=5, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(group['base_oid'])),
                    lexicographicMode=False
                ):
                    if errorIndication or errorStatus:
                        break
                    for varBind in varBinds:
                        oid_str = str(varBind[0])
                        # Find matching mapping
                        mapping_name = None
                        for m in mappings:
                            if oid_str.startswith(m['oid']):
                                mapping_name = m['name']
                                break
                        results.append({
                            'oid': oid_str,
                            'value': str(varBind[1]),
                            'type': varBind[1].__class__.__name__,
                            'mapping': mapping_name
                        })
                    if len(results) > 100:
                        break
            else:
                # Get individual OIDs
                for mapping in mappings:
                    iterator = getCmd(
                        SnmpEngine(),
                        CommunityData(community),
                        UdpTransportTarget((host, 161), timeout=5, retries=1),
                        ContextData(),
                        ObjectType(ObjectIdentity(mapping['oid']))
                    )
                    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                    if not errorIndication and not errorStatus:
                        for varBind in varBinds:
                            results.append({
                                'oid': str(varBind[0]),
                                'value': str(varBind[1]),
                                'type': varBind[1].__class__.__name__,
                                'mapping': mapping['name']
                            })
        
        return success_response({
            'host': host,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"Test poll failed: {e}")
        return error_response(str(e), status=500)


# ============================================================================
# MIB FILE PARSING
# ============================================================================

@mib_bp.route('/parse-mib', methods=['POST'])
def parse_mib():
    """
    Parse a MIB file and return discovered OIDs organized into groups.
    
    Accepts either:
    - File upload (multipart/form-data with 'file' field)
    - Raw MIB content (JSON with 'content' field)
    """
    try:
        from backend.services.mib_parser import parse_mib_content
        
        mib_content = None
        mib_name = None
        
        # Check for file upload
        if 'file' in request.files:
            file = request.files['file']
            mib_content = file.read().decode('utf-8', errors='ignore')
            mib_name = file.filename.replace('.txt', '').replace('.mib', '').replace('.my', '')
        # Check for JSON content
        elif request.is_json:
            data = request.get_json()
            mib_content = data.get('content')
            mib_name = data.get('mib_name')
        
        if not mib_content:
            return error_response("No MIB content provided. Upload a file or send content in JSON.", status=400)
        
        # Parse the MIB
        result = parse_mib_content(mib_content, mib_name)
        
        return success_response({
            'mib_name': result['mib_name'],
            'description': result['description'],
            'enterprise_oid': result['enterprise_oid'],
            'groups': result['groups'],
            'total_objects': len(result.get('objects', [])),
            'errors': result.get('errors', [])
        })
    except Exception as e:
        logger.error(f"MIB parsing failed: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/discover-oids', methods=['POST'])
def discover_oids():
    """
    Walk a device's SNMP tree to discover available OIDs.
    This helps identify what OIDs a device supports.
    """
    try:
        from backend.services.mib_parser import discover_oids_from_device
        
        data = request.get_json()
        host = data.get('host')
        community = data.get('community', 'public')
        base_oid = data.get('base_oid', '1.3.6.1.4.1')  # Default to enterprises
        
        if not host:
            return error_response("host is required", status=400)
        
        discovered = discover_oids_from_device(host, community, base_oid)
        
        return success_response({
            'host': host,
            'base_oid': base_oid,
            'discovered': discovered,
            'count': len(discovered)
        })
    except Exception as e:
        logger.error(f"OID discovery failed: {e}")
        return error_response(str(e), status=500)


@mib_bp.route('/import-mib', methods=['POST'])
def import_mib():
    """
    Import a parsed MIB into a profile, creating groups and OID mappings.
    
    Expects JSON with:
    - profile_id: ID of existing profile, or null to create new
    - profile_name: Name for new profile (if profile_id is null)
    - vendor: Vendor name for new profile
    - mib_name: Name of the MIB
    - groups: Array of groups with their OID mappings
    """
    try:
        data = request.get_json()
        profile_id = data.get('profile_id')
        groups_to_import = data.get('groups', [])
        mib_name = data.get('mib_name', 'Unknown MIB')
        
        if not groups_to_import:
            return error_response("No groups to import", status=400)
        
        db = DatabaseConnection()
        
        # Create or get profile
        if not profile_id:
            profile_name = data.get('profile_name')
            vendor = data.get('vendor')
            enterprise_oid = data.get('enterprise_oid')
            
            if not profile_name or not vendor:
                return error_response("profile_name and vendor required for new profile", status=400)
            
            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO snmp_profiles (name, vendor, description, enterprise_oid)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET updated_at = NOW()
                    RETURNING id
                """, (profile_name, vendor, f"Imported from {mib_name}", enterprise_oid))
                profile_id = cursor.fetchone()['id']
                db.get_connection().commit()
        
        # Import groups and mappings
        imported_groups = 0
        imported_mappings = 0
        
        with db.cursor() as cursor:
            for group in groups_to_import:
                # Create group
                cursor.execute("""
                    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (profile_id, name) DO UPDATE 
                    SET description = EXCLUDED.description, base_oid = EXCLUDED.base_oid
                    RETURNING id
                """, (
                    profile_id,
                    group['name'],
                    group.get('description', ''),
                    group.get('base_oid'),
                    mib_name,
                    group.get('is_table', False)
                ))
                group_id = cursor.fetchone()['id']
                imported_groups += 1
                
                # Create OID mappings
                for obj in group.get('objects', []):
                    if not obj.get('oid'):
                        continue
                    
                    cursor.execute("""
                        INSERT INTO snmp_oid_mappings 
                        (group_id, name, oid, description, mib_object_name, data_type, unit, is_index)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (group_id, name) DO UPDATE 
                        SET oid = EXCLUDED.oid, description = EXCLUDED.description
                    """, (
                        group_id,
                        obj['name'],
                        obj['oid'],
                        obj.get('description', ''),
                        obj.get('mib_object_name', obj['name']),
                        obj.get('data_type', 'string'),
                        obj.get('units'),
                        obj.get('is_index', False)
                    ))
                    imported_mappings += 1
            
            db.get_connection().commit()
        
        return success_response({
            'profile_id': profile_id,
            'imported_groups': imported_groups,
            'imported_mappings': imported_mappings
        }, message=f"Imported {imported_groups} groups with {imported_mappings} OID mappings")
    except Exception as e:
        logger.error(f"MIB import failed: {e}")
        return error_response(str(e), status=500)
