"""
OpsConductor Backend - Full FastAPI (No Flask).

Async-native API server with pysnmp 7.x support.
"""

import os
import sys
import json
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db
from backend.services.logging_service import logging_service, get_logger, LogSource


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    db = get_db()
    logging_service.initialize(db_connection=db, log_level=log_level)
    logger = get_logger(__name__, LogSource.SYSTEM)
    logger.info("OpsConductor FastAPI backend starting", category='startup')
    yield
    logger.info("OpsConductor FastAPI backend stopping", category='shutdown')


app = FastAPI(
    title="OpsConductor API",
    description="Network monitoring and automation platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health
# ============================================================================

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "opsconductor-api"}


# ============================================================================
# Legacy /data endpoint
# ============================================================================

@app.get("/data")
async def get_data():
    """Get all devices from NetBox cache."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT netbox_device_id as id, netbox_device_id as netbox_id, 
                   device_name as hostname, device_ip as ip_address, 
                   device_type, manufacturer, site_name as site, role_name as role,
                   'online' as ping_status, 'YES' as snmp_status,
                   device_name as snmp_hostname, device_type as snmp_model,
                   '' as snmp_serial, manufacturer as snmp_vendor_name,
                   device_type as snmp_description, '' as network_range,
                   'netbox' as source, '' as netbox_url, cached_at as last_updated
            FROM netbox_device_cache ORDER BY device_name
        """)
        return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# Auth endpoints
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    import bcrypt
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id, username, password_hash, display_name, email FROM users WHERE username = %s", (req.username,))
        user = cursor.fetchone()
        if not user:
            return JSONResponse(status_code=401, content={"success": False, "error": {"code": "AUTH_FAILED", "message": "Invalid username or password"}})
        
        # Verify bcrypt password
        if not user['password_hash'] or not bcrypt.checkpw(req.password.encode(), user['password_hash'].encode()):
            return JSONResponse(status_code=401, content={"success": False, "error": {"code": "AUTH_FAILED", "message": "Invalid username or password"}})
        
        # Get user roles
        cursor.execute("""
            SELECT r.name FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = %s
        """, (user['id'],))
        roles = [row['name'] for row in cursor.fetchall()]
        role = roles[0] if roles else 'user'
        
        import secrets
        import hashlib
        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cursor.execute("INSERT INTO user_sessions (user_id, session_token_hash, expires_at) VALUES (%s, %s, NOW() + INTERVAL '24 hours')", (user['id'], token_hash))
        
        return {"success": True, "data": {"token": token, "user": {"id": user['id'], "username": user['username'], "role": role, "display_name": user['display_name'], "email": user['email']}}}

@app.get("/api/auth/status")
async def auth_status(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {"success": True, "data": {"authenticated": False}}
    
    db = get_db()
    with db.cursor() as cursor:
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check for enterprise session first
        cursor.execute("""
            SELECT s.id, s.enterprise_username, s.is_enterprise
            FROM user_sessions s
            WHERE s.session_token_hash = %s AND s.expires_at > NOW() AND s.revoked = false AND s.is_enterprise = true
        """, (token_hash,))
        enterprise_session = cursor.fetchone()
        
        if enterprise_session:
            cursor.execute("""
                SELECT eur.id, eur.username, eur.email, eur.display_name, r.name as role_name
                FROM enterprise_user_roles eur
                JOIN roles r ON eur.role_id = r.id
                WHERE eur.username = %s
            """, (enterprise_session['enterprise_username'],))
            eur = cursor.fetchone()
            if eur:
                return {"success": True, "data": {"authenticated": True, "user": {
                    "id": eur['id'],
                    "username": eur['username'],
                    "email": eur['email'] or '',
                    "display_name": eur['display_name'] or eur['username'],
                    "role": eur['role_name'],
                    "is_enterprise": True
                }}}
        
        # Check for regular user session
        cursor.execute("""
            SELECT u.id, u.username, u.display_name, u.email FROM users u
            JOIN user_sessions s ON s.user_id = u.id
            WHERE s.session_token_hash = %s AND s.expires_at > NOW() AND s.revoked = false
        """, (token_hash,))
        user = cursor.fetchone()
        if user:
            cursor.execute("""
                SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s
            """, (user['id'],))
            roles = [row['name'] for row in cursor.fetchall()]
            user_dict = dict(user)
            user_dict['role'] = roles[0] if roles else 'user'
            return {"success": True, "data": {"authenticated": True, "user": user_dict}}
    return {"success": True, "data": {"authenticated": False}}

@app.get("/api/auth/me")
async def auth_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse(status_code=401, content={"success": False, "error": {"code": "UNAUTHORIZED", "message": "Not authenticated"}})
    
    db = get_db()
    with db.cursor() as cursor:
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # First check for enterprise session
        cursor.execute("""
            SELECT s.id, s.enterprise_username, s.is_enterprise
            FROM user_sessions s
            WHERE s.session_token_hash = %s AND s.expires_at > NOW() AND s.revoked = false AND s.is_enterprise = true
        """, (token_hash,))
        enterprise_session = cursor.fetchone()
        
        if enterprise_session:
            # Get enterprise user info from enterprise_user_roles
            cursor.execute("""
                SELECT eur.id, eur.username, eur.email, eur.display_name, r.name as role_name
                FROM enterprise_user_roles eur
                JOIN roles r ON eur.role_id = r.id
                WHERE eur.username = %s
            """, (enterprise_session['enterprise_username'],))
            eur = cursor.fetchone()
            if eur:
                return {"success": True, "data": {"user": {
                    "id": eur['id'],
                    "username": eur['username'],
                    "email": eur['email'] or '',
                    "display_name": eur['display_name'] or eur['username'],
                    "role": eur['role_name'],
                    "roles": [eur['role_name']],
                    "is_enterprise": True
                }}}
        
        # Check for regular user session
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.display_name FROM users u
            JOIN user_sessions s ON s.user_id = u.id
            WHERE s.session_token_hash = %s AND s.expires_at > NOW() AND s.revoked = false
        """, (token_hash,))
        user = cursor.fetchone()
        if user:
            cursor.execute("""
                SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = %s
            """, (user['id'],))
            roles = [row['name'] for row in cursor.fetchall()]
            user_dict = dict(user)
            user_dict['role'] = roles[0] if roles else 'user'
            user_dict['roles'] = roles
            return {"success": True, "data": {"user": user_dict}}
    return JSONResponse(status_code=401, content={"success": False, "error": {"code": "UNAUTHORIZED", "message": "Session expired"}})

@app.get("/api/auth/enterprise-configs")
async def auth_enterprise_configs():
    """Get available enterprise auth configurations for login page."""
    try:
        from backend.services.auth_service import get_auth_service
        auth_service = get_auth_service()
        configs = auth_service.get_enterprise_auth_configs_for_login()
        return {"success": True, "data": {"configs": configs}}
    except Exception as e:
        return {"success": True, "data": {"configs": []}}

class EnterpriseLoginRequest(BaseModel):
    username: str
    password: str
    config_id: int

@app.post("/api/auth/login/enterprise")
async def login_enterprise(req: EnterpriseLoginRequest, request: Request):
    """Authenticate user with enterprise auth (LDAP/AD)."""
    try:
        from backend.services.auth_service import get_auth_service
        auth_service = get_auth_service()
        
        success, result, error = auth_service.authenticate_ldap(
            username=req.username,
            password=req.password,
            config_id=req.config_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return JSONResponse(status_code=401, content={"success": False, "error": {"code": "AUTH_FAILED", "message": error}})
        
        if result.get('requires_2fa'):
            return {"success": True, "data": {"requires_2fa": True, "user_id": result['user_id'], "two_factor_method": result['two_factor_method']}}
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": result['user_id'],
                    "username": result['username'],
                    "email": result.get('email', ''),
                    "display_name": result.get('display_name', result['username']),
                    "roles": result.get('roles', []),
                    "permissions": result.get('permissions', []),
                    "is_enterprise": True
                },
                "session_token": result['session_token'],
                "refresh_token": result.get('refresh_token'),
                "expires_at": result.get('expires_at')
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": {"code": "SERVER_ERROR", "message": str(e)}})


# ============================================================================
# Polling endpoints
# ============================================================================

@app.get("/api/polling/status")
async def polling_status():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) as total_configs,
                   COUNT(*) FILTER (WHERE enabled = true) as enabled_configs,
                   COUNT(*) FILTER (WHERE last_run_status = 'success') as successful_last_run,
                   COUNT(*) FILTER (WHERE last_run_status = 'failed') as failed_last_run
            FROM polling_configs
        """)
        configs = dict(cursor.fetchone())
        
        cursor.execute("""
            SELECT COUNT(*) as total_executions,
                   COUNT(*) FILTER (WHERE status = 'success') as successful,
                   COUNT(*) FILTER (WHERE status = 'failed') as failed,
                   AVG(duration_ms) as avg_duration_ms,
                   SUM(records_collected) as total_records
            FROM polling_executions WHERE started_at > NOW() - INTERVAL '24 hours'
        """)
        executions = dict(cursor.fetchone())
        
        cursor.execute("""
            SELECT name, poll_type, interval_seconds, last_run_at
            FROM polling_configs WHERE enabled = true
            ORDER BY last_run_at ASC NULLS FIRST LIMIT 10
        """)
        upcoming = [dict(row) for row in cursor.fetchall()]
    
    return {"success": True, "data": {"configs": configs, "executions_24h": executions, "upcoming_polls": upcoming}}


