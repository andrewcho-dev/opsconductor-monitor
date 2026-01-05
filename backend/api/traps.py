"""
SNMP Trap API Blueprint.

Routes for viewing trap logs, events, and receiver status.
"""

from flask import Blueprint, request, jsonify
from database import DatabaseManager

traps_bp = Blueprint('traps', __name__, url_prefix='/api/traps')


def get_db():
    """Get database connection."""
    return DatabaseManager()


@traps_bp.route('/status', methods=['GET'])
def get_receiver_status():
    """Get SNMP trap receiver status."""
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT 
                    started_at,
                    last_trap_at,
                    traps_received,
                    traps_processed,
                    traps_errors,
                    queue_depth,
                    is_running,
                    updated_at
                FROM trap_receiver_status
                WHERE id = 1
            """)
            status = cur.fetchone()
            
            if status:
                return jsonify({
                    'success': True,
                    'data': {
                        'started_at': status['started_at'].isoformat() if status['started_at'] else None,
                        'last_trap_at': status['last_trap_at'].isoformat() if status['last_trap_at'] else None,
                        'traps_received': status['traps_received'],
                        'traps_processed': status['traps_processed'],
                        'traps_errors': status['traps_errors'],
                        'queue_depth': status['queue_depth'],
                        'is_running': status['is_running'],
                        'updated_at': status['updated_at'].isoformat() if status['updated_at'] else None,
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'data': {
                        'is_running': False,
                        'message': 'Trap receiver not initialized'
                    }
                })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traps_bp.route('/log', methods=['GET'])
def get_trap_log():
    """Get recent trap log entries."""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        source_ip = request.args.get('source_ip')
        vendor = request.args.get('vendor')
        
        db = get_db()
        with db.cursor() as cur:
            query = """
                SELECT 
                    id,
                    received_at,
                    source_ip,
                    snmp_version,
                    enterprise_oid,
                    trap_oid,
                    trap_type,
                    vendor,
                    uptime,
                    varbinds,
                    processed,
                    event_id
                FROM trap_log
                WHERE 1=1
            """
            params = []
            
            if source_ip:
                query += " AND source_ip = %s"
                params.append(source_ip)
            
            if vendor:
                query += " AND vendor = %s"
                params.append(vendor)
            
            query += " ORDER BY received_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            traps = cur.fetchall()
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM trap_log WHERE 1=1"
            count_params = []
            if source_ip:
                count_query += " AND source_ip = %s"
                count_params.append(source_ip)
            if vendor:
                count_query += " AND vendor = %s"
                count_params.append(vendor)
            
            cur.execute(count_query, count_params)
            total = cur.fetchone()['total']
            
            return jsonify({
                'success': True,
                'data': {
                    'traps': [{
                        'id': t['id'],
                        'received_at': t['received_at'].isoformat() if t['received_at'] else None,
                        'source_ip': str(t['source_ip']),
                        'snmp_version': t['snmp_version'],
                        'enterprise_oid': t['enterprise_oid'],
                        'trap_oid': t['trap_oid'],
                        'trap_type': t['trap_type'],
                        'vendor': t['vendor'],
                        'uptime': t['uptime'],
                        'varbinds': t['varbinds'],
                        'processed': t['processed'],
                        'event_id': t['event_id'],
                    } for t in traps],
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traps_bp.route('/events', methods=['GET'])
def get_trap_events():
    """Get trap events."""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        source_ip = request.args.get('source_ip')
        event_type = request.args.get('event_type')
        severity = request.args.get('severity')
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        db = get_db()
        with db.cursor() as cur:
            query = """
                SELECT 
                    id,
                    created_at,
                    source_ip,
                    device_name,
                    event_type,
                    severity,
                    object_type,
                    object_id,
                    description,
                    details,
                    alarm_id,
                    is_clear,
                    acknowledged,
                    acknowledged_at,
                    acknowledged_by
                FROM trap_events
                WHERE 1=1
            """
            params = []
            
            if source_ip:
                query += " AND source_ip = %s"
                params.append(source_ip)
            
            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)
            
            if severity:
                query += " AND severity = %s"
                params.append(severity)
            
            if active_only:
                query += " AND is_clear = FALSE"
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            events = cur.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'events': [{
                        'id': e['id'],
                        'created_at': e['created_at'].isoformat() if e['created_at'] else None,
                        'source_ip': str(e['source_ip']),
                        'device_name': e['device_name'],
                        'event_type': e['event_type'],
                        'severity': e['severity'],
                        'object_type': e['object_type'],
                        'object_id': e['object_id'],
                        'description': e['description'],
                        'details': e['details'],
                        'alarm_id': e['alarm_id'],
                        'is_clear': e['is_clear'],
                        'acknowledged': e['acknowledged'],
                        'acknowledged_at': e['acknowledged_at'].isoformat() if e['acknowledged_at'] else None,
                        'acknowledged_by': e['acknowledged_by'],
                    } for e in events],
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traps_bp.route('/events/active', methods=['GET'])
def get_active_alarms():
    """Get active alarms from traps (not cleared)."""
    try:
        source_ip = request.args.get('source_ip')
        
        db = get_db()
        with db.cursor() as cur:
            query = """
                SELECT 
                    id,
                    created_at,
                    source_ip,
                    device_name,
                    event_type,
                    severity,
                    object_type,
                    object_id,
                    description,
                    details,
                    alarm_id,
                    acknowledged,
                    acknowledged_at,
                    acknowledged_by
                FROM active_trap_alarms
                WHERE 1=1
            """
            params = []
            
            if source_ip:
                query += " AND source_ip = %s"
                params.append(source_ip)
            
            query += " ORDER BY created_at DESC"
            
            cur.execute(query, params)
            alarms = cur.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'alarms': [{
                        'id': a['id'],
                        'created_at': a['created_at'].isoformat() if a['created_at'] else None,
                        'source_ip': str(a['source_ip']),
                        'device_name': a['device_name'],
                        'event_type': a['event_type'],
                        'severity': a['severity'],
                        'object_type': a['object_type'],
                        'object_id': a['object_id'],
                        'description': a['description'],
                        'details': a['details'],
                        'alarm_id': a['alarm_id'],
                        'acknowledged': a['acknowledged'],
                    } for a in alarms],
                    'count': len(alarms),
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traps_bp.route('/events/<int:event_id>/acknowledge', methods=['POST'])
def acknowledge_event(event_id):
    """Acknowledge a trap event."""
    try:
        data = request.get_json() or {}
        acknowledged_by = data.get('acknowledged_by', 'system')
        
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                UPDATE trap_events
                SET acknowledged = TRUE,
                    acknowledged_at = NOW(),
                    acknowledged_by = %s
                WHERE id = %s
                RETURNING id
            """, (acknowledged_by, event_id))
            
            result = cur.fetchone()
            if result:
                return jsonify({
                    'success': True,
                    'message': f'Event {event_id} acknowledged'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traps_bp.route('/stats', methods=['GET'])
def get_trap_stats():
    """Get trap statistics."""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        db = get_db()
        with db.cursor() as cur:
            # Total traps by vendor
            cur.execute("""
                SELECT vendor, COUNT(*) as count
                FROM trap_log
                WHERE received_at > NOW() - INTERVAL '%s hours'
                GROUP BY vendor
                ORDER BY count DESC
            """, (hours,))
            by_vendor = cur.fetchall()
            
            # Total events by severity
            cur.execute("""
                SELECT severity, COUNT(*) as count
                FROM trap_events
                WHERE created_at > NOW() - INTERVAL '%s hours'
                GROUP BY severity
                ORDER BY count DESC
            """, (hours,))
            by_severity = cur.fetchall()
            
            # Total events by type
            cur.execute("""
                SELECT event_type, COUNT(*) as count
                FROM trap_events
                WHERE created_at > NOW() - INTERVAL '%s hours'
                GROUP BY event_type
                ORDER BY count DESC
            """, (hours,))
            by_type = cur.fetchall()
            
            # Top sources
            cur.execute("""
                SELECT source_ip, COUNT(*) as count
                FROM trap_log
                WHERE received_at > NOW() - INTERVAL '%s hours'
                GROUP BY source_ip
                ORDER BY count DESC
                LIMIT 10
            """, (hours,))
            top_sources = cur.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'hours': hours,
                    'by_vendor': [{
                        'vendor': v['vendor'] or 'unknown',
                        'count': v['count']
                    } for v in by_vendor],
                    'by_severity': [{
                        'severity': s['severity'],
                        'count': s['count']
                    } for s in by_severity],
                    'by_type': [{
                        'event_type': t['event_type'],
                        'count': t['count']
                    } for t in by_type],
                    'top_sources': [{
                        'source_ip': str(s['source_ip']),
                        'count': s['count']
                    } for s in top_sources],
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
