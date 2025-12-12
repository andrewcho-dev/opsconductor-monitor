"""
Notifications API endpoints.

Provides CRUD for notification channels and rules,
plus test and send functionality.
"""

import json
from flask import Blueprint, request, jsonify
from backend.database import get_db
from backend.utils.time import now_utc
from ..utils.responses import success_response, error_response
from ..utils.errors import NotFoundError, ValidationError

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


def get_db_connection():
    """Get database connection."""
    return get_db()


# ============================================================================
# CHANNELS
# ============================================================================

@notifications_bp.route('/channels', methods=['GET'])
def list_channels():
    """List all notification channels."""
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, channel_type, config, enabled,
                   created_at, updated_at, last_test_at, last_test_success
            FROM notification_channels
            ORDER BY name
        """)
        channels = []
        for row in cursor.fetchall():
            channel = dict(row)
            if isinstance(channel.get('config'), str):
                channel['config'] = json.loads(channel['config'])
            channels.append(channel)
    
    return jsonify(success_response({'channels': channels}))


@notifications_bp.route('/channels', methods=['POST'])
def create_channel():
    """Create a new notification channel."""
    data = request.get_json()
    
    if not data.get('name'):
        raise ValidationError('Channel name is required')
    if not data.get('channel_type'):
        raise ValidationError('Channel type is required')
    
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO notification_channels (name, channel_type, config, enabled)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            data['name'],
            data['channel_type'],
            json.dumps(data.get('config', {})),
            data.get('enabled', True)
        ))
        channel_id = cursor.fetchone()['id']
        db.get_connection().commit()
    
    return jsonify(success_response({'id': channel_id}, message='Channel created'))


@notifications_bp.route('/channels/<int:channel_id>', methods=['GET'])
def get_channel(channel_id):
    """Get a single notification channel."""
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, channel_type, config, enabled,
                   created_at, updated_at, last_test_at, last_test_success
            FROM notification_channels
            WHERE id = %s
        """, (channel_id,))
        row = cursor.fetchone()
        
        if not row:
            raise NotFoundError(f'Channel {channel_id} not found')
        
        channel = dict(row)
        if isinstance(channel.get('config'), str):
            channel['config'] = json.loads(channel['config'])
    
    return jsonify(success_response(channel))


