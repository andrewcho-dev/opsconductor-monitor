"""
MIB Mappings API Router - FastAPI.

Routes for SNMP MIB/OID mapping management.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class OIDMappingCreate(BaseModel):
    profile_id: int
    group_id: int
    oid: str
    name: str
    description: Optional[str] = None
    data_type: str = "string"
    transform: Optional[str] = None


class OIDMappingUpdate(BaseModel):
    oid: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    transform: Optional[str] = None


@router.get("/profiles")
async def list_profiles():
    """List all SNMP profiles."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, vendor, device_types, created_at
            FROM snmp_profiles
            ORDER BY name
        """)
        profiles = [dict(row) for row in cursor.fetchall()]
    return list_response(profiles)


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: int):
    """Get an SNMP profile with its OID groups."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM snmp_profiles WHERE id = %s", (profile_id,))
        profile = cursor.fetchone()
        if not profile:
            return error_response('NOT_FOUND', 'Profile not found')
        
        profile = dict(profile)
        
        cursor.execute("""
            SELECT id, name, description, poll_type
            FROM snmp_oid_groups WHERE profile_id = %s
            ORDER BY name
        """, (profile_id,))
        profile['groups'] = [dict(row) for row in cursor.fetchall()]
    
    return success_response(profile)


@router.get("/groups")
async def list_groups(profile_id: Optional[int] = None):
    """List OID groups."""
    db = get_db()
    
    query = """
        SELECT g.id, g.name, g.description, g.poll_type, g.profile_id,
               p.name as profile_name,
               COUNT(m.id) as mapping_count
        FROM snmp_oid_groups g
        LEFT JOIN snmp_profiles p ON g.profile_id = p.id
        LEFT JOIN snmp_oid_mappings m ON g.id = m.group_id
    """
    params = []
    
    if profile_id:
        query += " WHERE g.profile_id = %s"
        params.append(profile_id)
    
    query += " GROUP BY g.id, p.name ORDER BY g.name"
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        groups = [dict(row) for row in cursor.fetchall()]
    
    return list_response(groups)


@router.get("/groups/{group_id}")
async def get_group(group_id: int):
    """Get an OID group with its mappings."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT g.*, p.name as profile_name
            FROM snmp_oid_groups g
            LEFT JOIN snmp_profiles p ON g.profile_id = p.id
            WHERE g.id = %s
        """, (group_id,))
        group = cursor.fetchone()
        if not group:
            return error_response('NOT_FOUND', 'Group not found')
        
        group = dict(group)
        
        cursor.execute("""
            SELECT id, oid, name, description, data_type, transform
            FROM snmp_oid_mappings WHERE group_id = %s
            ORDER BY name
        """, (group_id,))
        group['mappings'] = [dict(row) for row in cursor.fetchall()]
    
    return success_response(group)


@router.get("/mappings")
async def list_mappings(group_id: Optional[int] = None, profile_id: Optional[int] = None):
    """List OID mappings."""
    db = get_db()
    
    query = """
        SELECT m.id, m.oid, m.name, m.description, m.data_type, m.transform,
               m.group_id, g.name as group_name, g.profile_id
        FROM snmp_oid_mappings m
        LEFT JOIN snmp_oid_groups g ON m.group_id = g.id
        WHERE 1=1
    """
    params = []
    
    if group_id:
        query += " AND m.group_id = %s"
        params.append(group_id)
    if profile_id:
        query += " AND g.profile_id = %s"
        params.append(profile_id)
    
    query += " ORDER BY m.name"
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        mappings = [dict(row) for row in cursor.fetchall()]
    
    return list_response(mappings)


@router.post("/mappings")
async def create_mapping(req: OIDMappingCreate):
    """Create a new OID mapping."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO snmp_oid_mappings (group_id, oid, name, description, data_type, transform)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, oid, name, description, data_type, transform, group_id
        """, (req.group_id, req.oid, req.name, req.description, req.data_type, req.transform))
        mapping = dict(cursor.fetchone())
        db.commit()
    return success_response(mapping)


@router.put("/mappings/{mapping_id}")
async def update_mapping(mapping_id: int, req: OIDMappingUpdate):
    """Update an OID mapping."""
    updates = []
    params = []
    
    if req.oid is not None:
        updates.append("oid = %s")
        params.append(req.oid)
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.description is not None:
        updates.append("description = %s")
        params.append(req.description)
    if req.data_type is not None:
        updates.append("data_type = %s")
        params.append(req.data_type)
    if req.transform is not None:
        updates.append("transform = %s")
        params.append(req.transform)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    params.append(mapping_id)
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE snmp_oid_mappings
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, oid, name, description, data_type, transform
        """, params)
        mapping = cursor.fetchone()
        if not mapping:
            return error_response('NOT_FOUND', 'Mapping not found')
        db.commit()
    
    return success_response(dict(mapping))


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int):
    """Delete an OID mapping."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM snmp_oid_mappings WHERE id = %s RETURNING id", (mapping_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Mapping not found')
        db.commit()
    return success_response({"deleted": True, "id": mapping_id})


@router.get("/enums")
async def list_enum_mappings(profile_id: Optional[int] = None):
    """List enum value mappings."""
    db = get_db()
    
    query = """
        SELECT e.id, e.oid_pattern, e.value, e.label, e.profile_id, p.name as profile_name
        FROM snmp_enum_mappings e
        LEFT JOIN snmp_profiles p ON e.profile_id = p.id
    """
    params = []
    
    if profile_id:
        query += " WHERE e.profile_id = %s"
        params.append(profile_id)
    
    query += " ORDER BY e.oid_pattern, e.value"
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        enums = [dict(row) for row in cursor.fetchall()]
    
    return list_response(enums)


@router.get("/poll-types")
async def list_poll_types():
    """List available poll types."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, default_interval_seconds
            FROM snmp_poll_types
            ORDER BY name
        """)
        poll_types = [dict(row) for row in cursor.fetchall()]
    return list_response(poll_types)
