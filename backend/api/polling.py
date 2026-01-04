"""
Polling Management API Blueprint.

Routes for managing SNMP polling configurations, schedules, and execution history.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from ..utils.responses import success_response, error_response
from ..database import DatabaseConnection

logger = logging.getLogger(__name__)

polling_bp = Blueprint('polling', __name__, url_prefix='/api/polling')


# ============================================================================
# POLLING CONFIGURATIONS
# ============================================================================

@polling_bp.route('/configs', methods=['GET'])
def list_configs():
    """
    List all polling configurations.
    
    Query params:
        enabled: Filter by enabled status (true/false)
        poll_type: Filter by poll type
        tag: Filter by tag
    """
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            query = """
                SELECT 
                    id, name, description, poll_type, enabled,
                    interval_seconds, cron_expression,
                    target_type, target_device_ip, target_site_name,
                    target_role, target_manufacturer,
                    snmp_community, snmp_version, snmp_timeout, snmp_retries,
                    max_concurrent, batch_size, tags,
                    created_at, updated_at,
                    last_run_at, last_run_status, last_run_duration_ms,
                    last_run_devices_polled, last_run_devices_success
                FROM polling_configs
                WHERE 1=1
            """
            params = []
            
            if request.args.get('enabled'):
                query += " AND enabled = %s"
                params.append(request.args.get('enabled').lower() == 'true')
            
            if request.args.get('poll_type'):
                query += " AND poll_type = %s"
                params.append(request.args.get('poll_type'))
            
            if request.args.get('tag'):
                query += " AND %s = ANY(tags)"
                params.append(request.args.get('tag'))
            
            query += " ORDER BY name"
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        configs = []
        for row in rows:
            config = dict(row)
            config['created_at'] = config['created_at'].isoformat() if config.get('created_at') else None
            config['updated_at'] = config['updated_at'].isoformat() if config.get('updated_at') else None
            config['last_run_at'] = config['last_run_at'].isoformat() if config.get('last_run_at') else None
            config['target_device_ip'] = str(config['target_device_ip']) if config.get('target_device_ip') else None
            configs.append(config)
        
        return success_response({
            'configs': configs,
            'count': len(configs)
        })
    except Exception as e:
        logger.error(f"Failed to list polling configs: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/configs/<int:config_id>', methods=['GET'])
def get_config(config_id):
    """Get a single polling configuration by ID."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM polling_configs WHERE id = %s
            """, (config_id,))
            row = cursor.fetchone()
        
        if not row:
            return error_response(f"Config {config_id} not found", code='NOT_FOUND', status=404)
        
        config = dict(row)
        config['created_at'] = config['created_at'].isoformat() if config.get('created_at') else None
        config['updated_at'] = config['updated_at'].isoformat() if config.get('updated_at') else None
        config['last_run_at'] = config['last_run_at'].isoformat() if config.get('last_run_at') else None
        config['target_device_ip'] = str(config['target_device_ip']) if config.get('target_device_ip') else None
        
        return success_response(config)
    except Exception as e:
        logger.error(f"Failed to get polling config {config_id}: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/configs', methods=['POST'])
def create_config():
    """
    Create a new polling configuration.
    
    Request body:
        {
            "name": "My Polling Config",
            "description": "Description",
            "poll_type": "snmp_ciena_full",
            "target_type": "manufacturer",
            "target_manufacturer": "Ciena",
            "interval_seconds": 300,
            "snmp_community": "public",
            "enabled": true,
            "tags": ["ciena", "optical"]
        }
    """
    try:
        data = request.get_json() or {}
        
        required = ['name', 'poll_type', 'target_type']
        for field in required:
            if not data.get(field):
                return error_response(f"'{field}' is required", code='VALIDATION_ERROR', status=400)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO polling_configs (
                    name, description, poll_type, enabled,
                    interval_seconds, cron_expression,
                    target_type, target_device_ip, target_site_name,
                    target_role, target_manufacturer, target_custom_filter,
                    snmp_community, snmp_version, snmp_port, snmp_timeout, snmp_retries,
                    max_concurrent, batch_size, tags, created_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                data['name'],
                data.get('description'),
                data['poll_type'],
                data.get('enabled', True),
                data.get('interval_seconds', 300),
                data.get('cron_expression'),
                data['target_type'],
                data.get('target_device_ip'),
                data.get('target_site_name'),
                data.get('target_role'),
                data.get('target_manufacturer'),
                data.get('target_custom_filter'),
                data.get('snmp_community', 'public'),
                data.get('snmp_version', '2c'),
                data.get('snmp_port', 161),
                data.get('snmp_timeout', 5),
                data.get('snmp_retries', 2),
                data.get('max_concurrent', 50),
                data.get('batch_size', 25),
                data.get('tags', []),
                data.get('created_by')
            ))
            config_id = cursor.fetchone()['id']
            db.get_connection().commit()
        
        return success_response({'id': config_id}, message=f"Polling config '{data['name']}' created", status=201)
    except Exception as e:
        logger.error(f"Failed to create polling config: {e}")
        if 'unique constraint' in str(e).lower():
            return error_response(f"Config with name '{data.get('name')}' already exists", code='DUPLICATE', status=409)
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/configs/<int:config_id>', methods=['PUT'])
def update_config(config_id):
    """Update a polling configuration."""
    try:
        data = request.get_json() or {}
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            # Build dynamic update query
            updates = []
            params = []
            
            updatable_fields = [
                'name', 'description', 'poll_type', 'enabled',
                'interval_seconds', 'cron_expression',
                'target_type', 'target_device_ip', 'target_site_name',
                'target_role', 'target_manufacturer', 'target_custom_filter',
                'snmp_community', 'snmp_version', 'snmp_port', 'snmp_timeout', 'snmp_retries',
                'max_concurrent', 'batch_size', 'tags'
            ]
            
            for field in updatable_fields:
                if field in data:
                    updates.append(f"{field} = %s")
                    params.append(data[field])
            
            if not updates:
                return error_response("No fields to update", code='VALIDATION_ERROR', status=400)
            
            updates.append("updated_at = NOW()")
            params.append(config_id)
            
            cursor.execute(f"""
                UPDATE polling_configs
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id
            """, params)
            
            if cursor.rowcount == 0:
                return error_response(f"Config {config_id} not found", code='NOT_FOUND', status=404)
            
            db.get_connection().commit()
        
        return success_response({'id': config_id}, message="Config updated")
    except Exception as e:
        logger.error(f"Failed to update polling config {config_id}: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/configs/<int:config_id>', methods=['DELETE'])
def delete_config(config_id):
    """Delete a polling configuration."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM polling_configs WHERE id = %s RETURNING name", (config_id,))
            row = cursor.fetchone()
            
            if not row:
                return error_response(f"Config {config_id} not found", code='NOT_FOUND', status=404)
            
            db.get_connection().commit()
        
        return success_response({'id': config_id}, message=f"Config '{row['name']}' deleted")
    except Exception as e:
        logger.error(f"Failed to delete polling config {config_id}: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/configs/<int:config_id>/toggle', methods=['POST'])
def toggle_config(config_id):
    """Toggle a polling configuration's enabled status."""
    try:
        data = request.get_json(silent=True) or {}
        enabled = data.get('enabled')
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            if enabled is None:
                # Toggle current state
                cursor.execute("""
                    UPDATE polling_configs
                    SET enabled = NOT enabled, updated_at = NOW()
                    WHERE id = %s
                    RETURNING enabled
                """, (config_id,))
            else:
                cursor.execute("""
                    UPDATE polling_configs
                    SET enabled = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING enabled
                """, (enabled, config_id))
            
            row = cursor.fetchone()
            if not row:
                return error_response(f"Config {config_id} not found", code='NOT_FOUND', status=404)
            
            db.get_connection().commit()
        
        status = "enabled" if row['enabled'] else "disabled"
        return success_response({'enabled': row['enabled']}, message=f"Config {status}")
    except Exception as e:
        logger.error(f"Failed to toggle polling config {config_id}: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


# ============================================================================
# MANUAL POLLING EXECUTION
# ============================================================================

@polling_bp.route('/configs/<int:config_id>/run', methods=['POST'])
def run_config(config_id):
    """
    Manually trigger a polling configuration to run now.
    """
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM polling_configs WHERE id = %s", (config_id,))
            config = cursor.fetchone()
        
        if not config:
            return error_response(f"Config {config_id} not found", code='NOT_FOUND', status=404)
        
        # Dispatch to Celery based on poll_type
        poll_type = config['poll_type']
        
        from ..tasks.polling_tasks import (
            poll_availability, poll_interfaces, poll_optical_power
        )
        
        task_map = {
            'snmp_availability': poll_availability,
            'snmp_interfaces': poll_interfaces,
            'snmp_optical': poll_optical_power,
            'snmp_ciena_optical': poll_optical_power,
        }
        
        task_func = task_map.get(poll_type)
        
        if task_func:
            # Build device filter from config
            device_filter = {}
            if config['target_site_name']:
                device_filter['site'] = config['target_site_name']
            if config['target_role']:
                device_filter['role'] = config['target_role']
            
            # Dispatch async task
            result = task_func.delay(device_filter if device_filter else None)
            
            return success_response({
                'task_id': result.id,
                'config_id': config_id,
                'poll_type': poll_type
            }, message=f"Polling task dispatched")
        else:
            # For Ciena full poll, use the SNMP service directly
            if poll_type == 'snmp_ciena_full':
                from ..services.ciena_snmp_service import poll_switch
                
                # Get target devices
                with db.cursor() as cursor:
                    query = """
                        SELECT device_ip FROM netbox_device_cache
                        WHERE device_ip IS NOT NULL
                    """
                    if config['target_manufacturer']:
                        query += " AND manufacturer ILIKE %s"
                        cursor.execute(query, (f"%{config['target_manufacturer']}%",))
                    else:
                        cursor.execute(query)
                    rows = cursor.fetchall()
                
                if not rows:
                    return error_response("No target devices found", code='NO_TARGETS', status=400)
                
                # Poll first device as a test (full batch would be async)
                test_ip = str(rows[0]['device_ip'])
                result = poll_switch(test_ip, config['snmp_community'] or 'public')
                
                return success_response({
                    'config_id': config_id,
                    'poll_type': poll_type,
                    'test_result': result,
                    'total_targets': len(rows)
                }, message=f"Test poll completed, {len(rows)} devices targeted")
            
            return error_response(f"Unknown poll type: {poll_type}", code='INVALID_TYPE', status=400)
    
    except Exception as e:
        logger.error(f"Failed to run polling config {config_id}: {e}")
        return error_response(str(e), code='EXECUTION_ERROR', status=500)


# ============================================================================
# EXECUTION HISTORY
# ============================================================================

@polling_bp.route('/executions', methods=['GET'])
def list_executions():
    """
    List polling execution history.
    
    Query params:
        config_id: Filter by config ID
        status: Filter by status
        limit: Max results (default 50)
    """
    try:
        limit = min(int(request.args.get('limit', 50)), 500)
        
        db = DatabaseConnection()
        with db.cursor() as cursor:
            query = """
                SELECT 
                    pe.id, pe.config_id, pe.config_name,
                    pe.started_at, pe.completed_at, pe.duration_ms,
                    pe.status, pe.devices_targeted, pe.devices_polled,
                    pe.devices_success, pe.devices_failed, pe.records_collected,
                    pe.error_message, pe.triggered_by
                FROM polling_executions pe
                WHERE 1=1
            """
            params = []
            
            if request.args.get('config_id'):
                query += " AND pe.config_id = %s"
                params.append(int(request.args.get('config_id')))
            
            if request.args.get('status'):
                query += " AND pe.status = %s"
                params.append(request.args.get('status'))
            
            query += " ORDER BY pe.started_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        executions = []
        for row in rows:
            exec_data = dict(row)
            exec_data['started_at'] = exec_data['started_at'].isoformat() if exec_data.get('started_at') else None
            exec_data['completed_at'] = exec_data['completed_at'].isoformat() if exec_data.get('completed_at') else None
            executions.append(exec_data)
        
        return success_response({
            'executions': executions,
            'count': len(executions)
        })
    except Exception as e:
        logger.error(f"Failed to list polling executions: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/executions/<int:execution_id>', methods=['GET'])
def get_execution(execution_id):
    """Get details of a specific polling execution including device results."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            # Get execution
            cursor.execute("""
                SELECT * FROM polling_executions WHERE id = %s
            """, (execution_id,))
            execution = cursor.fetchone()
            
            if not execution:
                return error_response(f"Execution {execution_id} not found", code='NOT_FOUND', status=404)
            
            # Get device results
            cursor.execute("""
                SELECT device_ip, device_name, status, duration_ms, records_collected, error_message, polled_at
                FROM polling_device_results
                WHERE execution_id = %s
                ORDER BY polled_at
            """, (execution_id,))
            device_results = cursor.fetchall()
        
        exec_data = dict(execution)
        exec_data['started_at'] = exec_data['started_at'].isoformat() if exec_data.get('started_at') else None
        exec_data['completed_at'] = exec_data['completed_at'].isoformat() if exec_data.get('completed_at') else None
        exec_data['device_results'] = [
            {
                **dict(r),
                'device_ip': str(r['device_ip']),
                'polled_at': r['polled_at'].isoformat() if r.get('polled_at') else None
            }
            for r in device_results
        ]
        
        return success_response(exec_data)
    except Exception as e:
        logger.error(f"Failed to get polling execution {execution_id}: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


# ============================================================================
# POLLING STATUS & SUMMARY
# ============================================================================

@polling_bp.route('/status', methods=['GET'])
def get_status():
    """Get overall polling system status and summary."""
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            # Get config counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_configs,
                    COUNT(*) FILTER (WHERE enabled = TRUE) as enabled_configs,
                    COUNT(*) FILTER (WHERE last_run_status = 'success') as successful_last_run,
                    COUNT(*) FILTER (WHERE last_run_status = 'failed') as failed_last_run
                FROM polling_configs
            """)
            config_stats = dict(cursor.fetchone())
            
            # Get recent execution stats (last 24 hours)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_executions,
                    COUNT(*) FILTER (WHERE status = 'success') as successful,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    AVG(duration_ms) as avg_duration_ms,
                    SUM(records_collected) as total_records
                FROM polling_executions
                WHERE started_at > NOW() - INTERVAL '24 hours'
            """)
            exec_stats = dict(cursor.fetchone())
            
            # Get next scheduled runs
            cursor.execute("""
                SELECT name, poll_type, last_run_at, interval_seconds,
                    CASE 
                        WHEN last_run_at IS NULL THEN NOW()
                        ELSE last_run_at + (interval_seconds || ' seconds')::INTERVAL
                    END AS next_run_at
                FROM polling_configs
                WHERE enabled = TRUE
                ORDER BY next_run_at
                LIMIT 5
            """)
            upcoming = [
                {
                    **dict(r),
                    'last_run_at': r['last_run_at'].isoformat() if r.get('last_run_at') else None,
                    'next_run_at': r['next_run_at'].isoformat() if r.get('next_run_at') else None
                }
                for r in cursor.fetchall()
            ]
        
        return success_response({
            'configs': config_stats,
            'executions_24h': exec_stats,
            'upcoming_polls': upcoming
        })
    except Exception as e:
        logger.error(f"Failed to get polling status: {e}")
        return error_response(str(e), code='DATABASE_ERROR', status=500)


@polling_bp.route('/poll-types', methods=['GET'])
def list_poll_types():
    """List available polling types - combines built-in types with user-defined from MIB mappings."""
    # Built-in poll types (always available)
    builtin_types = [
        {
            'id': 'snmp_availability',
            'name': 'Availability Check',
            'description': 'Check SNMP reachability and basic system info',
            'default_interval': 60,
            'source': 'builtin'
        },
        {
            'id': 'snmp_interfaces',
            'name': 'Interface Statistics',
            'description': 'Collect interface traffic counters and errors',
            'default_interval': 300,
            'source': 'builtin'
        },
        {
            'id': 'snmp_optical',
            'name': 'Optical Power (Generic)',
            'description': 'Collect optical TX/RX power using standard OIDs',
            'default_interval': 300,
            'source': 'builtin'
        },
        {
            'id': 'snmp_ciena_optical',
            'name': 'Ciena Optical Power',
            'description': 'Collect optical power from Ciena switches using WWP-LEOS MIB',
            'default_interval': 300,
            'source': 'builtin'
        },
        {
            'id': 'snmp_ciena_full',
            'name': 'Ciena Full Poll',
            'description': 'Full SNMP poll of Ciena switches (optical, traffic, alarms, rings, chassis)',
            'default_interval': 300,
            'source': 'builtin'
        }
    ]
    
    # Get user-defined poll types from MIB mappings
    try:
        db = DatabaseConnection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT pt.id, pt.name, pt.display_name, pt.description, pt.target_table, pt.enabled,
                       p.vendor, p.name as profile_name
                FROM snmp_poll_types pt
                JOIN snmp_profiles p ON p.id = pt.profile_id
                WHERE pt.enabled = true
                ORDER BY p.vendor, pt.display_name
            """)
            db_types = cursor.fetchall()
            
        for row in db_types:
            builtin_types.append({
                'id': row['name'],
                'name': row['display_name'],
                'description': row['description'] or f"Custom poll type from {row['vendor']} profile",
                'default_interval': 300,
                'source': 'custom',
                'vendor': row['vendor'],
                'profile': row['profile_name'],
                'target_table': row['target_table']
            })
    except Exception as e:
        logger.warning(f"Failed to load custom poll types: {e}")
    
    return success_response({'poll_types': builtin_types})


@polling_bp.route('/target-types', methods=['GET'])
def list_target_types():
    """List available target types for polling configurations."""
    target_types = [
        {'id': 'all', 'name': 'All Devices', 'description': 'Poll all devices in the system'},
        {'id': 'device', 'name': 'Specific Device', 'description': 'Poll a single device by IP'},
        {'id': 'site', 'name': 'Site', 'description': 'Poll all devices at a specific site'},
        {'id': 'role', 'name': 'Device Role', 'description': 'Poll devices with a specific role (e.g., Backbone Switch)'},
        {'id': 'manufacturer', 'name': 'Manufacturer', 'description': 'Poll devices from a specific manufacturer'},
        {'id': 'custom_query', 'name': 'Custom Filter', 'description': 'Poll devices matching a custom filter'}
    ]
    
    return success_response({'target_types': target_types})
