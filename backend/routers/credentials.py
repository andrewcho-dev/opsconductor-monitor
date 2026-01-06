"""
Credentials API Router (/credentials/v1)

Handles credential vault, secrets management, and device credential assignments.
"""

from fastapi import APIRouter, Query, Path, Body, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/credentials/v1", tags=["credentials", "vault", "secrets"])


@router.get("/", summary="List credentials")
async def list_credentials(
    limit: int = Query(50, ge=1, le=100),
    credential_type: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List stored credentials"""
    try:
        db = get_db()
        with db.cursor() as cursor:
            query = "SELECT id, name, credential_type, username, created_at FROM credentials"
            if credential_type:
                query += " WHERE credential_type = %s"
                cursor.execute(query + " ORDER BY name LIMIT %s", (credential_type, limit))
            else:
                cursor.execute(query + " ORDER BY name LIMIT %s", (limit,))
            creds = [dict(row) for row in cursor.fetchall()]
        return {"credentials": creds, "total": len(creds)}
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
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO credentials (name, credential_type, username, password, description)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (request['name'], request.get('credential_type', 'ssh'), 
                  request.get('username'), request.get('password'), request.get('description')))
            cred_id = cursor.fetchone()['id']
            db.commit()
        return {"success": True, "id": cred_id}
    except Exception as e:
        logger.error(f"Create credential error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "CREATE_CREDENTIAL_ERROR", "message": str(e)})


@router.get("/{credential_id}", summary="Get credential")
async def get_credential(
    credential_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get credential details (password masked)"""
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, credential_type, username, description, created_at
                FROM credentials WHERE id = %s
            """, (credential_id,))
            cred = cursor.fetchone()
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
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE credentials SET name = %s, username = %s, description = %s
                WHERE id = %s
            """, (request.get('name'), request.get('username'), request.get('description'), credential_id))
            db.commit()
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
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM credentials WHERE id = %s", (credential_id,))
            db.commit()
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
