"""
Addon Packager Tool

Extracts existing connectors as installable addon packages (zip files).
Can also be used to create addon packages from scratch.

Usage:
    python -m backend.tools.addon_packager extract axis --output ./addons/
    python -m backend.tools.addon_packager extract-all --output ./addons/
    python -m backend.tools.addon_packager list
"""

import os
import sys
import json
import zipfile
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Addon metadata for built-in connectors
BUILTIN_ADDONS = {
    'axis': {
        'name': 'Axis Cameras',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Axis network cameras via VAPIX events',
        'author': 'OpsConductor',
        'connector_class': 'AxisConnector',
        'normalizer_class': 'AxisNormalizer',
        'capabilities': ['polling'],
        'default_category': 'video',
    },
    'cradlepoint': {
        'name': 'Cradlepoint',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Cradlepoint cellular routers via NetCloud API',
        'author': 'OpsConductor',
        'connector_class': 'CradlepointConnector',
        'normalizer_class': 'CradlepointNormalizer',
        'capabilities': ['polling'],
        'default_category': 'wireless',
    },
    'siklu': {
        'name': 'Siklu Radios',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Siklu EtherHaul wireless radios',
        'author': 'OpsConductor',
        'connector_class': 'SikluConnector',
        'normalizer_class': 'SikluNormalizer',
        'capabilities': ['polling', 'snmp_traps'],
        'default_category': 'wireless',
    },
    'ubiquiti': {
        'name': 'Ubiquiti',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Ubiquiti wireless devices via UNMS/UISP API',
        'author': 'OpsConductor',
        'connector_class': 'UbiquitiConnector',
        'normalizer_class': 'UbiquitiNormalizer',
        'capabilities': ['polling'],
        'default_category': 'wireless',
    },
    'cisco_asa': {
        'name': 'Cisco ASA',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Cisco ASA firewalls',
        'author': 'OpsConductor',
        'connector_class': 'CiscoASAConnector',
        'normalizer_class': 'CiscoASANormalizer',
        'capabilities': ['polling'],
        'default_category': 'security',
    },
    'eaton': {
        'name': 'Eaton UPS',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Eaton UPS systems via SNMP',
        'author': 'OpsConductor',
        'connector_class': 'EatonConnector',
        'normalizer_class': 'EatonNormalizer',
        'capabilities': ['polling'],
        'default_category': 'power',
    },
    'milestone': {
        'name': 'Milestone VMS',
        'version': '1.0.0',
        'category': 'device',
        'description': 'Monitor Milestone XProtect video management system',
        'author': 'OpsConductor',
        'connector_class': 'MilestoneConnector',
        'normalizer_class': 'MilestoneNormalizer',
        'capabilities': ['polling'],
        'default_category': 'video',
    },
    'mcp': {
        'name': 'MCP (Ciena)',
        'version': '1.0.0',
        'category': 'nms',
        'description': 'Connect to Ciena MCP for optical network monitoring',
        'author': 'OpsConductor',
        'connector_class': 'MCPConnector',
        'normalizer_class': 'MCPNormalizer',
        'capabilities': ['polling'],
        'default_category': 'network',
    },
    'prtg': {
        'name': 'PRTG Network Monitor',
        'version': '1.0.0',
        'category': 'nms',
        'description': 'Connect to PRTG Network Monitor for centralized alerting',
        'author': 'OpsConductor',
        'connector_class': 'PRTGConnector',
        'normalizer_class': 'PRTGDatabaseNormalizer',
        'capabilities': ['polling', 'webhooks'],
        'default_category': 'network',
        'normalizer_file': 'database_normalizer.py',
    },
    'snmp_trap': {
        'name': 'SNMP Traps',
        'version': '1.0.0',
        'category': 'nms',
        'description': 'Receive SNMP traps from any device',
        'author': 'OpsConductor',
        'connector_class': 'SNMPTrapConnector',
        'normalizer_class': 'SNMPTrapNormalizer',
        'capabilities': ['traps'],
        'default_category': 'network',
        'source_dir': 'snmp',
    },
}


def get_connector_path(addon_id: str) -> Path:
    """Get the path to a connector's source directory."""
    source_dir = BUILTIN_ADDONS.get(addon_id, {}).get('source_dir', addon_id)
    return PROJECT_ROOT / 'backend' / 'connectors' / source_dir


