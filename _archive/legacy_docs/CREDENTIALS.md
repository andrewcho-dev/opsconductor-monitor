# OpsConductor Credentials & Authentication Documentation

This document covers the credential vault system for secure credential storage and the authentication/authorization system for user access control.

## Table of Contents

1. [Credential Vault](#credential-vault)
2. [Credential Types](#credential-types)
3. [Encryption](#encryption)
4. [Credential API](#credential-api)
5. [Authentication System](#authentication-system)
6. [Two-Factor Authentication](#two-factor-authentication)
7. [Role-Based Access Control](#role-based-access-control)
8. [Session Management](#session-management)
9. [Audit Logging](#audit-logging)
10. [Security Best Practices](#security-best-practices)

---

## Credential Vault

The credential vault provides secure, encrypted storage for sensitive credentials used by workflows and system operations.

### Features

- **AES-256 Encryption** - All credentials encrypted at rest using Fernet (AES-128-CBC with HMAC)
- **Key Derivation** - Master key derived using PBKDF2 with 100,000 iterations
- **Credential Types** - Support for SSH, SNMP, API keys, certificates, and more
- **Expiration Tracking** - Monitor credential expiration dates
- **Audit Logging** - Complete audit trail of credential access
- **Groups** - Organize credentials by purpose or environment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Credential API                            │
│              /api/credentials endpoints                      │
├─────────────────────────────────────────────────────────────┤
│                  Credential Service                          │
│         Encryption, validation, business logic               │
├─────────────────────────────────────────────────────────────┤
│                  Credential Audit Service                    │
│              Access logging and tracking                     │
├─────────────────────────────────────────────────────────────┤
│                     Database                                 │
│           credentials, credential_groups tables              │
└─────────────────────────────────────────────────────────────┘
```

---

## Credential Types

### SSH Credentials

For SSH-based device access:

```json
{
  "name": "Network Admin SSH",
  "credential_type": "ssh",
  "category": "network",
  "environment": "production",
  "credential_data": {
    "username": "admin",
    "password": "encrypted...",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
    "passphrase": "encrypted...",
    "port": 22
  }
}
```

### SNMP Credentials

For SNMP device polling:

```json
{
  "name": "SNMP v3 Read",
  "credential_type": "snmp",
  "credential_data": {
    "version": "3",
    "security_name": "snmpuser",
    "auth_protocol": "SHA",
    "auth_password": "encrypted...",
    "priv_protocol": "AES",
    "priv_password": "encrypted...",
    "context_name": ""
  }
}
```

For SNMP v2c:

```json
{
  "name": "SNMP v2c Community",
  "credential_type": "snmp",
  "credential_data": {
    "version": "2c",
    "community": "encrypted..."
  }
}
```

### API Key Credentials

For REST API authentication:

```json
{
  "name": "NetBox API Token",
  "credential_type": "api_key",
  "credential_data": {
    "api_key": "encrypted...",
    "header_name": "Authorization",
    "header_prefix": "Token"
  }
}
```

### Certificate Credentials

For certificate-based authentication:

```json
{
  "name": "Client Certificate",
  "credential_type": "certificate",
  "credential_data": {
    "certificate": "-----BEGIN CERTIFICATE-----...",
    "private_key": "-----BEGIN PRIVATE KEY-----...",
    "ca_certificate": "-----BEGIN CERTIFICATE-----...",
    "passphrase": "encrypted..."
  }
}
```

### WinRM Credentials

For Windows Remote Management:

```json
{
  "name": "Windows Admin",
  "credential_type": "winrm",
  "credential_data": {
    "username": "Administrator",
    "password": "encrypted...",
    "domain": "CORP",
    "transport": "ntlm",
    "port": 5985
  }
}
```

### Database Credentials

For database connections:

```json
{
  "name": "PostgreSQL Production",
  "credential_type": "database",
  "credential_data": {
    "host": "db.example.com",
    "port": 5432,
    "database": "production",
    "username": "app_user",
    "password": "encrypted...",
    "ssl_mode": "require"
  }
}
```

---

## Encryption

### Key Derivation

The encryption key is derived from a master secret:

```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

# Get master secret from environment
master_secret = os.environ.get('CREDENTIAL_MASTER_KEY')

# Derive encryption key using PBKDF2
salt = b'opsconductor-credential-vault-salt'
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
)
key = base64.urlsafe_b64encode(kdf.derive(master_secret.encode()))
fernet = Fernet(key)
```

### Encryption/Decryption

```python
class CredentialService:
    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt credential data."""
        json_data = json.dumps(data)
        encrypted = self._fernet.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt credential data."""
        encrypted = base64.b64decode(encrypted_data.encode())
        decrypted = self._fernet.decrypt(encrypted)
        return json.loads(decrypted.decode())
```

### Environment Configuration

Set the master key in environment:

```bash
# Generate a secure key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set in .env
CREDENTIAL_MASTER_KEY=your-generated-key-here
```

**Important:** The master key must be:
- At least 32 characters
- Stored securely (not in version control)
- Backed up securely
- Rotated periodically

---

## Credential API

### List Credentials

```http
GET /api/credentials
```

Query parameters:
- `type` - Filter by credential type
- `category` - Filter by category
- `environment` - Filter by environment
- `status` - Filter by status (active, expired, expiring)
- `include_expired` - Include expired credentials (default: true)

Response:
```json
{
  "success": true,
  "data": {
    "credentials": [
      {
        "id": 1,
        "name": "Network Admin SSH",
        "credential_type": "ssh",
        "category": "network",
        "environment": "production",
        "status": "active",
        "expires_at": "2025-12-31T00:00:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-06-01T00:00:00Z"
      }
    ]
  }
}
```

### Get Credential

```http
GET /api/credentials/:id
```

Query parameters:
- `decrypt` - Include decrypted data (requires permission)

### Create Credential

```http
POST /api/credentials
```

Request body:
```json
{
  "name": "New SSH Credential",
  "credential_type": "ssh",
  "category": "network",
  "environment": "production",
  "username": "admin",
  "password": "secret123",
  "port": 22,
  "expires_at": "2025-12-31T00:00:00Z",
  "notes": "For network devices"
}
```

### Update Credential

```http
PUT /api/credentials/:id
```

### Delete Credential

```http
DELETE /api/credentials/:id
```

### Rotate Credential

```http
POST /api/credentials/:id/rotate
```

Request body:
```json
{
  "new_password": "newSecret456"
}
```

### Test Credential

```http
POST /api/credentials/:id/test
```

Request body:
```json
{
  "target": "192.168.1.1"
}
```

---

## Authentication System

### Overview

The authentication system provides:

- **Username/Password Authentication** - Traditional login
- **Session Tokens** - JWT-like session management
- **Two-Factor Authentication** - TOTP and email codes
- **Password Policies** - Configurable password requirements
- **Account Lockout** - Protection against brute force

### Login Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │────▶│  Login  │────▶│  2FA    │────▶│ Session │
│         │     │  Form   │     │ Verify  │     │ Created │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                     │               │
                     ▼               ▼
              ┌─────────────┐  ┌─────────────┐
              │  Validate   │  │  Validate   │
              │  Password   │  │  2FA Code   │
              └─────────────┘  └─────────────┘
```

### Authentication API

#### Login

```http
POST /api/auth/login
```

Request:
```json
{
  "username": "admin",
  "password": "password123"
}
```

Response (2FA required):
```json
{
  "success": true,
  "requires_2fa": true,
  "session_token": "temporary-token",
  "methods": ["totp", "email"]
}
```

Response (no 2FA):
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "roles": ["admin"]
    },
    "session_token": "session-token",
    "refresh_token": "refresh-token",
    "expires_at": "2024-12-17T00:00:00Z"
  }
}
```

#### Verify 2FA

```http
POST /api/auth/verify-2fa
```

Request:
```json
{
  "session_token": "temporary-token",
  "code": "123456",
  "method": "totp"
}
```

#### Logout

```http
POST /api/auth/logout
```

#### Refresh Token

```http
POST /api/auth/refresh
```

Request:
```json
{
  "refresh_token": "refresh-token"
}
```

#### Get Current User

```http
GET /api/auth/me
```

---

## Two-Factor Authentication

### TOTP (Time-based One-Time Password)

Setup flow:

1. **Enable 2FA**
```http
POST /api/auth/2fa/setup
```
Request:
```json
{
  "method": "totp"
}
```
Response:
```json
{
  "success": true,
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_code": "otpauth://totp/OpsConductor:admin?secret=JBSWY3DPEHPK3PXP&issuer=OpsConductor",
    "backup_codes": ["12345678", "87654321", ...]
  }
}
```

2. **Verify Setup**
```http
POST /api/auth/2fa/verify-setup
```
Request:
```json
{
  "code": "123456"
}
```

3. **Disable 2FA**
```http
POST /api/auth/2fa/disable
```
Request:
```json
{
  "password": "current-password",
  "code": "123456"
}
```

### Email-based 2FA

When email 2FA is enabled, a code is sent to the user's email:

```http
POST /api/auth/2fa/send-email
```

The code expires after 10 minutes.

### Backup Codes

Backup codes are generated during 2FA setup:
- 10 single-use codes
- Each code can only be used once
- Regenerate codes if running low

```http
POST /api/auth/2fa/regenerate-backup-codes
```

---

## Role-Based Access Control

### Permission Structure

Permissions follow the format: `module.resource.action`

Examples:
- `devices.device.view` - View devices
- `devices.device.create` - Create devices
- `jobs.job.execute` - Execute jobs
- `system.settings.manage` - Manage system settings
- `credentials.credential.decrypt` - Decrypt credentials

### Built-in Roles

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `admin` | Full system access | All permissions |
| `operator` | Run jobs, view devices | `jobs.job.execute`, `devices.device.view` |
| `viewer` | Read-only access | `*.*.view` |
| `credential_admin` | Manage credentials | `credentials.*.*` |

### Role API

#### List Roles

```http
GET /api/auth/roles
```

#### Create Role

```http
POST /api/auth/roles
```

Request:
```json
{
  "name": "network_admin",
  "description": "Network device administrators",
  "permissions": [
    "devices.device.*",
    "jobs.job.view",
    "jobs.job.execute",
    "credentials.credential.view"
  ]
}
```

#### Assign Role to User

```http
POST /api/auth/users/:id/roles
```

Request:
```json
{
  "role_id": 2
}
```

### Permission Checking

Backend:
```python
from backend.services.auth_service import auth_service

# Check permission
if not auth_service.check_permission(user_id, 'devices.device.create'):
    raise ForbiddenError('Permission denied')
```

Frontend:
```jsx
import { useAuth } from './contexts/AuthContext';

function MyComponent() {
  const { hasPermission } = useAuth();
  
  if (!hasPermission('devices.device.create')) {
    return <div>Access denied</div>;
  }
  
  return <CreateDeviceForm />;
}
```

Route protection:
```jsx
<Route path="/devices/new" element={
  <ProtectedRoute permission="devices.device.create">
    <CreateDevicePage />
  </ProtectedRoute>
} />
```

---

## Session Management

### Session Tokens

- **Session Token** - Short-lived (24 hours), used for API requests
- **Refresh Token** - Long-lived (7 days), used to get new session tokens

### Token Storage

Frontend stores tokens in memory and localStorage:

```javascript
// Store tokens
localStorage.setItem('session_token', token);
localStorage.setItem('refresh_token', refreshToken);

// Include in requests
fetch('/api/devices', {
  headers: {
    'Authorization': `Bearer ${sessionToken}`
  }
});
```

### Token Refresh

Automatic refresh when session token expires:

```javascript
async function refreshSession() {
  const refreshToken = localStorage.getItem('refresh_token');
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (response.ok) {
    const { session_token, refresh_token } = await response.json();
    localStorage.setItem('session_token', session_token);
    localStorage.setItem('refresh_token', refresh_token);
  } else {
    // Redirect to login
    window.location.href = '/login';
  }
}
```

### Session Invalidation

Sessions are invalidated on:
- Logout
- Password change
- Account lockout
- Admin revocation

---

## Audit Logging

### Credential Access Audit

All credential access is logged:

```python
class CredentialAuditService:
    def log_access(self, credential_id, user_id, action, details=None):
        """Log credential access."""
        self.db.execute("""
            INSERT INTO credential_audit_log 
            (credential_id, user_id, action, details, ip_address, user_agent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (credential_id, user_id, action, json.dumps(details), 
              request.remote_addr, request.user_agent.string, now_utc()))
```

### Audit Actions

| Action | Description |
|--------|-------------|
| `view` | Credential metadata viewed |
| `decrypt` | Credential decrypted |
| `create` | Credential created |
| `update` | Credential updated |
| `delete` | Credential deleted |
| `rotate` | Credential rotated |
| `test` | Credential tested |
| `use` | Credential used in workflow |

### Viewing Audit Logs

```http
GET /api/credentials/audit
```

Query parameters:
- `credential_id` - Filter by credential
- `user_id` - Filter by user
- `action` - Filter by action
- `start_date` - Start date
- `end_date` - End date

---

## Security Best Practices

### Credential Management

1. **Use unique credentials** - Don't share credentials across systems
2. **Set expiration dates** - Rotate credentials regularly
3. **Use least privilege** - Grant minimum required access
4. **Monitor access** - Review audit logs regularly
5. **Secure the master key** - Store CREDENTIAL_MASTER_KEY securely

### Password Policy

Configure password requirements:

```http
PUT /api/auth/password-policy
```

```json
{
  "min_length": 12,
  "max_length": 128,
  "require_uppercase": true,
  "require_lowercase": true,
  "require_numbers": true,
  "require_special_chars": true,
  "min_uppercase": 1,
  "min_lowercase": 1,
  "min_numbers": 1,
  "min_special": 1,
  "password_expires": true,
  "expiration_days": 90,
  "password_history_count": 12,
  "max_failed_attempts": 5,
  "lockout_duration_minutes": 30
}
```

### Account Lockout

After `max_failed_attempts` failed logins:
- Account is locked for `lockout_duration_minutes`
- Admin can unlock manually
- User receives notification

### Session Security

1. **Use HTTPS** - Always use TLS in production
2. **Secure cookies** - Set HttpOnly and Secure flags
3. **Short session lifetime** - Use short-lived tokens
4. **Invalidate on logout** - Clear all session data

### Environment Variables

Required security environment variables:

```bash
# Credential encryption key (required)
CREDENTIAL_MASTER_KEY=your-32-char-minimum-key

# Session encryption key
ENCRYPTION_KEY=your-fernet-key

# FastAPI secret key
SECRET_KEY=your-fastapi-secret-key
```

### Database Security

1. **Encrypt at rest** - Use PostgreSQL encryption
2. **Limit access** - Use dedicated database user
3. **Audit queries** - Enable query logging
4. **Backup encryption** - Encrypt database backups