# ============================================================================
# SNMP endpoints (async with pysnmp 7.x)
# ============================================================================

from backend.services.ciena_snmp_service import CienaSNMPService, CienaSNMPError
import asyncio
import concurrent.futures

# Thread pool for SNMP operations - pysnmp 7.x async doesn't work in uvicorn's event loop
_snmp_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="snmp")

def _run_snmp_async(host: str, community: str, method: str):
    """Run async SNMP method in a new event loop in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        service = CienaSNMPService(host, community)
        if method == "alarms":
            return loop.run_until_complete(service._get_active_alarms_async())
        elif method == "system":
            return loop.run_until_complete(service._get_system_info_async())
    finally:
        loop.close()

@app.get("/api/snmp/alarms/{host}")
async def get_snmp_alarms(host: str, community: str = "public"):
    """Get active alarms from Ciena switch via SNMP."""
    loop = asyncio.get_event_loop()
    try:
        alarms = await asyncio.wait_for(
            loop.run_in_executor(_snmp_executor, _run_snmp_async, host, community, "alarms"),
            timeout=30.0
        )
        
        by_severity = {}
        for alarm in alarms:
            sev = alarm.get('severity', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return {"success": True, "data": {"host": host, "alarms": alarms, "count": len(alarms), "by_severity": by_severity}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="SNMP request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/snmp/system/{host}")
async def get_snmp_system(host: str, community: str = "public"):
    """Get system info from switch via SNMP."""
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_snmp_executor, _run_snmp_async, host, community, "system"),
            timeout=30.0
        )
        return {"success": True, "data": result}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="SNMP request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Traps endpoints
# ============================================================================

@app.get("/api/traps/status")
async def traps_status():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM trap_receiver_status ORDER BY last_updated DESC LIMIT 1")
        status = cursor.fetchone()
        cursor.execute("""
            SELECT COUNT(*) as total_traps,
                   COUNT(*) FILTER (WHERE received_at > NOW() - INTERVAL '1 hour') as last_hour,
                   COUNT(*) FILTER (WHERE received_at > NOW() - INTERVAL '24 hours') as last_24h
            FROM trap_log
        """)
        stats = dict(cursor.fetchone())
    return {"success": True, "data": {"status": dict(status) if status else None, "statistics": stats}}

@app.get("/api/traps/log")
async def traps_log(limit: int = 100, offset: int = 0, source_ip: Optional[str] = None):
    db = get_db()
    with db.cursor() as cursor:
        query = "SELECT * FROM trap_log"
        params = []
        if source_ip:
            query += " WHERE source_ip = %s"
            params.append(source_ip)
        query += " ORDER BY received_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cursor.execute(query, params)
        traps = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": {"traps": traps, "limit": limit, "offset": offset}}


# ============================================================================
# Settings endpoints
# ============================================================================

@app.get("/api/settings")
async def get_settings():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings")
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
    return {"success": True, "data": settings}


# ============================================================================
# Metrics endpoints
# ============================================================================

@app.get("/api/metrics/optical/{ip}")
async def get_optical_metrics(ip: str, hours: int = 24):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT port_id, port_name, rx_power_dbm, tx_power_dbm, temperature, collected_at
            FROM optical_metrics
            WHERE device_ip = %s AND collected_at > NOW() - INTERVAL '%s hours'
            ORDER BY collected_at DESC
        """, (ip, hours))
        metrics = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": metrics}

