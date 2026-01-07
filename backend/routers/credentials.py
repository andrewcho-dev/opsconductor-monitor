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


@router.get("/", summary="List credentials")
async def list_credentials(
    limit: int = Query(50, ge=1, le=100),
    credential_type: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List stored credentials"""
    try:
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
