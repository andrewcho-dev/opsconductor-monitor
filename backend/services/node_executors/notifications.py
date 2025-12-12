"""
Notification Node Executors

Executors for sending notifications via various channels.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any

logger = logging.getLogger(__name__)


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