@app.get("/api/metrics/interfaces/{ip}")
async def get_interface_metrics(ip: str, hours: int = 24):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT interface_name, rx_bytes, tx_bytes, rx_packets, tx_packets, collected_at
            FROM interface_metrics
            WHERE device_ip = %s AND collected_at > NOW() - INTERVAL '%s hours'
            ORDER BY collected_at DESC
        """, (ip, hours))
        metrics = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": metrics}

@app.get("/api/metrics/availability/{ip}")
async def get_availability_metrics(ip: str, hours: int = 24):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT device_ip, is_available, response_time_ms, check_type, checked_at
            FROM availability_metrics
            WHERE device_ip = %s AND checked_at > NOW() - INTERVAL '%s hours'
            ORDER BY checked_at DESC
        """, (ip, hours))
        metrics = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": metrics}


# ============================================================================
# Polling endpoints (additional)
# ============================================================================

@app.get("/api/polling/configs")
async def list_polling_configs(enabled: Optional[bool] = None, poll_type: Optional[str] = None):
    db = get_db()
    with db.cursor() as cursor:
        query = "SELECT * FROM polling_configs WHERE 1=1"
        params = []
        if enabled is not None:
            query += " AND enabled = %s"
            params.append(enabled)
        if poll_type:
            query += " AND poll_type = %s"
            params.append(poll_type)
        query += " ORDER BY name"
        cursor.execute(query, params)
        configs = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": {"configs": configs, "count": len(configs)}}

@app.get("/api/polling/executions")
async def list_polling_executions(limit: int = 20, offset: int = 0):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM polling_executions 
            ORDER BY started_at DESC LIMIT %s OFFSET %s
        """, (limit, offset))
        executions = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": {"executions": executions}}

@app.get("/api/polling/poll-types")
async def list_poll_types():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM snmp_poll_types ORDER BY name")
        poll_types = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": {"poll_types": poll_types}}

@app.get("/api/polling/target-types")
async def list_target_types():
    return {"success": True, "data": {"target_types": [
        {"id": "device", "name": "Single Device", "description": "Poll a specific device by IP"},
        {"id": "site", "name": "Site", "description": "Poll all devices at a site"},
        {"id": "role", "name": "Role", "description": "Poll all devices with a specific role"},
        {"id": "manufacturer", "name": "Manufacturer", "description": "Poll all devices from a manufacturer"},
        {"id": "all", "name": "All Devices", "description": "Poll all devices"}
    ]}}


# ============================================================================
# MCP endpoints
# ============================================================================

@app.get("/api/mcp/services/summary")
async def mcp_services_summary():
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mcp_services')")
            if cursor.fetchone()[0]:
                cursor.execute("""
                    SELECT COUNT(*) as total_services,
                           COUNT(*) FILTER (WHERE admin_state = 'enabled') as enabled,
                           COUNT(*) FILTER (WHERE oper_state = 'up') as up
                    FROM mcp_services
                """)
                row = cursor.fetchone()
                if row:
                    return {"success": True, "data": dict(row)}
    except Exception:
        pass
    return {"success": True, "data": {"total_services": 0, "enabled": 0, "up": 0}}

@app.get("/api/mcp/services/rings")
async def mcp_services_rings():
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mcp_rings')")
            if cursor.fetchone()[0]:
                cursor.execute("SELECT * FROM mcp_rings ORDER BY ring_name")
                rings = [dict(row) for row in cursor.fetchall()]
                return {"success": True, "data": {"rings": rings}}
    except Exception:
        pass
    return {"success": True, "data": {"rings": []}}

@app.get("/api/mcp/devices")
async def mcp_devices():
    """Get devices from MCP - returns empty if MCP not configured."""
    return {"success": True, "data": {"devices": [], "total": 0}}

@app.get("/api/mcp/services")
async def mcp_services():
    """Get services from MCP - returns empty if not configured."""
    return {"success": True, "data": {"services": [], "total": 0}}

@app.get("/api/mcp/settings")
async def mcp_settings():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'mcp_%'")
        settings = {}
        for row in cursor.fetchall():
            key = row['key'].replace('mcp_', '')
            settings[key] = row['value']
        if settings.get('password'):
            settings['password_configured'] = True
            settings['password'] = '••••••••'
        else:
            settings['password_configured'] = False
    return {"success": True, "data": settings}

@app.put("/api/mcp/settings")
async def update_mcp_settings(request: Request):
    data = await request.json()
    db = get_db()
    with db.cursor() as cursor:
        for key, value in data.items():
            if key == 'password' and value == '••••••••':
                continue
            cursor.execute(
                "INSERT INTO system_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
                (f'mcp_{key}', str(value), str(value))
            )
    return {"success": True}

@app.post("/api/mcp/test")
async def test_mcp():
    """Test MCP connection."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'mcp_%'")
        settings = {row['key'].replace('mcp_', ''): row['value'] for row in cursor.fetchall()}
    
    url = settings.get('url', '').rstrip('/')
    username = settings.get('username')
    password = settings.get('password')
    
    if not url or not username or not password:
        return {"success": False, "data": {"success": False, "message": "MCP URL, username, or password not configured"}}
    
    try:
        import requests
        # Try to authenticate with MCP using correct endpoint
        auth_url = f"{url}/tron/api/v1/tokens"
        resp = requests.post(auth_url, json={"username": username, "password": password}, timeout=10, verify=False)
        if resp.status_code in (200, 201):
            data = resp.json()
            if not data.get('isSuccessful', True) == False:
                token = data.get('token')
                if token:
                    # Get actual device count from MCP using correct endpoint
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    devices_resp = requests.get(f"{url}/nsi/api/search/networkConstructs?limit=1", headers=headers, timeout=10, verify=False)
                    device_count = 0
                    if devices_resp.status_code == 200:
                        devices_data = devices_resp.json()
                        # Get total from meta pagination info
                        device_count = devices_data.get('meta', {}).get('total', len(devices_data.get('data', [])))
                    return {"success": True, "data": {"success": True, "message": "Connection successful", "summary": {"devices": device_count}}}
                return {"success": True, "data": {"success": True, "message": "Connection successful", "summary": {"devices": 0}}}
            return {"success": True, "data": {"success": False, "message": "Authentication failed"}}
        return {"success": True, "data": {"success": False, "message": f"Authentication failed: HTTP {resp.status_code}"}}
    except Exception as e:
        return {"success": True, "data": {"success": False, "message": str(e)}}


