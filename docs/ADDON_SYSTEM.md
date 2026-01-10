# OpsConductor Addon System

## Overview

Addons are self-contained connector/normalizer packages that can be installed, uninstalled, and reinstalled cleanly. Every connector in OpsConductor is an addon - there are no "special" built-in connectors that work differently.

## Addon Package Structure

```
addon-id.zip
├── manifest.json              # Required: Addon metadata
├── backend/
│   ├── __init__.py
│   ├── connector.py          # Connector class
│   └── normalizer.py         # Normalizer class
├── migrations/
│   ├── install.sql           # Run on install (severity/category mappings)
│   └── uninstall.sql         # Run on uninstall (cleanup)
├── config/
│   └── defaults.json         # Default configuration values
└── README.md                 # Documentation
```

## manifest.json Schema

```json
{
  "id": "axis",
  "name": "Axis Cameras",
  "version": "1.0.0",
  "category": "device",
  "description": "Monitor Axis network cameras via VAPIX",
  "author": "OpsConductor",
  "license": "MIT",
  "connector_class": "AxisConnector",
  "normalizer_class": "AxisNormalizer",
  "base_classes": {
    "connector": "BaseConnector",
    "normalizer": "BaseNormalizer"
  },
  "capabilities": ["polling", "webhooks"],
  "dependencies": [],
  "min_opsconductor_version": "2.0.0",
  "config_schema": {
    "type": "object",
    "properties": {
      "poll_interval": {
        "type": "integer",
        "default": 60,
        "description": "Polling interval in seconds"
      }
    }
  }
}
```

## Addon Lifecycle

### Installation

1. **Validate Package**
   - Check manifest.json exists and is valid
   - Verify required files (connector.py, normalizer.py)
   - Check version compatibility

2. **Extract Files**
   - Extract to `/var/opsconductor/addons/{addon_id}/`
   - Set appropriate permissions

3. **Run Install Migration**
   - Execute `migrations/install.sql`
   - Inserts severity_mappings, category_mappings
   - Creates any addon-specific tables

4. **Register in Database**
   - Insert into `installed_addons` table
   - Record manifest, config, installation time

5. **Load Addon**
   - Dynamically import connector and normalizer classes
   - Make available to polling/webhook systems

### Uninstallation

1. **Stop Active Usage**
   - Stop any pollers using this connector
   - Disconnect any webhook listeners

2. **Run Uninstall Migration**
   - Execute `migrations/uninstall.sql`
   - Removes severity_mappings WHERE connector_type = '{addon_id}'
   - Removes category_mappings WHERE connector_type = '{addon_id}'
   - Drops any addon-specific tables

3. **Unload from Runtime**
   - Remove from loaded addons cache
   - Clear any cached mappings

4. **Remove from Database**
   - Delete from `installed_addons`
   - Delete from `addon_migrations`

5. **Delete Files**
   - Remove `/var/opsconductor/addons/{addon_id}/` directory

### Reinstallation

Simply install again from the same or updated package. The install migration uses `ON CONFLICT DO UPDATE` to handle existing data gracefully.

## Built-in Addons

Built-in addons ship with OpsConductor source code in `backend/connectors/`. They are special only in:

1. **Source Location**: Code lives in repo, not `/var/opsconductor/addons/`
2. **Cannot Delete Files**: Uninstall cleans DB but doesn't remove source
3. **Pre-registered**: Seeded in `installed_addons` during initial migration

When a built-in addon is "uninstalled":
- DB mappings are removed
- Marked as `enabled = false` and `installed = false` in `installed_addons`
- Not loaded at runtime
- Can be "reinstalled" which re-runs the install migration and re-enables

## Addon Extraction Tool

The extraction tool packages an existing connector as an installable addon zip:

```bash
python -m backend.tools.addon_packager extract axis --output ./addons/
```

This:
1. Reads connector/normalizer from `backend/connectors/{id}/`
2. Generates manifest.json from code analysis
3. Exports current DB mappings as install.sql
4. Creates uninstall.sql to reverse install.sql
5. Packages everything into `{id}-{version}.zip`

## Database Schema

### installed_addons

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(64) PK | Addon identifier (e.g., "axis") |
| name | VARCHAR(255) | Display name |
| version | VARCHAR(32) | Semantic version |
| category | VARCHAR(32) | "nms" or "device" |
| description | TEXT | Description |
| author | VARCHAR(255) | Author name |
| enabled | BOOLEAN | Currently enabled |
| installed | BOOLEAN | Currently installed (false = uninstalled) |
| installed_at | TIMESTAMPTZ | First installation time |
| uninstalled_at | TIMESTAMPTZ | Last uninstall time (null if installed) |
| updated_at | TIMESTAMPTZ | Last update time |
| manifest | JSONB | Full manifest.json |
| config | JSONB | User configuration |
| storage_path | VARCHAR(512) | Path to addon files |
| is_builtin | BOOLEAN | Ships with OpsConductor |

### addon_migrations

Tracks which migrations have been applied for each addon.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Migration ID |
| addon_id | VARCHAR(64) FK | Addon reference |
| migration_name | VARCHAR(255) | Migration file name |
| applied_at | TIMESTAMPTZ | When applied |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/addons | List all addons |
| GET | /api/v1/addons/{id} | Get addon details |
| POST | /api/v1/addons/install | Upload and install addon zip |
| POST | /api/v1/addons/{id}/enable | Enable addon |
| POST | /api/v1/addons/{id}/disable | Disable addon (keeps installed) |
| DELETE | /api/v1/addons/{id} | Uninstall addon |
| POST | /api/v1/addons/{id}/reinstall | Reinstall addon |
| GET | /api/v1/addons/{id}/export | Export addon as zip |
| PUT | /api/v1/addons/{id}/config | Update addon config |

## Frontend Location

Addons page is at `/connectors/addons` under the Connectors module, since addons ARE connectors.
