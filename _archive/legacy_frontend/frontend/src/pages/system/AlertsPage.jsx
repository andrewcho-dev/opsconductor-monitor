import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { 
  Bell, 
  RefreshCw,
  Check,
  X,
  AlertTriangle,
  XCircle,
  Info,
  Settings,
  History,
  CheckCircle,
  Trash2,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
import { fetchApi, formatShortTime } from '../../lib/utils';

export function AlertsPage() {
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [rules, setRules] = useState([]);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState('active');
  const [error, setError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load alerts
      const alertsResponse = await fetchApi('/monitoring/v1/alerts');
      setAlerts((alertsResponse.data || alertsResponse).alerts || []);
      
      // Load rules
      const rulesResponse = await fetchApi('/monitoring/v1/alerts/rules?all=true');
      setRules((rulesResponse.data || rulesResponse).rules || []);
      
      // Load stats
      const statsResponse = await fetchApi('/monitoring/v1/alerts/stats');
      setStats((statsResponse.data || statsResponse));
      
      // Load history
      const historyResponse = await fetchApi('/monitoring/v1/alerts/history?days=7');
      setHistory((historyResponse.data || historyResponse).history || []);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (alertId) => {
    try {
      await fetchApi(`/monitoring/v1/alerts/${alertId}/acknowledge`, { method: 'POST' });
      loadData();
    } catch (err) {
      console.error('Failed to acknowledge:', err);
    }
  };

  const handleResolve = async (alertId) => {
    try {
      await fetchApi(`/monitoring/v1/alerts/${alertId}/resolve`, { method: 'POST' });
      loadData();
    } catch (err) {
      console.error('Failed to resolve:', err);
    }
  };

  const handleToggleRule = async (ruleId, currentEnabled) => {
    try {
      await fetchApi(`/monitoring/v1/alerts/rules/${ruleId}`, {
        method: 'PUT',
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      loadData();
    } catch (err) {
      console.error('Failed to toggle rule:', err);
    }
  };

  const severityColors = {
    info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: Info },
    warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', icon: AlertTriangle },
    critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: XCircle },
  };

  const statusColors = {
    active: 'bg-red-100 text-red-700',
    acknowledged: 'bg-yellow-100 text-yellow-700',
    resolved: 'bg-green-100 text-green-700',
    expired: 'bg-gray-100 text-gray-600',
  };

  return (
    <PageLayout module="system">
      <PageHeader
        title="Alerts"
        description="Manage system alerts and alert rules"
        icon={Bell}
        actions={
          <button
            onClick={loadData}
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

        {/* Stats Summary */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <div className="text-3xl font-bold text-red-600">{stats.by_severity?.critical || 0}</div>
              <div className="text-sm text-gray-500">Critical</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <div className="text-3xl font-bold text-yellow-600">{stats.by_severity?.warning || 0}</div>
              <div className="text-sm text-gray-500">Warning</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <div className="text-3xl font-bold text-blue-600">{stats.by_severity?.info || 0}</div>
              <div className="text-sm text-gray-500">Info</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <div className="text-3xl font-bold text-gray-900">{stats.total_active || 0}</div>
              <div className="text-sm text-gray-500">Total Active</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-4">
            {[
              { id: 'active', label: 'Active Alerts', icon: Bell, count: alerts.length },
              { id: 'rules', label: 'Alert Rules', icon: Settings, count: rules.length },
              { id: 'history', label: 'History', icon: History, count: history.length },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                  {tab.count}
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Active Alerts Tab */}
        {activeTab === 'active' && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            {alerts.length === 0 ? (
              <div className="p-8 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-900 mb-1">No Active Alerts</h3>
                <p className="text-sm text-gray-500">All systems are operating normally.</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {alerts.map((alert) => {
                  const severity = severityColors[alert.severity] || severityColors.warning;
                  const SeverityIcon = severity.icon;
                  
                  return (
                    <div key={alert.id} className={`p-4 ${severity.bg} border-l-4 ${severity.border}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 min-w-0">
                          <SeverityIcon className={`w-5 h-5 mt-0.5 ${severity.text}`} />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-gray-900">{alert.title}</span>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[alert.status]}`}>
                                {alert.status}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">{alert.message}</p>
                            <div className="text-xs text-gray-500">
                              Triggered: {formatShortTime(alert.triggered_at)}
                              {alert.acknowledged_at && (
                                <span className="ml-3">
                                  Acknowledged: {formatShortTime(alert.acknowledged_at)}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {alert.status === 'active' && (
                            <button
                              onClick={() => handleAcknowledge(alert.id)}
                              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                              title="Acknowledge"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleResolve(alert.id)}
                            className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-lg"
                            title="Resolve & Dismiss"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Alert Rules Tab */}
        {activeTab === 'rules' && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Rule</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Severity</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Condition</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Cooldown</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-500 uppercase w-20">Enabled</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rules.map((rule) => {
                  const config = typeof rule.condition_config === 'string' 
                    ? JSON.parse(rule.condition_config) 
                    : rule.condition_config;
                  
                  const conditionSummary = Object.entries(config)
                    .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${Array.isArray(v) ? v.join(',') : v}`)
                    .join(', ');
                  
                  return (
                    <tr key={rule.id} className={`hover:bg-gray-50 ${!rule.enabled ? 'opacity-50' : ''}`}>
                      <td className="px-4 py-2">
                        <span className="font-medium text-gray-900">
                          {rule.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          rule.severity === 'critical' ? 'bg-red-100 text-red-700' :
                          rule.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {rule.severity}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-600 max-w-xs truncate" title={conditionSummary}>
                        {conditionSummary}
                      </td>
                      <td className="px-4 py-2 text-gray-600">{rule.cooldown_minutes}m</td>
                      <td className="px-4 py-2 text-center">
                        <button
                          onClick={() => handleToggleRule(rule.id, rule.enabled)}
                          className="inline-flex items-center gap-1"
                          title={rule.enabled ? 'Click to disable' : 'Click to enable'}
                        >
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                            rule.enabled 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-gray-200 text-gray-500'
                          }`}>
                            {rule.enabled ? 'ON' : 'OFF'}
                          </span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            {history.length === 0 ? (
              <div className="p-8 text-center">
                <History className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-900 mb-1">No Alert History</h3>
                <p className="text-sm text-gray-500">Resolved and expired alerts will appear here.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Triggered</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Title</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Severity</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Resolved</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {history.map((alert) => (
                      <tr key={alert.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          {formatShortTime(alert.triggered_at)}
                        </td>
                        <td className="px-4 py-3 text-gray-900">{alert.title}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                            alert.severity === 'critical' ? 'bg-red-100 text-red-700' :
                            alert.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {alert.severity}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[alert.status]}`}>
                            {alert.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          {formatShortTime(alert.resolved_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </PageLayout>
  );
}

export default AlertsPage;