@notifications_bp.route('/channels/<int:channel_id>', methods=['PUT'])
def update_channel(channel_id):
    """Update a notification channel."""
    data = request.get_json()
    db = get_db_connection()
    
    updates = []
    params = []
    
    if 'name' in data:
        updates.append('name = %s')
        params.append(data['name'])
    if 'channel_type' in data:
        updates.append('channel_type = %s')
        params.append(data['channel_type'])
    if 'config' in data:
        updates.append('config = %s')
        params.append(json.dumps(data['config']))
    if 'enabled' in data:
        updates.append('enabled = %s')
        params.append(data['enabled'])
    
    if not updates:
        raise ValidationError('No fields to update')
    
    updates.append('updated_at = %s')
    params.append(now_utc())
    params.append(channel_id)
    
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE notification_channels
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id
        """, params)
        
        if cursor.rowcount == 0:
            raise NotFoundError(f'Channel {channel_id} not found')
        
        db.get_connection().commit()
    
    return jsonify(success_response(message='Channel updated'))


@notifications_bp.route('/channels/<int:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """Delete a notification channel."""
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM notification_channels WHERE id = %s", (channel_id,))
        
        if cursor.rowcount == 0:
            raise NotFoundError(f'Channel {channel_id} not found')
        
        db.get_connection().commit()
    
    return jsonify(success_response(message='Channel deleted'))


@notifications_bp.route('/channels/<int:channel_id>/test', methods=['POST'])
def test_channel(channel_id):
    """Test a notification channel by sending a test message."""
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, channel_type, config
            FROM notification_channels
            WHERE id = %s
        """, (channel_id,))
        row = cursor.fetchone()
        
        if not row:
            raise NotFoundError(f'Channel {channel_id} not found')
        
        channel = dict(row)
        config = channel['config']
        if isinstance(config, str):
            config = json.loads(config)
    
    # Build Apprise URL from config
    apprise_url = build_apprise_url(channel['channel_type'], config)
    
    if not apprise_url:
        # Update test status
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE notification_channels
                SET last_test_at = %s, last_test_success = false
                WHERE id = %s
            """, (now_utc(), channel_id))
            db.get_connection().commit()
        
        return jsonify(error_response('Could not build notification URL from config'))
    
    # Send test notification
    # For Teams, use direct HTTP since Apprise can silently fail
    if channel['channel_type'] == 'teams':
        import requests
        webhook_url = config.get('webhook', '')
        if webhook_url:
            try:
                payload = {
                    "text": f"**OpsConductor Test Notification**\n\nThis is a test notification from channel: {channel['name']}"
                }
                response = requests.post(webhook_url, json=payload, timeout=10)
                success = response.status_code == 200 or response.text == '1'
            except Exception as e:
                logger.error(f"Teams webhook error: {e}")
                success = False
        else:
            success = False
    else:
        from backend.services.notification_service import NotificationService
        service = NotificationService([apprise_url])
        success = service.send(
            title='OpsConductor Test Notification',
            body=f'This is a test notification from channel: {channel["name"]}'
        )
    
    # Update test status
    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE notification_channels
            SET last_test_at = %s, last_test_success = %s
            WHERE id = %s
        """, (now_utc(), success, channel_id))
        db.get_connection().commit()
    
    if success:
        return jsonify(success_response(message='Test notification sent successfully'))
    else:
        return jsonify(error_response('Failed to send test notification'))


