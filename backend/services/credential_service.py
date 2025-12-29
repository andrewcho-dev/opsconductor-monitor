"""
Credential Service

Provides secure credential storage and retrieval with AES-256 encryption.
"""

import os
import json
import base64
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.database import get_db
from backend.utils.time import now_utc
from backend.services.credential_audit_service import get_audit_service

logger = logging.getLogger(__name__)


class CredentialService:
    """
    Service for managing encrypted credentials.
    
    Uses Fernet (AES-128-CBC with HMAC) for encryption.
    The encryption key is derived from a master secret using PBKDF2.
    """
    
    _instance = None
    _fernet = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_encryption()
        return cls._instance
    
    def _initialize_encryption(self):
        """Initialize the encryption key from environment or generate one."""
        # Get master secret from environment
        master_secret = os.environ.get('CREDENTIAL_MASTER_KEY')
        
        if not master_secret:
            # Fall back to a derived key from other secrets
            # In production, CREDENTIAL_MASTER_KEY should be set explicitly
            pg_password = os.environ.get('PG_PASSWORD', '')
            secret_key = os.environ.get('SECRET_KEY', 'opsconductor-default-key')
            master_secret = f"{secret_key}:{pg_password}:credential-vault"
            logger.warning("CREDENTIAL_MASTER_KEY not set, using derived key. Set this in production!")
        
        # Derive encryption key using PBKDF2
        salt = b'opsconductor-credential-vault-salt'  # Static salt (key derivation, not password storage)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_secret.encode()))
        self._fernet = Fernet(key)
    
    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt credential data."""
        json_data = json.dumps(data)
        encrypted = self._fernet.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()
    
    def _extract_certificate_info(self, credential_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract certificate information from PEM-encoded certificate data.
        
        Returns certificate metadata like fingerprint, issuer, subject, validity dates.
        """
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            cert_pem = credential_data.get('certificate') or credential_data.get('cert')
            if not cert_pem:
                return None
            
            # Parse the certificate
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
            
            # Extract info
            info = {
                'fingerprint': cert.fingerprint(hashes.SHA256()).hex(),
                'serial': str(cert.serial_number),
                'issuer': cert.issuer.rfc4514_string(),
                'subject': cert.subject.rfc4514_string(),
                'not_before': cert.not_valid_before_utc,
                'not_after': cert.not_valid_after_utc,
            }
            
            # Try to get key info
            try:
                public_key = cert.public_key()
                key_type = type(public_key).__name__
                if 'RSA' in key_type:
                    info['key_algorithm'] = 'RSA'
                    info['key_size'] = public_key.key_size
                elif 'EC' in key_type:
                    info['key_algorithm'] = 'ECDSA'
                    info['key_size'] = public_key.key_size
                elif 'Ed25519' in key_type:
                    info['key_algorithm'] = 'Ed25519'
                    info['key_size'] = 256
                else:
                    info['key_algorithm'] = key_type
            except Exception:
                pass
            
            return info
        except Exception as e:
            logger.warning(f"Failed to extract certificate info: {e}")
            return None
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt credential data."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise ValueError("Failed to decrypt credential data")
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def create_credential(
        self,
        name: str,
        credential_type: str,
        credential_data: Dict[str, Any],
        description: str = None,
        username: str = None,
        created_by: str = None,
        valid_from: datetime = None,
        valid_until: datetime = None,
        category: str = None,
        environment: str = None,
        owner: str = None,
        tags: List[str] = None,
        notes: str = None,
    ) -> Dict[str, Any]:
        """
        Create a new credential.
        
        Args:
            name: Unique name for the credential
            credential_type: Type (ssh, snmp, api_key, password, winrm, certificate, pki)
            credential_data: Sensitive data to encrypt (password, private_key, etc.)
            description: Optional description
            username: Optional username for display
            created_by: Who created this credential
            valid_from: When the credential becomes valid
            valid_until: When the credential expires
            category: Category (network, server, cloud, database)
            environment: Environment (production, staging, development)
            owner: Who owns/manages this credential
            tags: List of tags for filtering
            notes: Additional notes
        
        Returns:
            Created credential (without sensitive data)
        """
        encrypted_data = self.encrypt(credential_data)
        
        # Extract certificate info if it's a certificate type
        cert_fingerprint = None
        cert_issuer = None
        cert_subject = None
        cert_serial = None
        key_algorithm = None
        key_size = None
        
        if credential_type in ('certificate', 'pki'):
            cert_info = self._extract_certificate_info(credential_data)
            if cert_info:
                cert_fingerprint = cert_info.get('fingerprint')
                cert_issuer = cert_info.get('issuer')
                cert_subject = cert_info.get('subject')
                cert_serial = cert_info.get('serial')
                key_algorithm = cert_info.get('key_algorithm')
                key_size = cert_info.get('key_size')
                # Auto-set validity dates from certificate if not provided
                if not valid_from and cert_info.get('not_before'):
                    valid_from = cert_info['not_before']
                if not valid_until and cert_info.get('not_after'):
                    valid_until = cert_info['not_after']
        
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO credentials 
                (name, description, credential_type, encrypted_data, username, created_by,
                 valid_from, valid_until, category, environment, owner, tags, notes,
                 certificate_fingerprint, certificate_issuer, certificate_subject,
                 certificate_serial, key_algorithm, key_size, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, credential_type, username, 
                          used_by_count, last_used_at, created_at, updated_at,
                          valid_from, valid_until, category, environment, owner, tags, notes, status
            """, (name, description, credential_type, encrypted_data, username, created_by,
                  valid_from, valid_until, category, environment, owner, tags, notes,
                  cert_fingerprint, cert_issuer, cert_subject, cert_serial, key_algorithm, key_size, 'active'))
            
            row = cursor.fetchone()
            db.get_connection().commit()
            
            result = dict(row)
            
            # Log the creation
            audit = get_audit_service()
            audit.log_created(
                credential_id=result['id'],
                credential_name=name,
                credential_type=credential_type,
                performed_by=created_by
            )
            
            return result
    
    def get_credential(self, credential_id: int, include_secret: bool = False, accessed_by: str = None, access_reason: str = None) -> Optional[Dict[str, Any]]:
        """
        Get a credential by ID.
        
        Args:
            credential_id: Credential ID
            include_secret: If True, decrypt and include sensitive data
            accessed_by: Who is accessing (for audit logging when include_secret=True)
            access_reason: Why the secret is being accessed
        
        Returns:
            Credential data or None
        """
        db = get_db()
        with db.cursor() as cursor:
            if include_secret:
                cursor.execute("""
                    SELECT id, name, description, credential_type, encrypted_data,
                           username, used_by_count, last_used_at, created_at, updated_at,
                           valid_from, valid_until, is_expired, category, environment,
                           owner, tags, notes, status,
                           certificate_fingerprint, certificate_issuer, certificate_subject,
                           certificate_serial, key_algorithm, key_size
                    FROM credentials
                    WHERE id = %s AND is_deleted = FALSE
                """, (credential_id,))
            else:
                cursor.execute("""
                    SELECT id, name, description, credential_type, 
                           username, used_by_count, last_used_at, created_at, updated_at,
                           valid_from, valid_until, is_expired, category, environment,
                           owner, tags, notes, status,
                           certificate_fingerprint, certificate_issuer, certificate_subject,
                           certificate_serial, key_algorithm, key_size
                    FROM credentials
                    WHERE id = %s AND is_deleted = FALSE
                """, (credential_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            result = dict(row)
            
            if include_secret and 'encrypted_data' in result:
                result['secret_data'] = self.decrypt(result.pop('encrypted_data'))
                
                # Log the access
                audit = get_audit_service()
                audit.log_accessed(
                    credential_id=credential_id,
                    credential_name=result['name'],
                    credential_type=result['credential_type'],
                    performed_by=accessed_by,
                    access_reason=access_reason
                )
            
            return result
    
    def get_credential_by_name(self, name: str, include_secret: bool = False) -> Optional[Dict[str, Any]]:
        """Get a credential by name."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM credentials WHERE name = %s AND is_deleted = FALSE
            """, (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return self.get_credential(row['id'], include_secret)
    
    def list_credentials(
        self,
        credential_type: str = None,
        category: str = None,
        environment: str = None,
        status: str = None,
        tags: List[str] = None,
        include_expired: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all credentials (without sensitive data).
        
        Args:
            credential_type: Optional filter by type
            category: Optional filter by category
            environment: Optional filter by environment
            status: Optional filter by status
            tags: Optional filter by tags (any match)
            include_expired: Whether to include expired credentials
        
        Returns:
            List of credentials
        """
        db = get_db()
        
        conditions = ["is_deleted = FALSE"]
        params = []
        
        if credential_type:
            conditions.append("credential_type = %s")
            params.append(credential_type)
        
        if category:
            conditions.append("category = %s")
            params.append(category)
        
        if environment:
            conditions.append("environment = %s")
            params.append(environment)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if tags:
            conditions.append("tags && %s")
            params.append(tags)
        
        if not include_expired:
            conditions.append("(is_expired = FALSE OR is_expired IS NULL)")
        
        where_clause = " AND ".join(conditions)
        
        with db.cursor() as cursor:
            cursor.execute(f"""
                SELECT id, name, description, credential_type, 
                       username, used_by_count, last_used_at, created_at, updated_at,
                       valid_from, valid_until, is_expired, category, environment,
                       owner, tags, notes, status,
                       certificate_fingerprint, certificate_issuer, certificate_subject,
                       key_algorithm, key_size,
                       CASE 
                           WHEN valid_until IS NULL THEN NULL
                           WHEN valid_until < CURRENT_TIMESTAMP THEN 'expired'
                           WHEN valid_until < CURRENT_TIMESTAMP + INTERVAL '30 days' THEN 'expiring_soon'
                           ELSE 'valid'
                       END as expiration_status,
                       CASE 
                           WHEN valid_until IS NOT NULL THEN 
                               EXTRACT(DAY FROM (valid_until - CURRENT_TIMESTAMP))::INTEGER
                           ELSE NULL
                       END as days_until_expiration
                FROM credentials
                WHERE {where_clause}
                ORDER BY name
            """, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_credential(
        self,
        credential_id: int,
        name: str = None,
        description: str = None,
        credential_data: Dict[str, Any] = None,
        username: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a credential.
        
        Args:
            credential_id: Credential ID
            name: New name (optional)
            description: New description (optional)
            credential_data: New sensitive data (optional)
            username: New username (optional)
        
        Returns:
            Updated credential or None
        """
        db = get_db()
        
        # Build update query dynamically
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        
        if credential_data is not None:
            updates.append("encrypted_data = %s")
            params.append(self.encrypt(credential_data))
        
        if username is not None:
            updates.append("username = %s")
            params.append(username)
        
        if not updates:
            return self.get_credential(credential_id)
        
        updates.append("updated_at = %s")
        params.append(now_utc())
        params.append(credential_id)
        
        with db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE credentials
                SET {', '.join(updates)}
                WHERE id = %s AND is_deleted = FALSE
                RETURNING id, name, description, credential_type, 
                          username, used_by_count, last_used_at, created_at, updated_at
            """, params)
            
            row = cursor.fetchone()
            db.get_connection().commit()
            
            return dict(row) if row else None
    
    def delete_credential(self, credential_id: int, deleted_by: str = None) -> bool:
        """Soft delete a credential."""
        # Get credential info for audit log before deletion
        cred = self.get_credential(credential_id)
        if not cred:
            return False
        
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE credentials
                SET is_deleted = TRUE, updated_at = %s, status = 'deleted'
                WHERE id = %s AND is_deleted = FALSE
            """, (now_utc(), credential_id))
            db.get_connection().commit()
            
            if cursor.rowcount > 0:
                # Log the deletion
                audit = get_audit_service()
                audit.log_deleted(
                    credential_id=credential_id,
                    credential_name=cred['name'],
                    credential_type=cred['credential_type'],
                    performed_by=deleted_by
                )
                return True
            return False
    
    # =========================================================================
    # Credential Groups
    # =========================================================================
    
    def create_group(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a credential group."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO credential_groups (name, description)
                VALUES (%s, %s)
                RETURNING id, name, description, created_at, updated_at
            """, (name, description))
            row = cursor.fetchone()
            db.get_connection().commit()
            return dict(row)
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all credential groups with their members."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT g.id, g.name, g.description, g.created_at, g.updated_at,
                       COALESCE(
                           json_agg(
                               json_build_object('id', c.id, 'name', c.name)
                           ) FILTER (WHERE c.id IS NOT NULL),
                           '[]'
                       ) as credentials
                FROM credential_groups g
                LEFT JOIN credential_group_members cgm ON g.id = cgm.group_id
                LEFT JOIN credentials c ON cgm.credential_id = c.id AND c.is_deleted = FALSE
                GROUP BY g.id
                ORDER BY g.name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_to_group(self, credential_id: int, group_id: int) -> bool:
        """Add a credential to a group."""
        db = get_db()
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO credential_group_members (credential_id, group_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (credential_id, group_id))
                db.get_connection().commit()
                return True
            except Exception:
                return False
    
    def remove_from_group(self, credential_id: int, group_id: int) -> bool:
        """Remove a credential from a group."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                DELETE FROM credential_group_members
                WHERE credential_id = %s AND group_id = %s
            """, (credential_id, group_id))
            db.get_connection().commit()
            return cursor.rowcount > 0
    
    def delete_group(self, group_id: int) -> bool:
        """Delete a credential group."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM credential_groups WHERE id = %s", (group_id,))
            db.get_connection().commit()
            return cursor.rowcount > 0
    
    # =========================================================================
    # Device Assignments
    # =========================================================================
    
    def assign_to_device(
        self,
        credential_id: int,
        ip_address: str = None,
        device_id: int = None,
        credential_type: str = None,
        priority: int = 0
    ) -> bool:
        """Assign a credential to a device."""
        if not ip_address and not device_id:
            raise ValueError("Either ip_address or device_id must be provided")
        
        db = get_db()
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO device_credentials 
                    (device_id, ip_address, credential_id, credential_type, priority)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (device_id, ip_address, credential_id, credential_type, priority))
                db.get_connection().commit()
                return True
            except Exception:
                return False
    
    def unassign_from_device(
        self,
        credential_id: int,
        ip_address: str = None,
        device_id: int = None
    ) -> bool:
        """Remove a credential assignment from a device."""
        if not ip_address and not device_id:
            raise ValueError("Either ip_address or device_id must be provided")
        
        db = get_db()
        with db.cursor() as cursor:
            try:
                if ip_address:
                    cursor.execute("""
                        DELETE FROM device_credentials 
                        WHERE credential_id = %s AND ip_address = %s
                    """, (credential_id, ip_address))
                else:
                    cursor.execute("""
                        DELETE FROM device_credentials 
                        WHERE credential_id = %s AND device_id = %s
                    """, (credential_id, device_id))
                db.get_connection().commit()
                return cursor.rowcount > 0
            except Exception:
                return False
    
    def get_devices_for_credential(self, credential_id: int) -> List[Dict[str, Any]]:
        """
        Get all devices associated with a credential.
        
        Returns list of device IPs/IDs that have this credential assigned.
        """
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT dc.ip_address, dc.device_id, dc.credential_type, dc.priority, dc.created_at
                FROM device_credentials dc
                WHERE dc.credential_id = %s
                ORDER BY dc.ip_address
            """, (credential_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'ip_address': row['ip_address'],
                    'device_id': row['device_id'],
                    'credential_type': row['credential_type'],
                    'priority': row['priority'],
                    'assigned_at': row['created_at'].isoformat() if row['created_at'] else None,
                })
            
            return results
    
    def get_credentials_for_device(
        self,
        ip_address: str = None,
        device_id: int = None,
        credential_type: str = None,
        include_secret: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get credentials assigned to a device.
        
        Returns credentials ordered by priority (highest first).
        """
        db = get_db()
        with db.cursor() as cursor:
            query = """
                SELECT c.id, c.name, c.credential_type, c.username,
                       dc.priority
            """
            if include_secret:
                query += ", c.encrypted_data"
            
            query += """
                FROM device_credentials dc
                JOIN credentials c ON dc.credential_id = c.id
                WHERE c.is_deleted = FALSE
            """
            
            params = []
            if ip_address:
                query += " AND dc.ip_address = %s"
                params.append(ip_address)
            if device_id:
                query += " AND dc.device_id = %s"
                params.append(device_id)
            if credential_type:
                query += " AND (dc.credential_type = %s OR c.credential_type = %s)"
                params.extend([credential_type, credential_type])
            
            query += " ORDER BY dc.priority DESC, c.name"
            
            cursor.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                cred = dict(row)
                if include_secret and 'encrypted_data' in cred:
                    cred['secret_data'] = self.decrypt(cred.pop('encrypted_data'))
                results.append(cred)
            
            return results
    
    # =========================================================================
    # Usage Tracking
    # =========================================================================
    
    def log_usage(
        self,
        credential_id: int,
        credential_name: str,
        used_by: str,
        used_for: str,
        success: bool,
        error_message: str = None
    ):
        """Log credential usage for auditing."""
        db = get_db()
        with db.cursor() as cursor:
            # Log the usage
            cursor.execute("""
                INSERT INTO credential_usage_log 
                (credential_id, credential_name, used_by, used_for, success, error_message)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (credential_id, credential_name, used_by, used_for, success, error_message))
            
            # Update usage count and last_used_at
            if credential_id:
                cursor.execute("""
                    UPDATE credentials
                    SET used_by_count = used_by_count + 1, last_used_at = %s
                    WHERE id = %s
                """, (now_utc(), credential_id))
            
            db.get_connection().commit()
    
    def get_usage_log(
        self,
        credential_id: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get credential usage log."""
        db = get_db()
        with db.cursor() as cursor:
            if credential_id:
                cursor.execute("""
                    SELECT id, credential_id, credential_name, used_by, used_for,
                           success, error_message, used_at
                    FROM credential_usage_log
                    WHERE credential_id = %s
                    ORDER BY used_at DESC
                    LIMIT %s
                """, (credential_id, limit))
            else:
                cursor.execute("""
                    SELECT id, credential_id, credential_name, used_by, used_for,
                           success, error_message, used_at
                    FROM credential_usage_log
                    ORDER BY used_at DESC
                    LIMIT %s
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # Expiration Tracking
    # =========================================================================
    
    def get_expiring_credentials(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get credentials that will expire within the specified number of days."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, credential_type, valid_until, owner, category, environment,
                       EXTRACT(DAY FROM (valid_until - CURRENT_TIMESTAMP))::INTEGER as days_remaining
                FROM credentials
                WHERE is_deleted = FALSE
                  AND valid_until IS NOT NULL
                  AND valid_until > CURRENT_TIMESTAMP
                  AND valid_until < CURRENT_TIMESTAMP + (%s || ' days')::INTERVAL
                ORDER BY valid_until ASC
            """, (days_ahead,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_expired_credentials(self) -> List[Dict[str, Any]]:
        """Get all expired credentials."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, credential_type, valid_until, owner, category, environment
                FROM credentials
                WHERE is_deleted = FALSE
                  AND valid_until IS NOT NULL
                  AND valid_until < CURRENT_TIMESTAMP
                ORDER BY valid_until DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_expiration_status(self) -> int:
        """Update is_expired flag for all credentials. Returns count of newly expired."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE credentials
                SET is_expired = TRUE, status = 'expired'
                WHERE valid_until IS NOT NULL 
                  AND valid_until < CURRENT_TIMESTAMP 
                  AND is_expired = FALSE
                  AND is_deleted = FALSE
                RETURNING id, name, credential_type
            """)
            
            expired = cursor.fetchall()
            db.get_connection().commit()
            
            # Log expiration events
            if expired:
                audit = get_audit_service()
                for row in expired:
                    audit.log_expired(
                        credential_id=row['id'],
                        credential_name=row['name'],
                        credential_type=row['credential_type']
                    )
            
            return len(expired)
    
    def get_credential_statistics(self) -> Dict[str, Any]:
        """Get statistics about credentials in the vault."""
        db = get_db()
        with db.cursor() as cursor:
            # Total counts by type
            cursor.execute("""
                SELECT credential_type, COUNT(*) as count
                FROM credentials
                WHERE is_deleted = FALSE
                GROUP BY credential_type
                ORDER BY count DESC
            """)
            by_type = {row['credential_type']: row['count'] for row in cursor.fetchall()}
            
            # Total counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM credentials
                WHERE is_deleted = FALSE
                GROUP BY status
            """)
            by_status = {row['status'] or 'active': row['count'] for row in cursor.fetchall()}
            
            # Expiration stats
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE valid_until IS NULL) as no_expiration,
                    COUNT(*) FILTER (WHERE valid_until < CURRENT_TIMESTAMP) as expired,
                    COUNT(*) FILTER (WHERE valid_until BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '7 days') as expiring_7_days,
                    COUNT(*) FILTER (WHERE valid_until BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '30 days') as expiring_30_days,
                    COUNT(*) FILTER (WHERE valid_until > CURRENT_TIMESTAMP + INTERVAL '30 days') as valid
                FROM credentials
                WHERE is_deleted = FALSE
            """)
            expiration = dict(cursor.fetchone())
            
            # Usage stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE used_by_count > 0) as used_at_least_once,
                    COUNT(*) FILTER (WHERE last_used_at > CURRENT_TIMESTAMP - INTERVAL '30 days') as used_last_30_days,
                    COUNT(*) FILTER (WHERE last_used_at IS NULL OR last_used_at < CURRENT_TIMESTAMP - INTERVAL '90 days') as unused_90_days
                FROM credentials
                WHERE is_deleted = FALSE
            """)
            usage = dict(cursor.fetchone())
            
            return {
                'total': usage['total'],
                'by_type': by_type,
                'by_status': by_status,
                'expiration': expiration,
                'usage': usage
            }

    # =========================================================================
    # Enterprise Authentication Support
    # =========================================================================
    
    def get_enterprise_auth_config(self, auth_type: str, config_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Get enterprise auth server configuration.
        
        Args:
            auth_type: Type of auth (tacacs, radius, ldap, active_directory)
            config_name: Optional specific config name, otherwise returns default
        
        Returns:
            Auth config with decrypted server credentials
        """
        db = get_db()
        with db.cursor() as cursor:
            if config_name:
                cursor.execute("""
                    SELECT eac.*, c.encrypted_data, c.credential_type
                    FROM enterprise_auth_configs eac
                    LEFT JOIN credentials c ON eac.credential_id = c.id
                    WHERE eac.name = %s AND eac.enabled = TRUE
                """, (config_name,))
            else:
                cursor.execute("""
                    SELECT eac.*, c.encrypted_data, c.credential_type
                    FROM enterprise_auth_configs eac
                    LEFT JOIN credentials c ON eac.credential_id = c.id
                    WHERE eac.auth_type = %s AND eac.enabled = TRUE
                    ORDER BY eac.is_default DESC, eac.priority DESC
                    LIMIT 1
                """, (auth_type,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            config = dict(row)
            if config.get('encrypted_data'):
                config['server_config'] = self.decrypt(config['encrypted_data'])
                del config['encrypted_data']
            
            return config
    
    def get_enterprise_auth_user(self, user_id: int = None, user_name: str = None, 
                                  include_secret: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get enterprise auth user credentials.
        
        Args:
            user_id: User ID
            user_name: User name (alternative to ID)
            include_secret: Whether to include decrypted credentials
        
        Returns:
            User record with optional decrypted credentials
        """
        db = get_db()
        with db.cursor() as cursor:
            if user_id:
                cursor.execute("""
                    SELECT eau.*, eac.auth_type, eac.name as config_name
                    FROM enterprise_auth_users eau
                    JOIN enterprise_auth_configs eac ON eau.auth_config_id = eac.id
                    WHERE eau.id = %s AND eau.enabled = TRUE
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT eau.*, eac.auth_type, eac.name as config_name
                    FROM enterprise_auth_users eau
                    JOIN enterprise_auth_configs eac ON eau.auth_config_id = eac.id
                    WHERE eau.name = %s AND eau.enabled = TRUE
                """, (user_name,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user = dict(row)
            if include_secret and user.get('encrypted_credentials'):
                user['credentials'] = self.decrypt(user['encrypted_credentials'])
            if 'encrypted_credentials' in user:
                del user['encrypted_credentials']
            
            return user
    
    def resolve_device_credentials(self, device_ip: str, credential_type: str = 'ssh',
                                    include_secret: bool = True) -> Optional[Dict[str, Any]]:
        """
        Resolve credentials for a device, supporting both local and enterprise auth.
        
        This is the main method jobs should use to get credentials for device access.
        
        Args:
            device_ip: IP address of the device
            credential_type: Type of credential needed (ssh, snmp, etc.)
            include_secret: Whether to include decrypted secrets
        
        Returns:
            Dict with auth_method and credentials:
            - For local: {'auth_method': 'local', 'credentials': {...}}
            - For enterprise: {'auth_method': 'tacacs', 'credentials': {...}, 'server_config': {...}}
        """
        db = get_db()
        with db.cursor() as cursor:
            # Check device_credentials for this IP
            cursor.execute("""
                SELECT dc.*, c.name as credential_name, c.encrypted_data,
                       eau.id as enterprise_user_id, eau.encrypted_credentials as enterprise_creds,
                       eac.auth_type, eac.credential_id as server_credential_id
                FROM device_credentials dc
                LEFT JOIN credentials c ON dc.credential_id = c.id
                LEFT JOIN enterprise_auth_users eau ON dc.enterprise_auth_user_id = eau.id
                LEFT JOIN enterprise_auth_configs eac ON eau.auth_config_id = eac.id
                WHERE dc.ip_address = %s 
                  AND (dc.credential_type = %s OR dc.credential_type IS NULL)
                ORDER BY dc.priority DESC
                LIMIT 1
            """, (device_ip, credential_type))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            device_cred = dict(row)
            auth_method = device_cred.get('auth_method', 'local')
            
            result = {
                'auth_method': auth_method,
                'device_ip': device_ip,
                'credential_type': credential_type,
            }
            
            if auth_method == 'local':
                # Local credentials - decrypt from credential vault
                if include_secret and device_cred.get('encrypted_data'):
                    result['credentials'] = self.decrypt(device_cred['encrypted_data'])
                result['credential_name'] = device_cred.get('credential_name')
                result['credential_id'] = device_cred.get('credential_id')
            else:
                # Enterprise auth - get user credentials and server config
                if include_secret and device_cred.get('enterprise_creds'):
                    result['credentials'] = self.decrypt(device_cred['enterprise_creds'])
                
                result['enterprise_user_id'] = device_cred.get('enterprise_user_id')
                
                # Get server config
                if device_cred.get('server_credential_id'):
                    server_cred = self.get_credential(
                        device_cred['server_credential_id'], 
                        include_secret=include_secret
                    )
                    if server_cred:
                        result['server_config'] = server_cred.get('secret_data', {})
            
            return result
    
    def create_enterprise_auth_config(self, name: str, auth_type: str, 
                                       credential_id: int, is_default: bool = False,
                                       priority: int = 0) -> Dict[str, Any]:
        """Create an enterprise auth server configuration."""
        db = get_db()
        with db.cursor() as cursor:
            # If setting as default, unset other defaults for this type
            if is_default:
                cursor.execute("""
                    UPDATE enterprise_auth_configs 
                    SET is_default = FALSE 
                    WHERE auth_type = %s
                """, (auth_type,))
            
            cursor.execute("""
                INSERT INTO enterprise_auth_configs 
                (name, auth_type, credential_id, is_default, priority)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, auth_type, credential_id, is_default, priority, enabled, created_at
            """, (name, auth_type, credential_id, is_default, priority))
            
            row = cursor.fetchone()
            db.get_connection().commit()
            return dict(row)
    
    def create_enterprise_auth_user(self, name: str, auth_config_id: int,
                                     username: str, password: str,
                                     description: str = None,
                                     is_service_account: bool = False) -> Dict[str, Any]:
        """Create an enterprise auth user credential."""
        db = get_db()
        
        # Encrypt the credentials
        encrypted = self.encrypt({'username': username, 'password': password})
        
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO enterprise_auth_users 
                (name, description, auth_config_id, encrypted_credentials, username, is_service_account)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, auth_config_id, username, is_service_account, enabled, created_at
            """, (name, description, auth_config_id, encrypted, username, is_service_account))
            
            row = cursor.fetchone()
            db.get_connection().commit()
            return dict(row)
    
    def list_enterprise_auth_configs(self, auth_type: str = None) -> List[Dict[str, Any]]:
        """List enterprise auth configurations."""
        db = get_db()
        with db.cursor() as cursor:
            if auth_type:
                cursor.execute("""
                    SELECT eac.*, c.name as credential_name
                    FROM enterprise_auth_configs eac
                    LEFT JOIN credentials c ON eac.credential_id = c.id
                    WHERE eac.auth_type = %s
                    ORDER BY eac.is_default DESC, eac.priority DESC
                """, (auth_type,))
            else:
                cursor.execute("""
                    SELECT eac.*, c.name as credential_name
                    FROM enterprise_auth_configs eac
                    LEFT JOIN credentials c ON eac.credential_id = c.id
                    ORDER BY eac.auth_type, eac.is_default DESC, eac.priority DESC
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    def list_enterprise_auth_users(self, auth_config_id: int = None) -> List[Dict[str, Any]]:
        """List enterprise auth users."""
        db = get_db()
        with db.cursor() as cursor:
            if auth_config_id:
                cursor.execute("""
                    SELECT eau.id, eau.name, eau.description, eau.username, 
                           eau.is_service_account, eau.enabled, eau.created_at, eau.last_used_at,
                           eac.name as config_name, eac.auth_type
                    FROM enterprise_auth_users eau
                    JOIN enterprise_auth_configs eac ON eau.auth_config_id = eac.id
                    WHERE eau.auth_config_id = %s
                    ORDER BY eau.name
                """, (auth_config_id,))
            else:
                cursor.execute("""
                    SELECT eau.id, eau.name, eau.description, eau.username, 
                           eau.is_service_account, eau.enabled, eau.created_at, eau.last_used_at,
                           eac.name as config_name, eac.auth_type
                    FROM enterprise_auth_users eau
                    JOIN enterprise_auth_configs eac ON eau.auth_config_id = eac.id
                    ORDER BY eac.auth_type, eau.name
                """)
            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_credential_service = None


def get_credential_service() -> CredentialService:
    """Get the credential service singleton."""
    global _credential_service
    if _credential_service is None:
        _credential_service = CredentialService()
    return _credential_service
