"""
System Logs API Blueprint.

Routes for querying and managing system logs.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..services.logging_service import logging_service, get_logger, LogSource
from ..middleware.permissions import require_permission, require_auth, Permissions

logs_bp = Blueprint('logs', __name__, url_prefix='/api/logs')
logger = get_logger(__name__, LogSource.API)


@logs_bp.route('', methods=['GET'])
@require_permission(Permissions.SYSTEM_AUDIT_VIEW)
def get_logs():
    """
    Query system logs with filters.
    
    Query Parameters:
        source: Filter by source (api, scheduler, worker, ssh, snmp, etc.)
        level: Filter by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        category: Filter by category
        search: Search in message text
        start_time: ISO timestamp for start of range
        end_time: ISO timestamp for end of range
        job_id: Filter by job ID
        workflow_id: Filter by workflow ID
        execution_id: Filter by execution ID
        device_ip: Filter by device IP
        limit: Max results (default 100, max 1000)
        offset: Pagination offset
    
    Returns:
        List of log entries with pagination info
    """
    try:
        # Parse query parameters
        source = request.args.get('source')
        level = request.args.get('level')
        category = request.args.get('category')
        search = request.args.get('search')
        job_id = request.args.get('job_id')
        workflow_id = request.args.get('workflow_id')
        execution_id = request.args.get('execution_id')
        device_ip = request.args.get('device_ip')
        
        # Parse timestamps
        start_time = None
        end_time = None
        if request.args.get('start_time'):
            try:
                start_time = datetime.fromisoformat(request.args.get('start_time').replace('Z', '+00:00'))
            except:
                pass
        if request.args.get('end_time'):
            try:
                end_time = datetime.fromisoformat(request.args.get('end_time').replace('Z', '+00:00'))
            except:
                pass
        
        # Parse pagination
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        
        # Query logs
        result = logging_service.query_logs(
            source=source,
            level=level,
            category=category,
            search=search,
            start_time=start_time,
            end_time=end_time,
            job_id=job_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            device_ip=device_ip,
            limit=limit,
            offset=offset,
        )
        
        if 'error' in result and result['error']:
            return jsonify(error_response('LOG_QUERY_ERROR', result['error'])), 500
        
        return jsonify(success_response(result))
        
    except Exception as e:
        logger.exception("Failed to query logs")
        return jsonify(error_response('LOG_QUERY_ERROR', str(e))), 500


@logs_bp.route('/stats', methods=['GET'])
@require_permission(Permissions.SYSTEM_AUDIT_VIEW)
def get_log_stats():
    """
    Get log statistics for the dashboard.
    
    Query Parameters:
        hours: Number of hours to look back (default 24)
    
    Returns:
        Statistics including counts by level, source, and recent errors
    """
    try:
        hours = int(request.args.get('hours', 24))
        hours = min(hours, 168)  # Max 1 week
        
        stats = logging_service.get_log_stats(hours=hours)
        
        if 'error' in stats:
            return jsonify(error_response('STATS_ERROR', stats['error'])), 500
        
        return jsonify(success_response(stats))
        
    except Exception as e:
        logger.exception("Failed to get log stats")
        return jsonify(error_response('STATS_ERROR', str(e))), 500


@logs_bp.route('/sources', methods=['GET'])
@require_auth
def get_log_sources():
    """Get available log sources."""
    sources = [
        {'id': 'api', 'name': 'API', 'description': 'HTTP API requests and responses'},
        {'id': 'scheduler', 'name': 'Scheduler', 'description': 'Job scheduling events'},
        {'id': 'worker', 'name': 'Worker', 'description': 'Background task execution'},
        {'id': 'ssh', 'name': 'SSH', 'description': 'SSH connection and command execution'},
        {'id': 'snmp', 'name': 'SNMP', 'description': 'SNMP polling and queries'},
        {'id': 'ping', 'name': 'Ping', 'description': 'Network ping operations'},
        {'id': 'database', 'name': 'Database', 'description': 'Database operations'},
        {'id': 'workflow', 'name': 'Workflow', 'description': 'Workflow execution'},
        {'id': 'notification', 'name': 'Notification', 'description': 'Notification delivery'},
        {'id': 'system', 'name': 'System', 'description': 'System events and startup'},
    ]
    return jsonify(success_response({'sources': sources}))


@logs_bp.route('/levels', methods=['GET'])
@require_auth
def get_log_levels():
    """Get available log levels."""
    levels = [
        {'id': 'DEBUG', 'name': 'Debug', 'color': 'gray'},
        {'id': 'INFO', 'name': 'Info', 'color': 'blue'},
        {'id': 'WARNING', 'name': 'Warning', 'color': 'yellow'},
        {'id': 'ERROR', 'name': 'Error', 'color': 'red'},
        {'id': 'CRITICAL', 'name': 'Critical', 'color': 'purple'},
    ]
    return jsonify(success_response({'levels': levels}))


@logs_bp.route('/cleanup', methods=['POST'])
@require_permission(Permissions.SYSTEM_SETTINGS_EDIT)
def cleanup_logs():
    """
    Clean up old logs based on retention policy.
    
    Body Parameters:
        retention_days: Number of days to retain (default 30)
    
    Returns:
        Number of deleted log entries
    """
    try:
        data = request.get_json() or {}
        retention_days = int(data.get('retention_days', 30))
        retention_days = max(1, min(retention_days, 365))  # 1-365 days
        
        deleted = logging_service.cleanup_old_logs(retention_days)
        
        logger.info(
            f"Log cleanup completed: {deleted} entries deleted",
            category='maintenance',
            details={'retention_days': retention_days, 'deleted_count': deleted}
        )
        
        return jsonify(success_response({
            'deleted_count': deleted,
            'retention_days': retention_days,
        }))
        
    except Exception as e:
        logger.exception("Failed to cleanup logs")
        return jsonify(error_response('CLEANUP_ERROR', str(e))), 500


@logs_bp.route('/export', methods=['GET'])
def export_logs():
    """
    Export logs as JSON.
    
    Uses same query parameters as GET /api/logs but returns
    all matching logs (up to 10000) as a downloadable file.
    """
    try:
        # Parse query parameters (same as get_logs)
        source = request.args.get('source')
        level = request.args.get('level')
        search = request.args.get('search')
        
        start_time = None
        end_time = None
        if request.args.get('start_time'):
            try:
                start_time = datetime.fromisoformat(request.args.get('start_time').replace('Z', '+00:00'))
            except:
                pass
        if request.args.get('end_time'):
            try:
                end_time = datetime.fromisoformat(request.args.get('end_time').replace('Z', '+00:00'))
            except:
                pass
        
        # Query with higher limit for export
        result = logging_service.query_logs(
            source=source,
            level=level,
            search=search,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
            offset=0,
        )
        
        if 'error' in result and result['error']:
            return jsonify(error_response('EXPORT_ERROR', result['error'])), 500
        
        # Return as downloadable JSON
        from flask import Response
        import json
        
        export_data = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_count': result['total'],
            'logs': result['logs'],
        }
        
        response = Response(
            json.dumps(export_data, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=logs_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
        return response
        
    except Exception as e:
        logger.exception("Failed to export logs")
        return jsonify(error_response('EXPORT_ERROR', str(e))), 500
