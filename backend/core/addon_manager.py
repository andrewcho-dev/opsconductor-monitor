"""
OpsConductor Addon Manager

Manages addon lifecycle: install, enable, disable, uninstall.
Handles dynamic loading of connector/normalizer pairs.
"""

import logging
import os
import json
import zipfile
import shutil
import importlib.util
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from backend.utils.db import db_query, db_execute

logger = logging.getLogger(__name__)


@dataclass
class AddonInfo:
    """Information about an installed addon."""
    id: str
    name: str
    version: str
    category: str  # 'nms' or 'device'
    description: str
    author: str
    enabled: bool
    installed: bool
    installed_at: datetime
    is_builtin: bool
    manifest: Dict[str, Any]
    config: Dict[str, Any]


@dataclass
class LoadedAddon:
    """A loaded addon with its connector and normalizer classes."""
    info: AddonInfo
    connector_class: type
    normalizer_class: type


class AddonManager:
    """
    Manages addon lifecycle: install, enable, disable, uninstall.
    
    Addons are connector-normalizer pairs that can be:
    - Built-in (ship with OpsConductor)
    - User-installed (uploaded via UI)
    """
    
    # Default paths
    ADDON_STORAGE_PATH = "/var/opsconductor/addons"
    BUILTIN_ADDONS_PATH = "backend/connectors"
    
    def __init__(self):
        self._loaded_addons: Dict[str, LoadedAddon] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize addon manager and load all enabled addons."""
        if self._initialized:
            return
        
        logger.info("Initializing addon manager...")
        
        # Ensure addon storage directory exists
        os.makedirs(self.ADDON_STORAGE_PATH, exist_ok=True)
        
        # Load all enabled addons
        addons = self.get_installed_addons()
        for addon in addons:
            if addon.enabled:
                try:
                    self.load_addon(addon.id)
                except Exception as e:
                    logger.error(f"Failed to load addon {addon.id}: {e}")
        
        self._initialized = True
        logger.info(f"Addon manager initialized with {len(self._loaded_addons)} addons")
    
    def get_installed_addons(self, include_uninstalled: bool = False) -> List[AddonInfo]:
        """List all installed addons."""
        if include_uninstalled:
            rows = db_query("""
                SELECT id, name, version, category, description, author, 
                       enabled, installed_at, is_builtin, manifest, config,
                       COALESCE(installed, true) as installed
                FROM installed_addons
                ORDER BY category, name
            """)
        else:
            rows = db_query("""
                SELECT id, name, version, category, description, author, 
                       enabled, installed_at, is_builtin, manifest, config,
                       COALESCE(installed, true) as installed
                FROM installed_addons
                WHERE COALESCE(installed, true) = true
                ORDER BY category, name
            """)
        
        return [
            AddonInfo(
                id=row['id'],
                name=row['name'],
                version=row['version'],
                category=row['category'],
                description=row['description'] or '',
                author=row['author'] or '',
                enabled=row['enabled'],
                installed=row.get('installed', True),
                installed_at=row['installed_at'],
                is_builtin=row['is_builtin'],
                manifest=row['manifest'] if isinstance(row['manifest'], dict) else json.loads(row['manifest'] or '{}'),
                config=row['config'] if isinstance(row['config'], dict) else json.loads(row['config'] or '{}'),
            )
            for row in rows
        ]
    
    def get_addon(self, addon_id: str) -> Optional[AddonInfo]:
        """Get a specific addon by ID."""
        rows = db_query("""
            SELECT id, name, version, category, description, author, 
                   enabled, COALESCE(installed, true) as installed,
                   installed_at, is_builtin, manifest, config
            FROM installed_addons
            WHERE id = %s
        """, (addon_id,))
        
        if not rows:
            return None
        
        row = rows[0]
        return AddonInfo(
            id=row['id'],
            name=row['name'],
            version=row['version'],
            category=row['category'],
            description=row['description'] or '',
            author=row['author'] or '',
            enabled=row['enabled'],
            installed=row.get('installed', True),
            installed_at=row['installed_at'],
            is_builtin=row['is_builtin'],
            manifest=row['manifest'] if isinstance(row['manifest'], dict) else json.loads(row['manifest'] or '{}'),
            config=row['config'] if isinstance(row['config'], dict) else json.loads(row['config'] or '{}'),
        )
    
    def load_addon(self, addon_id: str) -> Optional[LoadedAddon]:
        """
        Dynamically load an addon's connector and normalizer.
        
        For built-in addons, loads from backend/connectors/{addon_id}/
        For user addons, loads from /var/opsconductor/addons/{addon_id}/
        """
        if addon_id in self._loaded_addons:
            return self._loaded_addons[addon_id]
        
        addon = self.get_addon(addon_id)
        if not addon:
            logger.error(f"Addon {addon_id} not found")
            return None
        
        if not addon.enabled:
            logger.warning(f"Addon {addon_id} is disabled")
            return None
        
        try:
            if addon.is_builtin:
                loaded = self._load_builtin_addon(addon)
            else:
                loaded = self._load_user_addon(addon)
            
            if loaded:
                self._loaded_addons[addon_id] = loaded
                logger.info(f"Loaded addon: {addon_id}")
            
            return loaded
            
        except Exception as e:
            logger.error(f"Failed to load addon {addon_id}: {e}")
            return None
    
    def _load_builtin_addon(self, addon: AddonInfo) -> Optional[LoadedAddon]:
        """Load a built-in addon from backend/connectors/."""
        connector_module_path = f"backend.connectors.{addon.id}.connector"
        normalizer_module_path = f"backend.connectors.{addon.id}.normalizer"
        
        # Handle special cases
        if addon.id == 'prtg':
            normalizer_module_path = f"backend.connectors.{addon.id}.database_normalizer"
        if addon.id == 'snmp_trap':
            connector_module_path = "backend.connectors.snmp.connector"
            normalizer_module_path = "backend.connectors.snmp.normalizer"
        
        try:
            # Import connector module
            connector_module = importlib.import_module(connector_module_path)
            connector_class_name = addon.manifest.get('connector_class', f"{addon.id.title()}Connector")
            connector_class = getattr(connector_module, connector_class_name, None)
            
            # Import normalizer module
            normalizer_module = importlib.import_module(normalizer_module_path)
            normalizer_class_name = addon.manifest.get('normalizer_class', f"{addon.id.title()}Normalizer")
            normalizer_class = getattr(normalizer_module, normalizer_class_name, None)
            
            if not connector_class or not normalizer_class:
                logger.error(f"Could not find classes for addon {addon.id}")
                return None
            
            return LoadedAddon(
                info=addon,
                connector_class=connector_class,
                normalizer_class=normalizer_class,
            )
            
        except ImportError as e:
            logger.error(f"Import error for addon {addon.id}: {e}")
            return None
    
    def _load_user_addon(self, addon: AddonInfo) -> Optional[LoadedAddon]:
        """Load a user-installed addon from addon storage."""
        addon_path = os.path.join(self.ADDON_STORAGE_PATH, addon.id)
        
        if not os.path.exists(addon_path):
            logger.error(f"Addon path does not exist: {addon_path}")
            return None
        
        connector_path = os.path.join(addon_path, "backend", "connector.py")
        normalizer_path = os.path.join(addon_path, "backend", "normalizer.py")
        
        if not os.path.exists(connector_path) or not os.path.exists(normalizer_path):
            logger.error(f"Missing connector or normalizer for addon {addon.id}")
            return None
        
        try:
            # Load connector module
            connector_class = self._load_module_from_file(
                addon.id, connector_path, "connector",
                addon.manifest.get('connector_class', f"{addon.id.title()}Connector")
            )
            
            # Load normalizer module
            normalizer_class = self._load_module_from_file(
                addon.id, normalizer_path, "normalizer",
                addon.manifest.get('normalizer_class', f"{addon.id.title()}Normalizer")
            )
            
            if not connector_class or not normalizer_class:
                return None
            
            return LoadedAddon(
                info=addon,
                connector_class=connector_class,
                normalizer_class=normalizer_class,
            )
            
        except Exception as e:
            logger.error(f"Error loading user addon {addon.id}: {e}")
            return None
    
    def _load_module_from_file(self, addon_id: str, file_path: str, module_name: str, class_name: str):
        """Dynamically load a Python module from file."""
        spec = importlib.util.spec_from_file_location(
            f"addons.{addon_id}.{module_name}",
            file_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"addons.{addon_id}.{module_name}"] = module
        spec.loader.exec_module(module)
        return getattr(module, class_name, None)
    
    def enable_addon(self, addon_id: str) -> bool:
        """Enable an addon."""
        addon = self.get_addon(addon_id)
        if not addon:
            return False
        
        db_execute(
            "UPDATE installed_addons SET enabled = true WHERE id = %s",
            (addon_id,)
        )
        
        # Load the addon
        self.load_addon(addon_id)
        
        logger.info(f"Enabled addon: {addon_id}")
        return True
    
    def disable_addon(self, addon_id: str) -> bool:
        """Disable an addon."""
        addon = self.get_addon(addon_id)
        if not addon:
            return False
        
        if addon.is_builtin:
            logger.warning(f"Cannot disable built-in addon: {addon_id}")
            # Allow disabling but warn
        
        db_execute(
            "UPDATE installed_addons SET enabled = false WHERE id = %s",
            (addon_id,)
        )
        
        # Unload the addon
        if addon_id in self._loaded_addons:
            del self._loaded_addons[addon_id]
        
        logger.info(f"Disabled addon: {addon_id}")
        return True
    
    def install_addon(self, zip_file_path: str) -> Dict[str, Any]:
        """
        Install addon from a zip file.
        
        Steps:
        1. Validate zip structure and manifest
        2. Extract to addon storage
        3. Run database migrations
        4. Register in installed_addons table
        5. Load addon
        
        Returns:
            Dict with success status and addon info or error message
        """
        try:
            # Validate zip file
            if not zipfile.is_zipfile(zip_file_path):
                return {"success": False, "error": "Invalid zip file"}
            
            with zipfile.ZipFile(zip_file_path, 'r') as zf:
                # Check for manifest.json
                if 'manifest.json' not in zf.namelist():
                    return {"success": False, "error": "Missing manifest.json"}
                
                # Read and validate manifest
                manifest_data = zf.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_data)
                
                required_fields = ['id', 'name', 'version', 'category']
                for field in required_fields:
                    if field not in manifest:
                        return {"success": False, "error": f"Missing required field in manifest: {field}"}
                
                addon_id = manifest['id']
                
                # Check if addon already exists
                existing = self.get_addon(addon_id)
                if existing and existing.is_builtin:
                    return {"success": False, "error": "Cannot overwrite built-in addon"}
                
                # Extract to addon storage
                addon_path = os.path.join(self.ADDON_STORAGE_PATH, addon_id)
                if os.path.exists(addon_path):
                    shutil.rmtree(addon_path)
                
                zf.extractall(addon_path)
            
            # Register in database
            db_execute("""
                INSERT INTO installed_addons (id, name, version, category, description, author, 
                                              enabled, is_builtin, storage_path, manifest)
                VALUES (%s, %s, %s, %s, %s, %s, true, false, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    version = EXCLUDED.version,
                    description = EXCLUDED.description,
                    manifest = EXCLUDED.manifest,
                    updated_at = NOW()
            """, (
                addon_id,
                manifest.get('name'),
                manifest.get('version'),
                manifest.get('category'),
                manifest.get('description', ''),
                manifest.get('author', ''),
                addon_path,
                json.dumps(manifest),
            ))
            
            # Run migrations if present
            migrations_path = os.path.join(addon_path, 'migrations')
            if os.path.exists(migrations_path):
                self._run_addon_migrations(addon_id, migrations_path)
            
            # Load the addon
            loaded = self.load_addon(addon_id)
            
            return {
                "success": True,
                "addon_id": addon_id,
                "name": manifest.get('name'),
                "version": manifest.get('version'),
            }
            
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid manifest.json: {e}"}
        except Exception as e:
            logger.exception(f"Error installing addon: {e}")
            return {"success": False, "error": str(e)}
    
    def uninstall_addon(self, addon_id: str) -> bool:
        """
        Uninstall an addon (built-in or user-installed).
        
        For built-in addons:
        - Removes severity/category mappings from DB
        - Marks as installed=false, enabled=false
        - Does NOT delete source code (stays in repo)
        
        For user addons:
        - Removes severity/category mappings from DB
        - Deletes from installed_addons table
        - Deletes addon files from storage
        """
        addon = self.get_addon(addon_id)
        if not addon:
            return False
        
        # Unload the addon from runtime
        if addon_id in self._loaded_addons:
            del self._loaded_addons[addon_id]
        
        # Run uninstall migration (clean up DB mappings)
        self._run_uninstall_cleanup(addon_id)
        
        if addon.is_builtin:
            # Mark built-in addon as uninstalled (don't delete from table)
            db_execute("""
                UPDATE installed_addons 
                SET enabled = false, 
                    installed = false, 
                    uninstalled_at = NOW()
                WHERE id = %s
            """, (addon_id,))
            logger.info(f"Uninstalled built-in addon: {addon_id}")
        else:
            # Fully remove user addon
            db_execute("DELETE FROM installed_addons WHERE id = %s", (addon_id,))
            db_execute("DELETE FROM addon_migrations WHERE addon_id = %s", (addon_id,))
            
            # Remove addon files
            addon_path = os.path.join(self.ADDON_STORAGE_PATH, addon_id)
            if os.path.exists(addon_path):
                shutil.rmtree(addon_path)
            
            logger.info(f"Uninstalled user addon: {addon_id}")
        
        return True
    
    def _run_uninstall_cleanup(self, addon_id: str) -> None:
        """Clean up DB entries for an addon (severity/category mappings)."""
        try:
            # Remove severity mappings
            db_execute(
                "DELETE FROM severity_mappings WHERE connector_type = %s",
                (addon_id,)
            )
            
            # Remove category mappings
            db_execute(
                "DELETE FROM category_mappings WHERE connector_type = %s",
                (addon_id,)
            )
            
            logger.info(f"Cleaned up mappings for addon: {addon_id}")
        except Exception as e:
            logger.error(f"Error cleaning up mappings for {addon_id}: {e}")
    
    def reinstall_addon(self, addon_id: str) -> Dict[str, Any]:
        """
        Reinstall a built-in addon that was previously uninstalled.
        
        Re-runs the install migration to restore DB mappings.
        """
        addon = self.get_addon(addon_id)
        if not addon:
            return {"success": False, "error": "Addon not found"}
        
        if not addon.is_builtin:
            return {"success": False, "error": "Use install for user addons"}
        
        try:
            # Mark as installed and enabled
            db_execute("""
                UPDATE installed_addons 
                SET enabled = true, 
                    installed = true, 
                    uninstalled_at = NULL,
                    updated_at = NOW()
                WHERE id = %s
            """, (addon_id,))
            
            # Re-run install migrations from addon storage path or built-in
            addon_path = os.path.join(self.ADDON_STORAGE_PATH, addon_id)
            migrations_path = os.path.join(addon_path, 'migrations')
            
            if os.path.exists(migrations_path):
                # Clear previous migration records for this addon
                db_execute(
                    "DELETE FROM addon_migrations WHERE addon_id = %s",
                    (addon_id,)
                )
                self._run_addon_migrations(addon_id, migrations_path)
            
            # Load the addon
            self.load_addon(addon_id)
            
            logger.info(f"Reinstalled addon: {addon_id}")
            return {"success": True, "addon_id": addon_id}
            
        except Exception as e:
            logger.exception(f"Error reinstalling addon {addon_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _run_addon_migrations(self, addon_id: str, migrations_path: str) -> None:
        """Run SQL migrations for an addon."""
        from backend.utils.db import db_execute
        
        migration_files = sorted([
            f for f in os.listdir(migrations_path)
            if f.endswith('.sql')
        ])
        
        for migration_file in migration_files:
            # Check if already applied
            rows = db_query(
                "SELECT 1 FROM addon_migrations WHERE addon_id = %s AND migration_name = %s",
                (addon_id, migration_file)
            )
            if rows:
                continue
            
            # Run migration
            migration_path = os.path.join(migrations_path, migration_file)
            with open(migration_path, 'r') as f:
                sql = f.read()
            
            try:
                db_execute(sql)
                db_execute(
                    "INSERT INTO addon_migrations (addon_id, migration_name) VALUES (%s, %s)",
                    (addon_id, migration_file)
                )
                logger.info(f"Applied addon migration: {addon_id}/{migration_file}")
            except Exception as e:
                logger.error(f"Failed to apply addon migration {addon_id}/{migration_file}: {e}")
                raise
    
    def get_loaded_addon(self, addon_id: str) -> Optional[LoadedAddon]:
        """Get a loaded addon by ID."""
        return self._loaded_addons.get(addon_id)
    
    def get_connector_class(self, addon_id: str) -> Optional[type]:
        """Get the connector class for an addon."""
        loaded = self.get_loaded_addon(addon_id)
        return loaded.connector_class if loaded else None
    
    def get_normalizer_class(self, addon_id: str) -> Optional[type]:
        """Get the normalizer class for an addon."""
        loaded = self.get_loaded_addon(addon_id)
        return loaded.normalizer_class if loaded else None
    
    def update_addon_config(self, addon_id: str, config: Dict[str, Any]) -> bool:
        """Update addon configuration."""
        addon = self.get_addon(addon_id)
        if not addon:
            return False
        
        db_execute(
            "UPDATE installed_addons SET config = %s WHERE id = %s",
            (json.dumps(config), addon_id)
        )
        
        return True


# Singleton instance
_addon_manager: Optional[AddonManager] = None


def get_addon_manager() -> AddonManager:
    """Get the singleton AddonManager instance."""
    global _addon_manager
    if _addon_manager is None:
        _addon_manager = AddonManager()
    return _addon_manager
