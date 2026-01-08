"""
OpsConductor Connectors API Router

REST endpoints for connector management and webhooks.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Form, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from backend.utils.db import db_query, db_query_one, db_execute
from connectors.registry import CONNECTOR_TYPES, get_connector_class, create_connector
from core.alert_manager import get_alert_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ConnectorResponse(BaseModel):
    """Connector response model."""
    id: str
    name: str
    type: str
    enabled: bool
    status: str
    error_message: Optional[str]
    last_poll_at: Optional[str]
    alerts_received: int
    alerts_today: int


class ConnectorDetailResponse(BaseModel):
    """Single connector detail response."""
    success: bool = True
    data: dict


class ConnectorListResponse(BaseModel):
    """Connector list response."""
    success: bool = True
    data: List[dict]


class ConnectorTypesResponse(BaseModel):
    """Available connector types response."""
    success: bool = True
    data: List[dict]


class CreateConnectorRequest(BaseModel):
    """Request to create a connector."""
    name: str
    type: str
    enabled: bool = False
    config: dict = {}


class UpdateConnectorRequest(BaseModel):
    """Request to update a connector."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None


class TestConnectionResponse(BaseModel):
    """Test connection response."""
    success: bool
    message: str
    details: Optional[dict]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/types", response_model=ConnectorTypesResponse)
async def list_connector_types():
    """
    List available connector types.
    """
    return ConnectorTypesResponse(data=CONNECTOR_TYPES)


@router.get("", response_model=ConnectorListResponse)
async def list_connectors():
    """
    List all configured connectors.
    """
    rows = db_query("""
        SELECT id, name, type, enabled, status, error_message,
               last_poll_at, alerts_received, alerts_today,
               created_at, updated_at
        FROM connectors
        ORDER BY name
    """)
    
    connectors = []
    for row in rows:
        connectors.append({
            "id": str(row["id"]),
            "name": row["name"],
            "type": row["type"],
            "enabled": row["enabled"],
            "status": row["status"],
            "error_message": row.get("error_message"),
            "last_poll_at": row["last_poll_at"].isoformat() if row.get("last_poll_at") else None,
            "alerts_received": row.get("alerts_received", 0),
            "alerts_today": row.get("alerts_today", 0),
        })
    
    return ConnectorListResponse(data=connectors)