def build_apprise_url(channel_type: str, config: dict) -> str:
    """Build an Apprise URL from channel type and config."""
    
    if channel_type == 'email':
        # Apprise email format: mailtos://user:pass@server:port?from=x&to=y
        server = config.get('server', '')
        port = config.get('port', '587')
        user = config.get('username', '')
        password = config.get('password', '')
        from_addr = config.get('from', '')
        to_addr = config.get('to', '')
        secure = config.get('secure', 'starttls')
        
        if not server or not to_addr:
            return None
        
        # Handle legacy server:port format
        if ':' in server:
            server, port = server.rsplit(':', 1)
        
        # URL encode credentials
        from urllib.parse import quote
        user_encoded = quote(user, safe='') if user else ''
        pass_encoded = quote(password, safe='') if password else ''
        
        # Build the URL based on security setting
        # mailtos = STARTTLS, mailtoss = SSL/TLS, mailto = no encryption
        if secure == 'ssl':
            scheme = 'mailtos'  # SSL/TLS
            if not port or port == '587':
                port = '465'
        elif secure == 'starttls':
            scheme = 'mailtos'  # STARTTLS
            if not port:
                port = '587'
        else:
            scheme = 'mailto'  # No encryption
            if not port:
                port = '25'
        
        # Build URL
        if user_encoded and pass_encoded:
            url = f"{scheme}://{user_encoded}:{pass_encoded}@{server}:{port}"
        elif user_encoded:
            url = f"{scheme}://{user_encoded}@{server}:{port}"
        else:
            url = f"{scheme}://{server}:{port}"
        
        # Add from and to parameters
        params = []
        if from_addr:
            params.append(f"from={quote(from_addr, safe='@')}")
        params.append(f"to={quote(to_addr, safe='@')}")
        
        if params:
            url += '?' + '&'.join(params)
        
        return url
    
    elif channel_type == 'slack':
        # slack://token_a/token_b/token_c or webhook URL
        webhook = config.get('webhook', '')
        if webhook:
            # Convert webhook URL to Apprise format
            if 'hooks.slack.com' in webhook:
                # Extract parts from webhook URL
                # https://hooks.slack.com/services/T.../B.../xxx
                parts = webhook.split('/services/')
                if len(parts) == 2:
                    tokens = parts[1]
                    return f"slack://hook/{tokens}"
            return webhook
        return None
    
    elif channel_type == 'webhook':
        url = config.get('url', '')
        return f"json://{url}" if url else None
    
    elif channel_type == 'pagerduty':
        integration_key = config.get('integration_key', '')
        return f"pagerduty://{integration_key}" if integration_key else None
    
    elif channel_type == 'teams':
        # MS Teams webhook URL format:
        # https://outlook.office.com/webhook/... or https://xxx.webhook.office.com/webhookb2/...
        # Apprise format: msteams://TokenA/TokenB/TokenC/...
        webhook = config.get('webhook', '')
        if not webhook:
            return None
        
        # Extract the path components from the webhook URL
        # New format: https://xxx.webhook.office.com/webhookb2/{uuid}@{uuid}/IncomingWebhook/{token}/{uuid}
        # Old format: https://outlook.office.com/webhook/{uuid}@{uuid}/IncomingWebhook/{token}/{uuid}
        import re
        
        # Try to parse the webhook URL
        match = re.search(r'webhookb2/([^/]+)/IncomingWebhook/([^/]+)/([^/]+)(?:/([^/]+))?', webhook)
        if match:
            token_a = match.group(1)  # UUID@UUID
            token_b = match.group(2)  # IncomingWebhook token
            token_c = match.group(3)  # Another UUID
            token_d = match.group(4)  # Optional additional token
            
            if token_d:
                return f"msteams://{token_a}/{token_b}/{token_c}/{token_d}"
            return f"msteams://{token_a}/{token_b}/{token_c}"
        
        # Try old format
        match = re.search(r'webhook/([^/]+)/IncomingWebhook/([^/]+)/([^/]+)', webhook)
        if match:
            token_a = match.group(1)
            token_b = match.group(2)
            token_c = match.group(3)
            return f"msteams://{token_a}/{token_b}/{token_c}"
        
        # If we can't parse it, return None
        return None
    
    elif channel_type == 'discord':
        webhook = config.get('webhook', '')
        if webhook and 'discord.com/api/webhooks' in webhook:
            # Extract webhook ID and token
            parts = webhook.split('/webhooks/')
            if len(parts) == 2:
                return f"discord://{parts[1]}"
        return None
    
    # Generic URL passthrough
    return config.get('url', None)


# ============================================================================
# RULES
# ============================================================================

