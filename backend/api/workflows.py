"""
Workflow API routes.

Provides REST endpoints for workflow CRUD operations, folders, tags, and packages.
"""

from flask import Blueprint, request, jsonify
from ..database import get_db
from ..repositories.workflow_repo import (
    WorkflowRepository, 
    FolderRepository, 
    TagRepository,
    PackageRepository
)

workflows_bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')
folders_bp = Blueprint('folders', __name__, url_prefix='/api/workflows/folders')
tags_bp = Blueprint('tags', __name__, url_prefix='/api/workflows/tags')
packages_bp = Blueprint('packages', __name__, url_prefix='/api/packages')


def get_workflow_repo():
    """Get workflow repository instance."""
    return WorkflowRepository(get_db())


def get_folder_repo():
    """Get folder repository instance."""
    return FolderRepository(get_db())


def get_tag_repo():
    """Get tag repository instance."""
    return TagRepository(get_db())


def get_package_repo():
    """Get package repository instance."""
    return PackageRepository(get_db())


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================

@workflows_bp.route('', methods=['GET'])
def list_workflows():
    """List all workflows with optional filters."""
    folder_id = request.args.get('folder_id')
    tag_ids = request.args.getlist('tag_id')
    search = request.args.get('search')
    enabled = request.args.get('enabled')
    include_templates = request.args.get('include_templates', 'false').lower() == 'true'
    
    if enabled is not None:
        enabled = enabled.lower() == 'true'
    
    workflows = get_workflow_repo().get_all(
        folder_id=folder_id,
        tag_ids=tag_ids if tag_ids else None,
        search=search,
        enabled=enabled,
        include_templates=include_templates
    )
    
    return jsonify({
        'success': True,
        'data': workflows,
        'count': len(workflows)
    })


@workflows_bp.route('/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """Get a single workflow by ID."""
    workflow = get_workflow_repo().get_by_id(workflow_id)
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': workflow
    })


@workflows_bp.route('', methods=['POST'])
def create_workflow():
    """Create a new workflow."""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({
            'success': False,
            'error': 'Name is required'
        }), 400
    
    repo = get_workflow_repo()
    workflow = repo.create(
        name=data['name'],
        description=data.get('description', ''),
        definition=data.get('definition', {}),
        settings=data.get('settings'),
        schedule=data.get('schedule'),
        folder_id=data.get('folder_id'),
        enabled=data.get('enabled', True)
    )
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Failed to create workflow'
        }), 500
    
    # Handle tags if provided
    if data.get('tag_ids'):
        workflow = repo.update_tags(workflow['id'], data['tag_ids'])
    
    return jsonify({
        'success': True,
        'data': workflow
    }), 201


