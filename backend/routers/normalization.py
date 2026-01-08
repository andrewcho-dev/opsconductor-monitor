"""
OpsConductor Normalization Rules API Router

REST endpoints for managing alert normalization rules.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.utils.db import db_query, db_query_one, db_execute

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class SeverityMappingResponse(BaseModel):
    """Severity mapping response."""
    success: bool = True
    data: List[dict]


class CategoryMappingResponse(BaseModel):
    """Category mapping response."""
    success: bool = True
    data: List[dict]


class PriorityRuleResponse(BaseModel):
    """Priority rule response."""
    success: bool = True
    data: List[dict]


class AlertTypeTemplateResponse(BaseModel):
    """Alert type template response."""
    success: bool = True
    data: List[dict]


class DeduplicationRuleResponse(BaseModel):
    """Deduplication rule response."""
    success: bool = True
    data: List[dict]


class CreateSeverityMappingRequest(BaseModel):
    """Request to create severity mapping."""
    connector_type: str
    source_value: str
    source_field: str = "status"
    target_severity: str
    priority: int = 100
    description: Optional[str] = None


class CreateCategoryMappingRequest(BaseModel):
    """Request to create category mapping."""
    connector_type: str
    source_value: str
    source_field: str = "type"
    target_category: str
    priority: int = 100
    description: Optional[str] = None


class CreatePriorityRuleRequest(BaseModel):
    """Request to create priority rule."""
    connector_type: str
    category: str
    severity: str
    impact: str
    urgency: str
    priority: str
    description: Optional[str] = None


class CreateAlertTypeTemplateRequest(BaseModel):
    """Request to create alert type template."""
    connector_type: str
    pattern: str
    template: str
    description: Optional[str] = None


class CreateDeduplicationRuleRequest(BaseModel):
    """Request to create deduplication rule."""
    connector_type: str
    fingerprint_fields: List[str]
    dedup_window_minutes: int = 300
    description: Optional[str] = None


# =============================================================================
# Severity Mappings
# =============================================================================

@router.get("/severity-mappings", response_model=SeverityMappingResponse)
async def list_severity_mappings(connector_type: Optional[str] = None):
    """List severity mappings."""
    query = """
        SELECT id, connector_type, source_value, source_field,
               target_severity, priority, enabled, description,
               created_at, updated_at
        FROM severity_mappings
    """
    params = []
    
    if connector_type:
        query += " WHERE connector_type = %s"
        params.append(connector_type)
    
    query += " ORDER BY connector_type, priority, source_value"
    
    rows = db_query(query, params)
    
    mappings = []
    for row in rows:
        mappings.append({
            "id": str(row["id"]),
            "connector_type": row["connector_type"],
            "source_value": row["source_value"],
            "source_field": row["source_field"],
            "target_severity": row["target_severity"],
            "priority": row["priority"],
            "enabled": row["enabled"],
            "description": row.get("description"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        })
    
    return SeverityMappingResponse(data=mappings)


@router.post("/severity-mappings", response_model=dict)
async def create_severity_mapping(request: CreateSeverityMappingRequest):
    """Create severity mapping."""
    try:
        mapping_id = db_execute("""
            INSERT INTO severity_mappings 
            (connector_type, source_value, source_field, target_severity, priority, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            request.connector_type,
            request.source_value,
            request.source_field,
            request.target_severity,
            request.priority,
            request.description
        ))
        
        return {"success": True, "id": str(mapping_id)}
        
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Mapping already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/severity-mappings/{mapping_id}")
async def update_severity_mapping(mapping_id: str, request: dict):
    """Update severity mapping."""
    # Check exists
    existing = db_query_one(
        "SELECT id FROM severity_mappings WHERE id = %s",
        (mapping_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    # Update
    updates = []
    params = []
    
    for field in ["target_severity", "priority", "enabled", "description"]:
        if field in request:
            updates.append(f"{field} = %s")
            params.append(request[field])
    
    if updates:
        params.append(mapping_id)
        db_execute(f"""
            UPDATE severity_mappings SET {", ".join(updates)}, updated_at = NOW()
            WHERE id = %s
        """, tuple(params))
    
    return {"success": True}


@router.delete("/severity-mappings/{mapping_id}")
async def delete_severity_mapping(mapping_id: str):
    """Delete severity mapping."""
    result = db_execute("DELETE FROM severity_mappings WHERE id = %s", (mapping_id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return {"success": True}


# =============================================================================
# Category Mappings
# =============================================================================

@router.get("/category-mappings", response_model=CategoryMappingResponse)
async def list_category_mappings(connector_type: Optional[str] = None):
    """List category mappings."""
    query = """
        SELECT id, connector_type, source_value, source_field,
               target_category, priority, enabled, description,
               created_at, updated_at
        FROM category_mappings
    """
    params = []
    
    if connector_type:
        query += " WHERE connector_type = %s"
        params.append(connector_type)
    
    query += " ORDER BY connector_type, priority, source_value"
    
    rows = db_query(query, params)
    
    mappings = []
    for row in rows:
        mappings.append({
            "id": str(row["id"]),
            "connector_type": row["connector_type"],
            "source_value": row["source_value"],
            "source_field": row["source_field"],
            "target_category": row["target_category"],
            "priority": row["priority"],
            "enabled": row["enabled"],
            "description": row.get("description"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        })
    
    return CategoryMappingResponse(data=mappings)


@router.post("/category-mappings", response_model=dict)
async def create_category_mapping(request: CreateCategoryMappingRequest):
    """Create category mapping."""
    try:
        mapping_id = db_execute("""
            INSERT INTO category_mappings 
            (connector_type, source_value, source_field, target_category, priority, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            request.connector_type,
            request.source_value,
            request.source_field,
            request.target_category,
            request.priority,
            request.description
        ))
        
        return {"success": True, "id": str(mapping_id)}
        
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Mapping already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/category-mappings/{mapping_id}")
async def update_category_mapping(mapping_id: str, request: dict):
    """Update category mapping."""
    existing = db_query_one(
        "SELECT id FROM category_mappings WHERE id = %s",
        (mapping_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    updates = []
    params = []
    
    for field in ["target_category", "priority", "enabled", "description"]:
        if field in request:
            updates.append(f"{field} = %s")
            params.append(request[field])
    
    if updates:
        params.append(mapping_id)
        db_execute(f"""
            UPDATE category_mappings SET {", ".join(updates)}, updated_at = NOW()
            WHERE id = %s
        """, tuple(params))
    
    return {"success": True}


@router.delete("/category-mappings/{mapping_id}")
async def delete_category_mapping(mapping_id: str):
    """Delete category mapping."""
    result = db_execute("DELETE FROM category_mappings WHERE id = %s", (mapping_id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return {"success": True}


# =============================================================================
# Priority Rules
# =============================================================================

@router.get("/priority-rules", response_model=PriorityRuleResponse)
async def list_priority_rules(connector_type: Optional[str] = None):
    """List priority rules."""
    query = """
        SELECT id, connector_type, category, severity,
               impact, urgency, priority, enabled, description,
               created_at, updated_at
        FROM priority_rules
    """
    params = []
    
    if connector_type:
        query += " WHERE connector_type = %s"
        params.append(connector_type)
    
    query += " ORDER BY connector_type, category, severity"
    
    rows = db_query(query, params)
    
    rules = []
    for row in rows:
        rules.append({
            "id": str(row["id"]),
            "connector_type": row["connector_type"],
            "category": row["category"],
            "severity": row["severity"],
            "impact": row["impact"],
            "urgency": row["urgency"],
            "priority": row["priority"],
            "enabled": row["enabled"],
            "description": row.get("description"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        })
    
    return PriorityRuleResponse(data=rules)


@router.post("/priority-rules", response_model=dict)
async def create_priority_rule(request: CreatePriorityRuleRequest):
    """Create priority rule."""
    try:
        rule_id = db_execute("""
            INSERT INTO priority_rules 
            (connector_type, category, severity, impact, urgency, priority, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            request.connector_type,
            request.category,
            request.severity,
            request.impact,
            request.urgency,
            request.priority,
            request.description
        ))
        
        return {"success": True, "id": str(rule_id)}
        
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Rule already exists")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Alert Type Templates
# =============================================================================

@router.get("/alert-type-templates", response_model=AlertTypeTemplateResponse)
async def list_alert_type_templates(connector_type: Optional[str] = None):
    """List alert type templates."""
    query = """
        SELECT id, connector_type, pattern, template, enabled, description,
               created_at, updated_at
        FROM alert_type_templates
    """
    params = []
    
    if connector_type:
        query += " WHERE connector_type = %s"
        params.append(connector_type)
    
    query += " ORDER BY connector_type, pattern"
    
    rows = db_query(query, params)
    
    templates = []
    for row in rows:
        templates.append({
            "id": str(row["id"]),
            "connector_type": row["connector_type"],
            "pattern": row["pattern"],
            "template": row["template"],
            "enabled": row["enabled"],
            "description": row.get("description"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        })
    
    return AlertTypeTemplateResponse(data=templates)


@router.post("/alert-type-templates", response_model=dict)
async def create_alert_type_template(request: CreateAlertTypeTemplateRequest):
    """Create alert type template."""
    try:
        template_id = db_execute("""
            INSERT INTO alert_type_templates 
            (connector_type, pattern, template, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            request.connector_type,
            request.pattern,
            request.template,
            request.description
        ))
        
        return {"success": True, "id": str(template_id)}
        
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Template already exists")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Deduplication Rules
# =============================================================================

@router.get("/deduplication-rules", response_model=DeduplicationRuleResponse)
async def list_deduplication_rules(connector_type: Optional[str] = None):
    """List deduplication rules."""
    query = """
        SELECT id, connector_type, fingerprint_fields, dedup_window_minutes,
               enabled, description, created_at, updated_at
        FROM deduplication_rules
    """
    params = []
    
    if connector_type:
        query += " WHERE connector_type = %s"
        params.append(connector_type)
    
    query += " ORDER BY connector_type"
    
    rows = db_query(query, params)
    
    rules = []
    for row in rows:
        rules.append({
            "id": str(row["id"]),
            "connector_type": row["connector_type"],
            "fingerprint_fields": row["fingerprint_fields"],
            "dedup_window_minutes": row["dedup_window_minutes"],
            "enabled": row["enabled"],
            "description": row.get("description"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        })
    
    return DeduplicationRuleResponse(data=rules)


@router.post("/deduplication-rules", response_model=dict)
async def create_deduplication_rule(request: CreateDeduplicationRuleRequest):
    """Create deduplication rule."""
    try:
        rule_id = db_execute("""
            INSERT INTO deduplication_rules 
            (connector_type, fingerprint_fields, dedup_window_minutes, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            request.connector_type,
            request.fingerprint_fields,
            request.dedup_window_minutes,
            request.description
        ))
        
        return {"success": True, "id": str(rule_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
