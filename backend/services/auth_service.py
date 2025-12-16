"""
Authentication and Authorization Service

Handles user authentication, session management, 2FA, and RBAC.
"""

import os
import secrets
import hashlib
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from functools import wraps

import bcrypt
import pyotp
from cryptography.fernet import Fernet

from backend.database import get_db

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication, authorization, and user management."""
    
    def __init__(self):
        self.db = get_db()
        # Use same encryption key as credential service or generate one
        self._encryption_key = os.environ.get('ENCRYPTION_KEY')
        if self._encryption_key:
            self._fernet = Fernet(self._encryption_key.encode())
        else:
            # Generate a key for development (should be set in production)
            self._fernet = Fernet(Fernet.generate_key())
        
        # Session settings
        self.session_duration = timedelta(hours=24)
        self.refresh_token_duration = timedelta(days=7)
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        
        # 2FA settings
        self.totp_issuer = "OpsConductor"
        self.email_code_expiry = timedelta(minutes=10)
        self.email_code_length = 6
    
    # =========================================================================
    # PASSWORD HASHING
    # =========================================================================
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def hash_token(self, token: str) -> str:
        """Hash a token using SHA-256."""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    # =========================================================================
    # ENCRYPTION
    # =========================================================================
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self._fernet.encrypt(data.encode('utf-8')).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self._fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
    
    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================
    
    def create_user(
        self,
        username: str,
        email: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        auth_method: str = 'local',
        role_names: Optional[List[str]] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new user account."""
        try:
            # Validate
            if auth_method == 'local' and not password:
                raise ValueError("Password required for local authentication")
            
            # Hash password if provided
            password_hash = self.hash_password(password) if password else None
            
            with self.db.cursor() as cursor:
                # Check for existing user
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s OR email = %s",
                    (username, email)
                )
                if cursor.fetchone():
                    raise ValueError("Username or email already exists")
                
                # Create user
                cursor.execute("""
                    INSERT INTO users (
                        username, email, password_hash, first_name, last_name,
                        display_name, auth_method, status, created_by, password_changed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, username, email, first_name, last_name, display_name,
                              status, auth_method, created_at
                """, (
                    username, email, password_hash, first_name, last_name,
                    f"{first_name or ''} {last_name or ''}".strip() or username,
                    auth_method, 'active', created_by,
                    datetime.utcnow() if password else None
                ))
                user = dict(cursor.fetchone())
                
                # Assign roles
                if role_names:
                    for role_name in role_names:
                        cursor.execute("""
                            INSERT INTO user_roles (user_id, role_id, assigned_by)
                            SELECT %s, id, %s FROM roles WHERE name = %s
                        """, (user['id'], created_by, role_name))
                else:
                    # Assign default role
                    cursor.execute("""
                        INSERT INTO user_roles (user_id, role_id)
                        SELECT %s, id FROM roles WHERE is_default = TRUE
                    """, (user['id'],))
                
                self.db.get_connection().commit()
                
                # Log event
                self._log_auth_event(
                    user_id=user['id'],
                    username=username,
                    event_type='user_created',
                    event_status='success'
                )
                
                return user
                
        except Exception as e:
            self.db.get_connection().rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, first_name, last_name, display_name,
                       avatar_url, status, auth_method, email_verified,
                       two_factor_enabled, two_factor_method, timezone, preferences,
                       created_at, last_login_at
                FROM users WHERE id = %s
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, password_hash, first_name, last_name,
                       display_name, status, auth_method, email_verified,
                       two_factor_enabled, two_factor_method, totp_secret_encrypted,
                       failed_login_attempts, locked_until
                FROM users WHERE username = %s OR email = %s
            """, (username, username))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """Get roles assigned to a user."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT r.id, r.name, r.display_name, r.description, r.priority
                FROM roles r
                JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = %s
                AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
                ORDER BY r.priority DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permission codes for a user (from all their roles)."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT p.code
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN user_roles ur ON rp.role_id = ur.role_id
                WHERE ur.user_id = %s
                AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
            """, (user_id,))
            return [row['code'] for row in cursor.fetchall()]
    
    def user_has_permission(self, user_id: int, permission_code: str) -> bool:
        """Check if user has a specific permission."""
        permissions = self.get_user_permissions(user_id)
        return permission_code in permissions
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user fields."""
        allowed_fields = [
            'email', 'first_name', 'last_name', 'display_name', 'avatar_url',
            'status', 'timezone', 'preferences'
        ]
        
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}
        if not update_fields:
            return self.get_user(user_id)
        
        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        values = list(update_fields.values()) + [user_id]
        
        with self.db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE users SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING id, username, email, first_name, last_name, display_name,
                          status, auth_method, created_at
            """, values)
            self.db.get_connection().commit()
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.get_user_by_username_internal(user_id)
        if not user:
            return False
        
        if not self.verify_password(current_password, user['password_hash']):
            return False
        
        new_hash = self.hash_password(new_password)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET password_hash = %s, password_changed_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """, (new_hash, user_id))
            self.db.get_connection().commit()
        
        self._log_auth_event(
            user_id=user_id,
            username=user['username'],
            event_type='password_changed',
            event_status='success'
        )
        
        return True
    
    def get_user_by_username_internal(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with password hash by ID (internal use only)."""
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    
    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticate user with username/password.
        
        Returns:
            (success, user_data, error_message)
            If 2FA is required, user_data will include 'requires_2fa': True
        """
        user = self.get_user_by_username(username)
        
        if not user:
            self._log_auth_event(
                username=username,
                event_type='login_failed',
                event_status='failure',
                ip_address=ip_address,
                details={'reason': 'user_not_found'}
            )
            return False, None, "Invalid username or password"
        
        # Check if account is locked
        if user['locked_until'] and user['locked_until'] > datetime.utcnow():
            return False, None, f"Account locked. Try again later."
        
        # Check account status
        if user['status'] != 'active':
            return False, None, f"Account is {user['status']}"
        
        # Verify password
        if not user['password_hash'] or not self.verify_password(password, user['password_hash']):
            self._increment_failed_attempts(user['id'])
            self._log_auth_event(
                user_id=user['id'],
                username=username,
                event_type='login_failed',
                event_status='failure',
                ip_address=ip_address,
                details={'reason': 'invalid_password'}
            )
            return False, None, "Invalid username or password"
        
        # Reset failed attempts on successful password
        self._reset_failed_attempts(user['id'])
        
        # Check if 2FA is required
        if user['two_factor_enabled']:
            return True, {
                'user_id': user['id'],
                'username': user['username'],
                'requires_2fa': True,
                'two_factor_method': user['two_factor_method']
            }, None
        
        # Create session
        session = self._create_session(user['id'], ip_address, user_agent)
        
        # Update last login
        self._update_last_login(user['id'], ip_address)
        
        self._log_auth_event(
            user_id=user['id'],
            username=username,
            event_type='login',
            event_status='success',
            ip_address=ip_address
        )
        
        return True, {
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'display_name': user['display_name'],
            'session_token': session['session_token'],
            'refresh_token': session['refresh_token'],
            'expires_at': session['expires_at'].isoformat()
        }, None
    
    def _increment_failed_attempts(self, user_id: int):
        """Increment failed login attempts and lock if needed."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET 
                    failed_login_attempts = failed_login_attempts + 1,
                    locked_until = CASE 
                        WHEN failed_login_attempts + 1 >= %s 
                        THEN NOW() + INTERVAL '%s minutes'
                        ELSE locked_until 
                    END
                WHERE id = %s
            """, (self.max_failed_attempts, int(self.lockout_duration.total_seconds() / 60), user_id))
            self.db.get_connection().commit()
    
    def _reset_failed_attempts(self, user_id: int):
        """Reset failed login attempts."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET failed_login_attempts = 0, locked_until = NULL
                WHERE id = %s
            """, (user_id,))
            self.db.get_connection().commit()
    
    def _update_last_login(self, user_id: int, ip_address: Optional[str]):
        """Update last login timestamp."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET last_login_at = NOW(), last_login_ip = %s
                WHERE id = %s
            """, (ip_address, user_id))
            self.db.get_connection().commit()
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def _create_session(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        two_factor_verified: bool = False
    ) -> Dict[str, Any]:
        """Create a new session for a user."""
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        expires_at = datetime.utcnow() + self.session_duration
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_sessions (
                    user_id, session_token_hash, refresh_token_hash,
                    ip_address, user_agent, expires_at, two_factor_verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                self.hash_token(session_token),
                self.hash_token(refresh_token),
                ip_address,
                user_agent,
                expires_at,
                two_factor_verified
            ))
            self.db.get_connection().commit()
        
        return {
            'session_token': session_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at
        }
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate a session token and return user info."""
        token_hash = self.hash_token(session_token)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT s.id as session_id, s.user_id, s.two_factor_verified,
                       s.expires_at, s.last_activity_at,
                       u.username, u.email, u.display_name, u.status,
                       u.two_factor_enabled
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token_hash = %s
                AND s.revoked = FALSE
                AND s.expires_at > NOW()
            """, (token_hash,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            session = dict(row)
            
            # Check if user is still active
            if session['status'] != 'active':
                return None
            
            # Check if 2FA is required but not verified
            if session['two_factor_enabled'] and not session['two_factor_verified']:
                return None
            
            # Update last activity
            cursor.execute("""
                UPDATE user_sessions SET last_activity_at = NOW()
                WHERE id = %s
            """, (session['session_id'],))
            self.db.get_connection().commit()
            
            return session
    
    def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh a session using the refresh token."""
        token_hash = self.hash_token(refresh_token)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.user_id, s.two_factor_verified, s.ip_address, s.user_agent
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.refresh_token_hash = %s
                AND s.revoked = FALSE
                AND u.status = 'active'
            """, (token_hash,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            old_session = dict(row)
            
            # Revoke old session
            cursor.execute("""
                UPDATE user_sessions SET revoked = TRUE, revoked_at = NOW(), revoked_reason = 'refreshed'
                WHERE id = %s
            """, (old_session['id'],))
            self.db.get_connection().commit()
        
        # Create new session
        return self._create_session(
            old_session['user_id'],
            old_session['ip_address'],
            old_session['user_agent'],
            old_session['two_factor_verified']
        )
    
    def revoke_session(self, session_token: str, reason: str = 'logout'):
        """Revoke a session."""
        token_hash = self.hash_token(session_token)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE user_sessions 
                SET revoked = TRUE, revoked_at = NOW(), revoked_reason = %s
                WHERE session_token_hash = %s
            """, (reason, token_hash))
            self.db.get_connection().commit()
    
    def revoke_all_sessions(self, user_id: int, except_session: Optional[str] = None):
        """Revoke all sessions for a user."""
        with self.db.cursor() as cursor:
            if except_session:
                except_hash = self.hash_token(except_session)
                cursor.execute("""
                    UPDATE user_sessions 
                    SET revoked = TRUE, revoked_at = NOW(), revoked_reason = 'revoke_all'
                    WHERE user_id = %s AND session_token_hash != %s AND revoked = FALSE
                """, (user_id, except_hash))
            else:
                cursor.execute("""
                    UPDATE user_sessions 
                    SET revoked = TRUE, revoked_at = NOW(), revoked_reason = 'revoke_all'
                    WHERE user_id = %s AND revoked = FALSE
                """, (user_id,))
            self.db.get_connection().commit()
    
    # =========================================================================
    # TWO-FACTOR AUTHENTICATION
    # =========================================================================
    
    def setup_totp(self, user_id: int) -> Dict[str, Any]:
        """Set up TOTP 2FA for a user. Returns secret and provisioning URI."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Generate secret
        secret = pyotp.random_base32()
        
        # Create provisioning URI for QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user['email'],
            issuer_name=self.totp_issuer
        )
        
        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        # Store encrypted secret and backup codes (not enabled yet)
        encrypted_secret = self.encrypt(secret)
        encrypted_backup = self.encrypt(json.dumps(backup_codes))
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET 
                    totp_secret_encrypted = %s,
                    totp_backup_codes_encrypted = %s
                WHERE id = %s
            """, (encrypted_secret, encrypted_backup, user_id))
            self.db.get_connection().commit()
        
        return {
            'secret': secret,
            'provisioning_uri': provisioning_uri,
            'backup_codes': backup_codes
        }
    
    def verify_totp_setup(self, user_id: int, code: str) -> bool:
        """Verify TOTP code to complete 2FA setup."""
        user = self.get_user_by_username_internal(user_id)
        if not user or not user.get('totp_secret_encrypted'):
            return False
        
        secret = self.decrypt(user['totp_secret_encrypted'])
        totp = pyotp.TOTP(secret)
        
        if totp.verify(code, valid_window=1):
            with self.db.cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET 
                        two_factor_enabled = TRUE,
                        two_factor_method = 'totp'
                    WHERE id = %s
                """, (user_id,))
                self.db.get_connection().commit()
            
            self._log_auth_event(
                user_id=user_id,
                username=user['username'],
                event_type='2fa_enabled',
                event_status='success',
                details={'method': 'totp'}
            )
            return True
        
        return False
    
    def verify_totp(self, user_id: int, code: str) -> bool:
        """Verify a TOTP code during login."""
        user = self.get_user_by_username_internal(user_id)
        if not user or not user.get('totp_secret_encrypted'):
            return False
        
        # Check if it's a backup code
        if len(code) == 8:
            return self._verify_backup_code(user_id, code)
        
        secret = self.decrypt(user['totp_secret_encrypted'])
        totp = pyotp.TOTP(secret)
        
        return totp.verify(code, valid_window=1)
    
    def _verify_backup_code(self, user_id: int, code: str) -> bool:
        """Verify and consume a backup code."""
        user = self.get_user_by_username_internal(user_id)
        if not user or not user.get('totp_backup_codes_encrypted'):
            return False
        
        backup_codes = json.loads(self.decrypt(user['totp_backup_codes_encrypted']))
        code_upper = code.upper()
        
        if code_upper in backup_codes:
            backup_codes.remove(code_upper)
            encrypted_backup = self.encrypt(json.dumps(backup_codes))
            
            with self.db.cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET totp_backup_codes_encrypted = %s
                    WHERE id = %s
                """, (encrypted_backup, user_id))
                self.db.get_connection().commit()
            
            return True
        
        return False
    
    def complete_2fa_login(
        self,
        user_id: int,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Complete login after 2FA verification."""
        user = self.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        # Verify the code
        if not self.verify_totp(user_id, code):
            self._log_auth_event(
                user_id=user_id,
                username=user['username'],
                event_type='2fa_failed',
                event_status='failure',
                ip_address=ip_address
            )
            return False, None, "Invalid verification code"
        
        # Create session with 2FA verified
        session = self._create_session(user_id, ip_address, user_agent, two_factor_verified=True)
        
        # Update last login
        self._update_last_login(user_id, ip_address)
        
        self._log_auth_event(
            user_id=user_id,
            username=user['username'],
            event_type='login',
            event_status='success',
            ip_address=ip_address,
            details={'2fa_verified': True}
        )
        
        return True, {
            'user_id': user_id,
            'username': user['username'],
            'email': user['email'],
            'display_name': user['display_name'],
            'session_token': session['session_token'],
            'refresh_token': session['refresh_token'],
            'expires_at': session['expires_at'].isoformat()
        }, None
    
    def disable_2fa(self, user_id: int, password: str) -> bool:
        """Disable 2FA for a user (requires password confirmation)."""
        user = self.get_user_by_username_internal(user_id)
        if not user:
            return False
        
        if not self.verify_password(password, user['password_hash']):
            return False
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET 
                    two_factor_enabled = FALSE,
                    two_factor_method = NULL,
                    totp_secret_encrypted = NULL,
                    totp_backup_codes_encrypted = NULL
                WHERE id = %s
            """, (user_id,))
            self.db.get_connection().commit()
        
        self._log_auth_event(
            user_id=user_id,
            username=user['username'],
            event_type='2fa_disabled',
            event_status='success'
        )
        
        return True
    
    # =========================================================================
    # EMAIL VERIFICATION CODES
    # =========================================================================
    
    def generate_email_code(self, user_id: int, code_type: str = 'login') -> str:
        """Generate and store an email verification code."""
        code = ''.join([str(secrets.randbelow(10)) for _ in range(self.email_code_length)])
        code_hash = self.hash_token(code)
        expires_at = datetime.utcnow() + self.email_code_expiry
        
        user = self.get_user(user_id)
        
        with self.db.cursor() as cursor:
            # Invalidate old codes
            cursor.execute("""
                DELETE FROM two_factor_codes 
                WHERE user_id = %s AND code_type = %s
            """, (user_id, code_type))
            
            # Create new code
            cursor.execute("""
                INSERT INTO two_factor_codes (user_id, code_hash, code_type, sent_to, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, code_hash, code_type, user['email'], expires_at))
            self.db.get_connection().commit()
        
        return code
    
    def verify_email_code(self, user_id: int, code: str, code_type: str = 'login') -> bool:
        """Verify an email code."""
        code_hash = self.hash_token(code)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, attempts, max_attempts
                FROM two_factor_codes
                WHERE user_id = %s AND code_hash = %s AND code_type = %s
                AND expires_at > NOW() AND used_at IS NULL
            """, (user_id, code_hash, code_type))
            row = cursor.fetchone()
            
            if not row:
                # Increment attempts on any matching code
                cursor.execute("""
                    UPDATE two_factor_codes SET attempts = attempts + 1
                    WHERE user_id = %s AND code_type = %s AND expires_at > NOW() AND used_at IS NULL
                """, (user_id, code_type))
                self.db.get_connection().commit()
                return False
            
            code_record = dict(row)
            
            if code_record['attempts'] >= code_record['max_attempts']:
                return False
            
            # Mark as used
            cursor.execute("""
                UPDATE two_factor_codes SET used_at = NOW()
                WHERE id = %s
            """, (code_record['id'],))
            self.db.get_connection().commit()
            
            return True
    
    # =========================================================================
    # ROLE MANAGEMENT
    # =========================================================================
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """List all roles."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT r.*, 
                       (SELECT COUNT(*) FROM user_roles ur WHERE ur.role_id = r.id) as user_count
                FROM roles r
                ORDER BY r.priority DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        """Get role by ID with its permissions."""
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            role = dict(row)
            
            # Get permissions
            cursor.execute("""
                SELECT p.* FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = %s
                ORDER BY p.module, p.resource, p.action
            """, (role_id,))
            role['permissions'] = [dict(r) for r in cursor.fetchall()]
            
            return role
    
    def assign_role(self, user_id: int, role_id: int, assigned_by: Optional[int] = None) -> bool:
        """Assign a role to a user."""
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_roles (user_id, role_id, assigned_by)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                """, (user_id, role_id, assigned_by))
                self.db.get_connection().commit()
            return True
        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return False
    
    def remove_role(self, user_id: int, role_id: int) -> bool:
        """Remove a role from a user."""
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM user_roles WHERE user_id = %s AND role_id = %s
                """, (user_id, role_id))
                self.db.get_connection().commit()
            return True
        except Exception as e:
            logger.error(f"Error removing role: {e}")
            return False
    
    # =========================================================================
    # PERMISSION MANAGEMENT
    # =========================================================================
    
    def list_permissions(self, module: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all permissions, optionally filtered by module."""
        with self.db.cursor() as cursor:
            if module:
                cursor.execute("""
                    SELECT * FROM permissions WHERE module = %s
                    ORDER BY module, resource, action
                """, (module,))
            else:
                cursor.execute("""
                    SELECT * FROM permissions ORDER BY module, resource, action
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_permission_modules(self) -> List[str]:
        """Get list of unique permission modules."""
        with self.db.cursor() as cursor:
            cursor.execute("SELECT DISTINCT module FROM permissions ORDER BY module")
            return [row['module'] for row in cursor.fetchall()]
    
    # =========================================================================
    # USER LISTING
    # =========================================================================
    
    def list_users(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List users with optional filtering."""
        conditions = []
        params = []
        
        if status:
            conditions.append("u.status = %s")
            params.append(status)
        
        if search:
            conditions.append("(u.username ILIKE %s OR u.email ILIKE %s OR u.display_name ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        with self.db.cursor() as cursor:
            # Get total count
            cursor.execute(f"SELECT COUNT(*) as count FROM users u {where_clause}", params)
            total = cursor.fetchone()['count']
            
            # Get users
            cursor.execute(f"""
                SELECT u.id, u.username, u.email, u.first_name, u.last_name, u.display_name,
                       u.status, u.auth_method, u.two_factor_enabled, u.email_verified,
                       u.created_at, u.last_login_at,
                       array_agg(r.display_name) FILTER (WHERE r.id IS NOT NULL) as roles
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                {where_clause}
                GROUP BY u.id
                ORDER BY u.created_at DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            
            users = [dict(row) for row in cursor.fetchall()]
        
        return {
            'users': users,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================
    
    def _log_auth_event(
        self,
        event_type: str,
        event_status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an authentication event."""
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_audit_log (user_id, username, event_type, event_status, ip_address, user_agent, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, username, event_type, event_status,
                    ip_address, user_agent,
                    json.dumps(details) if details else None
                ))
                self.db.get_connection().commit()
        except Exception as e:
            logger.error(f"Error logging auth event: {e}")
    
    def get_auth_audit_log(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get authentication audit log entries."""
        conditions = []
        params = []
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        with self.db.cursor() as cursor:
            cursor.execute(f"""
                SELECT * FROM auth_audit_log
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """, params + [limit])
            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_auth_service = None

def get_auth_service() -> AuthService:
    """Get the singleton AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
