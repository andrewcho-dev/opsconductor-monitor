import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { LoginPage } from "./pages/auth/LoginPage";
import { ProfilePage } from "./pages/auth/ProfilePage";

// Inventory Module
import { DevicesPage, DeviceDetailPage, GroupsPage, DeviceImporterPage, PRTGNetBoxImportPage } from "./pages/inventory";

// Workflows Module (replaced legacy Jobs)
import { WorkflowsListPage, WorkflowBuilderPage } from "./pages/workflows";

// Monitor Module
import { DashboardPage, TopologyPage, PowerTrendsPage, AlertsPage, ActiveJobsPage, JobHistoryPage, SNMPLivePage, SNMPAlarmsPage, UPSMonitorPage } from "./pages/monitor";
import PollingPage from "./pages/monitor/PollingPage";
import MibMappingsPage from "./pages/monitor/MibMappingsPage";

// Alert Aggregation Module (MVP)
import { AlertDashboard } from "./pages/AlertDashboard";
import { AlertDetailPage } from "./pages/AlertDetailPage";
import { ResolvedAlertsPage } from "./pages/ResolvedAlertsPage";
import { ConnectorsPage } from "./pages/ConnectorsPage";
import NormalizationRulesPage from "./pages/ColumnMappingPage.jsx";
import ConnectorPollingPage from "./pages/ConnectorPollingPage.jsx";
import { DependenciesPage } from "./pages/DependenciesPage";

// System Module
import { 
  SystemOverviewPage, 
  AlertsPage as SystemAlertsPage,
  SettingsPage as SystemSettingsPage,
  LogsPage,
  AboutPage
} from "./pages/system";
import NotificationsPage from "./pages/system/NotificationsPage.jsx";
import UsersPage from "./pages/system/UsersPage.jsx";
import RolesPage from "./pages/system/RolesPage.jsx";

