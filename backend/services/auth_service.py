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
from datetime import datetime, timedelta, timezone
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
    # PASSWORD POLICY
    # =========================================================================
    
    def get_password_policy(self) -> Dict[str, Any]:
        """Get the current password policy settings."""
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM password_policy ORDER BY id LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            # Return defaults if no policy exists
            return {
                'min_length': 8,
                'max_length': 128,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special_chars': True,
                'special_chars_allowed': '!@#$%^&*()_+-=[]{}|;:,.<>?',
                'min_uppercase': 1,
                'min_lowercase': 1,
                'min_numbers': 1,
                'min_special': 1,
                'password_expires': True,
                'expiration_days': 90,
                'expiration_warning_days': 14,
                'password_history_count': 12,
                'min_password_age_hours': 24,
                'max_failed_attempts': 5,
                'lockout_duration_minutes': 30,
                'prevent_username_in_password': True,
                'prevent_email_in_password': True,
                'prevent_common_passwords': True,
                'require_password_change_on_first_login': True
            }
    
    def update_password_policy(self, updates: Dict[str, Any], updated_by: int = None) -> Dict[str, Any]:
        """Update password policy settings."""
        allowed_fields = [
            'min_length', 'max_length', 'require_uppercase', 'require_lowercase',
            'require_numbers', 'require_special_chars', 'special_chars_allowed',
            'min_uppercase', 'min_lowercase', 'min_numbers', 'min_special',
            'password_expires', 'expiration_days', 'expiration_warning_days',
            'password_history_count', 'min_password_age_hours',
            'max_failed_attempts', 'lockout_duration_minutes', 'reset_failed_count_minutes',
            'prevent_username_in_password', 'prevent_email_in_password', 'prevent_common_passwords',
            'require_password_change_on_first_login', 'allow_password_reset'
        ]
        
        set_clauses = []
        params = []
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = %s")
                params.append(updates[field])
        
        if not set_clauses:
            return self.get_password_policy()
        
        set_clauses.append("updated_at = NOW()")
        if updated_by:
            set_clauses.append("updated_by = %s")
            params.append(updated_by)
        
        with self.db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE password_policy SET {', '.join(set_clauses)}
                WHERE id = (SELECT id FROM password_policy ORDER BY id LIMIT 1)
                RETURNING *
            """, params)
            row = cursor.fetchone()
            self.db.get_connection().commit()
            return dict(row) if row else self.get_password_policy()
    
    def validate_password(
        self, 
        password: str, 
        username: str = None, 
        email: str = None,
        user_id: int = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a password against the password policy.
        
        Returns:
            (is_valid, list_of_errors)
        """
        policy = self.get_password_policy()
        errors = []
        
        # Length checks
        if len(password) < policy['min_length']:
            errors.append(f"Password must be at least {policy['min_length']} characters")
        if len(password) > policy['max_length']:
            errors.append(f"Password must be no more than {policy['max_length']} characters")
        
        # Complexity checks
        if policy['require_uppercase']:
            uppercase_count = sum(1 for c in password if c.isupper())
            if uppercase_count < policy.get('min_uppercase', 1):
                errors.append(f"Password must contain at least {policy.get('min_uppercase', 1)} uppercase letter(s)")
        
        if policy['require_lowercase']:
            lowercase_count = sum(1 for c in password if c.islower())
            if lowercase_count < policy.get('min_lowercase', 1):
                errors.append(f"Password must contain at least {policy.get('min_lowercase', 1)} lowercase letter(s)")
        
        if policy['require_numbers']:
            number_count = sum(1 for c in password if c.isdigit())
            if number_count < policy.get('min_numbers', 1):
                errors.append(f"Password must contain at least {policy.get('min_numbers', 1)} number(s)")
        
        if policy['require_special_chars']:
            special_chars = policy.get('special_chars_allowed', '!@#$%^&*()_+-=[]{}|;:,.<>?')
            special_count = sum(1 for c in password if c in special_chars)
            if special_count < policy.get('min_special', 1):
                errors.append(f"Password must contain at least {policy.get('min_special', 1)} special character(s)")
        
        # Username/email in password check
        if policy['prevent_username_in_password'] and username:
            if username.lower() in password.lower():
                errors.append("Password cannot contain your username")
        
        if policy['prevent_email_in_password'] and email:
            email_local = email.split('@')[0].lower()
            if email_local in password.lower():
                errors.append("Password cannot contain your email address")
        
        # Common password check
        if policy['prevent_common_passwords']:
            password_hash = hashlib.sha256(password.lower().encode()).hexdigest()
            with self.db.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM common_passwords WHERE password_hash = %s",
                    (password_hash,)
                )
                if cursor.fetchone():
                    errors.append("This password is too common. Please choose a more unique password")
        
        # Password history check
        if user_id and policy['password_history_count'] > 0:
            if self._is_password_in_history(user_id, password, policy['password_history_count']):
                errors.append(f"Cannot reuse any of your last {policy['password_history_count']} passwords")
        
        # Minimum password age check
        if user_id and policy.get('min_password_age_hours', 0) > 0:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "SELECT password_changed_at FROM users WHERE id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row and row['password_changed_at']:
                    min_age = timedelta(hours=policy['min_password_age_hours'])
                    if datetime.now(timezone.utc) - row['password_changed_at'].replace(tzinfo=timezone.utc) < min_age:
                        errors.append(f"Password can only be changed once every {policy['min_password_age_hours']} hours")
        
        return len(errors) == 0, errors
    
    def _is_password_in_history(self, user_id: int, password: str, history_count: int) -> bool:
        """Check if password was used recently."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT password_hash FROM password_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, history_count))
            
            for row in cursor.fetchall():
                if self.verify_password(password, row['password_hash']):
                    return True
        return False
    
    def _add_password_to_history(self, user_id: int, password_hash: str):
        """Add a password hash to the user's history."""
        policy = self.get_password_policy()
        
        with self.db.cursor() as cursor:
            # Add new password to history
            cursor.execute("""
                INSERT INTO password_history (user_id, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (user_id, password_hash) DO UPDATE SET created_at = NOW()
            """, (user_id, password_hash))
            
            # Clean up old history entries beyond the limit
            cursor.execute("""
                DELETE FROM password_history
                WHERE user_id = %s AND id NOT IN (
                    SELECT id FROM password_history
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                )
            """, (user_id, user_id, policy['password_history_count']))
            
            self.db.get_connection().commit()
    
    def check_password_expiration(self, user_id: int) -> Dict[str, Any]:
        """Check if user's password is expired or expiring soon."""
        policy = self.get_password_policy()
        
        if not policy['password_expires']:
            return {'expired': False, 'expiring_soon': False, 'days_until_expiry': None}
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT password_changed_at, password_never_expires, must_change_password
                FROM users WHERE id = %s
            """, (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return {'expired': False, 'expiring_soon': False, 'days_until_expiry': None}
            
            if row['password_never_expires']:
                return {'expired': False, 'expiring_soon': False, 'days_until_expiry': None}
            
            if row['must_change_password']:
                return {'expired': True, 'expiring_soon': True, 'days_until_expiry': 0, 'must_change': True}
            
            if not row['password_changed_at']:
                return {'expired': True, 'expiring_soon': True, 'days_until_expiry': 0}
            
            password_age = datetime.now(timezone.utc) - row['password_changed_at'].replace(tzinfo=timezone.utc)
            days_until_expiry = policy['expiration_days'] - password_age.days
            
            return {
                'expired': days_until_expiry <= 0,
                'expiring_soon': days_until_expiry <= policy['expiration_warning_days'],
                'days_until_expiry': max(0, days_until_expiry)
            }
    
    def get_password_requirements_text(self) -> List[str]:
        """Get human-readable password requirements for display."""
        policy = self.get_password_policy()
        requirements = []
        
        requirements.append(f"At least {policy['min_length']} characters")
        
        if policy['require_uppercase']:
            requirements.append(f"At least {policy.get('min_uppercase', 1)} uppercase letter(s)")
        if policy['require_lowercase']:
            requirements.append(f"At least {policy.get('min_lowercase', 1)} lowercase letter(s)")
        if policy['require_numbers']:
            requirements.append(f"At least {policy.get('min_numbers', 1)} number(s)")
        if policy['require_special_chars']:
            requirements.append(f"At least {policy.get('min_special', 1)} special character(s)")
        
        if policy['prevent_username_in_password']:
            requirements.append("Cannot contain your username")
        if policy['prevent_common_passwords']:
            requirements.append("Cannot be a commonly used password")
        if policy['password_history_count'] > 0:
            requirements.append(f"Cannot reuse last {policy['password_history_count']} passwords")
        
        return requirements
    
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
                    datetime.now(timezone.utc) if password else None
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
    
    def get_user_permissions(self, user_id) -> List[str]:
        """
        Get all permission codes for a user (from all their roles).
        Handles both local users (integer ID) and enterprise users (string ID like 'enterprise_1').
        """
        with self.db.cursor() as cursor:
            # Handle enterprise users
            if isinstance(user_id, str) and user_id.startswith('enterprise_'):
                enterprise_id = int(user_id.replace('enterprise_', ''))
                cursor.execute("""
                    SELECT DISTINCT p.code
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN enterprise_user_roles eur ON rp.role_id = eur.role_id
                    WHERE eur.id = %s
                """, (enterprise_id,))
                return [row['code'] for row in cursor.fetchall()]
            
            # Handle local users
            cursor.execute("""
                SELECT DISTINCT p.code
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN user_roles ur ON rp.role_id = ur.role_id
                WHERE ur.user_id = %s
                AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
            """, (user_id,))
            return [row['code'] for row in cursor.fetchall()]
    
    def user_has_permission(self, user_id, permission_code: str) -> bool:
        """Check if user has a specific permission (works for both local and enterprise users)."""
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
        policy = self.get_password_policy()
        
        with self.db.cursor() as cursor:
            # Calculate expiration date
            expiration_days = policy.get('expiration_days', 90) if policy.get('password_expires') else None
            
            cursor.execute("""
                UPDATE users SET 
                    password_hash = %s, 
                    password_changed_at = NOW(),
                    password_expires_at = CASE WHEN %s IS NOT NULL THEN NOW() + INTERVAL '%s days' ELSE NULL END,
                    must_change_password = FALSE,
                    updated_at = NOW()
                WHERE id = %s
            """, (new_hash, expiration_days, expiration_days or 0, user_id))
            self.db.get_connection().commit()
        
        # Add old password to history
        if user.get('password_hash'):
            self._add_password_to_history(user_id, user['password_hash'])
        
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
        if user['locked_until'] and user['locked_until'] > datetime.now(timezone.utc):
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
        
        expires_at = datetime.now(timezone.utc) + self.session_duration
        
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
        """Validate a session token and return user info (local or enterprise)."""
        token_hash = self.hash_token(session_token)
        
        with self.db.cursor() as cursor:
            # First try to find a local user session
            cursor.execute("""
                SELECT s.id as session_id, s.user_id, s.two_factor_verified,
                       s.expires_at, s.last_activity_at, s.is_enterprise,
                       s.enterprise_username,
                       u.username, u.email, u.display_name, u.status,
                       u.two_factor_enabled
                FROM user_sessions s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.session_token_hash = %s
                AND s.revoked = FALSE
                AND s.expires_at > NOW()
            """, (token_hash,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            session = dict(row)
            
            # Handle enterprise session
            if session.get('is_enterprise'):
                # Get enterprise user's roles and permissions
                enterprise_username = session.get('enterprise_username')
                cursor.execute("""
                    SELECT eur.id, eur.username, eur.display_name, eur.email,
                           array_agg(r.name) as roles
                    FROM enterprise_user_roles eur
                    JOIN roles r ON eur.role_id = r.id
                    WHERE LOWER(eur.username) = LOWER(%s)
                    GROUP BY eur.id, eur.username, eur.display_name, eur.email
                """, (enterprise_username,))
                eur_row = cursor.fetchone()
                
                if not eur_row:
                    return None  # Enterprise user no longer has role assignment
                
                # Update last activity
                cursor.execute("""
                    UPDATE user_sessions SET last_activity_at = NOW()
                    WHERE id = %s
                """, (session['session_id'],))
                self.db.get_connection().commit()
                
                return {
                    'session_id': session['session_id'],
                    'user_id': f"enterprise_{eur_row['id']}",
                    'username': eur_row['username'],
                    'email': eur_row.get('email') or '',
                    'display_name': eur_row.get('display_name') or eur_row['username'],
                    'status': 'active',
                    'is_enterprise': True,
                    'roles': eur_row['roles'] or []
                }
            
            # Handle local user session
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
        
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET 
                        totp_secret_encrypted = %s,
                        totp_backup_codes_encrypted = %s
                    WHERE id = %s
                """, (encrypted_secret, encrypted_backup, user_id))
                self.db.get_connection().commit()
                logger.info(f"TOTP secret saved for user_id={user_id}")
        except Exception as e:
            logger.error(f"Failed to save TOTP secret: {e}")
            self.db.get_connection().rollback()
            raise
        
        return {
            'secret': secret,
            'provisioning_uri': provisioning_uri,
            'backup_codes': backup_codes
        }
    
    def verify_totp_setup(self, user_id: int, code: str) -> bool:
        """Verify TOTP code to complete 2FA setup."""
        try:
            user = self.get_user_by_username_internal(user_id)
            if not user or not user.get('totp_secret_encrypted'):
                logger.warning(f"2FA verify: user not found or no totp_secret for user_id={user_id}")
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
                    username=user.get('username'),
                    event_type='2fa_enabled',
                    event_status='success',
                    details={'method': 'totp'}
                )
                return True
            
            return False
        except Exception as e:
            logger.error(f"verify_totp_setup error: {e}")
            raise
    
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
        expires_at = datetime.now(timezone.utc) + self.email_code_expiry
        
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
        """List all roles with their permissions."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT r.*, 
                       (SELECT COUNT(*) FROM user_roles ur WHERE ur.role_id = r.id) as user_count,
                       (SELECT COUNT(*) FROM role_permissions rp WHERE rp.role_id = r.id) as permission_count
                FROM roles r
                ORDER BY r.priority DESC
            """)
            roles = [dict(row) for row in cursor.fetchall()]
            
            # Get permissions for each role
            for role in roles:
                cursor.execute("""
                    SELECT p.code FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = %s
                """, (role['id'],))
                role['permissions'] = [row['code'] for row in cursor.fetchall()]
            
            return roles
    
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
    
    def create_role(
        self,
        name: str,
        display_name: str,
        description: str = '',
        permissions: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new custom role."""
        try:
            with self.db.cursor() as cursor:
                # Check if role name exists
                cursor.execute("SELECT id FROM roles WHERE name = %s", (name,))
                if cursor.fetchone():
                    raise ValueError(f"Role '{name}' already exists")
                
                # Create role
                cursor.execute("""
                    INSERT INTO roles (name, display_name, description, is_system, priority)
                    VALUES (%s, %s, %s, FALSE, 50)
                    RETURNING *
                """, (name, display_name, description))
                role = dict(cursor.fetchone())
                
                # Assign permissions
                if permissions:
                    for perm_code in permissions:
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            SELECT %s, id FROM permissions WHERE code = %s
                        """, (role['id'], perm_code))
                
                self.db.get_connection().commit()
                
                # Get permissions list
                role['permissions'] = permissions or []
                return role
                
        except ValueError:
            raise
        except Exception as e:
            self.db.get_connection().rollback()
            logger.error(f"Error creating role: {e}")
            raise
    
    def update_role(
        self,
        role_id: int,
        display_name: str = None,
        description: str = None,
        permissions: List[str] = None
    ) -> Dict[str, Any]:
        """Update a role's properties and permissions."""
        try:
            with self.db.cursor() as cursor:
                # Update role properties
                updates = []
                params = []
                if display_name is not None:
                    updates.append("display_name = %s")
                    params.append(display_name)
                if description is not None:
                    updates.append("description = %s")
                    params.append(description)
                
                if updates:
                    params.append(role_id)
                    cursor.execute(f"""
                        UPDATE roles SET {', '.join(updates)}, updated_at = NOW()
                        WHERE id = %s
                    """, params)
                
                # Update permissions if provided
                if permissions is not None:
                    # Remove existing permissions
                    cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
                    
                    # Add new permissions
                    for perm_code in permissions:
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            SELECT %s, id FROM permissions WHERE code = %s
                        """, (role_id, perm_code))
                
                self.db.get_connection().commit()
                
                return self.get_role(role_id)
                
        except Exception as e:
            self.db.get_connection().rollback()
            logger.error(f"Error updating role: {e}")
            raise
    
    def delete_role(self, role_id: int) -> bool:
        """Delete a custom role."""
        try:
            with self.db.cursor() as cursor:
                # Remove role assignments first
                cursor.execute("DELETE FROM user_roles WHERE role_id = %s", (role_id,))
                # Remove role permissions
                cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
                # Delete role
                cursor.execute("DELETE FROM roles WHERE id = %s AND is_system = FALSE", (role_id,))
                self.db.get_connection().commit()
            return True
        except Exception as e:
            self.db.get_connection().rollback()
            logger.error(f"Error deleting role: {e}")
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
    
    # =========================================================================
    # ENTERPRISE AUTHENTICATION (LDAP/AD)
    # =========================================================================
    
    def authenticate_ldap(
        self,
        username: str,
        password: str,
        config_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticate user against LDAP/Active Directory.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            config_id: ID of the enterprise auth config to use
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            (success, user_data, error_message)
        """
        try:
            # Get LDAP config
            config = self._get_enterprise_auth_config(config_id)
            if not config:
                return False, None, "LDAP configuration not found"
            
            if config['auth_type'] not in ('ldap', 'active_directory'):
                return False, None, "Invalid auth type for LDAP authentication"
            
            # Try LDAP bind
            ldap_result = self._ldap_bind(config, username, password)
            
            if not ldap_result['success']:
                self._log_auth_event(
                    username=username,
                    event_type='login_failed',
                    event_status='failure',
                    ip_address=ip_address,
                    details={'reason': 'ldap_auth_failed', 'config_id': config_id}
                )
                return False, None, ldap_result.get('error', 'LDAP authentication failed')
            
            # Look up existing user - enterprise users must be pre-assigned to a role
            user = self._get_enterprise_user(username, ldap_result.get('user_info', {}), config)
            
            if not user:
                self._log_auth_event(
                    username=username,
                    event_type='login_failed',
                    event_status='failure',
                    ip_address=ip_address,
                    details={'reason': 'user_not_assigned', 'config_id': config_id}
                )
                return False, None, "User not authorized. Please contact your administrator to request access."
            
            # Enterprise users don't support 2FA (managed by AD)
            
            # Create session for enterprise user
            session = self._create_enterprise_session(user, ip_address, user_agent)
            
            self._log_auth_event(
                username=username,
                event_type='login',
                event_status='success',
                ip_address=ip_address,
                details={'auth_method': 'ldap', 'config_id': config_id, 'is_enterprise': True}
            )
            
            # Get permissions for the user's roles
            permissions = self._get_permissions_for_roles(user.get('roles', []))
            
            return True, {
                'user_id': user['id'],
                'username': user['username'],
                'email': user.get('email'),
                'display_name': user.get('display_name'),
                'session_token': session['session_token'],
                'refresh_token': session['refresh_token'],
                'expires_at': session['expires_at'].isoformat(),
                'roles': user.get('roles', []),
                'permissions': permissions,
                'is_enterprise': True
            }, None
            
        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            return False, None, "Authentication service error"
    
    def _get_enterprise_auth_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get enterprise auth configuration by ID, including credential data."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM enterprise_auth_configs
                WHERE id = %s AND enabled = TRUE
            """, (config_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            config = dict(row)
            
            # If there's a linked credential, fetch and decrypt it
            if config.get('credential_id'):
                from backend.services.credential_service import CredentialService
                cred_service = CredentialService()
                cred = cred_service.get_credential(
                    config['credential_id'], 
                    include_secret=True,
                    accessed_by='auth_service',
                    access_reason='enterprise_auth_login'
                )
                if cred and cred.get('secret_data'):
                    # Merge credential data into config
                    config.update(cred['secret_data'])
            
            return config
    
    def get_enterprise_auth_configs_for_login(self) -> List[Dict[str, Any]]:
        """Get active enterprise auth configs available for login."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, auth_type
                FROM enterprise_auth_configs
                WHERE enabled = TRUE
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def _ldap_bind(self, config: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
        """
        Attempt LDAP bind with provided credentials.
        
        Returns dict with 'success' boolean and optionally 'user_info' or 'error'.
        """
        try:
            import ldap3
            import ssl
            from ldap3 import Server, Connection, ALL, SUBTREE, Tls
            
            # Build server connection with optional SSL
            use_ssl = config.get('use_ssl', False)
            tls_config = None
            if use_ssl:
                # Allow self-signed certificates
                tls_config = Tls(validate=ssl.CERT_NONE)
            
            server = Server(
                config['host'],
                port=config.get('port', 636 if use_ssl else 389),
                use_ssl=use_ssl,
                tls=tls_config,
                get_info=ALL
            )
            
            # Build user DN
            bind_dn_template = config.get('bind_dn_template', 'cn={username}')
            base_dn = config.get('base_dn', '')
            
            if '{username}' in bind_dn_template:
                user_dn = bind_dn_template.replace('{username}', username)
            else:
                user_dn = f"{bind_dn_template}={username},{base_dn}"
            
            # For Active Directory, use UPN format
            if config['auth_type'] == 'active_directory':
                domain = config.get('domain', '')
                if domain and '@' not in username:
                    user_dn = f"{username}@{domain}"
            
            # Attempt bind
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=True
            )
            
            # Search for user attributes
            user_info = {}
            search_filter = config.get('user_search_filter', '(sAMAccountName={username})')
            search_filter = search_filter.replace('{username}', username)
            
            if conn.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['cn', 'mail', 'displayName', 'givenName', 'sn', 'memberOf']
            ):
                if conn.entries:
                    entry = conn.entries[0]
                    user_info = {
                        'cn': str(entry.cn) if hasattr(entry, 'cn') else username,
                        'email': str(entry.mail) if hasattr(entry, 'mail') else None,
                        'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else None,
                        'first_name': str(entry.givenName) if hasattr(entry, 'givenName') else None,
                        'last_name': str(entry.sn) if hasattr(entry, 'sn') else None,
                        'groups': [str(g) for g in entry.memberOf] if hasattr(entry, 'memberOf') else []
                    }
            
            conn.unbind()
            
            return {'success': True, 'user_info': user_info}
            
        except ImportError:
            logger.warning("ldap3 library not installed - LDAP auth unavailable")
            return {'success': False, 'error': 'LDAP support not available'}
        except Exception as e:
            logger.error(f"LDAP bind error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_enterprise_user(
        self,
        username: str,
        ldap_info: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get enterprise user role assignment by username.
        
        Enterprise users are NOT stored in the users table. Instead, they are
        mapped to roles via the enterprise_user_roles table. This keeps the
        Users page clean (local users only) while allowing enterprise users
        to be assigned to permission groups.
        
        Returns:
            Virtual user dict with role info if found, None otherwise
        """
        with self.db.cursor() as cursor:
            # Look up enterprise user role assignment
            cursor.execute("""
                SELECT eur.id, eur.username, eur.display_name, eur.email,
                       eur.config_id, array_agg(r.name) as roles
                FROM enterprise_user_roles eur
                JOIN roles r ON eur.role_id = r.id
                WHERE LOWER(eur.username) = LOWER(%s)
                GROUP BY eur.id, eur.username, eur.display_name, eur.email, eur.config_id
            """, (username,))
            row = cursor.fetchone()
            
            if not row:
                logger.info(f"Enterprise login denied: user '{username}' not assigned to any role")
                return None
            
            # Update display name/email from LDAP if changed
            updates = {}
            if ldap_info.get('display_name') and ldap_info['display_name'] != row.get('display_name'):
                updates['display_name'] = ldap_info['display_name']
            if ldap_info.get('email') and ldap_info['email'] != row.get('email'):
                updates['email'] = ldap_info['email']
            
            if updates:
                update_parts = [f"{k} = %s" for k in updates.keys()]
                cursor.execute(
                    f"UPDATE enterprise_user_roles SET {', '.join(update_parts)} WHERE id = %s",
                    list(updates.values()) + [row['id']]
                )
                self.db.get_connection().commit()
            
            # Return a virtual user dict (not a real users table record)
            return {
                'id': f"enterprise_{row['id']}",  # Prefix to distinguish from local users
                'username': row['username'],
                'email': ldap_info.get('email') or row.get('email') or '',
                'display_name': ldap_info.get('display_name') or row.get('display_name') or username,
                'auth_method': config['auth_type'],
                'roles': row['roles'] or [],
                'is_enterprise': True
            }
    
    def _create_enterprise_session(
        self,
        user: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a session for an enterprise user.
        
        Enterprise users don't have a record in the users table, so we store
        their session data differently - using their enterprise_user_roles ID
        and username instead of a user_id.
        """
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + self.session_duration
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_sessions (
                    user_id, session_token_hash, refresh_token_hash, expires_at,
                    ip_address, user_agent, is_enterprise, enterprise_username
                ) VALUES (NULL, %s, %s, %s, %s, %s, TRUE, %s)
                RETURNING id
            """, (
                self.hash_token(session_token),
                self.hash_token(refresh_token),
                expires_at,
                ip_address,
                user_agent,
                user['username']
            ))
            self.db.get_connection().commit()
        
        return {
            'session_token': session_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at
        }
    
    def _get_permissions_for_roles(self, role_names: List[str]) -> List[str]:
        """Get all permissions for a list of role names."""
        if not role_names:
            return []
        
        with self.db.cursor() as cursor:
            placeholders = ','.join(['%s'] * len(role_names))
            cursor.execute(f"""
                SELECT DISTINCT p.code
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN roles r ON rp.role_id = r.id
                WHERE r.name IN ({placeholders})
            """, role_names)
            return [row['code'] for row in cursor.fetchall()]
    
    def test_ldap_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test LDAP connection with provided configuration."""
        try:
            import ldap3
            from ldap3 import Server, Connection, ALL
            
            server = Server(
                config['host'],
                port=config.get('port', 389),
                use_ssl=config.get('use_ssl', False),
                get_info=ALL,
                connect_timeout=10
            )
            
            # Try anonymous bind or service account bind
            bind_dn = config.get('service_account_dn')
            bind_password = config.get('service_account_password')
            
            if bind_dn and bind_password:
                conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
            else:
                conn = Connection(server, auto_bind=True)
            
            server_info = {
                'vendor': str(server.info.vendor_name) if server.info else 'Unknown',
                'version': str(server.info.vendor_version) if server.info else 'Unknown',
                'naming_contexts': [str(nc) for nc in server.info.naming_contexts] if server.info else []
            }
            
            conn.unbind()
            
            return {
                'success': True,
                'message': 'Connection successful',
                'server_info': server_info
            }
            
        except ImportError:
            return {'success': False, 'error': 'ldap3 library not installed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Singleton instance
_auth_service = None

def get_auth_service() -> AuthService:
    """Get the singleton AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