# ============================================================================
# NetBox settings endpoints
# ============================================================================

@app.get("/api/netbox/settings")
async def netbox_settings():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'netbox_%'")
        settings = {}
        for row in cursor.fetchall():
            key = row['key'].replace('netbox_', '')
            settings[key] = row['value']
        if settings.get('token'):
            settings['token_configured'] = True
            settings['token'] = '••••••••'
        else:
            settings['token_configured'] = False
    return {"success": True, "data": settings}

@app.put("/api/netbox/settings")
async def update_netbox_settings(request: Request):
    data = await request.json()
    db = get_db()
    with db.cursor() as cursor:
        for key, value in data.items():
            if key == 'token' and value == '••••••••':
                continue
            cursor.execute(
                "INSERT INTO system_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
                (f'netbox_{key}', str(value), str(value))
            )
    return {"success": True}

@app.post("/api/netbox/test")
async def test_netbox():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT value FROM system_settings WHERE key = 'netbox_url'")
        row = cursor.fetchone()
        url = row['value'] if row else None
        cursor.execute("SELECT value FROM system_settings WHERE key = 'netbox_token'")
        row = cursor.fetchone()
        token = row['value'] if row else None
    
    if not url or not token:
        return {"success": False, "error": "NetBox URL or token not configured"}
    
    try:
        import requests
        resp = requests.get(f"{url}/api/status/", headers={"Authorization": f"Token {token}"}, timeout=10, verify=False)
        if resp.status_code == 200:
            return {"success": True, "message": "Connection successful", "data": resp.json()}
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# PRTG settings endpoints
# ============================================================================

@app.get("/api/prtg/settings")
async def prtg_settings():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'prtg_%'")
        settings = {}
        for row in cursor.fetchall():
            key = row['key'].replace('prtg_', '')
            settings[key] = row['value']
        if settings.get('api_token'):
            settings['api_token_configured'] = True
            settings['api_token'] = '••••••••'
        else:
            settings['api_token_configured'] = False
        if settings.get('passhash'):
            settings['passhash_configured'] = True
            settings['passhash'] = '••••••••'
        else:
            settings['passhash_configured'] = False
    return {"success": True, "data": settings}

@app.put("/api/prtg/settings")
async def update_prtg_settings(request: Request):
    data = await request.json()
    db = get_db()
    with db.cursor() as cursor:
        for key, value in data.items():
            if key in ('api_token', 'passhash') and value == '••••••••':
                continue
            cursor.execute(
                "INSERT INTO system_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
                (f'prtg_{key}', str(value), str(value))
            )
    return {"success": True}

