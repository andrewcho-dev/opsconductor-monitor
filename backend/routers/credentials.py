"""
Credentials API Router (/credentials/v1)

Handles credential vault, secrets management, and device credential assignments.
"""

from fastapi import APIRouter, Query, Path, Body, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
import logging

from backend.utils.db import db_query, db_query_one, db_execute

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/credentials/v1", tags=["credentials", "vault", "secrets"])


@router.get("/credentials/statistics", summary="Get credential statistics")
async def get_credential_statistics(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get credential vault statistics"""
    try:
        total = db_query_one("SELECT COUNT(*) as count FROM credentials")
        by_type = db_query("SELECT credential_type, COUNT(*) as count FROM credentials GROUP BY credential_type")
        
        return {
            "total": total['count'] if total else 0,
            "by_type": {r['credential_type']: r['count'] for r in by_type} if by_type else {},
            "expiring_soon": 0,
            "expired": 0
        }
    except Exception as e:
        logger.error(f"Get credential statistics error: {str(e)}")
        return {"total": 0, "by_type": {}, "expiring_soon": 0, "expired": 0}


async def _list_credentials_impl(limit: int = 50, credential_type: Optional[str] = None):
    """Internal implementation for listing credentials"""
    if credential_type:
        creds = db_query(
            "SELECT id, name, credential_type, username, created_at FROM credentials WHERE credential_type = %s ORDER BY name LIMIT %s",
            (credential_type, limit)
        )
    else:
        creds = db_query(
            "SELECT id, name, credential_type, username, created_at FROM credentials ORDER BY name LIMIT %s",
            (limit,)
        )
    return {"credentials": creds, "total": len(creds)}


@router.get("/", summary="List credentials")
async def list_credentials_root(
    limit: int = Query(50, ge=1, le=100),
    credential_type: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List stored credentials"""
    try:
        return await _list_credentials_impl(limit, credential_type)
    except Exception as e:
        logger.error(f"List credentials error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_CREDENTIALS_ERROR", "message": str(e)})


