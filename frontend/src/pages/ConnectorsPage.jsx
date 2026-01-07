/**
 * Connectors Management Page
 * 
 * Configure and monitor alert source connectors.
 */

import { useState } from 'react';
import { 
  RefreshCw, Settings, Play, Pause, TestTube, Check, X,
  Wifi, WifiOff, AlertCircle, Clock
} from 'lucide-react';
import { useConnectors, useConnectorActions } from '../hooks/useConnectors';
import { CONNECTOR_TYPES } from '../lib/constants';

function ConnectorCard({ connector, onTest, onToggle, onConfigure, testing }) {
  const typeInfo = CONNECTOR_TYPES.find(t => t.type === connector.type) || {};
  
  const statusColors = {
    connected: 'text-green-500',
    disconnected: 'text-gray-400',
    error: 'text-red-500',
    unknown: 'text-yellow-500',
  };

  const StatusIcon = connector.status === 'connected' ? Wifi : 
                     connector.status === 'error' ? AlertCircle : WifiOff;

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg border ${
      connector.enabled ? 'border-blue-200 dark:border-blue-800' : 'border-gray-200 dark:border-gray-700'
    } p-4`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{typeInfo.icon || '📡'}</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-white">
              {connector.name}
            </h3>
            <p className="text-sm text-gray-500">{typeInfo.name || connector.type}</p>
          </div>
        </div>
        <div className={`flex items-center gap-1 ${statusColors[connector.status]}`}>
          <StatusIcon className="h-4 w-4" />
          <span className="text-xs capitalize">{connector.status}</span>
        </div>
      </div>

      {connector.error_message && (
        <div className="mb-3 p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-700 dark:text-red-300">
          {connector.error_message}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-sm mb-4">
        <div>
          <span className="text-gray-500">Alerts Today:</span>
          <span className="ml-2 font-medium text-gray-900 dark:text-white">
            {connector.alerts_today || 0}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Total:</span>
          <span className="ml-2 font-medium text-gray-900 dark:text-white">
            {connector.alerts_received || 0}
          </span>
        </div>
        {connector.last_poll_at && (
          <div className="col-span-2 flex items-center gap-1 text-gray-500">
            <Clock className="h-3 w-3" />
            <span className="text-xs">
              Last poll: {new Date(connector.last_poll_at).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onToggle(connector.id, !connector.enabled)}
          className={`flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded text-sm font-medium ${
            connector.enabled
              ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {connector.enabled ? (
            <>
              <Pause className="h-4 w-4" />
              Disable
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Enable
            </>
          )}
        </button>
        <button
          onClick={() => onTest(connector.id)}
          disabled={testing === connector.id}
          className="flex items-center gap-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          {testing === connector.id ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <TestTube className="h-4 w-4" />
          )}
          Test
        </button>
        <button
          onClick={() => onConfigure(connector)}
          className="p-2 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function ConfigModal({ connector, onClose, onSave }) {
  const [config, setConfig] = useState(connector?.config || {});
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(connector.id, { config });
      onClose();
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!connector) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Configure {connector.name}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
          {Object.entries(config).map(([key, value]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </label>
              {key.includes('password') || key.includes('token') || key.includes('secret') ? (
                <input
                  type="password"
                  value={value}
                  onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                />
              ) : typeof value === 'boolean' ? (
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => setConfig({ ...config, [key]: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600"
                />
              ) : typeof value === 'number' ? (
                <input
                  type="number"
                  value={value}
                  onChange={(e) => setConfig({ ...config, [key]: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                />
              ) : (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                />
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ConnectorsPage() {
  const { connectors, loading, error, refresh } = useConnectors();
  const { testConnection, enableConnector, disableConnector, updateConnector } = useConnectorActions();
  
  const [testing, setTesting] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [configuring, setConfiguring] = useState(null);

  const handleTest = async (connectorId) => {
    setTesting(connectorId);
    setTestResult(null);
    try {
      const result = await testConnection(connectorId);
      setTestResult({ id: connectorId, ...result });
      refresh();
    } catch (err) {
      setTestResult({ id: connectorId, success: false, message: err.message });
    } finally {
      setTesting(null);
    }
  };

  const handleToggle = async (connectorId, enable) => {
    try {
      if (enable) {
        await enableConnector(connectorId);
      } else {
        await disableConnector(connectorId);
      }
      refresh();
    } catch (err) {
      console.error('Failed to toggle connector:', err);
    }
  };

  const handleSaveConfig = async (connectorId, data) => {
    await updateConnector(connectorId, data);
    refresh();
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Connectors
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Configure alert source integrations
            </p>
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Test Result Banner */}
        {testResult && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
            testResult.success 
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          }`}>
            {testResult.success ? (
              <Check className="h-5 w-5 text-green-600" />
            ) : (
              <X className="h-5 w-5 text-red-600" />
            )}
            <span className={testResult.success ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'}>
              {testResult.message}
            </span>
            <button
              onClick={() => setTestResult(null)}
              className="ml-auto text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && connectors.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : (
          /* Connector Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connectors.map((connector) => (
              <ConnectorCard
                key={connector.id}
                connector={connector}
                onTest={handleTest}
                onToggle={handleToggle}
                onConfigure={setConfiguring}
                testing={testing}
              />
            ))}
          </div>
        )}

        {/* Config Modal */}
        {configuring && (
          <ConfigModal
            connector={configuring}
            onClose={() => setConfiguring(null)}
            onSave={handleSaveConfig}
          />
        )}
      </div>
    </div>
  );
}

export default ConnectorsPage;
