import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { fetchApi } from '../lib/utils';

const AuthContext = createContext(null);

const TOKEN_KEY = 'opsconductor_session_token';
const REFRESH_KEY = 'opsconductor_refresh_token';
const USER_KEY = 'opsconductor_user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load user from storage on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);
    
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
        // Verify token is still valid
        verifySession();
      } catch (e) {
        clearAuth();
      }
    }
    setLoading(false);
  }, []);

  const verifySession = async () => {
    try {
      const res = await fetchApi('/identity/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem(TOKEN_KEY)}`
        }
      });
      
      if (res && !res.detail) {
        setUser(res);
        setPermissions(res.permissions || []);
        localStorage.setItem(USER_KEY, JSON.stringify(res));
      } else {
        // Try to refresh token
        await refreshToken();
      }
    } catch (err) {
      clearAuth();
    }
  };

  const refreshToken = async () => {
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!refresh) {
      clearAuth();
      return false;
    }

    try {
      const res = await fetchApi('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      });

      if (res.success) {
        localStorage.setItem(TOKEN_KEY, res.data.session_token);
        localStorage.setItem(REFRESH_KEY, res.data.refresh_token);
        return true;
      }
    } catch (err) {
      console.error('Token refresh failed:', err);
    }

    clearAuth();
    return false;
  };

  const clearAuth = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
    setPermissions([]);
  };

  const login = async (username, password) => {
    setError(null);
    
    try {
      const res = await fetchApi('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (res.detail) {
        setError(res.detail.message || 'Login failed');
        return { success: false, error: res.detail.message };
      }

      // Check if 2FA is required (not implemented yet)
      if (res.requires_2fa) {
        return {
          success: true,
          requires_2fa: true,
          user_id: res.user_id,
          two_factor_method: res.two_factor_method
        };
      }

      // Login successful
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.user));
      setUser(res.user);
      setPermissions(res.user.permissions || []);

      return { success: true };
    } catch (err) {
      const message = err.message || 'Login failed';
      setError(message);
      return { success: false, error: message };
    }
  };

  const verify2FA = async (userId, code) => {
    setError(null);

    try {
      const res = await fetchApi('/api/auth/login/2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, code })
      });

      if (!res.success) {
        setError(res.error?.message || '2FA verification failed');
        return { success: false, error: res.error?.message };
      }

      localStorage.setItem(TOKEN_KEY, res.data.session_token);
      localStorage.setItem(REFRESH_KEY, res.data.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
      setUser(res.data.user);
      setPermissions(res.data.user.permissions || []);

      return { success: true };
    } catch (err) {
      const message = err.message || '2FA verification failed';
      setError(message);
      return { success: false, error: message };
    }
  };

  const logout = async () => {
    try {
      await fetchApi('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem(TOKEN_KEY)}`
        }
      });
    } catch (err) {
      console.error('Logout error:', err);
    }
    
    clearAuth();
  };

  const hasPermission = useCallback((permissionCode) => {
    if (!user) return false;
    // Super admin has all permissions
    if (user.roles?.includes('super_admin')) return true;
    return permissions.includes(permissionCode);
  }, [user, permissions]);

  const hasAnyPermission = useCallback((permissionCodes) => {
    return permissionCodes.some(code => hasPermission(code));
  }, [hasPermission]);

  const hasAllPermissions = useCallback((permissionCodes) => {
    return permissionCodes.every(code => hasPermission(code));
  }, [hasPermission]);

  const getAuthHeader = useCallback(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }, []);

  const value = {
    user,
    permissions,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    verify2FA,
    logout,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    getAuthHeader,
    refreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
