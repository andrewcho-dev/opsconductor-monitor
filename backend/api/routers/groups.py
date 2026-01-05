"""
Groups API Router - FastAPI.

Routes for device group management.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "custom"  # custom, network, role, etc.
    filter_criteria: Optional[dict] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filter_criteria: Optional[dict] = None


class GroupMembersUpdate(BaseModel):
    device_ips: List[str]


@router.get("")
async def list_groups():
    """List all device groups."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.type, g.filter_criteria, g.created_at,
                   COUNT(gm.device_ip) as member_count
            FROM device_groups g
            LEFT JOIN group_members gm ON g.id = gm.group_id
            GROUP BY g.id
            ORDER BY g.name
        """)
        groups = [dict(row) for row in cursor.fetchall()]
    return list_response(groups)


@router.post("")
async def create_group(req: GroupCreate):
    """Create a new device group."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO device_groups (name, description, type, filter_criteria)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, description, type, filter_criteria, created_at
        """, (req.name, req.description, req.type, req.filter_criteria))
        group = dict(cursor.fetchone())
        db.commit()
    return success_response(group)


@router.get("/{group_id}")
async def get_group(group_id: int):
    """Get a group by ID with its members."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, type, filter_criteria, created_at
            FROM device_groups WHERE id = %s
        """, (group_id,))
        group = cursor.fetchone()
        if not group:
            return error_response('NOT_FOUND', 'Group not found')
        
        group = dict(group)
        
        # Get members
        cursor.execute("""
            SELECT device_ip FROM group_members WHERE group_id = %s
        """, (group_id,))
        group['members'] = [row['device_ip'] for row in cursor.fetchall()]
    
    return success_response(group)


@router.put("/{group_id}")
async def update_group(group_id: int, req: GroupUpdate):
    """Update a group."""
    db = get_db()
    
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.description is not None:
        updates.append("description = %s")
        params.append(req.description)
    if req.filter_criteria is not None:
        updates.append("filter_criteria = %s")
        params.append(req.filter_criteria)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    params.append(group_id)
    
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE device_groups
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, description, type, filter_criteria, created_at
        """, params)
        group = cursor.fetchone()
        if not group:
            return error_response('NOT_FOUND', 'Group not found')
        db.commit()
    
    return success_response(dict(group))


@router.delete("/{group_id}")
async def delete_group(group_id: int):
    """Delete a group."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM device_groups WHERE id = %s RETURNING id", (group_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Group not found')
        db.commit()
    return success_response({"deleted": True, "id": group_id})


@router.put("/{group_id}/members")
async def update_group_members(group_id: int, req: GroupMembersUpdate):
    """Update group members (replace all)."""
    db = get_db()
    with db.cursor() as cursor:
        # Verify group exists
        cursor.execute("SELECT id FROM device_groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            return error_response('NOT_FOUND', 'Group not found')
        
        # Clear existing members
        cursor.execute("DELETE FROM group_members WHERE group_id = %s", (group_id,))
        
        # Add new members
        for ip in req.device_ips:
            cursor.execute(
                "INSERT INTO group_members (group_id, device_ip) VALUES (%s, %s)",
                (group_id, ip)
            )
        
        db.commit()
    
    return success_response({"group_id": group_id, "member_count": len(req.device_ips)})


@router.post("/{group_id}/members/{device_ip}")
async def add_group_member(group_id: int, device_ip: str):
    """Add a device to a group."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO group_members (group_id, device_ip)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING group_id
        """, (group_id, device_ip))
        db.commit()
    return success_response({"added": True, "group_id": group_id, "device_ip": device_ip})


@router.delete("/{group_id}/members/{device_ip}")
async def remove_group_member(group_id: int, device_ip: str):
    """Remove a device from a group."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "DELETE FROM group_members WHERE group_id = %s AND device_ip = %s RETURNING group_id",
            (group_id, device_ip)
        )
        deleted = cursor.fetchone()
        db.commit()
    
    if not deleted:
        return error_response('NOT_FOUND', 'Member not found in group')
    
    return success_response({"removed": True, "group_id": group_id, "device_ip": device_ip})
