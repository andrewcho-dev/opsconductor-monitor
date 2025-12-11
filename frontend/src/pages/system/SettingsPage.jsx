import React from 'react';
import { Outlet, useLocation, Navigate } from 'react-router-dom';
import { PageLayout, PageHeader } from '../../components/layout';
import { Settings } from 'lucide-react';

export function SettingsPage() {
  const location = useLocation();
  
  // If at /system/settings exactly, redirect to /system/settings/general
  if (location.pathname === '/system/settings') {
    return <Navigate to="/system/settings/general" replace />;
  }

  return (
    <PageLayout module="system">
      <PageHeader
        title="System Settings"
        description="Configure system parameters and preferences"
        icon={Settings}
      />
      <div className="p-6">
        <Outlet />
      </div>
    </PageLayout>
  );
}

export default SettingsPage;