@router.get("/{connector_id}", response_model=ConnectorDetailResponse)
async def get_connector(connector_id: str):
    """
    Get connector details including configuration.
    """
    row = db_query_one(
        "SELECT * FROM connectors WHERE id = %s",
        (connector_id,)
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Don't expose sensitive config values
    config = dict(row.get("config", {}))
    for key in ["password", "passhash", "api_token", "secret"]:
        if key in config:
            config[key] = "********"
    
    return ConnectorDetailResponse(data={
        "id": str(row["id"]),
        "name": row["name"],
        "type": row["type"],
        "enabled": row["enabled"],
        "status": row["status"],
        "error_message": row.get("error_message"),
        "config": config,
        "last_poll_at": row["last_poll_at"].isoformat() if row.get("last_poll_at") else None,
        "last_success_at": row["last_success_at"].isoformat() if row.get("last_success_at") else None,
        "alerts_received": row.get("alerts_received", 0),
        "alerts_today": row.get("alerts_today", 0),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    })


@router.post("", response_model=ConnectorDetailResponse)
async def create_connector_endpoint(request: CreateConnectorRequest):
    """
    Create a new connector.
    """
    # Validate connector type
    valid_types = [t["type"] for t in CONNECTOR_TYPES]
    if request.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid connector type: {request.type}")
    
    from uuid import uuid4
    connector_id = uuid4()
    
    try:
        db_execute("""
            INSERT INTO connectors (id, name, type, enabled, config, status)
            VALUES (%s, %s, %s, %s, %s, 'unknown')
        """, (str(connector_id), request.name, request.type, request.enabled, str(request.config)))
        
        return await get_connector(str(connector_id))
        
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Connector '{request.name}' already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{connector_id}", response_model=ConnectorDetailResponse)
async def update_connector(connector_id: str, request: UpdateConnectorRequest):
    """
    Update connector configuration.
    """
    # Check exists
    existing = db_query_one("SELECT * FROM connectors WHERE id = %s", (connector_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    updates = []
    params = []
    
    if request.name is not None:
        updates.append("name = %s")
        params.append(request.name)
    
    if request.enabled is not None:
        updates.append("enabled = %s")
        params.append(request.enabled)
    
    if request.config is not None:
        # Merge with existing config to preserve passwords
        current_config = dict(existing.get("config", {}))
        for key, value in request.config.items():
            if value != "********":  # Don't overwrite with masked value
                current_config[key] = value
        updates.append("config = %s")
        params.append(str(current_config))
    
    if updates:
        params.append(connector_id)
        db_execute(f"""
            UPDATE connectors SET {", ".join(updates)}
            WHERE id = %s
        """, tuple(params))
    
    return await get_connector(connector_id)


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """
    Delete a connector.
    """
    result = db_execute("DELETE FROM connectors WHERE id = %s", (connector_id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    return {"success": True, "message": "Connector deleted"}


@router.post("/{connector_id}/test", response_model=TestConnectionResponse)
async def test_connector(connector_id: str):
    """
    Test connector connectivity.
    """
    row = db_query_one("SELECT * FROM connectors WHERE id = %s", (connector_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector_type = row["type"]
    config = dict(row.get("config", {}))
    
    # Get connector class
    connector_class = get_connector_class(connector_type)
    if not connector_class:
        return TestConnectionResponse(
            success=False,
            message=f"Connector type '{connector_type}' not implemented",
            details=None
        )
    
    try:
        # Create connector instance and test
        connector = connector_class(config)
        result = await connector.test_connection()
        
        # Update status in database
        status = "connected" if result.get("success") else "error"
        error_msg = None if result.get("success") else result.get("message")
        
        db_execute("""
            UPDATE connectors SET status = %s, error_message = %s
            WHERE id = %s
        """, (status, error_msg, connector_id))
        
        return TestConnectionResponse(**result)
        
    except Exception as e:
        logger.exception(f"Error testing connector {connector_id}")
        
        db_execute("""
            UPDATE connectors SET status = 'error', error_message = %s
            WHERE id = %s
        """, (str(e), connector_id))
        
        return TestConnectionResponse(
            success=False,
            message=str(e),
            details=None
        )


@router.post("/{connector_id}/enable")
async def enable_connector(connector_id: str):
    """Enable a connector."""
    db_execute("UPDATE connectors SET enabled = true WHERE id = %s", (connector_id,))
    return {"success": True, "message": "Connector enabled"}


@router.post("/{connector_id}/disable")
async def disable_connector(connector_id: str):
    """Disable a connector."""
    db_execute("UPDATE connectors SET enabled = false WHERE id = %s", (connector_id,))
    return {"success": True, "message": "Connector disabled"}


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/prtg/webhook")
async def prtg_webhook(request: Request):
    """
    Receive PRTG webhook notifications.
    
    PRTG sends form-encoded data with fields like:
    sensorid, deviceid, device, status, message, datetime, etc.
    """
    try:
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        logger.info(f"PRTG webhook received: sensor={data.get('sensorid')}, status={data.get('status')}")
        
        # Get PRTG connector
        row = db_query_one("SELECT * FROM connectors WHERE type = 'prtg' AND enabled = true LIMIT 1")
        
        if not row:
            logger.warning("PRTG webhook received but no enabled PRTG connector")
            return {"success": False, "message": "No enabled PRTG connector"}
        
        config = dict(row.get("config", {}))
        
        # Create connector and process webhook
        from connectors.prtg import PRTGConnector
        connector = PRTGConnector(config)
        
        alert = await connector.handle_webhook(data)
        
        # Process alert through AlertManager
        if alert:
            from core.alert_manager import get_alert_manager
            alert_manager = get_alert_manager()
            stored_alert = await alert_manager.process_alert(alert)
            logger.info(f"Stored alert {stored_alert.id}")
        
        # Update connector stats
        db_execute("""
            UPDATE connectors 
            SET alerts_received = alerts_received + 1,
                alerts_today = alerts_today + 1,
                last_poll_at = NOW()
            WHERE id = %s
        """, (str(row["id"]),))
        
        return {"success": True, "message": "Alert processed", "alert_id": str(alert.id) if alert else None}
        
    except Exception as e:
        logger.exception("Error processing PRTG webhook")
        return {"success": False, "message": str(e)}


@router.post("/{connector_id}/poll", summary="Manually trigger connector polling")
async def poll_connector(
    connector_id: str,
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
):
    """
    Manually trigger polling for a specific connector.
    
    This is useful for testing or immediate data refresh.
    """
    try:
        # Get connector
        row = db_query_one(
            "SELECT id, name, type, config, enabled FROM connectors WHERE id = %s",
            (connector_id,)
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Connector not found")
        
        if not row["enabled"]:
            raise HTTPException(status_code=400, detail="Connector is not enabled")
        
        # Create connector and poll
        from connectors.registry import create_connector
        connector = create_connector(row["type"], dict(row.get("config", {})))
        if not connector:
            raise HTTPException(status_code=400, detail=f"Unknown connector type: {row['type']}")
        
        logger.info(f"Manual poll triggered for {row['name']}")
        
        # Poll for alerts
        alerts = await connector.poll()
        
        if alerts:
            # Process alerts through AlertManager
            alert_manager = get_alert_manager()
            for alert in alerts:
                stored_alert = await alert_manager.process_alert(alert)
                logger.info(f"Stored alert {stored_alert.id} from {row['name']}")
        
        # Update connector stats
        db_execute("""
            UPDATE connectors 
            SET last_poll_at = NOW(),
                alerts_received = alerts_received + %s,
                alerts_today = alerts_today + %s,
                status = 'connected',
                error_message = NULL
            WHERE id = %s
        """, (len(alerts), len(alerts), connector_id))
        
        return {
            "success": True,
            "message": f"Poll completed for {row['name']}",
            "alerts": len(alerts),
            "connector": row["name"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual poll error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/axis/webhook")
async def axis_webhook(request: Request):
    """
    Receive Axis camera event notifications.
    """
    try:
        data = await request.json()
        logger.info(f"Axis webhook received")
        
        # TODO: Implement when Axis connector is built
        return {"success": True, "message": "Webhook received (not processed yet)"}
        
    except Exception as e:
        logger.exception("Error processing Axis webhook")
        return {"success": False, "message": str(e)}


@router.post("/milestone/webhook")
async def milestone_webhook(request: Request):
    """
    Receive Milestone VMS event notifications.
    """
    try:
        data = await request.json()
        logger.info(f"Milestone webhook received")
        
        # TODO: Implement when Milestone connector is built
        return {"success": True, "message": "Webhook received (not processed yet)"}
        
    except Exception as e:
        logger.exception("Error processing Milestone webhook")
        return {"success": False, "message": str(e)}
