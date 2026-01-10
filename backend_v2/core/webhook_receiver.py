"""
Webhook Receiver

Handle incoming HTTP webhooks from external systems (PRTG, Axis, etc.).
Routes are registered dynamically based on addon manifests.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WebhookReceiver:
    """
    Webhook receiver for HTTP POST callbacks.
    
    Addons register webhook paths in their manifests. When a webhook arrives,
    we lookup the addon, parse the data, and process through alert engine.
    
    Usage:
        # In FastAPI routes
        @app.post("/webhooks/{path:path}")
        async def webhook_handler(path: str, request: Request):
            return await webhook_receiver.handle(path, await request.json())
    """
    
    def __init__(self):
        self._stats = {
            'webhooks_received': 0,
            'webhooks_processed': 0,
            'webhooks_dropped': 0,
            'errors': 0,
        }
    
    async def handle(
        self, 
        path: str, 
        data: Dict[str, Any],
        source_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle incoming webhook.
        
        Args:
            path: Webhook path (e.g., '/webhooks/prtg' or just 'prtg')
            data: Request body (JSON dict or form data)
            source_ip: Source IP of the request
            
        Returns:
            Response dict with status
        """
        from .addon_registry import get_registry
        from .parser import get_parser
        from .alert_engine import get_engine
        
        self._stats['webhooks_received'] += 1
        
        # Normalize path
        if not path.startswith('/'):
            path = f'/webhooks/{path}'
        
        try:
            # Find addon by webhook path
            registry = get_registry()
            addon = registry.find_by_webhook(path)
            
            if not addon:
                logger.debug(f"No addon for webhook path {path}")
                self._stats['webhooks_dropped'] += 1
                return {'status': 'dropped', 'reason': 'no_addon_for_path'}
            
            # Add source IP to data if available
            if source_ip:
                data['_source_ip'] = source_ip
            
            data['_received_at'] = datetime.utcnow().isoformat()
            
            # Parse through addon rules
            parser = get_parser()
            parsed = parser.parse(data, addon.manifest, addon.id)
            
            if not parsed:
                logger.warning(f"Failed to parse webhook for {addon.id}")
                self._stats['errors'] += 1
                return {'status': 'error', 'reason': 'parse_failed'}
            
            # Process through alert engine
            engine = get_engine()
            alert = await engine.process(parsed, addon)
            
            self._stats['webhooks_processed'] += 1
            
            return {
                'status': 'processed',
                'alert_id': str(alert.id),
                'addon_id': addon.id,
            }
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            self._stats['errors'] += 1
            return {'status': 'error', 'reason': str(e)}
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get receiver statistics."""
        return self._stats.copy()


# Global receiver instance
_receiver: Optional[WebhookReceiver] = None


def get_webhook_receiver() -> WebhookReceiver:
    """Get global webhook receiver instance."""
    global _receiver
    if _receiver is None:
        _receiver = WebhookReceiver()
    return _receiver


async def handle_webhook(path: str, data: Dict, source_ip: str = None) -> Dict:
    """Convenience function to handle webhook."""
    return await get_webhook_receiver().handle(path, data, source_ip)