@workflows_bp.route('/<workflow_id>', methods=['PUT'])
def update_workflow(workflow_id):
    """Update a workflow."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        }), 400
    
    repo = get_workflow_repo()
    workflow = repo.update(
        id=workflow_id,
        name=data.get('name'),
        description=data.get('description'),
        definition=data.get('definition'),
        settings=data.get('settings'),
        schedule=data.get('schedule'),
        folder_id=data.get('folder_id'),
        enabled=data.get('enabled')
    )
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    # Handle tags if provided
    if 'tag_ids' in data:
        workflow = repo.update_tags(workflow_id, data['tag_ids'])
    
    return jsonify({
        'success': True,
        'data': workflow
    })


@workflows_bp.route('/<workflow_id>', methods=['DELETE'])
def delete_workflow(workflow_id):
    """Delete a workflow."""
    success = get_workflow_repo().delete(workflow_id)
    
    if not success:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Workflow deleted'
    })


@workflows_bp.route('/<workflow_id>/duplicate', methods=['POST'])
def duplicate_workflow(workflow_id):
    """Duplicate a workflow."""
    data = request.get_json() or {}
    new_name = data.get('name')
    
    if not new_name:
        # Generate a default name
        original = get_workflow_repo().get_by_id(workflow_id)
        if original:
            new_name = f"{original['name']} (Copy)"
        else:
            return jsonify({
                'success': False,
                'error': 'Workflow not found'
            }), 404
    
    workflow = get_workflow_repo().duplicate(workflow_id, new_name)
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Failed to duplicate workflow'
        }), 500
    
    return jsonify({
        'success': True,
        'data': workflow
    }), 201


@workflows_bp.route('/<workflow_id>/move', methods=['POST'])
def move_workflow(workflow_id):
    """Move a workflow to a folder."""
    data = request.get_json() or {}
    folder_id = data.get('folder_id')  # None means root
    
    workflow = get_workflow_repo().move_to_folder(workflow_id, folder_id)
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': workflow
    })


@workflows_bp.route('/<workflow_id>/tags', methods=['PUT'])
def update_workflow_tags(workflow_id):
    """Update workflow tags."""
    data = request.get_json() or {}
    tag_ids = data.get('tag_ids', [])
    
    workflow = get_workflow_repo().update_tags(workflow_id, tag_ids)
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': workflow
    })


@workflows_bp.route('/<workflow_id>/run', methods=['POST'])
def run_workflow(workflow_id):
    """Execute a workflow via Celery (async)."""
    workflow = get_workflow_repo().get_by_id(workflow_id)
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    # Get trigger data from request (handle empty body)
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    trigger_data = data.get('trigger_data', {})
    sync = data.get('sync', False)  # Allow sync execution if explicitly requested
    
    # Try to use Celery for async execution
    try:
        from celery_app import celery_app
        
        if sync:
            # Synchronous execution requested
            from ..tasks.job_tasks import run_workflow as run_workflow_sync
            result = run_workflow_sync(workflow_id, trigger_data)
            return jsonify({
                'success': True,
                'message': 'Workflow execution completed',
                'data': result
            })
        
        # Submit to Celery queue
        task = celery_app.send_task(
            'opsconductor.workflow.run',
            args=[workflow_id, trigger_data]
        )
        
        return jsonify({
            'success': True,
            'message': 'Workflow submitted to queue',
            'data': {
                'task_id': task.id,
                'workflow_id': workflow_id,
                'workflow_name': workflow.get('name'),
                'status': 'queued'
            }
        })
        
    except ImportError:
        # Celery not available, fall back to sync execution
        from ..tasks.job_tasks import run_workflow as run_workflow_sync
        result = run_workflow_sync(workflow_id, trigger_data)
        return jsonify({
            'success': True,
            'message': 'Workflow execution completed (sync - Celery not available)',
            'data': result
        })


@workflows_bp.route('/<workflow_id>/test', methods=['POST'])
def test_workflow(workflow_id):
    """Test run a workflow via Celery (async)."""
    workflow = get_workflow_repo().get_by_id(workflow_id)
    
    if not workflow:
        return jsonify({
            'success': False,
            'error': 'Workflow not found'
        }), 404
    
    # Get trigger data from request (handle empty body)
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    trigger_data = data.get('trigger_data', {})
    trigger_data['_test_mode'] = True  # Flag for test mode
    sync = data.get('sync', False)  # Allow sync execution if explicitly requested
    
    # Try to use Celery for async execution
    try:
        from celery_app import celery_app
        
        if sync:
            # Synchronous execution requested
            from ..tasks.job_tasks import run_workflow as run_workflow_sync
            result = run_workflow_sync(workflow_id, trigger_data)
            result['test_mode'] = True
            return jsonify({
                'success': True,
                'message': 'Test run completed',
                'data': result
            })
        
        # Submit to Celery queue
        task = celery_app.send_task(
            'opsconductor.workflow.run',
            args=[workflow_id, trigger_data]
        )
        
        return jsonify({
            'success': True,
            'message': 'Test workflow submitted to queue',
            'data': {
                'task_id': task.id,
                'workflow_id': workflow_id,
                'workflow_name': workflow.get('name'),
                'status': 'queued',
                'test_mode': True
            }
        })
        
    except ImportError:
        # Celery not available, fall back to sync execution
        from ..tasks.job_tasks import run_workflow as run_workflow_sync
        result = run_workflow_sync(workflow_id, trigger_data)
        result['test_mode'] = True
        return jsonify({
            'success': True,
            'message': 'Test run completed (sync - Celery not available)',
            'data': result
        })


@workflows_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a workflow task."""
    try:
        from celery_app import celery_app
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id, app=celery_app)
        
        response = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
        }
        
        if result.ready():
            if result.successful():
                response['result'] = result.result
            elif result.failed():
                response['error'] = str(result.result)
        
        return jsonify({
            'success': True,
            'data': response
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Celery not available'
        }), 503


# =============================================================================
# FOLDER ENDPOINTS
# =============================================================================

@folders_bp.route('', methods=['GET'])
def list_folders():
    """List all folders."""
    folders = get_folder_repo().get_all()
    
    return jsonify({
        'success': True,
        'data': folders,
        'count': len(folders)
    })


@folders_bp.route('/<folder_id>', methods=['GET'])
def get_folder(folder_id):
    """Get a single folder by ID."""
    folder = get_folder_repo().get_by_id(folder_id)
    
    if not folder:
        return jsonify({
            'success': False,
            'error': 'Folder not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': folder
    })


