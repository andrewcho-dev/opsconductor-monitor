"""
Credentials API Router - FastAPI.

Routes for credential management (SSH, SNMP, API keys, etc.).
"""

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response
from backend.api.routers.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class CredentialCreate(BaseModel):
    name: str
    type: str  # ssh, snmp, api_key, etc.
    username: Optional[str] = None
    password: Optional[str] = None
    community: Optional[str] = None
    api_key: Optional[str] = None
    private_key: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    community: Optional[str] = None
    api_key: Optional[str] = None
    private_key: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("")
async def list_credentials(
    type: Optional[str] = None,
    request: Request = None,
    user: dict = Depends(require_permission('credentials.view'))
):
    """List all credentials (without sensitive data)."""
    db = get_db()
    
    query = """
        SELECT id, name, type, username, description, tags, created_at, updated_at
        FROM credentials
        WHERE 1=1
    """
    params = []
    
    if type:
        query += " AND type = %s"
        params.append(type)
    
    query += " ORDER BY name"
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        credentials = [dict(row) for row in cursor.fetchall()]
    
    return list_response(credentials)


@router.post("")
async def create_credential(
    req: CredentialCreate,
    request: Request = None,
    user: dict = Depends(require_permission('credentials.create'))
):
    """Create a new credential."""
    db = get_db()
    
    # Encrypt sensitive fields before storing
    from backend.services.encryption_service import encrypt_value
    
    encrypted_password = encrypt_value(req.password) if req.password else None
    encrypted_community = encrypt_value(req.community) if req.community else None
    encrypted_api_key = encrypt_value(req.api_key) if req.api_key else None
    encrypted_private_key = encrypt_value(req.private_key) if req.private_key else None
    
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO credentials (name, type, username, password, community, api_key, private_key, description, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, type, username, description, tags, created_at
        """, (
            req.name, req.type, req.username,
            encrypted_password, encrypted_community, encrypted_api_key, encrypted_private_key,
            req.description, req.tags
        ))
        credential = dict(cursor.fetchone())
        db.commit()
    
    return success_response(credential)


@router.get("/{credential_id}")
async def get_credential(
    credential_id: int,
    request: Request = None,
    user: dict = Depends(require_permission('credentials.view'))
):
    """Get a credential by ID (without sensitive data)."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, type, username, description, tags, created_at, updated_at
            FROM credentials WHERE id = %s
        """, (credential_id,))
        credential = cursor.fetchone()
        if not credential:
            return error_response('NOT_FOUND', 'Credential not found')
    return success_response(dict(credential))


@router.put("/{credential_id}")
async def update_credential(
    credential_id: int,
    req: CredentialUpdate,
    request: Request = None,
    user: dict = Depends(require_permission('credentials.edit'))
):
    """Update a credential."""
    db = get_db()
    
    from backend.services.encryption_service import encrypt_value
    
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.username is not None:
        updates.append("username = %s")
        params.append(req.username)
    if req.password is not None:
        updates.append("password = %s")
        params.append(encrypt_value(req.password))
    if req.community is not None:
        updates.append("community = %s")
        params.append(encrypt_value(req.community))
    if req.api_key is not None:
        updates.append("api_key = %s")
        params.append(encrypt_value(req.api_key))
    if req.private_key is not None:
        updates.append("private_key = %s")
        params.append(encrypt_value(req.private_key))
    if req.description is not None:
        updates.append("description = %s")
        params.append(req.description)
    if req.tags is not None:
        updates.append("tags = %s")
        params.append(req.tags)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    updates.append("updated_at = NOW()")
    params.append(credential_id)
    
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE credentials
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, type, username, description, tags, created_at, updated_at
        """, params)
        credential = cursor.fetchone()
        if not credential:
            return error_response('NOT_FOUND', 'Credential not found')
        db.commit()
    
    return success_response(dict(credential))


@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: int,
    request: Request = None,
    user: dict = Depends(require_permission('credentials.delete'))
):
    """Delete a credential."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM credentials WHERE id = %s RETURNING id", (credential_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Credential not found')
        db.commit()
    return success_response({"deleted": True, "id": credential_id})


@router.get("/types")
async def get_credential_types():
    """Get available credential types."""
    return success_response({
        "types": [
            {"id": "ssh", "name": "SSH", "fields": ["username", "password", "private_key"]},
            {"id": "snmp_v2", "name": "SNMP v2c", "fields": ["community"]},
            {"id": "snmp_v3", "name": "SNMP v3", "fields": ["username", "password", "auth_protocol", "priv_protocol"]},
            {"id": "api_key", "name": "API Key", "fields": ["api_key"]},
            {"id": "http_basic", "name": "HTTP Basic Auth", "fields": ["username", "password"]},
        ]
    })


@router.post("/{credential_id}/test")
async def test_credential(
    credential_id: int,
    target_ip: str,
    request: Request = None,
    user: dict = Depends(require_permission('credentials.view'))
):
    """Test a credential against a target."""
    # This would need implementation based on credential type
    return success_response({
        "tested": True,
        "credential_id": credential_id,
        "target": target_ip,
        "result": "Test not implemented"
    })