@router.get("/credentials", summary="List credentials (alt path)")
async def list_credentials(
    limit: int = Query(50, ge=1, le=100),
    credential_type: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List stored credentials - alternative path"""
    try:
        return await _list_credentials_impl(limit, credential_type)
    except Exception as e:
        logger.error(f"List credentials error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_CREDENTIALS_ERROR", "message": str(e)})


@router.post("/", summary="Create credential")
async def create_credential(
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Create a new credential"""
    try:
        result = db_execute("""
            INSERT INTO credentials (name, credential_type, username, password, description)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (request['name'], request.get('credential_type', 'ssh'), 
              request.get('username'), request.get('password'), request.get('description')), returning=True)
        return {"success": True, "id": result['id']}
    except Exception as e:
        logger.error(f"Create credential error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "CREATE_CREDENTIAL_ERROR", "message": str(e)})


@router.get("/credentials/expiring", summary="Get expiring credentials")
async def get_expiring_credentials(
    days: int = Query(30, ge=1, le=365),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get credentials expiring within specified days"""
    try:
        # Most credentials don't have expiration dates, return empty for now
        return {"credentials": [], "total": 0, "days": days}
    except Exception as e:
        logger.error(f"Get expiring credentials error: {str(e)}")
        return {"credentials": [], "total": 0, "days": days}


@router.get("/credentials/audit", summary="Get credential audit log")
async def get_credential_audit(
    limit: int = Query(100, ge=1, le=1000),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get credential access/change audit log"""
    try:
        # Check if credential_audit table exists
        audit = db_query("""
            SELECT id, credential_id, action, user_id, timestamp, details
            FROM credential_audit
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))
        return {"audit": audit, "total": len(audit)}
    except Exception as e:
        if 'does not exist' in str(e):
            return {"audit": [], "total": 0}
        logger.error(f"Get credential audit error: {str(e)}")
        return {"audit": [], "total": 0}


@router.get("/credentials/enterprise/configs", summary="Get enterprise auth configs")
async def get_enterprise_configs(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get enterprise authentication configurations (AD/LDAP)"""
    try:
        configs = db_query("""
            SELECT id, name, credential_type, description, created_at 
            FROM credentials 
            WHERE credential_type IN ('active_directory', 'ldap', 'radius')
            ORDER BY name
        """)
        return {"configs": configs, "total": len(configs)}
    except Exception as e:
        logger.error(f"Get enterprise configs error: {str(e)}")
        return {"configs": [], "total": 0}


@router.get("/credentials/enterprise/users", summary="Get enterprise users")
async def get_enterprise_users(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get enterprise users from AD/LDAP"""
    try:
        users = db_query("""
            SELECT id, username, display_name, email, role_id, assigned_at
            FROM enterprise_user_roles
            ORDER BY username
        """)
        return {"users": users, "total": len(users)}
    except Exception as e:
        if 'does not exist' in str(e):
            return {"users": [], "total": 0}
        logger.error(f"Get enterprise users error: {str(e)}")
        return {"users": [], "total": 0}


@router.get("/credentials/groups", summary="Get credential groups")
async def get_credential_groups(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get credential groups"""
    try:
        groups = db_query("SELECT id, name, description, created_at FROM credential_groups ORDER BY name")
        return {"groups": groups, "total": len(groups)}
    except Exception as e:
        if 'does not exist' in str(e):
            return {"groups": [], "total": 0}
        logger.error(f"Get credential groups error: {str(e)}")
        return {"groups": [], "total": 0}


@router.get("/credentials/{credential_id}/devices", summary="Get credential device associations")
async def get_credential_devices(
    credential_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get devices associated with a credential"""
    try:
        # Check if credential_device_associations table exists
        devices = db_query("""
            SELECT d.id, d.name, d.ip_address, d.device_type
            FROM devices d
            JOIN credential_device_associations cda ON d.id = cda.device_id
            WHERE cda.credential_id = %s
            ORDER BY d.name
        """, (credential_id,))
        return {"devices": devices, "total": len(devices)}
    except Exception as e:
        # If table doesn't exist, return empty list
        if 'does not exist' in str(e):
            return {"devices": [], "total": 0}
        logger.error(f"Get credential devices error: {str(e)}")
        return {"devices": [], "total": 0}


@router.get("/{credential_id}", summary="Get credential")
async def get_credential(
    credential_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get credential details (password masked)"""
    try:
        cred = db_query_one("""
            SELECT id, name, credential_type, username, description, created_at
            FROM credentials WHERE id = %s
        """, (credential_id,))
        if not cred:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Credential not found"})
        return dict(cred)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get credential error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "GET_CREDENTIAL_ERROR", "message": str(e)})


@router.put("/{credential_id}", summary="Update credential")
async def update_credential(
    credential_id: int = Path(...),
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Update a credential"""
    try:
        db_execute("""
            UPDATE credentials SET name = %s, username = %s, description = %s
            WHERE id = %s
        """, (request.get('name'), request.get('username'), request.get('description'), credential_id))
        return {"success": True}
    except Exception as e:
        logger.error(f"Update credential error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "UPDATE_CREDENTIAL_ERROR", "message": str(e)})


@router.delete("/{credential_id}", summary="Delete credential")
async def delete_credential(
    credential_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Delete a credential"""
    try:
        db_execute("DELETE FROM credentials WHERE id = %s", (credential_id,))
        return {"success": True}
    except Exception as e:
        logger.error(f"Delete credential error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "DELETE_CREDENTIAL_ERROR", "message": str(e)})


@router.get("/groups", summary="List credential groups")
async def list_groups(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List credential groups"""
    return {"groups": [], "total": 0}


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Credentials API"""
    return {"success": True, "results": {}}
