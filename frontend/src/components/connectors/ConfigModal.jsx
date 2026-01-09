/**
 * Shared Connector Configuration Modal
 * 
 * Used by both ConnectorsPage and ConnectorPollingPage
 */

import { useState, useEffect } from 'react';
import { X, RefreshCw } from 'lucide-react';
import { fetchApi } from '../../lib/utils';

// Cradlepoint-specific configuration form
function CradlepointConfigForm({ config, setConfig }) {
  const [newRouter, setNewRouter] = useState({ ip: '', name: '', username: '', password: '' });
  const [bulkImportText, setBulkImportText] = useState('');
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [importError, setImportError] = useState('');
  
  const addRouter = () => {
    if (!newRouter.ip) return;
    const targets = config.targets || [];
    setConfig({ 
      ...config, 
      targets: [...targets, { ...newRouter, username: newRouter.username || config.default_username || 'admin' }]
    });
    setNewRouter({ ip: '', name: '', username: '', password: '' });
  };
  
  const removeRouter = (index) => {
    const targets = [...(config.targets || [])];
    targets.splice(index, 1);
    setConfig({ ...config, targets });
  };

  const clearAllRouters = () => {
    if (window.confirm(`Remove all ${(config.targets || []).length} routers?`)) {
      setConfig({ ...config, targets: [] });
    }
  };

  const handleBulkImport = () => {
    setImportError('');
    const lines = bulkImportText.trim().split('\n').filter(line => line.trim());
    const newTargets = [];
    const errors = [];

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      if (idx === 0 && (trimmed.toLowerCase().includes('ip') || trimmed.toLowerCase().includes('address'))) {
        return;
      }

      const parts = trimmed.split(/[,\t]/).map(p => p.trim());
      const ip = parts[0];
      
      const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (!ipRegex.test(ip)) {
        errors.push(`Line ${idx + 1}: Invalid IP "${ip}"`);
        return;
      }

      newTargets.push({
        ip: ip,
        name: parts[1] || '',
        username: config.default_username || 'admin',
        password: parts[2] || config.default_password || '',
      });
    });

    if (errors.length > 0) {
      setImportError(errors.slice(0, 5).join('\n') + (errors.length > 5 ? `\n...and ${errors.length - 5} more errors` : ''));
      return;
    }

    if (newTargets.length === 0) {
      setImportError('No valid routers found in input');
      return;
    }

    const existingIPs = new Set((config.targets || []).map(t => t.ip));
    const uniqueNew = newTargets.filter(t => !existingIPs.has(t.ip));
    const duplicates = newTargets.length - uniqueNew.length;

    setConfig({ 
      ...config, 
      targets: [...(config.targets || []), ...uniqueNew] 
    });
    
    setBulkImportText('');
    setShowBulkImport(false);
    
    if (duplicates > 0) {
      alert(`Imported ${uniqueNew.length} routers. Skipped ${duplicates} duplicates.`);
    }
  };

  return (
    <div className="space-y-4">
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-1 font-medium">Cradlepoint IBR900 Direct Connection</p>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Connect directly to Cradlepoint routers via the local NCOS API.
        </p>
      </div>

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

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Routers ({(config.targets || []).length})
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setShowBulkImport(!showBulkImport)}
              className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
            >
              {showBulkImport ? 'Cancel Import' : 'Bulk Import'}
            </button>
            {(config.targets || []).length > 0 && (
              <button
                onClick={clearAllRouters}
                className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Clear All
              </button>
            )}
          </div>
        </div>

        {showBulkImport && (
          <div className="mb-3 p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
            <p className="text-xs text-green-700 dark:text-green-300 mb-2">
              Paste router list (one per line). Formats: IP only, IP,Name, or IP,Name,Password
            </p>
            <textarea
              value={bulkImportText}
              onChange={(e) => setBulkImportText(e.target.value)}
              placeholder="10.1.2.3,Router-1&#10;10.1.2.4,Router-2"
              rows={6}
              className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono"
            />
            {importError && (
              <p className="text-xs text-red-600 mt-1 whitespace-pre-line">{importError}</p>
            )}
            <button
              onClick={handleBulkImport}
              disabled={!bulkImportText.trim()}
              className="mt-2 px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              Import Routers
            </button>
          </div>
        )}
        
        {(config.targets || []).length > 0 && (
          <div className="mb-3 max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded">
            {(config.targets || []).map((router, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0 text-sm">
                <div>
                  <span className="font-mono text-gray-700 dark:text-gray-300">{router.ip}</span>
                  {router.name && <span className="text-gray-500 ml-2">({router.name})</span>}
                </div>
                <button
                  onClick={() => removeRouter(idx)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

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
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_ethernet || false}
              onChange={(e) => setConfig({ ...config, monitor_ethernet: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Ethernet Ports</span>
          </label>
        </div>
      </div>
    </div>
  );
}

// Milestone-specific configuration form
function MilestoneConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-1 font-medium">Milestone XProtect Connection</p>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Connect to the Management Server URL.
        </p>
      </div>

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
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Username <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            placeholder="domain\\username"
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
      </div>

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
            <span className="text-gray-700 dark:text-gray-300">Camera Status</span>
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
        </div>
      </div>
    </div>
  );
}

// Axis-specific configuration form
function AxisConfigForm({ config, setConfig }) {
  const [newCamera, setNewCamera] = useState({ ip: '', name: '', username: '', password: '' });
  const [bulkImportText, setBulkImportText] = useState('');
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [importError, setImportError] = useState('');
  
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

  const clearAllCameras = () => {
    if (window.confirm(`Remove all ${(config.targets || []).length} cameras?`)) {
      setConfig({ ...config, targets: [] });
    }
  };

  const handleBulkImport = () => {
    setImportError('');
    const lines = bulkImportText.trim().split('\n').filter(line => line.trim());
    const newTargets = [];
    const errors = [];

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      if (idx === 0 && (trimmed.toLowerCase().includes('ip') || trimmed.toLowerCase().includes('address'))) {
        return;
      }

      const parts = trimmed.split(/[,\t]/).map(p => p.trim());
      const ip = parts[0];
      
      const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (!ipRegex.test(ip)) {
        errors.push(`Line ${idx + 1}: Invalid IP "${ip}"`);
        return;
      }

      newTargets.push({
        ip: ip,
        name: parts[1] || '',
        username: parts[2] || config.default_username || 'root',
        password: parts[3] || config.default_password || '',
      });
    });

    if (errors.length > 0) {
      setImportError(errors.slice(0, 5).join('\n') + (errors.length > 5 ? `\n...and ${errors.length - 5} more errors` : ''));
      return;
    }

    if (newTargets.length === 0) {
      setImportError('No valid cameras found in input');
      return;
    }

    const existingIPs = new Set((config.targets || []).map(t => t.ip));
    const uniqueNew = newTargets.filter(t => !existingIPs.has(t.ip));
    const duplicates = newTargets.length - uniqueNew.length;

    setConfig({ 
      ...config, 
      targets: [...(config.targets || []), ...uniqueNew] 
    });
    
    setBulkImportText('');
    setShowBulkImport(false);
    
    if (duplicates > 0) {
      alert(`Imported ${uniqueNew.length} cameras. Skipped ${duplicates} duplicates.`);
    }
  };

  return (
    <div className="space-y-4">
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

      {config.camera_source === 'prtg' && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">PRTG Filter</p>
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

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Poll Interval (seconds)</label>
        <input
          type="number"
          value={config.poll_interval || 60}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 60 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
      </div>

      {config.camera_source !== 'prtg' && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Cameras ({(config.targets || []).length})
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setShowBulkImport(!showBulkImport)}
                className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
              >
                {showBulkImport ? 'Cancel Import' : 'Bulk Import'}
              </button>
              {(config.targets || []).length > 0 && (
                <button
                  onClick={clearAllCameras}
                  className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>

          {showBulkImport && (
            <div className="mb-3 p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
              <p className="text-xs text-green-700 dark:text-green-300 mb-2">
                Paste camera list. Formats: IP, IP,Name, or IP,Name,Username,Password
              </p>
              <textarea
                value={bulkImportText}
                onChange={(e) => setBulkImportText(e.target.value)}
                placeholder="10.1.2.3,Camera-1&#10;10.1.2.4,Camera-2"
                rows={6}
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono"
              />
              {importError && (
                <p className="text-xs text-red-600 mt-1 whitespace-pre-line">{importError}</p>
              )}
              <button
                onClick={handleBulkImport}
                disabled={!bulkImportText.trim()}
                className="mt-2 px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                Import Cameras
              </button>
            </div>
          )}
          
          <div className="max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded mb-2">
            {(config.targets || []).length === 0 ? (
              <p className="text-sm text-gray-500 p-3 text-center">No cameras configured</p>
            ) : (config.targets || []).map((cam, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div className="text-sm">
                  <span className="font-medium font-mono">{cam.ip}</span>
                  {cam.name && <span className="text-gray-500 ml-2">({cam.name})</span>}
                </div>
                <button onClick={() => removeCamera(idx)} className="text-red-500 hover:text-red-700 text-xs">Remove</button>
              </div>
            ))}
          </div>

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

// Eaton REST API configuration form
function EatonRESTConfigForm({ config, setConfig }) {
  const [newTarget, setNewTarget] = useState({ ip: '', name: '', username: '', password: '' });
  const [bulkImportText, setBulkImportText] = useState('');
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [importError, setImportError] = useState('');

  const addTarget = () => {
    if (!newTarget.ip) return;
    const targets = config.targets || [];
    setConfig({ 
      ...config, 
      targets: [...targets, { 
        ...newTarget, 
        username: newTarget.username || config.default_username || 'admin',
        password: newTarget.password || config.default_password || ''
      }]
    });
    setNewTarget({ ip: '', name: '', username: '', password: '' });
  };

  const removeTarget = (index) => {
    const targets = [...(config.targets || [])];
    targets.splice(index, 1);
    setConfig({ ...config, targets });
  };

  const clearAllTargets = () => {
    if (window.confirm(`Remove all ${(config.targets || []).length} UPS devices?`)) {
      setConfig({ ...config, targets: [] });
    }
  };

  const handleBulkImport = () => {
    setImportError('');
    const lines = bulkImportText.trim().split('\n').filter(line => line.trim());
    const newTargets = [];
    const errors = [];

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      // Skip header row
      if (idx === 0 && (trimmed.toLowerCase().includes('ip') || trimmed.toLowerCase().includes('address'))) {
        return;
      }

      const parts = trimmed.split(/[,\t]/).map(p => p.trim());
      const ip = parts[0];
      
      const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (!ipRegex.test(ip)) {
        errors.push(`Line ${idx + 1}: Invalid IP "${ip}"`);
        return;
      }

      newTargets.push({
        ip: ip,
        name: parts[1] || '',
        username: config.default_username || 'admin',
        password: parts[2] || config.default_password || '',
      });
    });

    if (errors.length > 0) {
      setImportError(errors.slice(0, 5).join('\n') + (errors.length > 5 ? `\n...and ${errors.length - 5} more errors` : ''));
      return;
    }

    if (newTargets.length === 0) {
      setImportError('No valid UPS devices found in input');
      return;
    }

    const existingIPs = new Set((config.targets || []).map(t => t.ip));
    const uniqueNew = newTargets.filter(t => !existingIPs.has(t.ip));
    const duplicates = newTargets.length - uniqueNew.length;

    setConfig({ 
      ...config, 
      targets: [...(config.targets || []), ...uniqueNew] 
    });
    
    setBulkImportText('');
    setShowBulkImport(false);
    
    if (duplicates > 0) {
      alert(`Imported ${uniqueNew.length} UPS devices. Skipped ${duplicates} duplicates.`);
    }
  };

  return (
    <div className="space-y-4">
      <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
        <p className="text-sm text-green-700 dark:text-green-300 mb-1 font-medium">Eaton Network-M2 REST API</p>
        <p className="text-xs text-green-600 dark:text-green-400">
          Poll active alarms from Eaton UPS Network-M2 cards via REST API.
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
          min="60"
          value={config.poll_interval || 300}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 300 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
      </div>

      {/* UPS Targets */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            UPS Devices ({(config.targets || []).length})
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setShowBulkImport(!showBulkImport)}
              className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
            >
              {showBulkImport ? 'Cancel Import' : 'Bulk Import'}
            </button>
            {(config.targets || []).length > 0 && (
              <button
                onClick={clearAllTargets}
                className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Clear All
              </button>
            )}
          </div>
        </div>

        {showBulkImport && (
          <div className="mb-3 p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
            <p className="text-xs text-green-700 dark:text-green-300 mb-2">
              Paste UPS list (one per line). Formats: IP only, IP,Name, or IP,Name,Password
            </p>
            <textarea
              value={bulkImportText}
              onChange={(e) => setBulkImportText(e.target.value)}
              placeholder="10.120.51.71,SNA-UPS01&#10;10.120.51.72,SNA-UPS02"
              rows={6}
              className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono"
            />
            {importError && (
              <p className="text-xs text-red-600 mt-1 whitespace-pre-line">{importError}</p>
            )}
            <button
              onClick={handleBulkImport}
              disabled={!bulkImportText.trim()}
              className="mt-2 px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              Import UPS Devices
            </button>
          </div>
        )}
        
        {(config.targets || []).length > 0 && (
          <div className="mb-3 max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded">
            {(config.targets || []).map((target, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0 text-sm">
                <div>
                  <span className="font-mono text-gray-700 dark:text-gray-300">{target.ip}</span>
                  {target.name && <span className="text-gray-500 ml-2">({target.name})</span>}
                </div>
                <button
                  onClick={() => removeTarget(idx)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add new UPS */}
        <div className="grid grid-cols-4 gap-2">
          <input
            type="text"
            placeholder="IP Address"
            value={newTarget.ip}
            onChange={(e) => setNewTarget({ ...newTarget, ip: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="text"
            placeholder="Name (optional)"
            value={newTarget.name}
            onChange={(e) => setNewTarget({ ...newTarget, name: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="password"
            placeholder="Password"
            value={newTarget.password}
            onChange={(e) => setNewTarget({ ...newTarget, password: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <button
            onClick={addTarget}
            disabled={!newTarget.ip}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
}

// Cisco ASA configuration form
function CiscoASAConfigForm({ config, setConfig }) {
  const [newTarget, setNewTarget] = useState({ ip: '', name: '', username: '', password: '', port: 22 });
  const [newPeer, setNewPeer] = useState('');

  const addTarget = () => {
    if (!newTarget.ip) return;
    const targets = config.targets || [];
    setConfig({ 
      ...config, 
      targets: [...targets, { ...newTarget, username: newTarget.username || config.default_username || 'admin' }]
    });
    setNewTarget({ ip: '', name: '', username: '', password: '', port: 22 });
  };

  const removeTarget = (index) => {
    const targets = [...(config.targets || [])];
    targets.splice(index, 1);
    setConfig({ ...config, targets });
  };

  const addVpnPeer = () => {
    if (!newPeer) return;
    const peers = config.vpn_peers || [];
    if (!peers.includes(newPeer)) {
      setConfig({ ...config, vpn_peers: [...peers, newPeer] });
    }
    setNewPeer('');
  };

  const removeVpnPeer = (index) => {
    const peers = [...(config.vpn_peers || [])];
    peers.splice(index, 1);
    setConfig({ ...config, vpn_peers: peers });
  };

  return (
    <div className="space-y-4">
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-1 font-medium">Cisco ASA SSH/CLI Monitoring</p>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Monitor IPSec VPN tunnels, system health, and interface status via SSH.
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
          min="60"
          value={config.poll_interval || 300}
          onChange={(e) => setConfig({ ...config, poll_interval: parseInt(e.target.value) || 300 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
      </div>

      {/* Thresholds */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Thresholds</label>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <label className="block text-xs text-gray-500 mb-1">CPU Warning (%)</label>
            <input
              type="number"
              value={config.thresholds?.cpu_warning || 80}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, cpu_warning: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">CPU Critical (%)</label>
            <input
              type="number"
              value={config.thresholds?.cpu_critical || 95}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, cpu_critical: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Memory Warning (%)</label>
            <input
              type="number"
              value={config.thresholds?.memory_warning || 80}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, memory_warning: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Memory Critical (%)</label>
            <input
              type="number"
              value={config.thresholds?.memory_critical || 95}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, memory_critical: parseInt(e.target.value) }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* ASA Targets */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            ASA Devices ({(config.targets || []).length})
          </label>
        </div>
        
        {(config.targets || []).length > 0 && (
          <div className="mb-3 max-h-32 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded">
            {(config.targets || []).map((target, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0 text-sm">
                <div>
                  <span className="font-mono text-gray-700 dark:text-gray-300">{target.ip}</span>
                  {target.name && <span className="text-gray-500 ml-2">({target.name})</span>}
                </div>
                <button
                  onClick={() => removeTarget(idx)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-5 gap-2">
          <input
            type="text"
            placeholder="IP Address"
            value={newTarget.ip}
            onChange={(e) => setNewTarget({ ...newTarget, ip: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="text"
            placeholder="Name"
            value={newTarget.name}
            onChange={(e) => setNewTarget({ ...newTarget, name: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="text"
            placeholder="Username"
            value={newTarget.username}
            onChange={(e) => setNewTarget({ ...newTarget, username: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <input
            type="password"
            placeholder="Password"
            value={newTarget.password}
            onChange={(e) => setNewTarget({ ...newTarget, password: e.target.value })}
            className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <button
            onClick={addTarget}
            disabled={!newTarget.ip}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            Add
          </button>
        </div>
      </div>

      {/* VPN Peers to Monitor */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            VPN Peers to Monitor ({(config.vpn_peers || []).length})
          </label>
        </div>
        <p className="text-xs text-gray-500 mb-2">
          Add peer IPs to monitor. Leave empty to auto-discover from ASA config.
        </p>
        
        {(config.vpn_peers || []).length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {(config.vpn_peers || []).map((peer, idx) => (
              <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm">
                {peer}
                <button
                  onClick={() => removeVpnPeer(idx)}
                  className="text-red-500 hover:text-red-700"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            type="text"
            placeholder="VPN Peer IP"
            value={newPeer}
            onChange={(e) => setNewPeer(e.target.value)}
            className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
          />
          <button
            onClick={addVpnPeer}
            disabled={!newPeer}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            Add Peer
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
              checked={config.monitor_vpn !== false}
              onChange={(e) => setConfig({ ...config, monitor_vpn: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">IPSec VPN Tunnels</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_system !== false}
              onChange={(e) => setConfig({ ...config, monitor_system: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">CPU/Memory</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_interfaces !== false}
              onChange={(e) => setConfig({ ...config, monitor_interfaces: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Interfaces</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_failover !== false}
              onChange={(e) => setConfig({ ...config, monitor_failover: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Failover Status</span>
          </label>
        </div>
      </div>
    </div>
  );
}

// SNMP Traps config form
function SNMPTrapConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      {/* Status Info */}
      <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
        <h4 className="font-medium text-green-800 dark:text-green-200 mb-2">SNMP Trap Receiver Status</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-gray-600 dark:text-gray-400">Listen Address:</div>
          <div className="font-mono text-gray-900 dark:text-white">{config.listen_address || '0.0.0.0'}:{config.port || 1162}</div>
          <div className="text-gray-600 dark:text-gray-400">Community:</div>
          <div className="font-mono text-gray-900 dark:text-white">{config.community || 'public'}</div>
        </div>
      </div>

      {/* Configuration */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Listen Port
        </label>
        <input
          type="number"
          value={config.port || 1162}
          onChange={(e) => setConfig({ ...config, port: parseInt(e.target.value) || 1162 })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
        <p className="text-xs text-gray-500 mt-1">Default: 1162 (requires restart to change)</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Community String
        </label>
        <input
          type="text"
          value={config.community || 'public'}
          onChange={(e) => setConfig({ ...config, community: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
      </div>

      {/* How to Use */}
      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2">How to Configure Devices</h4>
        <ol className="text-sm text-gray-700 dark:text-gray-300 space-y-1 list-decimal list-inside">
          <li>Configure your devices to send SNMP traps to this server's IP on port {config.port || 1162}</li>
          <li>Use community string: <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">{config.community || 'public'}</code></li>
          <li>Go to <strong>System → Normalization → SNMP Traps</strong> to map trap OIDs to severities/categories</li>
          <li>Use the vendor filter to organize mappings by device vendor (Siklu, Ciena, etc.)</li>
        </ol>
      </div>

      {/* Vendor Mappings Link */}
      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <strong>Configured Vendors:</strong> Siklu, Standard (IF-MIB)
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Add more vendors by creating trap OID mappings in System → Normalization
        </p>
      </div>
    </div>
  );
}

// Generic config form for other connectors
function GenericConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      {Object.entries(config).map(([key, value]) => (
        <div key={key}>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </label>
          {key.includes('password') || key.includes('token') || key.includes('secret') ? (
            <input
              type="password"
              value={value || ''}
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
          ) : typeof value === 'object' ? (
            <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-auto max-h-32">
              {JSON.stringify(value, null, 2)}
            </pre>
          ) : (
            <input
              type="text"
              value={value || ''}
              onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          )}
        </div>
      ))}
    </div>
  );
}

// Ubiquiti UISP configuration form
function UbiquitiConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-1 font-medium">Ubiquiti UISP Connection</p>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Connect to UISP for device monitoring and alerts.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          UISP Server URL <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          placeholder="https://uisp.example.com"
          value={config.url || ''}
          onChange={(e) => setConfig({ ...config, url: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
        <p className="text-xs text-gray-500 mt-1">UISP server URL without trailing slash</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          API Token <span className="text-red-500">*</span>
        </label>
        <input
          type="password"
          placeholder="Enter API token"
          value={config.api_token || ''}
          onChange={(e) => setConfig({ ...config, api_token: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
        />
        <p className="text-xs text-gray-500 mt-1">Generate in UISP: Settings → Users → API Tokens</p>
      </div>

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

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Alert Thresholds</label>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <label className="block text-xs text-gray-500 mb-1">CPU Warning (%)</label>
            <input
              type="number"
              min="1"
              max="100"
              value={config.thresholds?.cpu_warning || 80}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, cpu_warning: parseInt(e.target.value) || 80 }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Memory Warning (%)</label>
            <input
              type="number"
              min="1"
              max="100"
              value={config.thresholds?.memory_warning || 80}
              onChange={(e) => setConfig({ 
                ...config, 
                thresholds: { ...config.thresholds, memory_warning: parseInt(e.target.value) || 80 }
              })}
              className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Monitoring Options</label>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_offline !== false}
              onChange={(e) => setConfig({ ...config, monitor_offline: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Device Offline</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_cpu !== false}
              onChange={(e) => setConfig({ ...config, monitor_cpu: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">High CPU</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_memory !== false}
              onChange={(e) => setConfig({ ...config, monitor_memory: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">High Memory</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_signal !== false}
              onChange={(e) => setConfig({ ...config, monitor_signal: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Signal Degraded</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.monitor_outages !== false}
              onChange={(e) => setConfig({ ...config, monitor_outages: e.target.checked })}
              className="rounded border-gray-300 text-blue-600"
            />
            <span className="text-gray-700 dark:text-gray-300">Outages</span>
          </label>
        </div>
      </div>

      <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-600 dark:text-gray-400">
          <strong>Alert Types:</strong> device_offline, device_online, high_cpu, high_memory, signal_degraded, outage, firmware_update
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Configure severity/category mappings in Connectors → Normalization Rules
        </p>
      </div>
    </div>
  );
}

// Main ConfigModal component
export default function ConfigModal({ connector, onClose, onSave, getAuthHeader }) {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!connector?.id) return;
    
    const fetchConfig = async () => {
      setLoading(true);
      try {
        const headers = getAuthHeader ? getAuthHeader() : {};
        const response = await fetchApi(`/api/v1/connectors/${connector.id}`, { headers });
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
  const isMilestone = connector.type === 'milestone';
  const isCradlepoint = connector.type === 'cradlepoint';
  const isCiscoASA = connector.type === 'cisco_asa';
  const isEatonREST = connector.type === 'eaton_rest';
  const isSNMPTrap = connector.type === 'snmp_trap';
  const isUbiquiti = connector.type === 'ubiquiti';
  const hasSpecialForm = isAxis || isMilestone || isCradlepoint || isCiscoASA || isEatonREST || isSNMPTrap || isUbiquiti;

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
          ) : isCiscoASA ? (
            <CiscoASAConfigForm config={config} setConfig={setConfig} />
          ) : isEatonREST ? (
            <EatonRESTConfigForm config={config} setConfig={setConfig} />
          ) : isSNMPTrap ? (
            <SNMPTrapConfigForm config={config} setConfig={setConfig} />
          ) : isUbiquiti ? (
            <UbiquitiConfigForm config={config} setConfig={setConfig} />
          ) : Object.keys(config).length === 0 ? (
            <p className="text-gray-500 text-center py-8">No configuration options available</p>
          ) : (
            <GenericConfigForm config={config} setConfig={setConfig} />
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

export { AxisConfigForm, MilestoneConfigForm, CradlepointConfigForm, CiscoASAConfigForm, EatonRESTConfigForm, SNMPTrapConfigForm, UbiquitiConfigForm, GenericConfigForm };
