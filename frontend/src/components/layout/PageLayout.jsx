import React from 'react';
import { GlobalNav } from './GlobalNav';
import { ModuleSidebar } from './ModuleSidebar';

/**
 * PageLayout - Consistent layout wrapper for all pages
 * 
 * @param {string} module - The active module (inventory, jobs, monitor, system)
 * @param {React.ReactNode} children - Page content
 * @param {React.ReactNode} sidebarContent - Optional additional sidebar content
 * @param {boolean} fullWidth - If true, hide sidebar and use full width
 */
export function PageLayout({ module, children, sidebarContent, fullWidth = false }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Global Navigation Bar */}
      <GlobalNav />
      
      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - hidden if fullWidth */}
        {!fullWidth && (
          <ModuleSidebar module={module}>
            {sidebarContent}
          </ModuleSidebar>
        )}
        
        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export default PageLayout;
