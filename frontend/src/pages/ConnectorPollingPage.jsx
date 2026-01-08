/**
 * Connector Polling Configuration Page
 * 
 * Configure polling intervals and trigger manual polls
 */

import { useState, useEffect } from 'react';
import { 
  Play, Pause, RefreshCw, Clock, Settings,
  Check, X, AlertTriangle
} from 'lucide-react';
import { PageLayout } from '../components/layout/PageLayout';
import { fetchApi } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';

// Axis-specific configuration form
function AxisConfigForm({ config, setConfig }) {
  const [newCamera, setNewCamera] = useState({ ip: '', name: '', username: '' });
  
  const addCamera = () => {
    if (!newCamera.ip) return;
    const targets = config.targets || [];
    setConfig({ 
      ...config, 
      targets: [...targets, { ...newCamera, username: newCamera.username || config.default_username || 'root' }]
    });
    setNewCamera({ ip: '', name: '', username: '' });
  };
  
  const removeCamera = (index) => {
    const targets = [...(config.targets || [])];
    targets.splice(index, 1);
    setConfig({ ...config, targets });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Camera Source</label>
        <select
          value={config.camera_source || 'manual'}
          onChange={(e) => setConfig({ ...config, camera_source: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded bg-white text-gray-900"
        >
          <option value="manual">Manual List</option>
          <option value="prtg">From PRTG (auto-discover)</option>
        </select>
      </div>

      {config.camera_source === 'prtg' && (
        <div className="p-3 bg-blue-50 rounded border border-blue-200">
          <p className="text-sm text-blue-700 mb-2">PRTG Filter</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600">Tag Contains</label>
              <input
                type="text"
                placeholder="e.g., camera"
                value={config.prtg_filter?.tags || ''}
                onChange={(e) => setConfig({ ...config, prtg_filter: { ...config.prtg_filter, tags: e.target.value } })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Group Contains</label>
              <input
                type="text"
                placeholder="e.g., Cameras"
                value={config.prtg_filter?.group || ''}
                onChange={(e) => setConfig({ ...config, prtg_filter: { ...config.prtg_filter, group: e.target.value } })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
              />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Default Username</label>
          <input
            type="text"
            value={config.default_username || config.username || 'root'}
            onChange={(e) => setConfig({ ...config, default_username: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Default Password</label>
          <input
            type="password"
            value={config.default_password || config.password || ''}
            onChange={(e) => setConfig({ ...config, default_password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Poll Interval (seconds)</label>
        <input
          type="number"
          value={config.poll_interval || 60}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 60 })}
          className="w-full px-3 py-2 border border-gray-300 rounded"
        />
      </div>

      {config.camera_source !== 'prtg' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Cameras ({(config.targets || []).length})
          </label>
          <div className="max-h-40 overflow-y-auto border border-gray-200 rounded mb-2">
            {(config.targets || []).length === 0 ? (
              <p className="text-sm text-gray-500 p-3 text-center">No cameras configured</p>
            ) : (config.targets || []).map((cam, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b last:border-0">
                <div className="text-sm">
                  <span className="font-medium">{cam.ip}</span>
                  {cam.name && <span className="text-gray-500 ml-2">({cam.name})</span>}
                </div>
                <button onClick={() => removeCamera(idx)} className="text-red-500 hover:text-red-700 text-xs">Remove</button>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-2">
            <input type="text" placeholder="IP Address" value={newCamera.ip}
              onChange={(e) => setNewCamera({ ...newCamera, ip: e.target.value })}
              className="px-2 py-1 text-sm border border-gray-300 rounded" />
            <input type="text" placeholder="Name" value={newCamera.name}
              onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
              className="px-2 py-1 text-sm border border-gray-300 rounded" />
            <input type="text" placeholder="Username" value={newCamera.username}
              onChange={(e) => setNewCamera({ ...newCamera, username: e.target.value })}
              className="px-2 py-1 text-sm border border-gray-300 rounded" />
            <button onClick={addCamera} disabled={!newCamera.ip}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              Add
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Configuration modal
function ConfigModal({ connector, onClose, onSave, getAuthHeader }) {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!connector?.id) return;
    const fetchConfig = async () => {
      setLoading(true);
      try {
        const response = await fetchApi(`/api/v1/connectors/${connector.id}`, { headers: getAuthHeader() });
        if (response.success && response.data?.config) {
          setConfig(response.data.config);
        }
      } catch (err) {
        console.error('Failed to fetch config:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, [connector?.id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(connector.id, config);
      onClose();
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!connector) return null;
  const isAxis = connector.type === 'axis';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className={`bg-white rounded-lg shadow-xl w-full mx-4 ${isAxis ? 'max-w-2xl' : 'max-w-lg'}`}>
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-medium">Configure {connector.name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 max-h-[70vh] overflow-y-auto">
          {loading ? (
            <div className="flex justify-center py-8"><RefreshCw className="h-6 w-6 animate-spin text-blue-600" /></div>
          ) : isAxis ? (
            <AxisConfigForm config={config} setConfig={setConfig} />
          ) : (
            <div className="space-y-4">
              {Object.entries(config).map(([key, value]) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </label>
                  {key.includes('password') || key.includes('token') ? (
                    <input type="password" value={value} onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded" />
                  ) : typeof value === 'number' ? (
                    <input type="number" value={value} onChange={(e) => setConfig({ ...config, [key]: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-gray-300 rounded" />
                  ) : (
                    <input type="text" value={value} onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded" />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 p-4 border-t">
          <button onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">Cancel</button>
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ConnectorPollingPage() {
  const { getAuthHeader } = useAuth();
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);
  const [configuring, setConfiguring] = useState(null);

  useEffect(() => {
    loadConnectors();
  }, []);

  const loadConnectors = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi('/api/v1/connectors', { headers: getAuthHeader() });
      if (response.success) {
        setConnectors(response.data || []);
      } else {
        setError(response.error?.message || 'Failed to load connectors');
      }
    } catch (err) {
      setError(err.message || 'Failed to load connectors');
    } finally {
      setLoading(false);
    }
  };

  const toggleConnector = async (connectorId, enabled) => {
    try {
      await fetchApi(`/api/v1/connectors/${connectorId}`, {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify({ enabled }),
      });
      await loadConnectors();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const updatePollInterval = async (connectorId, pollInterval) => {
    try {
      // Get current connector config
      const connector = connectors.find(c => c.id === connectorId);
      if (!connector) return;

      // Update config with new poll interval
      const updatedConfig = {
        ...connector.config,
        poll_interval: parseInt(pollInterval)
      };

      await fetchApi(`/api/v1/connectors/${connectorId}`, {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify({ config: updatedConfig }),
      });
      
      await loadConnectors();
      setEditing(null);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const pollConnector = async (connectorId) => {
    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}/poll`, {
        method: 'POST',
        headers: getAuthHeader(),
      });
      
      if (response.success) {
        alert(`Poll completed: ${response.alerts || 0} alerts found`);
        await loadConnectors();
      } else {
        alert(`Poll failed: ${response.message || 'Unknown error'}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const saveConnectorConfig = async (connectorId, config) => {
    await fetchApi(`/api/v1/connectors/${connectorId}`, {
      method: 'PUT',
      headers: getAuthHeader(),
      body: JSON.stringify({ config }),
    });
    await loadConnectors();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'text-green-600';
      case 'error': return 'text-red-600';
      case 'connecting': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return <Check className="h-4 w-4" />;
      case 'error': return <AlertTriangle className="h-4 w-4" />;
      case 'connecting': return <RefreshCw className="h-4 w-4 animate-spin" />;
      default: return <X className="h-4 w-4" />;
    }
  };

  if (loading) return (
    <PageLayout module="system">
      <div className="p-6"><RefreshCw className="h-6 w-6 animate-spin" /></div>
    </PageLayout>
  );

  if (error) return (
    <PageLayout module="system">
      <div className="p-6 text-red-600">Error: {error}</div>
    </PageLayout>
  );

  return (
    <PageLayout module="system">
      <div className="p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Connector Polling
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Configure polling intervals and trigger manual polls
          </p>
        </div>

        {/* Global Polling Info */}
        <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="h-5 w-5 text-blue-600" />
            <h3 className="font-medium text-gray-900 dark:text-white">Global Polling Schedule</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            All connectors are checked every 60 seconds. Individual connectors poll only if their interval has elapsed.
          </p>
        </div>

        {/* Connectors Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900 border-b">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Connector
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Poll Interval
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Last Poll
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Alerts Today
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Enabled
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {connectors.map((connector) => (
                <tr key={connector.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-4 py-3">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {connector.name}
                      </div>
                      <div className="text-sm text-gray-500">
                        {connector.type}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className={`flex items-center gap-2 ${getStatusColor(connector.status)}`}>
                      {getStatusIcon(connector.status)}
                      <span className="text-sm capitalize">{connector.status}</span>
                    </div>
                    {connector.error_message && (
                      <div className="text-xs text-red-600 mt-1">
                        {connector.error_message}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">
                        {connector.config?.poll_interval || 60}s
                      </span>
                      <button
                        onClick={() => setConfiguring(connector)}
                        className="text-gray-400 hover:text-blue-600"
                        title="Configure connector"
                      >
                        <Settings className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {connector.last_poll_at ? 
                        new Date(connector.last_poll_at).toLocaleTimeString() : 
                        'Never'
                      }
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {connector.alerts_today || 0}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleConnector(connector.id, !connector.enabled)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        connector.enabled ? 'bg-blue-600' : 'bg-gray-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          connector.enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => pollConnector(connector.id)}
                        disabled={!connector.enabled}
                        className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                      >
                        <Play className="h-3 w-3" />
                        Poll Now
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {connectors.length === 0 && (
          <div className="text-center py-12">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No connectors configured
            </h3>
            <p className="text-gray-500 mb-4">
              Add connectors to configure polling intervals
            </p>
            <button
              onClick={() => window.location.href = '/connectors'}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Configure Connectors
            </button>
          </div>
        )}

        {/* Config Modal */}
        {configuring && (
          <ConfigModal
            connector={configuring}
            onClose={() => setConfiguring(null)}
            onSave={saveConnectorConfig}
            getAuthHeader={getAuthHeader}
          />
        )}
      </div>
    </PageLayout>
  );
}