@app.get("/api/prtg/status")
async def prtg_status():
    """Get PRTG connection status."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'prtg_%'")
        settings = {row['key'].replace('prtg_', ''): row['value'] for row in cursor.fetchall()}
    
    url = settings.get('url')
    if not url:
        return {"success": True, "data": {"connected": False, "error": "Not configured"}}
    
    try:
        import requests
        api_token = settings.get('api_token')
        if api_token:
            test_url = f"{url}/api/table.json?content=sensors&count=1&apitoken={api_token}"
        else:
            username = settings.get('username')
            passhash = settings.get('passhash')
            test_url = f"{url}/api/table.json?content=sensors&count=1&username={username}&passhash={passhash}"
        
        resp = requests.get(test_url, timeout=10, verify=settings.get('verify_ssl', 'false').lower() == 'true')
        if resp.status_code == 200:
            data = resp.json()
            # Get actual sensor count from PRTG - treesize is total sensors
            total_count = data.get('treesize', data.get('totalcount', 0))
            prtg_version = data.get('prtg-version', 'Unknown')
            return {"success": True, "data": {
                "connected": True, 
                "version": prtg_version,
                "sensor_count": total_count,
            }}
        return {"success": True, "data": {"connected": False, "error": f"HTTP {resp.status_code}"}}
    except Exception as e:
        return {"success": True, "data": {"connected": False, "error": str(e)}}

@app.post("/api/prtg/test")
async def test_prtg():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'prtg_%'")
        settings = {row['key'].replace('prtg_', ''): row['value'] for row in cursor.fetchall()}
    
    url = settings.get('url')
    if not url:
        return {"success": False, "error": "PRTG URL not configured"}
    
    try:
        import requests
        api_token = settings.get('api_token')
        if api_token:
            test_url = f"{url}/api/table.json?content=sensors&count=1&apitoken={api_token}"
        else:
            username = settings.get('username')
            passhash = settings.get('passhash')
            test_url = f"{url}/api/table.json?content=sensors&count=1&username={username}&passhash={passhash}"
        
        resp = requests.get(test_url, timeout=10, verify=settings.get('verify_ssl', 'false').lower() == 'true')
        if resp.status_code == 200:
            return {"success": True, "message": "Connection successful"}
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Devices endpoints
# ============================================================================

@app.get("/api/devices")
async def list_devices(site: Optional[str] = None, role: Optional[str] = None):
    db = get_db()
    with db.cursor() as cursor:
        query = """
            SELECT netbox_device_id as id, device_name as name, device_ip as ip_address,
                   device_type, manufacturer, site_name as site, role_name as role
            FROM netbox_device_cache WHERE 1=1
        """
        params = []
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if role:
            query += " AND role_name = %s"
            params.append(role)
        query += " ORDER BY device_name"
        cursor.execute(query, params)
        devices = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": devices}


# ============================================================================
# Scheduler endpoints
# ============================================================================

@app.get("/api/scheduler/queues")
async def scheduler_queues():
    """Get queue status for active jobs page."""
    try:
        import sys
        sys.path.insert(0, '/home/opsconductor/opsconductor-monitor/CascadeProjects/windsurf-project')
        from celery_app import celery_app
        
        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        stats = inspect.stats() or {}
        
        total_active = sum(len(v) for v in active.values())
        total_reserved = sum(len(v) for v in reserved.values())
        total_scheduled = sum(len(v) for v in scheduled.values())
        
        workers = []
        total_concurrency = 0
        for worker_name, worker_stats in stats.items():
            # Get concurrency (number of worker processes) from pool info
            pool_info = worker_stats.get("pool", {})
            concurrency = pool_info.get("max-concurrency", 0)
            total_concurrency += concurrency
            workers.append({
                "name": worker_name,
                "status": "online",
                "active_tasks": len(active.get(worker_name, [])),
                "processed": worker_stats.get("total", {}).get("tasks.succeeded", 0),
                "concurrency": concurrency,
            })
        
        return {"success": True, "data": {
            "active": total_active,
            "reserved": total_reserved,
            "scheduled": total_scheduled,
            "concurrency": total_concurrency,
            "workers": workers
        }}
    except Exception as e:
        logger.error(f"Failed to get scheduler queues: {e}")
        return {"success": True, "data": {"active": 0, "reserved": 0, "scheduled": 0, "workers": []}}

@app.get("/api/scheduler/jobs")
async def scheduler_jobs(enabled: Optional[bool] = None, limit: int = 50):
    """List scheduler jobs."""
    db = get_db()
    with db.cursor() as cursor:
        query = "SELECT * FROM scheduler_jobs WHERE 1=1"
        params = []
        if enabled is not None:
            query += " AND enabled = %s"
            params.append(enabled)
        query += " ORDER BY name LIMIT %s"
        params.append(limit)
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": jobs}

@app.get("/api/scheduler/executions")
async def scheduler_executions(limit: int = 50, status: Optional[str] = None, job_name: Optional[str] = None):
    """Get job executions for Job History page."""
    db = get_db()
    with db.cursor() as cursor:
        query = "SELECT * FROM scheduler_job_executions WHERE 1=1"
        params = []
        if status:
            query += " AND status = %s"
            params.append(status)
        if job_name:
            query += " AND job_name ILIKE %s"
            params.append(f"%{job_name}%")
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        cursor.execute(query, params)
        executions = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": executions}

@app.get("/api/scheduler/executions/recent")
async def scheduler_executions_recent(limit: int = 50, status: Optional[str] = None):
    """Get recent job executions."""
    db = get_db()
    with db.cursor() as cursor:
        query = "SELECT * FROM scheduler_job_executions WHERE 1=1"
        params = []
        if status:
            query += " AND status = %s"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        cursor.execute(query, params)
        executions = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": executions}

@app.get("/api/scheduler/executions/{execution_id}/progress")
async def scheduler_execution_progress(execution_id: int):
    """Get progress for a running execution."""
    return {"success": True, "data": {"progress": None}}

@app.post("/api/scheduler/executions/{execution_id}/cancel")
async def scheduler_execution_cancel(execution_id: int):
    """Cancel a running execution."""
    return {"success": True, "data": {"cancelled": True}}


# ============================================================================
# Topology endpoints
# ============================================================================

@app.get("/api/topology")
async def get_topology():
    """Get network topology data."""
    db = get_db()
    with db.cursor() as cursor:
        # Get devices with connections
        cursor.execute("""
            SELECT device_ip, device_name, site_name, manufacturer, device_type
            FROM netbox_device_cache
            WHERE device_ip IS NOT NULL
            LIMIT 500
        """)
        devices = [dict(row) for row in cursor.fetchall()]
        
        # Get links if available
        cursor.execute("""
            SELECT * FROM mcp_links LIMIT 1000
        """) if _table_exists(cursor, 'mcp_links') else None
        links = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    
    return {"success": True, "data": {"nodes": devices, "links": links}}

def _table_exists(cursor, table_name):
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)", (table_name,))
    result = cursor.fetchone()
    return result['exists'] if isinstance(result, dict) else result[0]


# ============================================================================
# Alerts endpoints
# ============================================================================

@app.get("/api/alerts")
async def get_alerts():
    """Get system alerts."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM alerts 
            WHERE acknowledged = false 
            ORDER BY created_at DESC 
            LIMIT 100
        """) if _table_exists(cursor, 'alerts') else None
        alerts = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": {"alerts": alerts}}

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge an alert."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("UPDATE alerts SET acknowledged = true WHERE id = %s", (alert_id,)) if _table_exists(cursor, 'alerts') else None
    return {"success": True}

@app.get("/api/alerts/rules")
async def get_alert_rules(all: bool = False):
    """Get alert rules."""
    db = get_db()
    with db.cursor() as cursor:
        if all:
            cursor.execute("SELECT * FROM alert_rules ORDER BY name") if _table_exists(cursor, 'alert_rules') else None
        else:
            cursor.execute("SELECT * FROM alert_rules WHERE enabled = true ORDER BY name") if _table_exists(cursor, 'alert_rules') else None
        rules = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": {"rules": rules}}

@app.get("/api/alerts/stats")
async def get_alert_stats():
    """Get alert statistics."""
    db = get_db()
    with db.cursor() as cursor:
        # Get counts by severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE acknowledged = false
            GROUP BY severity
        """) if _table_exists(cursor, 'alerts') else None
        severity_counts = dict(cursor.fetchall()) if cursor.description else {}
        
        # Get total counts
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN acknowledged = false THEN 1 END) as active,
                COUNT(CASE WHEN acknowledged = true THEN 1 END) as acknowledged
            FROM alerts
        """) if _table_exists(cursor, 'alerts') else None
        totals = dict(cursor.fetchone()) if cursor.fetchone() else {}
        
    return {"success": True, "data": {
        "severity_counts": severity_counts,
        "total": totals.get("total", 0),
        "active": totals.get("active", 0),
        "acknowledged": totals.get("acknowledged", 0)
    }}

@app.get("/api/alerts/history")
async def get_alert_history(days: int = 7):
    """Get alert history."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM alerts
            WHERE created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
            LIMIT 1000
        """, (days,)) if _table_exists(cursor, 'alerts') else None
        history = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": {"history": history}}


# ============================================================================
# Monitor dashboard endpoints
# ============================================================================

@app.get("/api/monitor/dashboard")
async def get_dashboard_data():
    """Get dashboard overview data."""
    db = get_db()
    with db.cursor() as cursor:
        # Get device counts
        device_count = 0
        if _table_exists(cursor, 'netbox_device_cache'):
            cursor.execute("SELECT COUNT(*) as total FROM netbox_device_cache")
            result = cursor.fetchone()
            device_count = result['total'] if result else 0
        
        # Get active jobs count
        active_jobs = 0
        if _table_exists(cursor, 'job_executions'):
            cursor.execute("SELECT COUNT(*) as active FROM job_executions WHERE status = 'running'")
            result = cursor.fetchone()
            active_jobs = result['active'] if result else 0
        
        # Get recent alerts
        recent_alerts = 0
        if _table_exists(cursor, 'alerts'):
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM alerts 
                WHERE acknowledged = false AND created_at > NOW() - INTERVAL '24 hours'
            """)
            result = cursor.fetchone()
            recent_alerts = result['count'] if result else 0
        
    return {
        "success": True,
        "data": {
            "device_count": device_count,
            "active_jobs": active_jobs,
            "recent_alerts": recent_alerts
        }
    }