// Credentials Module
import { CredentialVaultPage } from "./pages/credentials";
import {
  GeneralSettings,
  DatabaseSettings,
  SecuritySettings,
  LoggingSettings,
  NetBoxSettings,
  BackupSettings,
  PRTGSettings,
  MCPSettings,
} from "./pages/system/settings";

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Auth routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          
          {/* Root redirect to alerts dashboard (MVP) */}
          <Route path="/" element={<ProtectedRoute><Navigate to="/alerts" replace /></ProtectedRoute>} />

        {/* INVENTORY MODULE */}
        <Route path="/inventory" element={<ProtectedRoute><Navigate to="/inventory/devices" replace /></ProtectedRoute>} />
        <Route path="/inventory/devices" element={<ProtectedRoute permission="devices.device.view"><DevicesPage /></ProtectedRoute>} />
        <Route path="/inventory/devices/:ip" element={<ProtectedRoute permission="devices.device.view"><DeviceDetailPage /></ProtectedRoute>} />
        <Route path="/inventory/groups" element={<ProtectedRoute permission="devices.group.manage"><GroupsPage /></ProtectedRoute>} />
        <Route path="/inventory/import" element={<ProtectedRoute permission="devices.device.create"><DeviceImporterPage /></ProtectedRoute>} />
        <Route path="/inventory/prtg-import" element={<ProtectedRoute permission="devices.device.create"><PRTGNetBoxImportPage /></ProtectedRoute>} />

        {/* WORKFLOWS MODULE */}
        <Route path="/workflows" element={<ProtectedRoute permission="jobs.job.view"><WorkflowsListPage /></ProtectedRoute>} />
        <Route path="/workflows/new" element={<ProtectedRoute permission="jobs.job.create"><WorkflowBuilderPage /></ProtectedRoute>} />
        <Route path="/workflows/:id" element={<ProtectedRoute permission="jobs.job.view"><WorkflowBuilderPage /></ProtectedRoute>} />

        {/* MONITOR MODULE */}
        <Route path="/monitor" element={<ProtectedRoute><Navigate to="/monitor/dashboard" replace /></ProtectedRoute>} />
        <Route path="/monitor/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/monitor/topology" element={<ProtectedRoute><TopologyPage /></ProtectedRoute>} />
        <Route path="/monitor/power" element={<ProtectedRoute><PowerTrendsPage /></ProtectedRoute>} />
        <Route path="/monitor/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
        <Route path="/monitor/active-jobs" element={<ProtectedRoute permission="jobs.job.view"><ActiveJobsPage /></ProtectedRoute>} />
        <Route path="/monitor/job-history" element={<ProtectedRoute permission="jobs.job.view"><JobHistoryPage /></ProtectedRoute>} />
        <Route path="/monitor/snmp-live" element={<ProtectedRoute><SNMPLivePage /></ProtectedRoute>} />
        <Route path="/monitor/snmp-alarms" element={<ProtectedRoute><SNMPAlarmsPage /></ProtectedRoute>} />
        <Route path="/monitor/ups" element={<ProtectedRoute><UPSMonitorPage /></ProtectedRoute>} />
        <Route path="/monitor/polling" element={<ProtectedRoute><PollingPage /></ProtectedRoute>} />
        <Route path="/monitor/mib-mappings" element={<ProtectedRoute><MibMappingsPage /></ProtectedRoute>} />

        {/* ALERT AGGREGATION MODULE (MVP) */}
        <Route path="/alerts" element={<ProtectedRoute><AlertDashboard /></ProtectedRoute>} />
        <Route path="/alerts/resolved" element={<ProtectedRoute><ResolvedAlertsPage /></ProtectedRoute>} />
        <Route path="/alerts/:alertId" element={<ProtectedRoute><AlertDetailPage /></ProtectedRoute>} />
        
        {/* CONNECTORS MODULE */}
        <Route path="/connectors" element={<ProtectedRoute><ConnectorsPage /></ProtectedRoute>} />
        <Route path="/connectors/polling" element={<ProtectedRoute><ConnectorPollingPage /></ProtectedRoute>} />
        <Route path="/connectors/normalization" element={<ProtectedRoute><NormalizationRulesPage /></ProtectedRoute>} />
        
        <Route path="/dependencies" element={<ProtectedRoute><DependenciesPage /></ProtectedRoute>} />

        {/* CREDENTIALS MODULE */}
        <Route path="/credentials" element={<ProtectedRoute permission="credentials.credential.view"><CredentialVaultPage /></ProtectedRoute>} />
        <Route path="/credentials/groups" element={<ProtectedRoute permission="credentials.group.manage"><CredentialVaultPage /></ProtectedRoute>} />
        <Route path="/credentials/expiring" element={<ProtectedRoute permission="credentials.credential.view"><CredentialVaultPage /></ProtectedRoute>} />
        <Route path="/credentials/audit" element={<ProtectedRoute permission="system.audit.view"><CredentialVaultPage /></ProtectedRoute>} />
        <Route path="/credentials/enterprise" element={<ProtectedRoute permission="credentials.enterprise.manage"><CredentialVaultPage /></ProtectedRoute>} />
        <Route path="/credentials/enterprise/users" element={<ProtectedRoute permission="credentials.enterprise.manage"><CredentialVaultPage /></ProtectedRoute>} />

        {/* SYSTEM MODULE */}
        <Route path="/system" element={<ProtectedRoute><Navigate to="/system/overview" replace /></ProtectedRoute>} />
        <Route path="/system/overview" element={<ProtectedRoute permission="system.settings.view"><SystemOverviewPage /></ProtectedRoute>} />
        <Route path="/system/alerts" element={<ProtectedRoute><SystemAlertsPage /></ProtectedRoute>} />
        <Route path="/system/settings" element={<ProtectedRoute permission="system.settings.view"><SystemSettingsPage /></ProtectedRoute>}>
          <Route index element={<Navigate to="general" replace />} />
          <Route path="general" element={<GeneralSettings />} />
          <Route path="database" element={<DatabaseSettings />} />
          <Route path="security" element={<SecuritySettings />} />
          <Route path="logging" element={<LoggingSettings />} />
          <Route path="netbox" element={<NetBoxSettings />} />
          <Route path="prtg" element={<PRTGSettings />} />
          <Route path="mcp" element={<MCPSettings />} />
          <Route path="backup" element={<BackupSettings />} />
        </Route>
        {/* Legacy redirects to new connectors module */}
        <Route path="/system/normalization" element={<Navigate to="/connectors/normalization" replace />} />
        <Route path="/system/polling" element={<Navigate to="/connectors/polling" replace />} />
        <Route path="/system/notifications" element={<ProtectedRoute permission="system.settings.view"><NotificationsPage /></ProtectedRoute>} />
        <Route path="/system/credentials" element={<ProtectedRoute><Navigate to="/credentials" replace /></ProtectedRoute>} />
        <Route path="/system/logs" element={<ProtectedRoute permission="system.audit.view"><LogsPage /></ProtectedRoute>} />
        <Route path="/system/about" element={<ProtectedRoute><AboutPage /></ProtectedRoute>} />
        <Route path="/system/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
        <Route path="/system/roles" element={<ProtectedRoute><RolesPage /></ProtectedRoute>} />

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
      </AuthProvider>
    </Router>
  );
}

export default App;
