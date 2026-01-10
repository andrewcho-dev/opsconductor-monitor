"""
Addon Registry

Load, register, and lookup addons. Single source of truth for addon management.
Addons are declarative manifests (JSON) - no Python code.
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .db import query, query_one, execute

logger = logging.getLogger(__name__)


@dataclass
class Addon:
    """Addon definition loaded from database."""
    id: str
    name: str
    version: str
    method: str  # snmp_trap, webhook, api_poll, snmp_poll, ssh
    category: str
    description: str
    manifest: Dict
    enabled: bool = True
    
    @property
    def enterprise_oid(self) -> Optional[str]:
        """Get enterprise OID for SNMP trap addons."""
        if self.method == 'snmp_trap':
            return self.manifest.get('snmp_trap', {}).get('enterprise_oid')
        return None
    
    @property
    def webhook_path(self) -> Optional[str]:
        """Get webhook path for webhook addons."""
        if self.method == 'webhook':
            return self.manifest.get('webhook', {}).get('endpoint_path')
        return None
    
    @property
    def severity_mappings(self) -> Dict[str, str]:
        """Get severity mappings from manifest (supports both old and new format)."""
        # New grouped alert_mappings format
        if 'alert_mappings' in self.manifest:
            mappings = {}
            for group in self.manifest['alert_mappings']:
                for alert in group.get('alerts', []):
                    if alert.get('enabled', True):
                        mappings[alert['alert_type']] = alert.get('severity', 'warning')
            return mappings
        # Legacy flat format
        return self.manifest.get('severity_mappings', {})
    
    @property
    def category_mappings(self) -> Dict[str, str]:
        """Get category mappings from manifest (supports both old and new format)."""
        # New grouped alert_mappings format
        if 'alert_mappings' in self.manifest:
            mappings = {}
            for group in self.manifest['alert_mappings']:
                for alert in group.get('alerts', []):
                    if alert.get('enabled', True):
                        mappings[alert['alert_type']] = alert.get('category', 'unknown')
            return mappings
        # Legacy flat format
        return self.manifest.get('category_mappings', {})
    
    @property
    def title_mappings(self) -> Dict[str, str]:
        """Get title mappings from manifest (supports both old and new format)."""
        # New grouped alert_mappings format
        if 'alert_mappings' in self.manifest:
            mappings = {}
            for group in self.manifest['alert_mappings']:
                for alert in group.get('alerts', []):
                    if alert.get('enabled', True) and alert.get('title'):
                        mappings[alert['alert_type']] = alert['title']
            return mappings
        # Legacy flat format
        return self.manifest.get('title_templates', {})
    
    @property
    def description_mappings(self) -> Dict[str, str]:
        """Get description mappings from manifest (supports both old and new format)."""
        # New grouped alert_mappings format
        if 'alert_mappings' in self.manifest:
            mappings = {}
            for group in self.manifest['alert_mappings']:
                for alert in group.get('alerts', []):
                    if alert.get('enabled', True) and alert.get('description'):
                        mappings[alert['alert_type']] = alert['description']
            return mappings
        # Legacy flat format
        return self.manifest.get('description_templates', {})
    
    def is_alert_enabled(self, alert_type: str) -> bool:
        """Check if an alert type is enabled."""
        if 'alert_mappings' in self.manifest:
            for group in self.manifest['alert_mappings']:
                for alert in group.get('alerts', []):
                    if alert['alert_type'] == alert_type:
                        return alert.get('enabled', True)
            return False  # Alert type not found = disabled
        return True  # Legacy format = all enabled
    
    @property
    def parser_config(self) -> Dict:
        """Get parser configuration from manifest."""
        return self.manifest.get('parser', {})


class AddonRegistry:
    """
    Registry of all addons. Loads from database, provides lookup.
    
    Usage:
        registry = AddonRegistry()
        registry.load_all()
        
        addon = registry.get('siklu')
        addon = registry.find_by_oid('1.3.6.1.4.1.31926')
        addon = registry.find_by_webhook('/webhooks/prtg')
    """
    
    def __init__(self):
        self._addons: Dict[str, Addon] = {}
        self._oid_index: Dict[str, str] = {}  # OID prefix -> addon_id
        self._webhook_index: Dict[str, str] = {}  # path -> addon_id
    
    def load_all(self) -> int:
        """
        Load all enabled addons from database.
        Returns count of addons loaded.
        """
        rows = query("""
            SELECT id, name, version, method, category, description, manifest, enabled
            FROM addons
            WHERE enabled = true
            ORDER BY name
        """)
        
        self._addons.clear()
        self._oid_index.clear()
        self._webhook_index.clear()
        
        for row in rows:
            manifest = row['manifest']
            if isinstance(manifest, str):
                manifest = json.loads(manifest)
            
            addon = Addon(
                id=row['id'],
                name=row['name'],
                version=row['version'] or '1.0.0',
                method=row['method'],
                category=row['category'] or 'unknown',
                description=row['description'] or '',
                manifest=manifest,
                enabled=row['enabled']
            )
            
            self._addons[addon.id] = addon
            
            # Index by OID prefix for trap lookup
            if addon.enterprise_oid:
                self._oid_index[addon.enterprise_oid] = addon.id
            
            # Index by webhook path
            if addon.webhook_path:
                self._webhook_index[addon.webhook_path] = addon.id
        
        logger.info(f"Loaded {len(self._addons)} addons")
        return len(self._addons)
    
    def get(self, addon_id: str) -> Optional[Addon]:
        """Get addon by ID."""
        return self._addons.get(addon_id)
    
    def find_by_oid(self, oid: str) -> Optional[Addon]:
        """
        Find addon by OID prefix match.
        Used for SNMP trap dispatch.
        
        Example:
            addon = registry.find_by_oid('1.3.6.1.4.1.31926.1.1.2.1.1')
            # Matches addon with enterprise_oid '1.3.6.1.4.1.31926'
        """
        for prefix, addon_id in self._oid_index.items():
            if oid.startswith(prefix):
                return self._addons.get(addon_id)
        return None
    
    def find_by_webhook(self, path: str) -> Optional[Addon]:
        """
        Find addon by webhook path.
        Used for webhook dispatch.
        
        Example:
            addon = registry.find_by_webhook('/webhooks/prtg')
        """
        addon_id = self._webhook_index.get(path)
        if addon_id:
            return self._addons.get(addon_id)
        return None
    
    def get_enabled(self) -> List[Addon]:
        """Get all enabled addons."""
        return list(self._addons.values())
    
    def get_by_method(self, method: str) -> List[Addon]:
        """Get addons by method type."""
        return [a for a in self._addons.values() if a.method == method]
    
    def reload(self) -> int:
        """Reload all addons from database."""
        return self.load_all()


# Addon management functions

def install_addon(manifest: Dict) -> Addon:
    """
    Install a new addon from manifest.
    
    Args:
        manifest: Addon manifest dictionary
        
    Returns:
        Installed Addon object
    """
    addon_id = manifest['id']
    
    execute("""
        INSERT INTO addons (id, name, version, method, category, description, manifest, enabled, installed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, true, NOW())
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            version = EXCLUDED.version,
            method = EXCLUDED.method,
            category = EXCLUDED.category,
            description = EXCLUDED.description,
            manifest = EXCLUDED.manifest,
            enabled = true
    """, (
        addon_id,
        manifest.get('name', addon_id),
        manifest.get('version', '1.0.0'),
        manifest['method'],
        manifest.get('category', 'unknown'),
        manifest.get('description', ''),
        json.dumps(manifest)
    ))
    
    logger.info(f"Installed addon: {addon_id}")
    
    return Addon(
        id=addon_id,
        name=manifest.get('name', addon_id),
        version=manifest.get('version', '1.0.0'),
        method=manifest['method'],
        category=manifest.get('category', 'unknown'),
        description=manifest.get('description', ''),
        manifest=manifest,
        enabled=True
    )


def uninstall_addon(addon_id: str) -> bool:
    """
    Uninstall an addon.
    
    Args:
        addon_id: Addon ID to uninstall
        
    Returns:
        True if uninstalled
    """
    result = execute("DELETE FROM addons WHERE id = %s", (addon_id,))
    if result > 0:
        logger.info(f"Uninstalled addon: {addon_id}")
        return True
    return False


def enable_addon(addon_id: str) -> bool:
    """Enable an addon."""
    result = execute("UPDATE addons SET enabled = true WHERE id = %s", (addon_id,))
    return result > 0


def disable_addon(addon_id: str) -> bool:
    """Disable an addon."""
    result = execute("UPDATE addons SET enabled = false WHERE id = %s", (addon_id,))
    return result > 0


def get_addon_from_db(addon_id: str) -> Optional[Addon]:
    """Get addon directly from database (not cache)."""
    row = query_one("""
        SELECT id, name, version, method, category, description, manifest, enabled
        FROM addons WHERE id = %s
    """, (addon_id,))
    
    if not row:
        return None
    
    manifest = row['manifest']
    if isinstance(manifest, str):
        manifest = json.loads(manifest)
    
    return Addon(
        id=row['id'],
        name=row['name'],
        version=row['version'] or '1.0.0',
        method=row['method'],
        category=row['category'] or 'unknown',
        description=row['description'] or '',
        manifest=manifest,
        enabled=row['enabled']
    )


def list_all_addons(include_disabled: bool = False) -> List[Addon]:
    """List all addons from database."""
    if include_disabled:
        rows = query("SELECT * FROM addons ORDER BY name")
    else:
        rows = query("SELECT * FROM addons WHERE enabled = true ORDER BY name")
    
    addons = []
    for row in rows:
        manifest = row['manifest']
        if isinstance(manifest, str):
            manifest = json.loads(manifest)
        
        addons.append(Addon(
            id=row['id'],
            name=row['name'],
            version=row['version'] or '1.0.0',
            method=row['method'],
            category=row['category'] or 'unknown',
            description=row['description'] or '',
            manifest=manifest,
            enabled=row['enabled']
        ))
    
    return addons


# Global registry instance
_registry: Optional[AddonRegistry] = None


def get_registry() -> AddonRegistry:
    """Get the global addon registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = AddonRegistry()
        _registry.load_all()
    return _registry


def reload_registry() -> int:
    """Reload the global registry."""
    return get_registry().reload()
