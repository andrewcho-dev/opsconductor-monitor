"""
System Alerts API

Endpoints for managing system alerts, rules, and history.
"""

from flask import Blueprint, request, jsonify

from ..utils.responses import success_response, error_response
from ..utils.errors import NotFoundError, ValidationError
from ..services.alert_service import (
    AlertService, AlertEvaluator, get_alert_service,
    AlertSeverity, AlertStatus, AlertCategory
)
from ..middleware.permissions import require_permission, require_auth

alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')


def get_service():
    """Get alert service instance."""
    return get_alert_service()


@alerts_bp.route('', methods=['GET'])
@require_auth
def get_alerts():
    """
    Get active alerts.
    
    Query params:
        severity: Filter by severity (info, warning, critical)
        category: Filter by category (logs, jobs, infrastructure, custom)
        limit: Max results (default 50)
    
    Returns:
        List of active alerts
    """
    service = get_service()
    
    severity = request.args.get('severity')
    category = request.args.get('category')
    limit = request.args.get('limit', 50, type=int)
    
    alerts = service.get_active_alerts(
        severity=severity,
        category=category,
        limit=limit
    )
    
    return jsonify(success_response({
        'alerts': alerts,
        'count': len(alerts)
    }))


@alerts_bp.route('/<int:alert_id>', methods=['GET'])
@require_auth
def get_alert(alert_id):
    """Get a single alert by ID."""
    service = get_service()
    
    alert = service.get_alert_by_id(alert_id)
    if not alert:
        raise NotFoundError(f'Alert {alert_id} not found')
    
    return jsonify(success_response(alert))


@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['POST'])
@require_auth
def acknowledge_alert(alert_id):
    """
    Acknowledge an alert.
    
    Body (optional):
        acknowledged_by: User who acknowledged
    """
    service = get_service()
    
    data = request.get_json(silent=True) or {}
    acknowledged_by = data.get('acknowledged_by')
    
    success = service.acknowledge_alert(alert_id, acknowledged_by)
    if not success:
        raise NotFoundError(f'Alert {alert_id} not found or already acknowledged')
    
    return jsonify(success_response(message='Alert acknowledged'))


@alerts_bp.route('/<int:alert_id>/resolve', methods=['POST'])
@require_auth
def resolve_alert(alert_id):
    """Resolve an alert and move to history."""
    service = get_service()
    
    success = service.resolve_alert(alert_id)
    if not success:
        raise NotFoundError(f'Alert {alert_id} not found')
    
    return jsonify(success_response(message='Alert resolved'))


@alerts_bp.route('/stats', methods=['GET'])
@require_auth
def get_alert_stats():
    """Get alert statistics."""
    service = get_service()
    stats = service.get_alert_stats()
    return jsonify(success_response(stats))


@alerts_bp.route('/history', methods=['GET'])
@require_auth
def get_alert_history():
    """
    Get alert history.
    
    Query params:
        days: Number of days to look back (default 7)
        limit: Max results (default 100)
    """
    service = get_service()
    
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 100, type=int)
    
    history = service.get_alert_history(days=days, limit=limit)
    
    return jsonify(success_response({
        'history': history,
        'count': len(history)
    }))


@alerts_bp.route('/rules', methods=['GET'])
@require_auth
def get_alert_rules():
    """
    Get alert rules.
    
    Query params:
        all: Include disabled rules (default false)
    """
    service = get_service()
    
    include_disabled = request.args.get('all', 'false').lower() == 'true'
    rules = service.get_alert_rules(enabled_only=not include_disabled)
    
    return jsonify(success_response({
        'rules': rules,
        'count': len(rules)
    }))


@alerts_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@require_auth
def update_alert_rule(rule_id):
    """
    Update an alert rule.
    
    Body:
        enabled: Enable/disable rule
        severity: Alert severity
        condition_config: Rule configuration
        cooldown_minutes: Cooldown period
        description: Rule description
    """
    service = get_service()
    
    data = request.get_json()
    if not data:
        raise ValidationError('Request body required')
    
    success = service.update_rule(rule_id, data)
    if not success:
        raise NotFoundError(f'Rule {rule_id} not found')
    
    return jsonify(success_response(message='Rule updated'))


@alerts_bp.route('/evaluate', methods=['POST'])
@require_auth
def evaluate_alerts():
    """
    Manually trigger alert evaluation.
    
    Evaluates all enabled rules and creates alerts as needed.
    Normally this runs automatically via background task.
    """
    evaluator = AlertEvaluator()
    results = evaluator.evaluate_all_rules()
    
    return jsonify(success_response(results))


@alerts_bp.route('/create', methods=['POST'])
def create_manual_alert():
    """
    Create a manual/custom alert.
    
    Body:
        title: Alert title (required)
        message: Alert message (required)
        severity: info, warning, critical (default warning)
        category: Alert category (default custom)
        details: Additional details (optional)
    """
    data = request.get_json()
    if not data:
        raise ValidationError('Request body required')
    
    title = data.get('title')
    message = data.get('message')
    
    if not title or not message:
        raise ValidationError('title and message are required')
    
    service = get_service()
    
    alert_key = f"manual_{title.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
    
    alert_id = service.create_alert(
        alert_key=alert_key,
        title=title,
        message=message,
        severity=data.get('severity', AlertSeverity.WARNING),
        category=data.get('category', AlertCategory.CUSTOM),
        details=data.get('details'),
    )
    
    if alert_id:
        return jsonify(success_response({
            'alert_id': alert_id
        }, message='Alert created'))
    else:
        return jsonify(error_response('DUPLICATE', 'Similar alert already exists'))


# Import datetime for manual alert creation
from datetime import datetime