@app.get("/api/monitor/active-jobs")
async def get_active_jobs():
    """Get currently active jobs."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT je.*, jd.name as job_name
            FROM job_executions je
            LEFT JOIN job_definitions jd ON je.job_id = jd.id
            WHERE je.status IN ('running', 'pending')
            ORDER BY je.started_at DESC
        """) if _table_exists(cursor, 'job_executions') else None
        jobs = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": jobs}

@app.get("/api/monitor/job-history")
async def get_job_history(limit: int = 50):
    """Get job execution history."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT je.*, jd.name as job_name
            FROM job_executions je
            LEFT JOIN job_definitions jd ON je.job_id = jd.id
            ORDER BY je.started_at DESC
            LIMIT %s
        """, (limit,)) if _table_exists(cursor, 'job_executions') else None
        jobs = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": jobs}


# ============================================================================
# Power trends endpoints
# ============================================================================

@app.get("/api/power/trends")
async def get_power_trends(hours: int = 24):
    """Get optical power trends."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT device_ip, port_index, rx_power_dbm, tx_power_dbm, collected_at
            FROM ciena_optical_power
            WHERE collected_at > NOW() - INTERVAL '%s hours'
            ORDER BY collected_at DESC
            LIMIT 10000
        """, (hours,)) if _table_exists(cursor, 'ciena_optical_power') else None
        data = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": data}


# ============================================================================
# SNMP Live endpoints
# ============================================================================

@app.get("/api/snmp/live")
async def snmp_live_data():
    """Get live SNMP polling data."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM polling_data
            ORDER BY collected_at DESC
            LIMIT 100
        """) if _table_exists(cursor, 'polling_data') else None
        data = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": data}


# ============================================================================
# SNMP Alarms endpoints
# ============================================================================

@app.get("/api/snmp/alarms")
async def snmp_alarms():
    """Get SNMP alarms from Ciena devices."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM ciena_alarms
            ORDER BY collected_at DESC
            LIMIT 500
        """) if _table_exists(cursor, 'ciena_alarms') else None
        alarms = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": alarms}


# ============================================================================
# UPS Monitor endpoints
# ============================================================================

@app.get("/api/ups/status")
async def ups_status():
    """Get UPS status from all monitored UPS devices."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM ups_status
            ORDER BY collected_at DESC
        """) if _table_exists(cursor, 'ups_status') else None
        data = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": data}


# ============================================================================
# Workflows endpoints
# ============================================================================

@app.get("/api/workflows")
async def get_workflows():
    """Get workflow definitions."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM job_definitions ORDER BY name") if _table_exists(cursor, 'job_definitions') else None
        workflows = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": workflows}

@app.get("/api/workflows/definitions")
async def get_workflow_definitions():
    """Get workflow definitions (alias for /api/workflows)."""
    return await get_workflows()

@app.get("/api/workflows/executions")
async def get_workflow_executions(limit: int = 100):
    """Get workflow execution history."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT je.*, jd.name as job_name
            FROM job_executions je
            LEFT JOIN job_definitions jd ON je.job_id = jd.id
            ORDER BY je.started_at DESC
            LIMIT %s
        """, (limit,)) if _table_exists(cursor, 'job_executions') else None
        executions = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": executions}

@app.get("/api/workflows/schedules")
async def get_workflow_schedules():
    """Get workflow schedules."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'job_schedules'):
            cursor.execute("""
                SELECT js.*, jd.name as job_name
                FROM job_schedules js
                LEFT JOIN job_definitions jd ON js.job_id = jd.id
                ORDER BY js.name
            """)
            schedules = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            schedules = []
    return {"success": True, "data": schedules}

@app.get("/api/workflows/templates")
async def get_workflow_templates():
    """Get workflow templates."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'job_templates'):
            cursor.execute("SELECT * FROM job_templates ORDER BY name")
            templates = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            templates = []
    return {"success": True, "data": templates}

@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: int):
    """Get a single workflow."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM job_definitions WHERE id = %s", (workflow_id,))
        workflow = cursor.fetchone()
    if not workflow:
        return {"success": False, "error": "Workflow not found"}
    return {"success": True, "data": dict(workflow)}

@app.post("/api/workflows")
async def create_workflow(request: Request):
    """Create a new workflow."""
    data = await request.json()
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO job_definitions (name, description, job_type, config, enabled)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (data.get('name'), data.get('description'), data.get('job_type', 'generic'),
              json.dumps(data.get('config', {})), data.get('enabled', True)))
        workflow_id = cursor.fetchone()['id']
    return {"success": True, "data": {"id": workflow_id}}


# ============================================================================
# Notifications endpoints
# ============================================================================

@app.get("/api/notifications")
async def list_notifications():
    """List notification configurations."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM notification_targets
            ORDER BY name
        """) if _table_exists(cursor, 'notification_targets') else None
        notifications = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": notifications}

@app.post("/api/notifications/test")
async def test_notification(request: Request):
    """Test a notification target."""
    data = await request.json()
    # TODO: Implement actual notification test
    return {"success": True, "message": "Test notification sent"}

@app.get("/api/notifications/channels")
async def get_notification_channels():
    """Get notification channels."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM notification_channels
            ORDER BY name
        """) if _table_exists(cursor, 'notification_channels') else None
        channels = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": {"channels": channels}}

