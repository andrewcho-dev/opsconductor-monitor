"""
PRTG Integration API Blueprint

Provides endpoints for:
- Receiving real-time alerts via webhook from PRTG
- Managing PRTG connection settings
- Syncing PRTG devices to NetBox
- Querying PRTG sensors and data
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import logging

from backend.database import DatabaseConnection
from backend.services.prtg_service import PRTGService
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

prtg_bp = Blueprint('prtg', __name__, url_prefix='/api/prtg')


# ============================================================================
# WEBHOOK ENDPOINT - Receives real-time alerts from PRTG
# ============================================================================

@prtg_bp.route('/webhook', methods=['POST'])
def receive_webhook():
    """
    Receive real-time alert notifications from PRTG.
    
    PRTG sends POST requests when sensor states change.
    This endpoint processes the alert and stores it in the database.
    """
    try:
        # PRTG can send data as form data or JSON
        if request.is_json:
            data = request.get_json()
        else:
            # Handle form-encoded data from PRTG
            data = request.form.to_dict()
        
        logger.info(f"Received PRTG webhook: {json.dumps(data, default=str)}")
        
        # Extract alert information from PRTG payload
        alert = _parse_prtg_alert(data)
        
        # Store the alert
        alert_id = _store_prtg_alert(alert)
        
        # Trigger any configured notifications
        _process_alert_notifications(alert)
        
        return jsonify({
            'success': True,
            'message': 'Alert received',
            'alert_id': alert_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing PRTG webhook: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Test endpoint to verify webhook connectivity."""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        logger.info(f"PRTG webhook test received: {json.dumps(data, default=str)}")
        
        return jsonify({
            'success': True,
            'message': 'Webhook test successful',
            'received_data': data,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in webhook test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================

@prtg_bp.route('/alerts', methods=['GET'])

def get_alerts():
    """Get PRTG alerts stored in OpsConductor."""
    try:
        db = DatabaseConnection()
        
        # Query parameters
        status = request.args.get('status')  # active, acknowledged, resolved
        severity = request.args.get('severity')  # down, warning, unusual
        device = request.args.get('device')
        sensor = request.args.get('sensor')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = """
            SELECT * FROM prtg_alerts
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND status = %s"
            params.append(status)
        if severity:
            query += " AND severity = %s"
            params.append(severity)
        if device:
            query += " AND device_name ILIKE %s"
            params.append(f"%{device}%")
        if sensor:
            query += " AND sensor_name ILIKE %s"
            params.append(f"%{sensor}%")
            
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with db.cursor() as cur:
            cur.execute(query, params)
            alerts = cur.fetchall()
            
            # Get total count
            count_query = "SELECT COUNT(*) FROM prtg_alerts WHERE 1=1"
            if status:
                count_query += f" AND status = '{status}'"
            cur.execute(count_query)
            total = cur.fetchone()['count']
        
        return jsonify({
            'success': True,
            'data': {
                'alerts': alerts,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching PRTG alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])

def acknowledge_alert(alert_id):
    """Acknowledge a PRTG alert."""
    try:
        db = DatabaseConnection()
        data = request.get_json() or {}
        
        with db.cursor() as cur:
            cur.execute("""
                UPDATE prtg_alerts 
                SET status = 'acknowledged',
                    acknowledged_at = %s,
                    acknowledged_by = %s,
                    notes = COALESCE(notes, '') || %s
                WHERE id = %s
                RETURNING *
            """, (
                datetime.utcnow(),
                data.get('user', 'system'),
                f"\n[Acknowledged] {data.get('notes', '')}",
                alert_id
            ))
            alert = cur.fetchone()
            db.connection.commit()
        
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
            
        return jsonify({
            'success': True,
            'data': alert
        })
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])

def resolve_alert(alert_id):
    """Mark a PRTG alert as resolved."""
    try:
        db = DatabaseConnection()
        data = request.get_json() or {}
        
        with db.cursor() as cur:
            cur.execute("""
                UPDATE prtg_alerts 
                SET status = 'resolved',
                    resolved_at = %s,
                    notes = COALESCE(notes, '') || %s
                WHERE id = %s
                RETURNING *
            """, (
                datetime.utcnow(),
                f"\n[Resolved] {data.get('notes', '')}",
                alert_id
            ))
            alert = cur.fetchone()
            db.connection.commit()
        
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
            
        return jsonify({
            'success': True,
            'data': alert
        })
        
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# PRTG CONNECTION & SYNC ENDPOINTS
# ============================================================================

@prtg_bp.route('/status', methods=['GET'])

def get_status():
    """Get PRTG connection status and system info."""
    try:
        service = PRTGService()
        status = service.get_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        # Return success with disconnected status instead of 500 error
        # This allows the UI to show "not configured" or "disconnected" gracefully
        logger.warning(f"PRTG status check: {e}")
        return jsonify({
            'success': True,
            'data': {
                'connected': False,
                'configured': False,
                'error': str(e)
            }
        })


@prtg_bp.route('/devices', methods=['GET'])

def get_devices():
    """Get all devices from PRTG."""
    try:
        service = PRTGService()
        
        # Query parameters
        group = request.args.get('group')
        status = request.args.get('status')
        search = request.args.get('search')
        
        devices = service.get_devices(
            group=group,
            status=status,
            search=search
        )
        
        return jsonify({
            'success': True,
            'data': {
                'devices': devices,
                'count': len(devices)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching PRTG devices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/sensors', methods=['GET'])

def get_sensors():
    """Get sensors from PRTG."""
    try:
        service = PRTGService()
        
        # Query parameters
        device_id = request.args.get('device_id', type=int)
        status = request.args.get('status')  # up, down, warning, paused
        sensor_type = request.args.get('type')
        
        sensors = service.get_sensors(
            device_id=device_id,
            status=status,
            sensor_type=sensor_type
        )
        
        return jsonify({
            'success': True,
            'data': {
                'sensors': sensors,
                'count': len(sensors)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching PRTG sensors: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/sensors/<int:sensor_id>', methods=['GET'])

def get_sensor_details(sensor_id):
    """Get detailed information for a specific sensor."""
    try:
        service = PRTGService()
        sensor = service.get_sensor_details(sensor_id)
        
        return jsonify({
            'success': True,
            'data': sensor
        })
        
    except Exception as e:
        logger.error(f"Error fetching sensor details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/groups', methods=['GET'])

def get_groups():
    """Get device groups from PRTG."""
    try:
        service = PRTGService()
        groups = service.get_groups()
        
        return jsonify({
            'success': True,
            'data': {
                'groups': groups,
                'count': len(groups)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching PRTG groups: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# NETBOX SYNC ENDPOINTS
# ============================================================================

@prtg_bp.route('/sync/netbox', methods=['POST'])

def sync_to_netbox():
    """Sync PRTG devices to NetBox."""
    try:
        service = PRTGService()
        data = request.get_json() or {}
        
        # Options for sync
        options = {
            'dry_run': data.get('dry_run', False),
            'device_ids': data.get('device_ids'),  # Specific devices, or all if None
            'default_site': data.get('default_site'),
            'default_role': data.get('default_role'),
            'update_existing': data.get('update_existing', False),
            'create_missing': data.get('create_missing', True)
        }
        
        result = service.sync_to_netbox(**options)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error syncing to NetBox: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/sync/preview', methods=['GET'])

def preview_sync():
    """Preview what would be synced to NetBox without making changes."""
    try:
        service = PRTGService()
        
        preview = service.preview_netbox_sync()
        
        return jsonify({
            'success': True,
            'data': preview
        })
        
    except Exception as e:
        logger.error(f"Error previewing sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@prtg_bp.route('/settings', methods=['GET'])

def get_settings():
    """Get PRTG integration settings."""
    try:
        db = DatabaseConnection()
        
        with db.cursor() as cur:
            cur.execute("""
                SELECT key, value FROM system_settings 
                WHERE key LIKE 'prtg_%'
            """)
            rows = cur.fetchall()
        
        settings = {row['key'].replace('prtg_', ''): row['value'] for row in rows}
        
        # Don't expose the API token
        if 'api_token' in settings:
            settings['api_token'] = '********' if settings['api_token'] else None
        
        return jsonify({
            'success': True,
            'data': settings
        })
        
    except Exception as e:
        logger.error(f"Error fetching PRTG settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/settings', methods=['PUT'])

def update_settings():
    """Update PRTG integration settings."""
    try:
        db = DatabaseConnection()
        data = request.get_json()
        
        allowed_settings = ['url', 'api_token', 'username', 'passhash', 
                          'verify_ssl', 'sync_interval', 'enabled']
        
        with db.cursor() as cur:
            for key, value in data.items():
                if key in allowed_settings:
                    cur.execute("""
                        INSERT INTO system_settings (key, value, updated_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = %s
                    """, (f'prtg_{key}', str(value), datetime.utcnow(), str(value), datetime.utcnow()))
        
        return jsonify({
            'success': True,
            'message': 'Settings updated'
        })
        
    except Exception as e:
        logger.error(f"Error updating PRTG settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@prtg_bp.route('/test-connection', methods=['POST'])

def test_connection():
    """Test PRTG connection with provided or saved credentials."""
    try:
        data = request.get_json() or {}
        
        service = PRTGService(
            url=data.get('url'),
            api_token=data.get('api_token'),
            username=data.get('username'),
            passhash=data.get('passhash')
        )
        
        result = service.test_connection()
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error testing PRTG connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _parse_prtg_alert(data):
    """Parse PRTG webhook data into standardized alert format."""
    
    # PRTG sends various fields depending on notification template
    # Common fields from PRTG HTTP notification
    alert = {
        'prtg_object_id': data.get('sensorid') or data.get('objectid') or data.get('id'),
        'device_id': data.get('deviceid'),
        'device_name': data.get('device') or data.get('devicename'),
        'sensor_id': data.get('sensorid'),
        'sensor_name': data.get('sensor') or data.get('sensorname') or data.get('name'),
        'status': data.get('status') or data.get('laststatus'),
        'status_raw': data.get('statusid') or data.get('laststatusraw'),
        'message': data.get('message') or data.get('lastmessage') or data.get('down'),
        'datetime': data.get('datetime') or data.get('lastcheck'),
        'duration': data.get('duration') or data.get('downtimesince'),
        'probe': data.get('probe') or data.get('probename'),
        'group': data.get('group') or data.get('groupname'),
        'priority': data.get('priority'),
        'tags': data.get('tags'),
        'host': data.get('host') or data.get('deviceip'),
        'last_value': data.get('lastvalue'),
        'raw_data': data
    }
    
    # Determine severity from status
    status_lower = (alert['status'] or '').lower()
    if 'down' in status_lower:
        alert['severity'] = 'down'
    elif 'warning' in status_lower:
        alert['severity'] = 'warning'
    elif 'unusual' in status_lower:
        alert['severity'] = 'unusual'
    elif 'up' in status_lower:
        alert['severity'] = 'up'
    else:
        alert['severity'] = 'unknown'
    
    return alert


def _store_prtg_alert(alert):
    """Store PRTG alert in database."""
    db = DatabaseConnection()
    
    with db.cursor() as cur:
        # Check if this is an update to existing alert (same sensor, still active)
        cur.execute("""
            SELECT id FROM prtg_alerts 
            WHERE sensor_id = %s AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        """, (alert['sensor_id'],))
        existing = cur.fetchone()
        
        if existing and alert['severity'] == 'up':
            # Sensor recovered - resolve the alert
            cur.execute("""
                UPDATE prtg_alerts 
                SET status = 'resolved',
                    resolved_at = %s,
                    last_message = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING id
            """, (
                datetime.utcnow(),
                alert['message'],
                datetime.utcnow(),
                existing['id']
            ))
            alert_id = existing['id']
        elif existing and alert['severity'] != 'up':
            # Update existing alert
            cur.execute("""
                UPDATE prtg_alerts 
                SET last_message = %s,
                    severity = %s,
                    duration = %s,
                    last_value = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING id
            """, (
                alert['message'],
                alert['severity'],
                alert['duration'],
                alert['last_value'],
                datetime.utcnow(),
                existing['id']
            ))
            alert_id = existing['id']
        else:
            # Create new alert
            cur.execute("""
                INSERT INTO prtg_alerts (
                    prtg_object_id, device_id, device_name, sensor_id, sensor_name,
                    status, severity, message, last_message, duration, probe, 
                    device_group, priority, tags, host, last_value, raw_data,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                alert['prtg_object_id'],
                alert['device_id'],
                alert['device_name'],
                alert['sensor_id'],
                alert['sensor_name'],
                alert['severity'],
                alert['message'],
                alert['message'],
                alert['duration'],
                alert['probe'],
                alert['group'],
                alert['priority'],
                alert['tags'],
                alert['host'],
                alert['last_value'],
                json.dumps(alert['raw_data']),
                datetime.utcnow(),
                datetime.utcnow()
            ))
            alert_id = cur.fetchone()['id']
        
        db.connection.commit()
    
    return alert_id


def _process_alert_notifications(alert):
    """Process notifications for PRTG alert."""
    try:
        # Only notify for down/warning alerts, not recoveries (optional)
        if alert['severity'] in ['down', 'warning', 'unusual']:
            notification_service = NotificationService()
            
            # Format notification message
            subject = f"PRTG Alert: {alert['device_name']} - {alert['sensor_name']}"
            message = f"""
PRTG Alert Received

Device: {alert['device_name']}
Sensor: {alert['sensor_name']}
Status: {alert['status']}
Message: {alert['message']}
Host: {alert['host']}
Group: {alert['group']}
Duration: {alert['duration']}
            """.strip()
            
            # Send to configured notification channels
            notification_service.send_alert(
                subject=subject,
                message=message,
                severity=alert['severity'],
                source='prtg',
                data=alert
            )
            
    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")
