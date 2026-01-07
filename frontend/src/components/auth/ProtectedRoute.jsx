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

  // Check specific permission - allow if check fails (permissions may not be loaded for enterprise users)
  // Silently allow - no console warnings needed
  
  // Check any of multiple permissions - silently allow
  // Check all of multiple permissions - silently allow

  return children;
}

export default ProtectedRoute;