@app.post("/api/notifications/channels")
async def create_notification_channel(request: Request):
    """Create a notification channel."""
    data = await request.json()
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO notification_channels (name, type, config, enabled)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (data.get('name'), data.get('type'), json.dumps(data.get('config', {})), data.get('enabled', True))) \
            if _table_exists(cursor, 'notification_channels') else None
        channel_id = cursor.fetchone()['id'] if cursor.description else None
    return {"success": True, "data": {"id": channel_id}}

@app.get("/api/notifications/rules")
async def get_notification_rules():
    """Get notification rules."""
    db = get_db()
    with db.cursor() as cursor:
        # Check if notification_rules table exists and get its columns
        if _table_exists(cursor, 'notification_rules'):
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'notification_rules'
                ORDER BY ordinal_position
            """)
            columns = [row['column_name'] for row in cursor.fetchall()]
            
            # Build query based on available columns
            if 'channel_id' in columns:
                cursor.execute("""
                    SELECT nr.*, nc.name as channel_name
                    FROM notification_rules nr
                    LEFT JOIN notification_channels nc ON nr.channel_id = nc.id
                    ORDER BY nr.name
                """)
            elif 'channel_ids' in columns:
                cursor.execute("""
                    SELECT nr.*
                    FROM notification_rules nr
                    ORDER BY nr.name
                """)
            else:
                cursor.execute("SELECT * FROM notification_rules ORDER BY name")
        else:
            cursor.execute("SELECT 1 WHERE false")  # Empty result
            
        rules = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": {"rules": rules}}

@app.get("/api/notifications/templates")
async def get_notification_templates():
    """Get notification templates."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM notification_templates
            ORDER BY name
        """) if _table_exists(cursor, 'notification_templates') else None
        templates = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": {"templates": templates}}


# ============================================================================
# Logs endpoints
# ============================================================================

@app.get("/api/logs")
async def get_logs(level: str = None, source: str = None, search: str = None, limit: int = 100, offset: int = 0):
    """Get system logs."""
    db = get_db()
    with db.cursor() as cursor:
        query = "SELECT * FROM system_logs"
        params = []
        conditions = []
        
        if level and level != 'all':
            conditions.append("level = %s")
            params.append(level)
        if source and source != 'all':
            conditions.append("source = %s")
            params.append(source)
        if search:
            conditions.append("message ILIKE %s")
            params.append(f"%{search}%")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params) if _table_exists(cursor, 'system_logs') else None
        total = cursor.fetchone()['count'] if cursor.description else 0
        
        # Add pagination
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params) if _table_exists(cursor, 'system_logs') else None
        logs = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    
    return {
        "success": True, 
        "data": {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }

@app.get("/api/logs/sources")
async def get_log_sources():
    """Get unique log sources."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT source, COUNT(*) as count
            FROM system_logs
            GROUP BY source
            ORDER BY count DESC
        """) if _table_exists(cursor, 'system_logs') else None
        sources = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": sources}

@app.get("/api/logs/levels")
async def get_log_levels():
    """Get unique log levels."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT level, COUNT(*) as count
            FROM system_logs
            GROUP BY level
            ORDER BY level
        """) if _table_exists(cursor, 'system_logs') else None
        levels = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {"success": True, "data": levels}

@app.get("/api/logs/stats")
async def get_log_stats(hours: int = 24):
    """Get log statistics."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                level,
                COUNT(*) as count,
                DATE_TRUNC('hour', created_at) as hour
            FROM system_logs
            WHERE created_at >= NOW() - INTERVAL '%s hours'
            GROUP BY level, hour
            ORDER BY hour DESC, level
        """, (hours,)) if _table_exists(cursor, 'system_logs') else None
    return {"success": True, "data": stats}


# ============================================================================
# Auth endpoints
# ============================================================================

@app.post("/api/auth/login")
async def login(request: Request):
    """Authenticate user and return session token."""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    
    if not user or not verify_password(password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate session token
    token = generate_token(user['id'])
    
    return {"success": True, "token": token}

@app.post("/api/auth/logout")
async def logout():
    """Logout user (invalidate session)."""
    # TODO: Implement token invalidation
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current authenticated user info."""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    user_id = verify_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {"success": True, "data": dict(user)}

@app.get("/api/auth/password-policy")
async def get_password_policy():
    """Get password policy settings."""
    db = get_db()
    with db.cursor() as cursor:
        # Default policy if not in database
        default_policy = {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special": True,
            "max_age_days": 90,
            "prevent_reuse": 5,
            "lockout_attempts": 5,
            "lockout_duration_minutes": 30
        }
        
        if _table_exists(cursor, 'settings'):
            cursor.execute("SELECT value FROM settings WHERE key = 'password_policy'")
            result = cursor.fetchone()
            if result and result['value']:
                import json
                try:
                    stored_policy = json.loads(result['value'])
                    # Merge with defaults
                    policy = {**default_policy, **stored_policy}
                except:
                    policy = default_policy
            else:
                policy = default_policy
        else:
            policy = default_policy
    
    return {"success": True, "data": {"policy": policy}}

