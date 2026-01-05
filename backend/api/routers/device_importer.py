"""
Device Importer API Router - FastAPI.

Routes for importing devices from various sources.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ImportRequest(BaseModel):
    source: str  # prtg, csv, netbox, manual
    data: Optional[List[Dict[str, Any]]] = None
    options: Optional[Dict[str, Any]] = None


class CSVImportRequest(BaseModel):
    csv_content: str
    column_mapping: Dict[str, str]
    has_header: bool = True


@router.get("/sources")
async def list_import_sources():
    """List available import sources."""
    return success_response({
        "sources": [
            {"id": "prtg", "name": "PRTG", "description": "Import from PRTG monitoring system"},
            {"id": "csv", "name": "CSV File", "description": "Import from CSV file"},
            {"id": "netbox", "name": "NetBox", "description": "Import from NetBox DCIM"},
            {"id": "manual", "name": "Manual Entry", "description": "Manually enter devices"},
        ]
    })


@router.post("/preview")
async def preview_import(req: ImportRequest):
    """Preview devices to be imported."""
    try:
        if req.source == "prtg":
            from backend.services.prtg_service import PRTGService
            # Get PRTG settings and fetch devices
            return success_response({
                "devices": [],
                "count": 0,
                "message": "PRTG preview - connect to PRTG to see devices"
            })
        
        elif req.source == "csv" and req.data:
            return success_response({
                "devices": req.data[:10],  # Preview first 10
                "count": len(req.data),
                "message": f"CSV preview - {len(req.data)} devices found"
            })
        
        elif req.source == "netbox":
            from backend.api.routers.netbox import get_netbox_service
            netbox = get_netbox_service()
            if netbox.is_configured:
                result = netbox.get_devices(limit=10)
                return success_response({
                    "devices": result.get('results', [])[:10],
                    "count": result.get('count', 0),
                    "message": "NetBox preview"
                })
            return error_response('NOT_CONFIGURED', 'NetBox not configured')
        
        return success_response({"devices": [], "count": 0})
        
    except Exception as e:
        logger.error(f"Import preview error: {e}")
        return error_response('IMPORT_ERROR', str(e))


@router.post("/execute")
async def execute_import(req: ImportRequest):
    """Execute device import."""
    try:
        imported = 0
        errors = []
        
        if req.source == "manual" and req.data:
            db = get_db()
            with db.cursor() as cursor:
                for device in req.data:
                    try:
                        # Import to local cache or NetBox
                        cursor.execute("""
                            INSERT INTO netbox_device_cache 
                            (device_name, device_ip, device_type, site_name, cached_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            ON CONFLICT (device_ip) DO UPDATE SET
                                device_name = EXCLUDED.device_name,
                                device_type = EXCLUDED.device_type,
                                site_name = EXCLUDED.site_name,
                                cached_at = NOW()
                        """, (
                            device.get('name', device.get('hostname', '')),
                            device.get('ip', device.get('ip_address', '')),
                            device.get('type', device.get('device_type', '')),
                            device.get('site', ''),
                        ))
                        imported += 1
                    except Exception as e:
                        errors.append({"device": device, "error": str(e)})
                db.commit()
        
        return success_response({
            "imported": imported,
            "errors": errors,
            "error_count": len(errors)
        })
        
    except Exception as e:
        logger.error(f"Import execute error: {e}")
        return error_response('IMPORT_ERROR', str(e))


@router.post("/csv/parse")
async def parse_csv(req: CSVImportRequest):
    """Parse CSV content and return devices."""
    try:
        import csv
        from io import StringIO
        
        reader = csv.reader(StringIO(req.csv_content))
        rows = list(reader)
        
        if not rows:
            return error_response('EMPTY_CSV', 'CSV content is empty')
        
        if req.has_header:
            headers = rows[0]
            data_rows = rows[1:]
        else:
            headers = [f"col_{i}" for i in range(len(rows[0]))]
            data_rows = rows
        
        devices = []
        for row in data_rows:
            device = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    header = headers[i]
                    # Map to standard field if mapping provided
                    mapped_field = req.column_mapping.get(header, header)
                    device[mapped_field] = value
            devices.append(device)
        
        return success_response({
            "headers": headers,
            "devices": devices,
            "count": len(devices)
        })
        
    except Exception as e:
        logger.error(f"CSV parse error: {e}")
        return error_response('PARSE_ERROR', str(e))


@router.get("/history")
async def get_import_history(limit: int = 20):
    """Get import history."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, source, imported_count, error_count, created_at, created_by
            FROM import_history
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        history = [dict(row) for row in cursor.fetchall()]
    return list_response(history)
