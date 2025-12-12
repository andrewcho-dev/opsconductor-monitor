import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

// Inventory Module
import { DevicesPage, DeviceDetailPage, GroupsPage } from "./pages/inventory";

// Workflows Module (replaced legacy Jobs)
import { WorkflowsListPage, WorkflowBuilderPage } from "./pages/workflows";

// Monitor Module
import { DashboardPage, TopologyPage, PowerTrendsPage, AlertsPage, ActiveJobsPage, JobHistoryPage } from "./pages/monitor";

// System Module
import { 
  SystemOverviewPage, 
  WorkersPage, 
  AlertsPage as SystemAlertsPage,
  SettingsPage as SystemSettingsPage,
  NotificationsPage,
  CredentialsPage,
  LogsPage,
  AboutPage 
} from "./pages/system";
import {
  GeneralSettings,
  NetworkSettings,
  SSHSettings,
  DatabaseSettings,
  APISettings,
  SecuritySettings,
  LoggingSettings,
  BackupSettings
} from "./pages/system/settings";

function App() {
  return (
    <Router>
      <Routes>
        {/* Root redirect to dashboard */}
        <Route path="/" element={<Navigate to="/monitor/dashboard" replace />} />

        {/* INVENTORY MODULE */}
        <Route path="/inventory" element={<Navigate to="/inventory/devices" replace />} />
        <Route path="/inventory/devices" element={<DevicesPage />} />
        <Route path="/inventory/devices/:ip" element={<DeviceDetailPage />} />
        <Route path="/inventory/groups" element={<GroupsPage />} />

        {/* WORKFLOWS MODULE */}
        <Route path="/workflows" element={<WorkflowsListPage />} />
        <Route path="/workflows/new" element={<WorkflowBuilderPage />} />
        <Route path="/workflows/:id" element={<WorkflowBuilderPage />} />

        {/* MONITOR MODULE */}
        <Route path="/monitor" element={<Navigate to="/monitor/dashboard" replace />} />
        <Route path="/monitor/dashboard" element={<DashboardPage />} />
        <Route path="/monitor/topology" element={<TopologyPage />} />
        <Route path="/monitor/power" element={<PowerTrendsPage />} />
        <Route path="/monitor/alerts" element={<AlertsPage />} />
        <Route path="/monitor/active-jobs" element={<ActiveJobsPage />} />
        <Route path="/monitor/job-history" element={<JobHistoryPage />} />

        {/* SYSTEM MODULE */}
        <Route path="/system" element={<Navigate to="/system/overview" replace />} />
        <Route path="/system/overview" element={<SystemOverviewPage />} />
        <Route path="/system/workers" element={<WorkersPage />} />
        <Route path="/system/alerts" element={<SystemAlertsPage />} />
        <Route path="/system/settings" element={<SystemSettingsPage />}>
          <Route index element={<Navigate to="general" replace />} />
          <Route path="general" element={<GeneralSettings />} />
          <Route path="network" element={<NetworkSettings />} />
          <Route path="ssh" element={<SSHSettings />} />
          <Route path="database" element={<DatabaseSettings />} />
          <Route path="api" element={<APISettings />} />
          <Route path="security" element={<SecuritySettings />} />
          <Route path="logging" element={<LoggingSettings />} />
          <Route path="backup" element={<BackupSettings />} />
        </Route>
        <Route path="/system/notifications" element={<NotificationsPage />} />
        <Route path="/system/credentials" element={<CredentialsPage />} />
        <Route path="/system/logs" element={<LogsPage />} />
        <Route path="/system/about" element={<AboutPage />} />

        {/* LEGACY REDIRECTS */}
        <Route path="/device/:ip" element={<DeviceDetailPage />} />
        <Route path="/scheduler" element={<Navigate to="/monitor/active-jobs" replace />} />
        <Route path="/jobs/scheduler" element={<Navigate to="/monitor/active-jobs" replace />} />
        <Route path="/jobs" element={<Navigate to="/workflows" replace />} />
        <Route path="/jobs/*" element={<Navigate to="/workflows" replace />} />
        <Route path="/job-definitions" element={<Navigate to="/workflows" replace />} />
        <Route path="/job-builder" element={<Navigate to="/workflows" replace />} />
        <Route path="/topology" element={<Navigate to="/monitor/topology" replace />} />
        <Route path="/power-trends" element={<Navigate to="/monitor/power" replace />} />
        <Route path="/settings" element={<Navigate to="/system/settings" replace />} />
        <Route path="/poller" element={<Navigate to="/monitor/active-jobs" replace />} />

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/monitor/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