def generate_manifest(addon_id: str) -> dict:
    """Generate manifest.json for an addon."""
    if addon_id not in BUILTIN_ADDONS:
        raise ValueError(f"Unknown addon: {addon_id}")
    
    meta = BUILTIN_ADDONS[addon_id]
    
    return {
        'id': addon_id,
        'name': meta['name'],
        'version': meta['version'],
        'category': meta['category'],
        'description': meta['description'],
        'author': meta['author'],
        'license': 'Proprietary',
        'connector_class': meta['connector_class'],
        'normalizer_class': meta['normalizer_class'],
        'capabilities': meta['capabilities'],
        'dependencies': [],
        'min_opsconductor_version': '2.0.0',
        'default_category': meta.get('default_category', 'unknown'),
        'created_at': datetime.utcnow().isoformat() + 'Z',
    }


def generate_install_sql(addon_id: str) -> str:
    """Generate install.sql migration for an addon."""
    meta = BUILTIN_ADDONS.get(addon_id, {})
    default_category = meta.get('default_category', 'unknown')
    
    return f"""-- Install migration for {addon_id} addon
-- This file is executed when the addon is installed

-- Severity mappings for {addon_id}
-- Add your severity mappings here using:
-- INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description)
-- VALUES ('{addon_id}', 'event_name', 'event_type', 'warning', true, 'Description')
-- ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
--     target_severity = EXCLUDED.target_severity,
--     description = EXCLUDED.description;

-- Category mappings for {addon_id}
-- Add your category mappings here using:
-- INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description)
-- VALUES ('{addon_id}', 'event_name', 'event_type', '{default_category}', true, 'Description')
-- ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
--     target_category = EXCLUDED.target_category,
--     description = EXCLUDED.description;
"""


def generate_uninstall_sql(addon_id: str) -> str:
    """Generate uninstall.sql migration for an addon."""
    return f"""-- Uninstall migration for {addon_id} addon
-- This file is executed when the addon is uninstalled

-- Remove all severity mappings for this connector
DELETE FROM severity_mappings WHERE connector_type = '{addon_id}';

-- Remove all category mappings for this connector
DELETE FROM category_mappings WHERE connector_type = '{addon_id}';

-- Add any additional cleanup here (addon-specific tables, etc.)
"""


def export_db_mappings(addon_id: str) -> str:
    """Export current DB mappings as SQL INSERT statements."""
    try:
        from backend.utils.db import db_query
        
        lines = [f"-- Exported mappings for {addon_id}"]
        lines.append(f"-- Generated at {datetime.utcnow().isoformat()}Z\n")
        
        # Export severity mappings
        severity_rows = db_query(
            "SELECT source_value, source_field, target_severity, enabled, description "
            "FROM severity_mappings WHERE connector_type = %s ORDER BY source_value",
            (addon_id,)
        )
        
        if severity_rows:
            lines.append("-- Severity mappings")
            lines.append(f"INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES")
            values = []
            for row in severity_rows:
                desc = (row['description'] or '').replace("'", "''")
                values.append(
                    f"('{addon_id}', '{row['source_value']}', '{row['source_field']}', "
                    f"'{row['target_severity']}', {str(row['enabled']).lower()}, '{desc}')"
                )
            lines.append(",\n".join(values))
            lines.append("ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET")
            lines.append("    target_severity = EXCLUDED.target_severity,")
            lines.append("    description = EXCLUDED.description;\n")
        
        # Export category mappings
        category_rows = db_query(
            "SELECT source_value, source_field, target_category, enabled, description "
            "FROM category_mappings WHERE connector_type = %s ORDER BY source_value",
            (addon_id,)
        )
        
        if category_rows:
            lines.append("-- Category mappings")
            lines.append(f"INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES")
            values = []
            for row in category_rows:
                desc = (row['description'] or '').replace("'", "''")
                values.append(
                    f"('{addon_id}', '{row['source_value']}', '{row['source_field']}', "
                    f"'{row['target_category']}', {str(row['enabled']).lower()}, '{desc}')"
                )
            lines.append(",\n".join(values))
            lines.append("ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET")
            lines.append("    target_category = EXCLUDED.target_category,")
            lines.append("    description = EXCLUDED.description;\n")
        
        return "\n".join(lines)
        
    except Exception as e:
        print(f"Warning: Could not export DB mappings: {e}")
        return generate_install_sql(addon_id)


