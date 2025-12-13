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
        created_by: str = None
    ) -> Dict[str, Any]:
        """
        Create a new credential.
        
        Args:
            name: Unique name for the credential
            credential_type: Type (ssh, snmp, api_key, password)
            credential_data: Sensitive data to encrypt (password, private_key, etc.)
            description: Optional description
            username: Optional username for display
            created_by: Who created this credential
        
        Returns:
            Created credential (without sensitive data)
        """
        encrypted_data = self.encrypt(credential_data)
        
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO credentials 
                (name, description, credential_type, encrypted_data, username, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, credential_type, username, 
                          used_by_count, last_used_at, created_at, updated_at
            """, (name, description, credential_type, encrypted_data, username, created_by))
            
            row = cursor.fetchone()
            db.get_connection().commit()
            
            return dict(row)
    
    def get_credential(self, credential_id: int, include_secret: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a credential by ID.
        
        Args:
            credential_id: Credential ID
            include_secret: If True, decrypt and include sensitive data
        
        Returns:
            Credential data or None
        """
        db = get_db()
        with db.cursor() as cursor:
            if include_secret:
                cursor.execute("""
                    SELECT id, name, description, credential_type, encrypted_data,
                           username, used_by_count, last_used_at, created_at, updated_at
                    FROM credentials
                    WHERE id = %s AND is_deleted = FALSE
                """, (credential_id,))
            else:
                cursor.execute("""
                    SELECT id, name, description, credential_type, 
                           username, used_by_count, last_used_at, created_at, updated_at
                    FROM credentials
                    WHERE id = %s AND is_deleted = FALSE
                """, (credential_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            result = dict(row)
            
            if include_secret and 'encrypted_data' in result:
                result['secret_data'] = self.decrypt(result.pop('encrypted_data'))
            
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
    
    def list_credentials(self, credential_type: str = None) -> List[Dict[str, Any]]:
        """
        List all credentials (without sensitive data).
        
        Args:
            credential_type: Optional filter by type
        
        Returns:
            List of credentials
        """
        db = get_db()
        with db.cursor() as cursor:
            if credential_type:
                cursor.execute("""
                    SELECT id, name, description, credential_type, 
                           username, used_by_count, last_used_at, created_at, updated_at
                    FROM credentials
                    WHERE is_deleted = FALSE AND credential_type = %s
                    ORDER BY name
                """, (credential_type,))
            else:
                cursor.execute("""
                    SELECT id, name, description, credential_type, 
                           username, used_by_count, last_used_at, created_at, updated_at
                    FROM credentials
                    WHERE is_deleted = FALSE
                    ORDER BY name
                """)
            
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
    
    def delete_credential(self, credential_id: int) -> bool:
        """Soft delete a credential."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE credentials
                SET is_deleted = TRUE, updated_at = %s
                WHERE id = %s AND is_deleted = FALSE
            """, (now_utc(), credential_id))
            db.get_connection().commit()
            return cursor.rowcount > 0
    
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


# Singleton instance
_credential_service = None


def get_credential_service() -> CredentialService:
    """Get the credential service singleton."""
    global _credential_service
    if _credential_service is None:
        _credential_service = CredentialService()
    return _credential_service