@notifications_bp.route('/rules', methods=['GET'])
def list_rules():
    """List all notification rules."""
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, enabled, trigger_type, trigger_config,
                   channel_ids, severity_filter, category_filter,
                   cooldown_minutes, last_triggered_at, created_at, updated_at
            FROM notification_rules
            ORDER BY name
        """)
        rules = []
        for row in cursor.fetchall():
            rule = dict(row)
            if isinstance(rule.get('trigger_config'), str):
                rule['trigger_config'] = json.loads(rule['trigger_config'])
            rules.append(rule)
    
    return jsonify(success_response({'rules': rules}))


@notifications_bp.route('/rules', methods=['POST'])
def create_rule():
    """Create a new notification rule."""
    data = request.get_json()
    
    if not data.get('name'):
        raise ValidationError('Rule name is required')
    if not data.get('trigger_type'):
        raise ValidationError('Trigger type is required')
    if not data.get('channel_ids'):
        raise ValidationError('At least one channel is required')
    
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO notification_rules 
            (name, description, enabled, trigger_type, trigger_config, 
             channel_ids, severity_filter, category_filter, cooldown_minutes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['name'],
            data.get('description'),
            data.get('enabled', True),
            data['trigger_type'],
            json.dumps(data.get('trigger_config', {})),
            data['channel_ids'],
            data.get('severity_filter'),
            data.get('category_filter'),
            data.get('cooldown_minutes', 5)
        ))
        rule_id = cursor.fetchone()['id']
        db.get_connection().commit()
    
    return jsonify(success_response({'id': rule_id}, message='Rule created'))


@notifications_bp.route('/rules/<int:rule_id>', methods=['PUT'])
def update_rule(rule_id):
    """Update a notification rule."""
    data = request.get_json()
    db = get_db_connection()
    
    updates = []
    params = []
    
    if 'name' in data:
        updates.append('name = %s')
        params.append(data['name'])
    if 'description' in data:
        updates.append('description = %s')
        params.append(data['description'])
    if 'enabled' in data:
        updates.append('enabled = %s')
        params.append(data['enabled'])
    if 'trigger_type' in data:
        updates.append('trigger_type = %s')
        params.append(data['trigger_type'])
    if 'trigger_config' in data:
        updates.append('trigger_config = %s')
        params.append(json.dumps(data['trigger_config']))
    if 'channel_ids' in data:
        updates.append('channel_ids = %s')
        params.append(data['channel_ids'])
    if 'severity_filter' in data:
        updates.append('severity_filter = %s')
        params.append(data['severity_filter'])
    if 'category_filter' in data:
        updates.append('category_filter = %s')
        params.append(data['category_filter'])
    if 'cooldown_minutes' in data:
        updates.append('cooldown_minutes = %s')
        params.append(data['cooldown_minutes'])
    
    if not updates:
        raise ValidationError('No fields to update')
    
    updates.append('updated_at = %s')
    params.append(now_utc())
    params.append(rule_id)
    
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE notification_rules
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id
        """, params)
        
        if cursor.rowcount == 0:
            raise NotFoundError(f'Rule {rule_id} not found')
        
        db.get_connection().commit()
    
    return jsonify(success_response(message='Rule updated'))


@notifications_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    """Delete a notification rule."""
    db = get_db_connection()
    
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM notification_rules WHERE id = %s", (rule_id,))
        
        if cursor.rowcount == 0:
            raise NotFoundError(f'Rule {rule_id} not found')
        
        db.get_connection().commit()
    
    return jsonify(success_response(message='Rule deleted'))


# ============================================================================
# HISTORY
# ============================================================================

@notifications_bp.route('/history', methods=['GET'])
def get_history():
    """Get notification history."""
    limit = int(request.args.get('limit', 50))
    channel_id = request.args.get('channel_id')
    
    db = get_db_connection()
    
    query = """
        SELECT h.id, h.channel_id, h.rule_id, h.title, h.message,
               h.trigger_type, h.trigger_id, h.status, h.error_message, h.sent_at,
               c.name as channel_name
        FROM notification_history h
        LEFT JOIN notification_channels c ON h.channel_id = c.id
    """
    params = []
    
    if channel_id:
        query += " WHERE h.channel_id = %s"
        params.append(int(channel_id))
    
    query += " ORDER BY h.sent_at DESC LIMIT %s"
    params.append(limit)
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        history = [dict(row) for row in cursor.fetchall()]
    
    return jsonify(success_response({'history': history}))


# ============================================================================
# SEND NOTIFICATION
# ============================================================================

# ============================================================================
# TEMPLATES
# ============================================================================

@notifications_bp.route('/templates', methods=['GET'])
def list_templates():
    """List all notification templates."""
    from backend.services.template_service import get_template_service
    
    template_type = request.args.get('type')
    service = get_template_service()
    templates = service.get_templates(template_type)
    
    return jsonify(success_response({'templates': templates}))