def extract_addon(addon_id: str, output_dir: str, include_db_mappings: bool = True) -> str:
    """
    Extract an existing connector as an installable addon package.
    
    Returns the path to the created zip file.
    """
    if addon_id not in BUILTIN_ADDONS:
        raise ValueError(f"Unknown addon: {addon_id}. Available: {list(BUILTIN_ADDONS.keys())}")
    
    meta = BUILTIN_ADDONS[addon_id]
    connector_path = get_connector_path(addon_id)
    
    if not connector_path.exists():
        raise FileNotFoundError(f"Connector source not found: {connector_path}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for packaging
    temp_dir = output_path / f".{addon_id}_temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    try:
        # Create directory structure
        backend_dir = temp_dir / 'backend'
        migrations_dir = temp_dir / 'migrations'
        config_dir = temp_dir / 'config'
        
        backend_dir.mkdir()
        migrations_dir.mkdir()
        config_dir.mkdir()
        
        # Copy connector.py
        connector_file = connector_path / 'connector.py'
        if connector_file.exists():
            shutil.copy(connector_file, backend_dir / 'connector.py')
        
        # Copy normalizer.py (or alternate file)
        normalizer_filename = meta.get('normalizer_file', 'normalizer.py')
        normalizer_file = connector_path / normalizer_filename
        if normalizer_file.exists():
            shutil.copy(normalizer_file, backend_dir / 'normalizer.py')
        
        # Copy __init__.py if exists
        init_file = connector_path / '__init__.py'
        if init_file.exists():
            shutil.copy(init_file, backend_dir / '__init__.py')
        else:
            (backend_dir / '__init__.py').write_text(f"# {meta['name']} addon\n")
        
        # Generate manifest.json
        manifest = generate_manifest(addon_id)
        (temp_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        
        # Generate install.sql (with DB mappings if available)
        if include_db_mappings:
            install_sql = export_db_mappings(addon_id)
        else:
            install_sql = generate_install_sql(addon_id)
        (migrations_dir / 'install.sql').write_text(install_sql)
        
        # Generate uninstall.sql
        uninstall_sql = generate_uninstall_sql(addon_id)
        (migrations_dir / 'uninstall.sql').write_text(uninstall_sql)
        
        # Generate default config
        default_config = {
            'poll_interval': 60,
            'enabled': True,
        }
        (config_dir / 'defaults.json').write_text(json.dumps(default_config, indent=2))
        
        # Generate README
        readme = f"""# {meta['name']}

{meta['description']}

## Installation

Upload this zip file via the OpsConductor Addons page at `/connectors/addons`.

## Configuration

Configure this addon in the Connectors settings after installation.

## Version

- Version: {meta['version']}
- Author: {meta['author']}
- Category: {meta['category']}
- Capabilities: {', '.join(meta['capabilities'])}
"""
        (temp_dir / 'README.md').write_text(readme)
        
        # Create zip file
        zip_filename = f"{addon_id}-{meta['version']}.zip"
        zip_path = output_path / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    zf.write(file_path, arcname)
        
        print(f"Created addon package: {zip_path}")
        return str(zip_path)
        
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def extract_all_addons(output_dir: str, include_db_mappings: bool = True) -> list:
    """Extract all built-in addons as installable packages."""
    results = []
    for addon_id in BUILTIN_ADDONS:
        try:
            zip_path = extract_addon(addon_id, output_dir, include_db_mappings)
            results.append({'addon_id': addon_id, 'path': zip_path, 'success': True})
        except Exception as e:
            print(f"Error extracting {addon_id}: {e}")
            results.append({'addon_id': addon_id, 'error': str(e), 'success': False})
    return results


def list_addons():
    """List all available built-in addons."""
    print("\nAvailable built-in addons:\n")
    print(f"{'ID':<15} {'Name':<25} {'Category':<10} {'Description'}")
    print("-" * 80)
    for addon_id, meta in BUILTIN_ADDONS.items():
        print(f"{addon_id:<15} {meta['name']:<25} {meta['category']:<10} {meta['description'][:40]}...")


def main():
    parser = argparse.ArgumentParser(description='OpsConductor Addon Packager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Extract single addon
    extract_parser = subparsers.add_parser('extract', help='Extract a single addon as zip')
    extract_parser.add_argument('addon_id', help='Addon ID to extract')
    extract_parser.add_argument('--output', '-o', default='./addons', help='Output directory')
    extract_parser.add_argument('--no-db', action='store_true', help='Skip exporting DB mappings')
    
    # Extract all addons
    extract_all_parser = subparsers.add_parser('extract-all', help='Extract all addons')
    extract_all_parser.add_argument('--output', '-o', default='./addons', help='Output directory')
    extract_all_parser.add_argument('--no-db', action='store_true', help='Skip exporting DB mappings')
    
    # List addons
    subparsers.add_parser('list', help='List available addons')
    
    args = parser.parse_args()
    
    if args.command == 'extract':
        extract_addon(args.addon_id, args.output, not args.no_db)
    elif args.command == 'extract-all':
        extract_all_addons(args.output, not args.no_db)
    elif args.command == 'list':
        list_addons()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
