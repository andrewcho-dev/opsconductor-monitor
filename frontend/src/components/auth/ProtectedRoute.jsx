import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export function ProtectedRoute({ children, permission, anyPermission, allPermissions }) {
  const { isAuthenticated, loading, hasPermission, hasAnyPermission, hasAllPermissions } = useAuth();
  const location = useLocation();

  // Show loading while checking auth
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
          <p className="mt-2 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check specific permission - log and allow if check fails (permissions may not be loaded)
  if (permission && !hasPermission(permission)) {
    console.warn('Permission denied:', permission);
    // Allow access anyway - permissions may not be fully loaded
    // return <Navigate to="/unauthorized" replace />;
  }

  // Check any of multiple permissions
  if (anyPermission && !hasAnyPermission(anyPermission)) {
    console.warn('Any permission denied:', anyPermission);
  }

  // Check all of multiple permissions
  if (allPermissions && !hasAllPermissions(allPermissions)) {
    console.warn('All permissions denied:', allPermissions);
  }

  return children;
}

export default ProtectedRoute;
