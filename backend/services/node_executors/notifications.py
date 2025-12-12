"""
Notification Node Executors

Executors for sending notifications via various channels.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class TemplatedNotificationExecutor:
    """
    Executor for sending templated notifications through configured channels.
    
    This executor uses the notification template system and can send to
    any configured notification channel (Slack, Email, Webhook, etc.)
    """
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Send a notification using a template and configured channels.
        
        Node parameters:
            template_id: ID of the template to use (optional)
            template_name: Name of the template to use (optional)
            channel_ids: List of channel IDs to send to (optional, uses all enabled if not specified)
            title: Custom title (overrides template)
            message: Custom message (overrides template)
            variables: Additional variables to merge with context
        
        Args:
            node: Node definition with parameters
            context: Execution context with workflow variables
        
        Returns:
            Notification result with sent status per channel
        """
        from backend.database import get_db
        from backend.services.template_service import get_template_service, build_workflow_step_context
        from backend.api.notifications import build_apprise_url
        from backend.services.notification_service import NotificationService
        
        params = node.get('data', {}).get('parameters', {})
        template_id = params.get('template_id')
        template_name = params.get('template_name')
        channel_ids = params.get('channel_ids', [])
        custom_title = params.get('title', '')
        custom_message = params.get('message', '')
        extra_variables = params.get('variables', {})
        
        # Build context for template rendering
        template_context = self._build_template_context(context, extra_variables)
        
        # Get title and body
        title = custom_title
        body = custom_message
        
        template_service = get_template_service()
        
        if not title or not body:
            # Try to use template
            if template_id:
                rendered = template_service.render_template(template_id, template_context)
                title = title or rendered.get('title', '')
                body = body or rendered.get('body', '')
            elif template_name:
                rendered = template_service.render_template_by_name(template_name, template_context)
                title = title or rendered.get('title', '')
                body = body or rendered.get('body', '')
            else:
                # Use default workflow step template
                rendered = template_service.render_template_by_name('Workflow Step Notification', template_context)
                title = title or rendered.get('title', '')
                body = body or rendered.get('body', '')
        
        # Substitute any remaining variables in custom title/message
        if custom_title:
            title = template_service.render(custom_title, template_context)
        if custom_message:
            body = template_service.render(custom_message, template_context)
        
        if not title:
            title = f"Workflow Notification: {context.get('workflow_name', 'Unknown')}"
        if not body:
            body = "Workflow notification triggered."
        
        # Get channels to send to
        db = get_db()
        with db.cursor() as cursor:
            if channel_ids:
                cursor.execute("""
                    SELECT id, name, channel_type, config
                    FROM notification_channels
                    WHERE id = ANY(%s) AND enabled = true
                """, (channel_ids,))
            else:
                # Send to all enabled channels
                cursor.execute("""
                    SELECT id, name, channel_type, config
                    FROM notification_channels
                    WHERE enabled = true
                """)
            channels = [dict(row) for row in cursor.fetchall()]
        
        if not channels:
            return {
                'sent': False,
                'error': 'No enabled notification channels found',
                'title': title,
            }
        
        # Send to each channel
        results = []
        for channel in channels:
            config = channel['config']
            if isinstance(config, str):
                config = json.loads(config)
            
            apprise_url = build_apprise_url(channel['channel_type'], config)
            if not apprise_url:
                results.append({
                    'channel': channel['name'],
                    'sent': False,
                    'error': 'Invalid channel configuration'
                })
                continue
            
            try:
                service = NotificationService([apprise_url])
                success = service.send(title=title, body=body)
                
                # Log to notification history
                with db.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO notification_history 
                        (channel_id, title, message, trigger_type, trigger_id, status)
                        VALUES (%s, %s, %s, 'workflow', %s, %s)
                    """, (
                        channel['id'],
                        title,
                        body,
                        context.get('execution_id', ''),
                        'sent' if success else 'failed'
                    ))
                    db.get_connection().commit()
                
                results.append({
                    'channel': channel['name'],
                    'sent': success,
                })
            except Exception as e:
                results.append({
                    'channel': channel['name'],
                    'sent': False,
                    'error': str(e)
                })
        
        successful = sum(1 for r in results if r.get('sent'))
        
        return {
            'sent': successful > 0,
            'title': title,
            'channels_attempted': len(results),
            'channels_successful': successful,
            'results': results,
        }
    
    def _build_template_context(self, context: Dict, extra_variables: Dict) -> Dict:
        """Build template context from workflow execution context."""
        # Merge workflow variables with extra variables
        variables = {**context.get('variables', {}), **extra_variables}
        
        return {
            'workflow': {
                'id': context.get('workflow_id'),
                'name': context.get('workflow_name', 'Unknown Workflow'),
                'variables': variables,
            },
            'step': {
                'id': context.get('current_node_id'),
                'name': context.get('current_node_name', 'Notification'),
                'status': 'running',
                'message': extra_variables.get('message', ''),
                'data': extra_variables,
            },
            'job': {
                'id': context.get('execution_id'),
                'name': context.get('workflow_name'),
                'status': context.get('status', 'running'),
                'started_at': context.get('started_at'),
            },
            # Also expose variables at top level for simple access
            **variables,
        }


class SlackExecutor:
    """Executor for Slack notification nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Send a Slack notification.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            Notification result
        """
        params = node.get('data', {}).get('parameters', {})
        webhook_url = params.get('webhook_url', '')
        channel = params.get('channel', '')
        message = params.get('message', '')
        
        if not webhook_url:
            return {'error': 'No webhook URL specified', 'sent': False}
        
        if not message:
            # Build default message from context
            message = self._build_default_message(context)
        
        # Substitute variables in message
        message = self._substitute_variables(message, context)
        
        payload = {
            'text': message,
        }
        
        if channel:
            payload['channel'] = channel
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return {
                    'sent': True,
                    'channel': channel,
                    'message': message[:100] + '...' if len(message) > 100 else message,
                    'status_code': response.status,
                }
        except urllib.error.HTTPError as e:
            return {
                'sent': False,
                'error': f'HTTP {e.code}: {e.reason}',
            }
        except Exception as e:
            return {
                'sent': False,
                'error': str(e),
            }
    
    def _build_default_message(self, context: Dict) -> str:
        """Build a default notification message from context."""
        workflow_id = context.get('workflow_id', 'Unknown')
        node_results = context.get('node_results', {})
        
        success_count = sum(1 for r in node_results.values() if r.status.value == 'success')
        failure_count = sum(1 for r in node_results.values() if r.status.value == 'failure')
        
        return f"Workflow {workflow_id} completed: {success_count} succeeded, {failure_count} failed"
    
    def _substitute_variables(self, message: str, context: Dict) -> str:
        """Substitute {{variable}} placeholders in message."""
        variables = context.get('variables', {})
        
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            if placeholder in message:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                message = message.replace(placeholder, str(value))
        
        return message


class EmailExecutor:
    """Executor for email notification nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Send an email notification.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            Notification result
        """
        params = node.get('data', {}).get('parameters', {})
        to_addresses = params.get('to', '')
        subject = params.get('subject', 'Workflow Notification')
        body = params.get('body', '')
        smtp_host = params.get('smtp_host', 'localhost')
        smtp_port = int(params.get('smtp_port', 25))
        
        if not to_addresses:
            return {'error': 'No recipient specified', 'sent': False}
        
        if not body:
            body = self._build_default_body(context)
        
        # Substitute variables
        subject = self._substitute_variables(subject, context)
        body = self._substitute_variables(body, context)
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['To'] = to_addresses
            msg['From'] = params.get('from', 'opsconductor@localhost')
            
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.sendmail(msg['From'], to_addresses.split(','), msg.as_string())
            
            return {
                'sent': True,
                'to': to_addresses,
                'subject': subject,
            }
        except Exception as e:
            return {
                'sent': False,
                'error': str(e),
            }
    
    def _build_default_body(self, context: Dict) -> str:
        """Build default email body."""
        workflow_id = context.get('workflow_id', 'Unknown')
        return f"Workflow {workflow_id} has completed execution."
    
    def _substitute_variables(self, text: str, context: Dict) -> str:
        """Substitute variables in text."""
        variables = context.get('variables', {})
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        return text


class WebhookExecutor:
    """Executor for webhook notification nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Send a webhook notification.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            Webhook result
        """
        params = node.get('data', {}).get('parameters', {})
        url = params.get('url', '')
        method = params.get('method', 'POST').upper()
        headers = params.get('headers', {})
        body_template = params.get('body', '')
        
        if not url:
            return {'error': 'No URL specified', 'sent': False}
        
        # Build request body
        if body_template:
            body = self._substitute_variables(body_template, context)
        else:
            # Send context variables as JSON
            body = json.dumps({
                'workflow_id': context.get('workflow_id'),
                'execution_id': context.get('execution_id'),
                'variables': context.get('variables', {}),
            })
        
        try:
            data = body.encode('utf-8') if body else None
            
            req_headers = {'Content-Type': 'application/json'}
            if isinstance(headers, dict):
                req_headers.update(headers)
            
            req = urllib.request.Request(
                url,
                data=data,
                headers=req_headers,
                method=method
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_body = response.read().decode('utf-8', errors='replace')
                
                return {
                    'sent': True,
                    'url': url,
                    'method': method,
                    'status_code': response.status,
                    'response': response_body[:500],  # Limit response size
                }
        except urllib.error.HTTPError as e:
            return {
                'sent': False,
                'url': url,
                'error': f'HTTP {e.code}: {e.reason}',
            }
        except Exception as e:
            return {
                'sent': False,
                'url': url,
                'error': str(e),
            }
    
    def _substitute_variables(self, text: str, context: Dict) -> str:
        """Substitute variables in text."""
        variables = context.get('variables', {})
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            if placeholder in text:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                text = text.replace(placeholder, str(value))
        return text