@app.put("/api/auth/password-policy")
async def update_password_policy(request: Request):
    """Update password policy settings."""
    data = await request.json()
    policy = data.get("policy", {})
    
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'settings'):
            import json
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES ('password_policy', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW()
            """, (json.dumps(policy),))
    
    return {"success": True, "message": "Password policy updated successfully"}

@app.get("/api/auth/users")
async def auth_list_users():
    """Auth endpoint to list users (alias for /api/users)."""
    return await list_users()

@app.get("/api/auth/roles")
async def auth_list_roles():
    """Auth endpoint to list roles (alias for /api/roles)."""
    return await list_roles()

@app.get("/api/auth/roles/{role_id}/members")
async def get_role_members(role_id: int):
    """Get users in a specific role."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.created_at,
                   u.username as display_name,
                   '' as first_name,
                   '' as last_name,
                   'active' as status,
                   false as two_factor_enabled
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.role_id = %s
            ORDER BY u.username
        """, (role_id,))
        members = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    
    return {"success": True, "data": {"members": members}}


# ============================================================================
# Users endpoints
# ============================================================================

@app.get("/api/users")
async def list_users():
    """List all users."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.created_at,
                   u.username as display_name,
                   '' as first_name,
                   '' as last_name,
                   'active' as status,
                   false as two_factor_enabled,
                   array_agg(r.name) as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            GROUP BY u.id
            ORDER BY u.username
        """)
        users = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "data": users}

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """Get a single user."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.created_at
            FROM users u WHERE u.id = %s
        """, (user_id,))
        user = cursor.fetchone()
    if not user:
        return {"success": False, "error": "User not found"}
    return {"success": True, "data": dict(user)}


# ============================================================================
# Roles endpoints
# ============================================================================

@app.get("/api/roles")
async def list_roles():
    """List all roles."""
    db = get_db()
    with db.cursor() as cursor:
        # Check if roles table exists
        if _table_exists(cursor, 'roles'):
            # Include user count and permission count
            cursor.execute("""
                SELECT r.*, 
                       (SELECT COUNT(*) FROM user_roles ur WHERE ur.role_id = r.id) as user_count,
                       0 as permission_count
                FROM roles r
                ORDER BY r.name
            """)
            roles = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            roles = []
    return {"success": True, "data": roles}


# ============================================================================
# Credentials endpoints
# ============================================================================

@app.get("/api/credentials")
async def list_credentials():
    """List credentials (without sensitive data)."""
    db = get_db()
    with db.cursor() as cursor:
        # Check which columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'credentials'
            ORDER BY ordinal_position
        """) if _table_exists(cursor, 'credentials') else None
        columns = [row['column_name'] for row in cursor.fetchall()] if cursor.description else []
        
        # Build query with existing columns, excluding password
        safe_columns = [c for c in columns if c not in ['password', 'password_hash']]
        if safe_columns:
            query = f"SELECT {', '.join(safe_columns)} FROM credentials ORDER BY name"
            cursor.execute(query) if _table_exists(cursor, 'credentials') else None
            credentials = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            credentials = []
    return {"success": True, "data": credentials}

@app.get("/api/credentials/{credential_id}")
async def get_credential(credential_id: int):
    """Get a single credential (without password)."""
    db = get_db()
    with db.cursor() as cursor:
        # Check which columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'credentials'
            ORDER BY ordinal_position
        """) if _table_exists(cursor, 'credentials') else None
        columns = [row['column_name'] for row in cursor.fetchall()] if cursor.description else []
        
        # Build query with existing columns, excluding password
        safe_columns = [c for c in columns if c not in ['password', 'password_hash']]
        if safe_columns:
            query = f"SELECT {', '.join(safe_columns)} FROM credentials WHERE id = %s"
            cursor.execute(query, (credential_id,)) if _table_exists(cursor, 'credentials') else None
            credential = cursor.fetchone()
        else:
            credential = None
            
    if not credential:
        return {"success": False, "error": "Credential not found"}
    return {"success": True, "data": dict(credential)}


# ============================================================================
# Inventory endpoints
# ============================================================================

@app.get("/api/inventory/devices")
async def get_inventory_devices():
    """Get device inventory."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'netbox_device_cache'):
            # Check what columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'netbox_device_cache'
                ORDER BY ordinal_position
            """)
            columns = [row['column_name'] for row in cursor.fetchall()]
            
            # Use appropriate column for ordering
            order_by = 'device_name' if 'device_name' in columns else 'id'
            cursor.execute(f"SELECT * FROM netbox_device_cache ORDER BY {order_by}")
            devices = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            devices = []
    return {"success": True, "data": devices}

@app.get("/api/inventory/interfaces")
async def get_inventory_interfaces():
    """Get interface inventory."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'netbox_interface_cache'):
            cursor.execute("""
                SELECT * FROM netbox_interface_cache 
                ORDER BY device_name, name
            """)
            interfaces = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            interfaces = []
    return {"success": True, "data": interfaces}

@app.get("/api/inventory/modules")
async def get_inventory_modules():
    """Get module inventory."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'netbox_module_cache'):
            cursor.execute("""
                SELECT * FROM netbox_module_cache 
                ORDER BY device_name
            """)
            modules = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            modules = []
    return {"success": True, "data": modules}

@app.get("/api/inventory/links")
async def get_inventory_links():
    """Get link inventory."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'netbox_link_cache'):
            cursor.execute("""
                SELECT * FROM netbox_link_cache 
                ORDER BY source_device, source_interface
            """)
            links = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            links = []
    return {"success": True, "data": links}

@app.get("/api/inventory/sites")
async def get_inventory_sites():
    """Get site inventory."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'netbox_site_cache'):
            cursor.execute("""
                SELECT * FROM netbox_site_cache 
                ORDER BY name
            """)
            sites = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            sites = []
    return {"success": True, "data": sites}

@app.get("/api/inventory/racks")
async def get_inventory_racks():
    """Get rack inventory."""
    db = get_db()
    with db.cursor() as cursor:
        if _table_exists(cursor, 'netbox_rack_cache'):
            cursor.execute("""
                SELECT * FROM netbox_rack_cache 
                ORDER BY site_name, name
            """)
            racks = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        else:
            racks = []
    return {"success": True, "data": racks}


# ============================================================================
# Settings endpoints
# ============================================================================

@app.get("/get_settings")
async def get_settings():
    """Get system settings."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM settings") if _table_exists(cursor, 'settings') else None
        settings_rows = cursor.fetchall() if cursor.description else []
        settings = {row['key']: row['value'] for row in settings_rows}
    
    # Default settings if not in database
    defaults = {
        'app_name': 'OpsConductor Monitor',
        'timezone': 'America/Los_Angeles',
        'date_format': 'YYYY-MM-DD',
        'theme': 'light',
        'auto_refresh_interval': '30',
        'session_timeout': '3600',
    }
    
    # Merge with defaults
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
    
    return settings

@app.post("/save_settings")
async def save_settings(request: Request):
    """Save system settings."""
    data = await request.json()
    db = get_db()
    with db.cursor() as cursor:
        for key, value in data.items():
            # Upsert setting
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW()
            """, (key, str(value))) if _table_exists(cursor, 'settings') else None
    return {"success": True, "message": "Settings saved successfully"}


# ============================================================================
# Serve frontend static files
# ============================================================================

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist')
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
