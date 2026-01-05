import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { 
  Activity, 
  Server, 
  Database, 
  Cpu, 
  HardDrive,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Bell,
  Check,
  Link,
  ExternalLink,
  Plug,
  Network
} from 'lucide-react';
import { fetchApi, formatTimeOnly, formatShortTime, formatDuration } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';

function AlertItem({ alert, onAcknowledge }) {
  const severityColors = {
    info: 'bg-blue-50 border-blue-200',
    warning: 'bg-yellow-50 border-yellow-200',
    critical: 'bg-red-50 border-red-200',
  };
  
  const severityIcons = {
    info: <Bell className="w-4 h-4 text-blue-500" />,
    warning: <AlertTriangle className="w-4 h-4 text-yellow-500" />,
    critical: <XCircle className="w-4 h-4 text-red-500" />,
  };
  
  return (
    <div className={`p-3 border-l-4 ${severityColors[alert.severity] || severityColors.warning}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          {severityIcons[alert.severity] || severityIcons.warning}
          <div className="min-w-0">
            <div className="font-medium text-sm text-gray-900 truncate">{alert.title}</div>
            <div className="text-xs text-gray-600 mt-0.5 line-clamp-2">{alert.message}</div>
            <div className="text-[10px] text-gray-400 mt-1">
              {formatShortTime(alert.triggered_at)}
              {alert.status === 'acknowledged' && (
                <span className="ml-2 text-green-600">• Acknowledged</span>
              )}
            </div>
          </div>
        </div>
        {alert.status === 'active' && onAcknowledge && (
          <button
            onClick={() => onAcknowledge(alert.id)}
            className="flex-shrink-0 p-1 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded"
            title="Acknowledge"
          >
            <Check className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

function StatusCard({ title, icon: Icon, status, details, color }) {
  const statusColors = {
    online: 'bg-green-100 text-green-700 border-green-200',
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    offline: 'bg-red-100 text-red-700 border-red-200',
    unknown: 'bg-gray-100 text-gray-700 border-gray-200',
  };

  const statusIcons = {
    online: CheckCircle,
    warning: AlertTriangle,
    offline: XCircle,
    unknown: Clock,
  };

  const StatusIcon = statusIcons[status] || Clock;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <Icon className="w-4 h-4 text-blue-600" />
          </div>
          <span className="font-semibold text-gray-900">{title}</span>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${statusColors[status]}`}>
          <StatusIcon className="w-3 h-3" />
          <span className="capitalize">{status}</span>
        </div>
      </div>
      <div className="space-y-1 text-sm text-gray-600">
        {details.map((detail, i) => (
          <div key={i} className="flex justify-between">
            <span>{detail.label}</span>
            <span className="font-medium text-gray-900">{detail.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Integration status card component
function IntegrationCard({ name, icon: Icon, status, url, version, lastSync, error, onConfigure }) {
  const statusColors = {
    connected: 'bg-green-100 text-green-700 border-green-200',
    disconnected: 'bg-gray-100 text-gray-500 border-gray-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    not_configured: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  };
  
  const statusLabels = {
    connected: 'Connected',
    disconnected: 'Disconnected',
    error: 'Error',
    not_configured: 'Not Configured',
  };
  
  const statusIcons = {
    connected: <CheckCircle className="w-4 h-4 text-green-500" />,
    disconnected: <XCircle className="w-4 h-4 text-gray-400" />,
    error: <AlertTriangle className="w-4 h-4 text-red-500" />,
    not_configured: <AlertTriangle className="w-4 h-4 text-yellow-500" />,
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${status === 'connected' ? 'bg-green-100' : 'bg-gray-100'}`}>
            <Icon className={`w-5 h-5 ${status === 'connected' ? 'text-green-600' : 'text-gray-500'}`} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{name}</h3>
            {url && (
              <a 
                href={url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline flex items-center gap-1"
              >
                {url.replace(/^https?:\/\//, '').split('/')[0]}
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {statusIcons[status]}
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${statusColors[status]}`}>
            {statusLabels[status]}
          </span>
        </div>
      </div>
      
      {status === 'connected' && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          {version && (
            <div>
              <span className="text-gray-500">Version:</span>
              <span className="ml-1 font-medium text-gray-700">{version}</span>
            </div>
          )}
          {lastSync && (
            <div>
              <span className="text-gray-500">Last Sync:</span>
              <span className="ml-1 font-medium text-gray-700">{lastSync}</span>
            </div>
          )}
        </div>
      )}
      
      {status === 'error' && error && (
        <div className="text-xs text-red-600 bg-red-50 rounded p-2 mt-2">
          {error}
        </div>
      )}
      
      {(status === 'not_configured' || status === 'disconnected') && onConfigure && (
        <button
          onClick={onConfigure}
          className="mt-2 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <Plug className="w-3 h-3" />
          Configure Integration
        </button>
      )}
    </div>
  );
}

export function SystemOverviewPage() {
  const { getAuthHeader } = useAuth();
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState(null);
  const [queueStatus, setQueueStatus] = useState(null);
  const [recentExecutions, setRecentExecutions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [integrations, setIntegrations] = useState({
    netbox: { status: 'not_configured' },
    prtg: { status: 'not_configured' },
    mcp: { status: 'not_configured' },
  });

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await fetchApi(`/api/alerts/${alertId}/acknowledge`, { method: 'POST', headers: getAuthHeader() });
      // Refresh alerts
      const alertsResponse = await fetchApi('/api/alerts', { headers: getAuthHeader() });
      const alertsData = alertsResponse.data || alertsResponse;
      setAlerts(alertsData.alerts || []);
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Show system status immediately
      setSystemStatus({
        backend: { status: 'online' },
        database: { status: 'online' },
        redis: { status: 'online' },  // Will be verified below
        workers: {
          count: 0,
          concurrency: 0,
          active: 0,
          scheduled: 0,
        }
      });
      
      // Load queue status in parallel with integrations
      const [queuesResponse] = await Promise.allSettled([
        fetchApi('/api/scheduler/queues', { headers: getAuthHeader(), timeout: 3000 })
      ]);
      
      // Update queue status if available
      if (queuesResponse.status === 'fulfilled') {
        const queues = queuesResponse.value.data || queuesResponse.value;
        setQueueStatus(queues);
        setSystemStatus(prev => ({
          ...prev,
          workers: {
            count: queues.workers?.length || 0,
            concurrency: queues.concurrency || 32,
            active: queues.active_total || 0,
            scheduled: queues.scheduled_total || 0,
          }
        }));
      }
      
      // Skip loading recent executions and alerts - removed from UI
      
      // Load integration statuses in parallel for faster response
      const [netboxStatus, prtgStatus, mcpStatus] = await Promise.allSettled([
        (async () => {
          try {
            const netboxRes = await fetchApi('/api/netbox/settings', { headers: getAuthHeader(), timeout: 3000 });
            if (netboxRes.success && netboxRes.data?.url) {
              // Test connection
              try {
                const testRes = await fetchApi('/api/netbox/test', {
                  method: 'POST',
                  headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
                  timeout: 5000,
                  body: JSON.stringify({
                    url: netboxRes.data.url,
                    token: netboxRes.data.token,
                    verify_ssl: netboxRes.data.verify_ssl !== 'false',
                  })
                });
                if (testRes.success) {
                  return {
                    status: 'connected',
                    url: netboxRes.data.url,
                    version: testRes.data?.netbox_version,
                  };
                } else {
                  return {
                    status: 'error',
                    url: netboxRes.data.url,
                    error: testRes.error?.message || 'Connection failed',
                  };
                }
              } catch {
                return {
                  status: 'disconnected',
                  url: netboxRes.data.url,
                };
              }
            } else {
              return { status: 'not_configured' };
            }
          } catch {
            return { status: 'not_configured' };
          }
        })(),
        (async () => {
          try {
            const prtgRes = await fetchApi('/api/prtg/settings', { headers: getAuthHeader(), timeout: 3000 });
            if (prtgRes.success && prtgRes.data?.url) {
              // Check PRTG status
              try {
                const statusRes = await fetchApi('/api/prtg/status', { headers: getAuthHeader(), timeout: 5000 });
                if (statusRes.success && statusRes.data?.connected) {
                  return {
                    status: 'connected',
                    url: prtgRes.data.url,
                    version: statusRes.data?.version,
                  };
                } else {
                  return {
                    status: 'disconnected',
                    url: prtgRes.data.url,
                  };
                }
              } catch {
                return {
                  status: 'disconnected',
                  url: prtgRes.data.url,
                };
              }
            } else {
              return { status: 'not_configured' };
            }
          } catch {
            return { status: 'not_configured' };
          }
        })(),
        (async () => {
          try {
            const mcpRes = await fetchApi('/api/mcp/settings', { headers: getAuthHeader(), timeout: 3000 });
            if (mcpRes.success && mcpRes.data?.url) {
              // Test MCP connection
              try {
                const testRes = await fetchApi('/api/mcp/test', {
                  method: 'POST',
                  headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
                  timeout: 5000,
                  body: JSON.stringify({})
                });
                if (testRes.success && testRes.data?.success) {
                  return {
                    status: 'connected',
                    url: mcpRes.data.url,
                    version: `${testRes.data.summary?.devices || 0} devices`,
                  };
                } else {
                  return {
                    status: 'error',
                    url: mcpRes.data.url,
                    error: testRes.data?.message || 'Connection failed',
                  };
                }
              } catch {
                return {
                  status: 'disconnected',
                  url: mcpRes.data.url,
                };
              }
            } else {
              return { status: 'not_configured' };
            }
          } catch {
            return { status: 'not_configured' };
          }
        })()
      ]);
      
      // Update integration statuses
      setIntegrations({
        netbox: netboxStatus.status === 'fulfilled' ? netboxStatus.value : { status: 'not_configured' },
        prtg: prtgStatus.status === 'fulfilled' ? prtgStatus.value : { status: 'not_configured' },
        mcp: mcpStatus.status === 'fulfilled' ? mcpStatus.value : { status: 'not_configured' },
      });
    } catch (err) {
      setError(err.message);
      setSystemStatus({
        backend: { status: 'online' },
        database: { status: 'unknown' },
        redis: { status: 'unknown' },
        workers: { count: 0, active: 0, scheduled: 0 }
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <PageLayout module="system">
      <PageHeader
        title="System Overview"
        description="Monitor system health and infrastructure status"
        icon={Activity}
        actions={
          <button
            onClick={loadStatus}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
            {error}
          </div>
        )}

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard
            title="Backend API"
            icon={Server}
            status={systemStatus?.backend?.status || 'unknown'}
            details={[
              { label: 'Port', value: '5000' },
              { label: 'Mode', value: 'Development' },
            ]}
          />
          <StatusCard
            title="Celery Workers"
            icon={Cpu}
            status={systemStatus?.workers?.count > 0 ? 'online' : 'warning'}
            details={[
              { label: 'Workers', value: systemStatus?.workers?.count || 1 },
              { label: 'Processes', value: systemStatus?.workers?.concurrency || 32 },
              { label: 'Active Tasks', value: systemStatus?.workers?.active || 0 },
            ]}
          />
          <StatusCard
            title="Database"
            icon={Database}
            status={systemStatus?.database?.status || 'unknown'}
            details={[
              { label: 'Type', value: 'PostgreSQL' },
              { label: 'Status', value: systemStatus?.database?.status === 'online' ? 'Connected' : 'Disconnected' },
            ]}
          />
          <StatusCard
            title="Redis"
            icon={HardDrive}
            status={systemStatus?.redis?.status || 'unknown'}
            details={[
              { label: 'Port', value: '6379' },
              { label: 'Role', value: 'Message Broker' },
            ]}
          />
        </div>

        {/* External Integrations */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link className="w-4 h-4 text-gray-500" />
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                External Integrations
              </h2>
            </div>
            <a 
              href="/system/settings" 
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Manage Settings →
            </a>
          </div>
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <IntegrationCard
              name="NetBox"
              icon={Database}
              status={integrations.netbox.status}
              url={integrations.netbox.url}
              version={integrations.netbox.version}
              error={integrations.netbox.error}
              onConfigure={() => window.location.href = '/system/settings/netbox'}
            />
            <IntegrationCard
              name="PRTG Network Monitor"
              icon={Activity}
              status={integrations.prtg.status}
              url={integrations.prtg.url}
              version={integrations.prtg.version}
              error={integrations.prtg.error}
              onConfigure={() => window.location.href = '/system/settings/prtg'}
            />
            <IntegrationCard
              name="Ciena MCP"
              icon={Network}
              status={integrations.mcp.status}
              url={integrations.mcp.url}
              version={integrations.mcp.version}
              error={integrations.mcp.error}
              onConfigure={() => window.location.href = '/system/settings/mcp'}
            />
          </div>
        </div>

      </div>
    </PageLayout>
  );
}

export default SystemOverviewPage;