@folders_bp.route('', methods=['POST'])
def create_folder():
    """Create a new folder."""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({
            'success': False,
            'error': 'Name is required'
        }), 400
    
    folder = get_folder_repo().create(
        name=data['name'],
        parent_id=data.get('parent_id'),
        color=data.get('color', '#6B7280'),
        icon=data.get('icon', 'folder')
    )
    
    if not folder:
        return jsonify({
            'success': False,
            'error': 'Failed to create folder'
        }), 500
    
    return jsonify({
        'success': True,
        'data': folder
    }), 201


@folders_bp.route('/<folder_id>', methods=['PUT'])
def update_folder(folder_id):
    """Update a folder."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        }), 400
    
    folder = get_folder_repo().update(
        id=folder_id,
        name=data.get('name'),
        parent_id=data.get('parent_id'),
        color=data.get('color'),
        icon=data.get('icon')
    )
    
    if not folder:
        return jsonify({
            'success': False,
            'error': 'Folder not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': folder
    })


@folders_bp.route('/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder."""
    success = get_folder_repo().delete(folder_id)
    
    if not success:
        return jsonify({
            'success': False,
            'error': 'Folder not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Folder deleted'
    })


# =============================================================================
# TAG ENDPOINTS
# =============================================================================

@tags_bp.route('', methods=['GET'])
def list_tags():
    """List all tags."""
    tags = get_tag_repo().get_all()
    
    return jsonify({
        'success': True,
        'data': tags,
        'count': len(tags)
    })


@tags_bp.route('/<tag_id>', methods=['GET'])
def get_tag(tag_id):
    """Get a single tag by ID."""
    tag = get_tag_repo().get_by_id(tag_id)
    
    if not tag:
        return jsonify({
            'success': False,
            'error': 'Tag not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': tag
    })


@tags_bp.route('', methods=['POST'])
def create_tag():
    """Create a new tag."""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({
            'success': False,
            'error': 'Name is required'
        }), 400
    
    tag = get_tag_repo().create(
        name=data['name'],
        color=data.get('color', '#6B7280')
    )
    
    if not tag:
        return jsonify({
            'success': False,
            'error': 'Failed to create tag'
        }), 500
    
    return jsonify({
        'success': True,
        'data': tag
    }), 201


@tags_bp.route('/<tag_id>', methods=['PUT'])
def update_tag(tag_id):
    """Update a tag."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        }), 400
    
    tag = get_tag_repo().update(
        id=tag_id,
        name=data.get('name'),
        color=data.get('color')
    )
    
    if not tag:
        return jsonify({
            'success': False,
            'error': 'Tag not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': tag
    })


@tags_bp.route('/<tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete a tag."""
    success = get_tag_repo().delete(tag_id)
    
    if not success:
        return jsonify({
            'success': False,
            'error': 'Tag not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Tag deleted'
    })


# =============================================================================
# PACKAGE ENDPOINTS
# =============================================================================

@packages_bp.route('', methods=['GET'])
def list_packages():
    """List all packages."""
    packages = get_package_repo().get_all()
    
    return jsonify({
        'success': True,
        'data': packages,
        'count': len(packages)
    })


@packages_bp.route('/enabled', methods=['GET'])
def list_enabled_packages():
    """List enabled package IDs."""
    enabled = get_package_repo().get_enabled()
    
    return jsonify({
        'success': True,
        'data': enabled
    })


@packages_bp.route('/<package_id>/enable', methods=['PUT'])
def enable_package(package_id):
    """Enable a package."""
    package = get_package_repo().set_enabled(package_id, True)
    
    if not package:
        return jsonify({
            'success': False,
            'error': 'Package not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': package
    })


@packages_bp.route('/<package_id>/disable', methods=['PUT'])
def disable_package(package_id):
    """Disable a package."""
    package = get_package_repo().set_enabled(package_id, False)
    
    if not package:
        return jsonify({
            'success': False,
            'error': 'Package not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': package
    })


# =============================================================================
# MIGRATION ENDPOINTS
# =============================================================================

@workflows_bp.route('/migrate', methods=['POST'])
def migrate_jobs():
    """Migrate all old job definitions to new workflow format."""
    from ..services.job_migration import JobMigrationService
    
    migration_service = JobMigrationService(get_db())
    result = migration_service.migrate_all_jobs()
    
    return jsonify({
        'success': 'error' not in result,
        'data': result
    })


@workflows_bp.route('/migrate/preview', methods=['POST'])
def preview_migration():
    """Preview migration of a single job definition."""
    from ..services.job_migration import JobMigrationService
    
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'No job definition provided'
        }), 400
    
    migration_service = JobMigrationService()
    workflow = migration_service.migrate_job(data)
    
    return jsonify({
        'success': True,
        'data': workflow
    })