@notifications_bp.route('/templates', methods=['POST'])
def create_template():
    """Create a new notification template."""
    from backend.services.template_service import get_template_service
    
    data = request.get_json()
    
    if not data.get('name'):
        raise ValidationError('Template name is required')
    if not data.get('title_template'):
        raise ValidationError('Title template is required')
    if not data.get('body_template'):
        raise ValidationError('Body template is required')
    
    service = get_template_service()
    template = service.create_template(
        name=data['name'],
        title_template=data['title_template'],
        body_template=data['body_template'],
        template_type=data.get('template_type', 'system'),
        description=data.get('description'),
        available_variables=data.get('available_variables', [])
    )
    
    return jsonify(success_response(template, message='Template created'))


@notifications_bp.route('/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Get a single template."""
    from backend.services.template_service import get_template_service
    
    service = get_template_service()
    template = service.get_template(template_id)
    
    if not template:
        raise NotFoundError(f'Template {template_id} not found')
    
    return jsonify(success_response(template))


@notifications_bp.route('/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """Update a notification template."""
    from backend.services.template_service import get_template_service
    
    data = request.get_json()
    service = get_template_service()
    
    template = service.update_template(template_id, **data)
    
    if not template:
        raise NotFoundError(f'Template {template_id} not found')
    
    return jsonify(success_response(template, message='Template updated'))


@notifications_bp.route('/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a notification template."""
    from backend.services.template_service import get_template_service
    
    service = get_template_service()
    deleted = service.delete_template(template_id)
    
    if not deleted:
        raise NotFoundError(f'Template {template_id} not found or is a default template')
    
    return jsonify(success_response(message='Template deleted'))


@notifications_bp.route('/templates/<int:template_id>/preview', methods=['POST'])
def preview_template(template_id):
    """Preview a template with sample data."""
    from backend.services.template_service import get_template_service
    
    data = request.get_json() or {}
    context = data.get('context', {})
    
    service = get_template_service()
    template = service.get_template(template_id)
    
    if not template:
        raise NotFoundError(f'Template {template_id} not found')
    
    rendered = service.render_template(template_id, context)
    
    return jsonify(success_response({
        'title': rendered['title'],
        'body': rendered['body'],
        'template': template
    }))


@notifications_bp.route('/send', methods=['POST'])
def send_notification():
    """
    Send a notification manually.
    
    Body:
        title: Notification title
        message: Notification body
        channel_ids: List of channel IDs to send to (optional, sends to all enabled if not specified)
    """
    data = request.get_json()
    
    if not data.get('title'):
        raise ValidationError('Title is required')
    if not data.get('message'):
        raise ValidationError('Message is required')
    
    db = get_db_connection()
    channel_ids = data.get('channel_ids')
    
    # Get channels
    with db.cursor() as cursor:
        if channel_ids:
            cursor.execute("""
                SELECT id, name, channel_type, config
                FROM notification_channels
                WHERE id = ANY(%s) AND enabled = true
            """, (channel_ids,))
        else:
            cursor.execute("""
                SELECT id, name, channel_type, config
                FROM notification_channels
                WHERE enabled = true
            """)
        channels = [dict(row) for row in cursor.fetchall()]
    
    if not channels:
        return jsonify(error_response('No enabled channels found'))
    
    from backend.services.notification_service import NotificationService
    
    results = []
    for channel in channels:
        config = channel['config']
        if isinstance(config, str):
            config = json.loads(config)
        
        apprise_url = build_apprise_url(channel['channel_type'], config)
        
        if not apprise_url:
            results.append({'channel': channel['name'], 'success': False, 'error': 'Invalid config'})
            continue
        
        service = NotificationService([apprise_url])
        success = service.send(title=data['title'], body=data['message'])
        
        # Log to history
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO notification_history 
                (channel_id, title, message, trigger_type, status)
                VALUES (%s, %s, %s, 'manual', %s)
            """, (
                channel['id'],
                data['title'],
                data['message'],
                'sent' if success else 'failed'
            ))
            db.get_connection().commit()
        
        results.append({'channel': channel['name'], 'success': success})
    
    successful = sum(1 for r in results if r['success'])
    return jsonify(success_response({
        'results': results,
        'sent': successful,
        'total': len(results)
    }))
