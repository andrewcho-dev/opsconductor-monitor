/**
 * Connectors Management Page
 * 
 * Configure and monitor alert source connectors.
 */

import { useState, useEffect } from 'react';
import { 
  RefreshCw, Settings, Play, Pause, TestTube, Check, X,
  Wifi, WifiOff, AlertCircle, Clock
} from 'lucide-react';
import { useConnectors, useConnectorActions } from '../hooks/useConnectors';
import { CONNECTOR_TYPES } from '../lib/constants';
import { PageLayout } from '../components/layout/PageLayout';

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
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50 border border-green-300 dark:border-green-700'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 border border-gray-300 dark:border-gray-600'
          }`}
        >
          {connector.enabled ? (
            <>
              <Check className="h-4 w-4" />
              Enabled
            </>
          ) : (
            <>
              <Pause className="h-4 w-4" />
              Disabled
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

function CradlepointConfigForm({ config, setConfig }) {
  const [newRouter, setNewRouter] = useState({ ip: '', name: '', username: '', password: '' });
  
  const addRouter = () => {
    if (!newRouter.ip) return;
    const targets = config.targets || [];
    setConfig({ 
      ...config, 
      targets: [...targets, { ...newRouter, username: newRouter.username || 'admin' }]
    });
    setNewRouter({ ip: '', name: '', username: '', password: '' });
  };
  
  const removeRouter = (index) => {
    const targets = [...(config.targets || [])];
    targets.splice(index, 1);
    setConfig({ ...config, targets });
  };

  return (
    <div className="space-y-4">
      {/* Connection Info */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-1 font-medium">Cradlepoint IBR900 Direct Connection</p>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Connect directly to Cradlepoint routers via the local NCOS API. Each router is polled individually for signal, connection, and system status.
        </p>
      </div>

      {/* Default Credentials */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Username</label>
          <input
            type="text"
            placeholder="admin"
            value={config.default_username || ''}
            onChange={(e) => setConfig({ ...config, default_username: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Password</label>
          <input
            type="password"
            value={config.default_password || ''}
            onChange={(e) => setConfig({ ...config, default_password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          />
        </div>
      </div>

      {/* Poll Interval */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Poll Interval (seconds)</label>
        <input
          type="number"
          min="30"
          value={config.poll_interval || 60}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 60 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
      </div>

      {/* Signal Thresholds */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Signal Thresholds</label>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <label className="block text-xs text-gray-500 mb-1">RSRP Warning (dBm)</label>
            <input
              type="number"
              value={config.thresholds?.rsrp_warning || -100}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, rsrp_warning: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">RSRP Critical (dBm)</label>
            <input
              type="number"
              value={config.thresholds?.rsrp_critical || -110}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, rsrp_critical: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">SINR Warning (dB)</label>
            <input
              type="number"
              value={config.thresholds?.sinr_warning || 5}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, sinr_warning: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">SINR Critical (dB)</label>
            <input
              type="number"
              value={config.thresholds?.sinr_critical || 0}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, sinr_critical: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Router List */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Routers ({(config.targets || []).length})
        </label>
        
        {/* Existing routers */}
        {(config.targets || []).length > 0 && (
          <div className="mb-3 space-y-2 max-h-40 overflow-y-auto">
            {(config.targets || []).map((router, idx) => (
              <div key={idx} className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                <span className="font-mono text-gray-600 dark:text-gray-300">{router.ip}</span>
                <span className="text-gray-500">{router.name || 'Unnamed'}</span>
                <button
                  onClick={() => removeRouter(idx)}
                  className="ml-auto text-red-500 hover:text-red-700"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add new router */}
        <div className="grid grid-cols-4 gap-2">
          <input
            type="text"
            placeholder="IP Address"
            value={newRouter.ip}
            onChange={(e) => setNewRouter({ ...newRouter, ip: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="text"
            placeholder="Name (optional)"
            value={newRouter.name}
            onChange={(e) => setNewRouter({ ...newRouter, name: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="password"
            placeholder="Password"
            value={newRouter.password}
            onChange={(e) => setNewRouter({ ...newRouter, password: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <button
            onClick={addRouter}
            disabled={!newRouter.ip}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            Add
          </button>
        </div>
      </div>

      {/* Monitoring Options */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Monitoring Options</label>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_signal !== false}
              onChange={(e) => setConfig({ ...config, monitor_signal: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Cellular Signal</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_connection !== false}
              onChange={(e) => setConfig({ ...config, monitor_connection: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Connection State</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_temperature !== false}
              onChange={(e) => setConfig({ ...config, monitor_temperature: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Temperature</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_gps !== false}
              onChange={(e) => setConfig({ ...config, monitor_gps: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">GPS Status</span>
          </label>
        </div>
      </div>

      {/* Help Text */}
      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600">
        <p className="text-xs text-gray-600 dark:text-gray-400">
          <strong>Note:</strong> This connector polls Cradlepoint routers directly via the local NCOS API (not NetCloud). 
          Ensure each router is reachable on the network and has API access enabled. Default credentials are used unless 
          overridden per-router.
        </p>
      </div>
    </div>
  );
}

function MilestoneConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      {/* Connection Info */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-1 font-medium">Milestone XProtect Connection</p>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Connect to the <strong>Management Server</strong> URL. The API will query all Recording Servers and cameras through this central endpoint.
        </p>
      </div>

      {/* Management Server URL */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Management Server URL <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          placeholder="https://milestone-server:8081"
          value={config.url || ''}
          onChange={(e) => setConfig({ ...config, url: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
        <p className="text-xs text-gray-500 mt-1">
          The base URL of your Milestone XProtect Management Server (typically port 8081 for HTTPS or 80 for HTTP)
        </p>
      </div>

      {/* Credentials */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Username <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            placeholder="domain\\username or username"
            value={config.username || ''}
            onChange={(e) => setConfig({ ...config, username: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Password <span className="text-red-500">*</span>
          </label>
          <input
            type="password"
            value={config.password || ''}
            onChange={(e) => setConfig({ ...config, password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          />
        </div>
      </div>

      {/* SSL Verification */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="verify_ssl"
          checked={config.verify_ssl || false}
          onChange={(e) => setConfig({ ...config, verify_ssl: e.target.checked })}
          className="rounded border-gray-300 text-blue-600"
        />
        <label htmlFor="verify_ssl" className="text-sm text-gray-700 dark:text-gray-300">
          Verify SSL Certificate
        </label>
        <span className="text-xs text-gray-500">(disable for self-signed certificates)</span>
      </div>

      {/* Poll Interval */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Poll Interval (seconds)</label>
        <input
          type="number"
          min="30"
          value={config.poll_interval || 60}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 60 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
        <p className="text-xs text-gray-500 mt-1">
          How often to poll for camera status and events (minimum 30 seconds)
        </p>
      </div>

      {/* Event Types to Monitor */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Event Types to Monitor</label>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_camera_status !== false}
              onChange={(e) => setConfig({ ...config, monitor_camera_status: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Camera Status (online/offline)</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_recording !== false}
              onChange={(e) => setConfig({ ...config, monitor_recording: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Recording Status</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_storage !== false}
              onChange={(e) => setConfig({ ...config, monitor_storage: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Storage Alerts</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_server !== false}
              onChange={(e) => setConfig({ ...config, monitor_server: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Server Health</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_motion || false}
              onChange={(e) => setConfig({ ...config, monitor_motion: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Motion Events</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_analytics || false}
              onChange={(e) => setConfig({ ...config, monitor_analytics: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Analytics Events</span>
          </label>
        </div>
      </div>

      {/* Help Text */}
      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600">
        <p className="text-xs text-gray-600 dark:text-gray-400">
          <strong>Note:</strong> The Milestone connector uses the Management Server API to query all Recording Servers. 
          Ensure the user account has API access permissions. For XProtect Corporate/Expert, use a Windows domain account. 
          For XProtect Essential+/Express+, use the built-in administrator account.
        </p>
      </div>
    </div>
  );
}

function AxisConfigForm({ config, setConfig }) {
  const [newCamera, setNewCamera] = useState({ ip: '', name: '', username: '', password: '' });
  
  const addCamera = () => {
    if (!newCamera.ip) return;
    const targets = config.targets || [];
    setConfig({ 
      ...config, 
      targets: [...targets, { ...newCamera, username: newCamera.username || config.default_username || 'root' }]
    });
    setNewCamera({ ip: '', name: '', username: '', password: '' });
  };
  
  const removeCamera = (index) => {
    const targets = [...(config.targets || [])];
    targets.splice(index, 1);
    setConfig({ ...config, targets });
  };

  return (
    <div className="space-y-4">
      {/* Camera Source */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Camera Source</label>
        <select
          value={config.camera_source || 'manual'}
          onChange={(e) => setConfig({ ...config, camera_source: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        >
          <option value="manual">Manual List</option>
          <option value="prtg">From PRTG (auto-discover)</option>
        </select>
      </div>

      {/* PRTG Filter (if PRTG source) */}
      {config.camera_source === 'prtg' && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">PRTG Filter (cameras matching these criteria)</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400">Tag Contains</label>
              <input
                type="text"
                placeholder="e.g., camera"
                value={config.prtg_filter?.tags || ''}
                onChange={(e) => setConfig({ ...config, prtg_filter: { ...config.prtg_filter, tags: e.target.value } })}
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400">Group Contains</label>
              <input
                type="text"
                placeholder="e.g., Cameras"
                value={config.prtg_filter?.group || ''}
                onChange={(e) => setConfig({ ...config, prtg_filter: { ...config.prtg_filter, group: e.target.value } })}
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
              />
            </div>
          </div>
        </div>
      )}

      {/* Default Credentials */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Username</label>
          <input
            type="text"
            value={config.default_username || 'root'}
            onChange={(e) => setConfig({ ...config, default_username: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Password</label>
          <input
            type="password"
            value={config.default_password || ''}
            onChange={(e) => setConfig({ ...config, default_password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          />
        </div>
      </div>

      {/* Poll Interval */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Poll Interval (seconds)</label>
        <input
          type="number"
          value={config.poll_interval || 60}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 60 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
      </div>

      {/* Manual Camera List (if manual source) */}
      {config.camera_source !== 'prtg' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Cameras ({(config.targets || []).length})
          </label>
          
          {/* Camera List */}
          <div className="max-h-40 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded mb-2">
            {(config.targets || []).length === 0 ? (
              <p className="text-sm text-gray-500 p-3 text-center">No cameras configured</p>
            ) : (config.targets || []).map((cam, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div className="text-sm">
                  <span className="font-medium">{cam.ip}</span>
                  {cam.name && <span className="text-gray-500 ml-2">({cam.name})</span>}
                </div>
                <button onClick={() => removeCamera(idx)} className="text-red-500 hover:text-red-700 text-xs">Remove</button>
              </div>
            ))}
          </div>

          {/* Add Camera Form */}
          <div className="grid grid-cols-4 gap-2">
            <input
              type="text"
              placeholder="IP Address"
              value={newCamera.ip}
              onChange={(e) => setNewCamera({ ...newCamera, ip: e.target.value })}
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
            />
            <input
              type="text"
              placeholder="Name (optional)"
              value={newCamera.name}
              onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
            />
            <input
              type="text"
              placeholder="Username"
              value={newCamera.username}
              onChange={(e) => setNewCamera({ ...newCamera, username: e.target.value })}
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
            />
            <button
              onClick={addCamera}
              disabled={!newCamera.ip}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              Add
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfigModal({ connector, onClose, onSave }) {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!connector?.id) return;
    
    const fetchConfig = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/v1/connectors/${connector.id}`);
        const data = await response.json();
        if (data.success && data.data?.config) {
          setConfig(data.data.config);
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
      await onSave(connector.id, { config });
      onClose();
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!connector) return null;

  // Use specialized form for specific connectors
  const isAxis = connector.type === 'axis';
  const isMilestone = connector.type === 'milestone';
  const isCradlepoint = connector.type === 'cradlepoint';
  const hasSpecialForm = isAxis || isMilestone || isCradlepoint;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full mx-4 ${hasSpecialForm ? 'max-w-2xl' : 'max-w-lg'}`}>
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Configure {connector.name}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 max-h-[70vh] overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : isAxis ? (
            <AxisConfigForm config={config} setConfig={setConfig} />
          ) : isMilestone ? (
            <MilestoneConfigForm config={config} setConfig={setConfig} />
          ) : isCradlepoint ? (
            <CradlepointConfigForm config={config} setConfig={setConfig} />
          ) : Object.keys(config).length === 0 ? (
            <p className="text-gray-500 text-center py-8">No configuration options available</p>
          ) : (
            <div className="space-y-4">
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
          )}
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
    <PageLayout module="connectors">
      <div className="p-6">
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
    </PageLayout>
  );
}

export default ConnectorsPage;
