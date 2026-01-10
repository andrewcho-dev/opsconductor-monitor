"""
OpsConductor Dependencies API Router

REST endpoints for device dependency management.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.models import DependencyType
from core.dependency_registry import get_dependency_registry

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class DependencyResponse(BaseModel):
    """Dependency response model."""
    id: str
    device_ip: str
    device_name: Optional[str]
    depends_on_ip: str
    depends_on_name: Optional[str]
    dependency_type: str
    description: Optional[str]
    auto_discovered: bool
    confidence: Optional[float]
    created_at: Optional[str]
    created_by: Optional[str]


class DependencyListResponse(BaseModel):
    """Paginated dependency list response."""
    success: bool = True
    data: List[DependencyResponse]
    meta: dict


class DependencyDetailResponse(BaseModel):
    """Single dependency detail response."""
    success: bool = True
    data: DependencyResponse


class DeviceDependenciesResponse(BaseModel):
    """Device dependencies summary response."""
    success: bool = True
    data: dict


class CreateDependencyRequest(BaseModel):
    """Request to create a dependency."""
    device_ip: str
    depends_on_ip: str
    dependency_type: str = "network"
    description: Optional[str] = None


class BulkCreateRequest(BaseModel):
    """Request to create multiple dependencies."""
    dependencies: List[CreateDependencyRequest]


class BulkCreateResponse(BaseModel):
    """Response for bulk create."""
    success: bool = True
    data: dict


# =============================================================================
# Helper Functions
# =============================================================================

def dependency_to_response(dep) -> DependencyResponse:
    """Convert Dependency model to response."""
    return DependencyResponse(
        id=str(dep.id),
        device_ip=dep.device_ip,
        device_name=dep.device_name,
        depends_on_ip=dep.depends_on_ip,
        depends_on_name=dep.depends_on_name,
        dependency_type=dep.dependency_type.value if hasattr(dep.dependency_type, 'value') else dep.dependency_type,
        description=dep.description,
        auto_discovered=dep.auto_discovered,
        confidence=dep.confidence,
        created_at=dep.created_at.isoformat() if dep.created_at else None,
        created_by=dep.created_by,
    )


def get_current_user() -> str:
    """Get current user from auth context. Placeholder for now."""
    # TODO: Integrate with actual auth
    return "system"


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=DependencyListResponse)
async def list_dependencies(
    device_ip: Optional[str] = Query(None, description="Filter by device IP"),
    depends_on_ip: Optional[str] = Query(None, description="Filter by upstream device IP"),
    type: Optional[str] = Query(None, description="Filter by dependency type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=500, description="Items per page"),
):
    """
    List dependencies with filtering and pagination.
    """
    registry = get_dependency_registry()
    
    # Parse type filter
    dep_type = None
    if type:
        try:
            dep_type = DependencyType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid dependency type: {type}")
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Query dependencies
    deps = await registry.get_dependencies(
        device_ip=device_ip,
        depends_on_ip=depends_on_ip,
        dependency_type=dep_type,
        limit=per_page,
        offset=offset,
    )
    
    # Get total count
    total = await registry.get_dependency_count()
    
    return DependencyListResponse(
        data=[dependency_to_response(d) for d in deps],
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    )


@router.get("/device/{device_ip}", response_model=DeviceDependenciesResponse)
async def get_device_dependencies(device_ip: str):
    """
    Get all dependencies for a specific device (upstream and downstream).
    """
    registry = get_dependency_registry()
    
    summary = await registry.get_device_summary(device_ip)
    
    return DeviceDependenciesResponse(data=summary)


@router.get("/{dependency_id}", response_model=DependencyDetailResponse)
async def get_dependency(dependency_id: str):
    """
    Get a single dependency by ID.
    """
    registry = get_dependency_registry()
    
    try:
        uuid = UUID(dependency_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dependency ID format")
    
    dep = await registry.get_dependency(uuid)
    
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    
    return DependencyDetailResponse(data=dependency_to_response(dep))


@router.post("", response_model=DependencyDetailResponse)
async def create_dependency(request: CreateDependencyRequest):
    """
    Create a new dependency relationship.
    """
    registry = get_dependency_registry()
    user = get_current_user()
    
    # Parse type
    try:
        dep_type = DependencyType(request.dependency_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dependency type: {request.dependency_type}")
    
    try:
        dep = await registry.add_dependency(
            device_ip=request.device_ip,
            depends_on_ip=request.depends_on_ip,
            dependency_type=dep_type,
            description=request.description,
            created_by=user,
        )
        return DependencyDetailResponse(data=dependency_to_response(dep))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating dependency")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dependency_id}")
async def delete_dependency(dependency_id: str):
    """
    Delete a dependency relationship.
    """
    registry = get_dependency_registry()
    
    try:
        uuid = UUID(dependency_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dependency ID format")
    
    deleted = await registry.remove_dependency(uuid)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Dependency not found")
    
    return {"success": True, "message": "Dependency deleted"}


@router.post("/bulk", response_model=BulkCreateResponse)
async def bulk_create_dependencies(request: BulkCreateRequest):
    """
    Create multiple dependencies at once.
    """
    registry = get_dependency_registry()
    user = get_current_user()
    
    # Convert to list of dicts
    deps_data = [
        {
            "device_ip": d.device_ip,
            "depends_on_ip": d.depends_on_ip,
            "dependency_type": d.dependency_type,
            "description": d.description,
        }
        for d in request.dependencies
    ]
    
    try:
        created = await registry.bulk_add_dependencies(deps_data, created_by=user)
        return BulkCreateResponse(
            data={
                "created": created,
                "total": len(request.dependencies),
            }
        )
    except Exception as e:
        logger.exception("Error in bulk create")
        raise HTTPException(status_code=500, detail=str(e))
