"""
Workflows API Router - FastAPI.

Routes for workflow builder and management.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    folder_id: Optional[str] = None  # UUID
    tags: Optional[List[str]] = None
    definition: Dict[str, Any] = {}
    settings: Optional[Dict[str, Any]] = None
    is_template: bool = False


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[str] = None  # UUID
    tags: Optional[List[str]] = None
    definition: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    is_template: Optional[bool] = None


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"


@router.get("")
async def list_workflows(
    folder_id: Optional[int] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None
):
    """List all workflows."""
    db = get_db()
    
    query = """
        SELECT w.id, w.name, w.description, w.folder_id, w.definition, w.settings,
               w.enabled, w.is_template, w.created_at, w.updated_at, w.last_run_at,
               f.name as folder_name
        FROM workflows w
        LEFT JOIN job_folders f ON w.folder_id = f.id
        WHERE 1=1
    """
    params = []
    
    if folder_id is not None:
        query += " AND w.folder_id = %s"
        params.append(folder_id)
    if tag:
        query += " AND EXISTS (SELECT 1 FROM workflow_tags wt WHERE wt.workflow_id = w.id AND wt.tag = %s)"
        params.append(tag)
    if search:
        query += " AND (w.name ILIKE %s OR w.description ILIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY w.name"
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        workflows = [dict(row) for row in cursor.fetchall()]
    
    return list_response(workflows)


@router.post("")
async def create_workflow(req: WorkflowCreate):
    """Create a new workflow."""
    import json
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO workflows (name, description, folder_id, definition, settings, is_template)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, folder_id, definition, settings, enabled, is_template, created_at
        """, (req.name, req.description, req.folder_id, json.dumps(req.definition), 
              json.dumps(req.settings) if req.settings else None, req.is_template))
        workflow = dict(cursor.fetchone())
        
        # Add tags if provided
        if req.tags:
            for tag in req.tags:
                cursor.execute("""
                    INSERT INTO workflow_tags (workflow_id, tag) VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (workflow['id'], tag))
        
        db.commit()
    return success_response(workflow)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a workflow by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT w.*, f.name as folder_name
            FROM workflows w
            LEFT JOIN job_folders f ON w.folder_id = f.id
            WHERE w.id = %s
        """, (workflow_id,))
        workflow = cursor.fetchone()
        if not workflow:
            return error_response('NOT_FOUND', 'Workflow not found')
    return success_response(dict(workflow))


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, req: WorkflowUpdate):
    """Update a workflow."""
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.description is not None:
        updates.append("description = %s")
        params.append(req.description)
    if req.folder_id is not None:
        updates.append("folder_id = %s")
        params.append(req.folder_id)
    if req.tags is not None:
        updates.append("tags = %s")
        params.append(req.tags)
    if req.steps is not None:
        updates.append("steps = %s")
        params.append(req.steps)
    if req.enabled is not None:
        updates.append("enabled = %s")
        params.append(req.enabled)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    updates.append("updated_at = NOW()")
    params.append(workflow_id)
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE workflows
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, description, folder_id, tags, enabled, updated_at
        """, params)
        workflow = cursor.fetchone()
        if not workflow:
            return error_response('NOT_FOUND', 'Workflow not found')
        db.commit()
    
    return success_response(dict(workflow))


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM workflows WHERE id = %s RETURNING id", (workflow_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Workflow not found')
        db.commit()
    return success_response({"deleted": True, "id": workflow_id})


@router.post("/{workflow_id}/duplicate")
async def duplicate_workflow(workflow_id: str):
    """Duplicate a workflow."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM workflows WHERE id = %s", (workflow_id,))
        original = cursor.fetchone()
        if not original:
            return error_response('NOT_FOUND', 'Workflow not found')
        
        cursor.execute("""
            INSERT INTO workflows (name, description, folder_id, definition, settings, is_template)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, folder_id, definition, settings, enabled, is_template, created_at
        """, (
            f"{original['name']} (Copy)",
            original['description'],
            original['folder_id'],
            original['definition'],
            original['settings'],
            original['is_template']
        ))
        new_workflow = dict(cursor.fetchone())
        db.commit()
    
    return success_response(new_workflow)


# =============================================================================
# FOLDERS
# =============================================================================

@router.get("/folders")
async def list_folders():
    """List all workflow folders."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT f.id, f.name, f.parent_id, f.description, f.created_at,
                   COUNT(w.id) as workflow_count
            FROM job_folders f
            LEFT JOIN workflows w ON f.id = w.folder_id
            GROUP BY f.id
            ORDER BY f.name
        """)
        folders = [dict(row) for row in cursor.fetchall()]
    return list_response(folders)


@router.post("/folders")
async def create_folder(req: FolderCreate):
    """Create a new folder."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO job_folders (name, parent_id, description)
            VALUES (%s, %s, %s)
            RETURNING id, name, parent_id, description, created_at
        """, (req.name, req.parent_id, req.description))
        folder = dict(cursor.fetchone())
        db.commit()
    return success_response(folder)


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int):
    """Delete a folder."""
    db = get_db()
    with db.cursor() as cursor:
        # Check if folder has workflows
        cursor.execute("SELECT COUNT(*) FROM workflows WHERE folder_id = %s", (folder_id,))
        count = cursor.fetchone()['count']
        if count > 0:
            return error_response('HAS_CHILDREN', f'Folder contains {count} workflows')
        
        cursor.execute("DELETE FROM job_folders WHERE id = %s RETURNING id", (folder_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Folder not found')
        db.commit()
    return success_response({"deleted": True, "id": folder_id})


# =============================================================================
# TAGS
# =============================================================================

@router.get("/tags")
async def list_tags():
    """List all workflow tags."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, color, created_at
            FROM workflow_tags
            ORDER BY name
        """)
        tags = [dict(row) for row in cursor.fetchall()]
    return list_response(tags)


@router.post("/tags")
async def create_tag(req: TagCreate):
    """Create a new tag."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO workflow_tags (name, color)
            VALUES (%s, %s)
            RETURNING id, name, color, created_at
        """, (req.name, req.color))
        tag = dict(cursor.fetchone())
        db.commit()
    return success_response(tag)


@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: int):
    """Delete a tag."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM workflow_tags WHERE id = %s RETURNING id", (tag_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Tag not found')
        db.commit()
    return success_response({"deleted": True, "id": tag_id})


# =============================================================================
# PACKAGES (workflow templates)
# =============================================================================

@router.get("/packages")
async def list_packages():
    """List workflow packages/templates."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, version, author, workflows, created_at
            FROM workflow_packages
            ORDER BY name
        """)
        packages = [dict(row) for row in cursor.fetchall()]
    return list_response(packages)


@router.post("/packages/{package_id}/install")
async def install_package(package_id: int):
    """Install workflows from a package."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM workflow_packages WHERE id = %s", (package_id,))
        package = cursor.fetchone()
        if not package:
            return error_response('NOT_FOUND', 'Package not found')
        
        # Install each workflow from the package
        installed = 0
        for workflow_def in package.get('workflows', []):
            cursor.execute("""
                INSERT INTO workflows (name, description, steps, tags)
                VALUES (%s, %s, %s, %s)
            """, (
                workflow_def.get('name'),
                workflow_def.get('description'),
                workflow_def.get('steps', []),
                workflow_def.get('tags', [])
            ))
            installed += 1
        
        db.commit()
    
    return success_response({"installed": installed, "package": package['name']})
