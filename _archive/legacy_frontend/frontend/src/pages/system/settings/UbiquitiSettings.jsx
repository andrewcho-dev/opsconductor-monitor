import { useState, useEffect } from 'react';
import { 
  Radio, 
  Save, 
  TestTube, 
  RefreshCw, 
  CheckCircle, 
  XCircle,
  Eye,
  EyeOff,
  AlertTriangle,
  Wifi,
  WifiOff,
  Plus,
  Trash2,
  Upload
} from 'lucide-react';
import { fetchApi } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export default function UbiquitiSettings() {
  const { getAuthHeader } = useAuth();
  const [settings, setSettings] = useState({
    default_username: 'ubnt',
    default_password: '',
    enabled: false,
    poll_interval: 60,
    targets: [],
    thresholds: {
      cpu_warning: 80,
      memory_warning: 80,
      signal_warning: -70,
    }
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState(null);
  const [newDevice, setNewDevice] = useState({ ip: '', name: '', username: '', password: '' });
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [bulkImportText, setBulkImportText] = useState('');

  useEffect(() => {
    fetchSettings();
    fetchStatus();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await fetchApi('/integrations/v1/ubiquiti/settings', { headers: getAuthHeader() });
      if (data.success) {
        setSettings(prev => ({ ...prev, ...data.data }));
      }
    } catch (error) {
      console.error('Error fetching Ubiquiti settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const data = await fetchApi('/integrations/v1/ubiquiti/status', { headers: getAuthHeader() });
      if (data.success) {
        setStatus(data.data);
      }
    } catch (error) {
      console.error('Error fetching Ubiquiti status:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await fetchApi('/integrations/v1/ubiquiti/settings', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (data.success) {
        setTestResult({ success: true, message: 'Settings saved successfully' });
        setTimeout(() => setTestResult(null), 3000);
      } else {
        setTestResult({ success: false, message: data.error || 'Failed to save settings' });
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const data = await fetchApi('/integrations/v1/ubiquiti/test', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (data.success && data.data?.success) {
        setTestResult({ 
          success: true, 
          message: data.data.message || 'Connected to devices',
          details: data.data.details
        });
        setStatus({ connected: true, ...data.data.details });
      } else {
        setTestResult({ 
          success: false, 
          message: data.data?.message || data.error || 'Connection failed'
        });
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setTesting(false);
    }
  };

  const addDevice = () => {
    if (!newDevice.ip) return;
    setSettings(prev => ({
      ...prev,
      targets: [...(prev.targets || []), { ...newDevice }]
    }));
    setNewDevice({ ip: '', name: '', username: '', password: '' });
  };

  const removeDevice = (index) => {
    setSettings(prev => ({
      ...prev,
      targets: prev.targets.filter((_, i) => i !== index)
    }));
  };

  const handleBulkImport = () => {
    const lines = bulkImportText.trim().split('\n').filter(line => line.trim());
    const newTargets = [];
    
    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      if (idx === 0 && (trimmed.toLowerCase().includes('ip') || trimmed.toLowerCase().includes('address'))) return;
      
      const parts = trimmed.split(/[,\t]/).map(p => p.trim());
      const ip = parts[0];
      const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (!ipRegex.test(ip)) return;
      
      newTargets.push({
        ip: ip,
        name: parts[1] || '',
        username: parts[2] || '',
        password: parts[3] || '',
      });
    });

    if (newTargets.length > 0) {
      const existingIPs = new Set((settings.targets || []).map(t => t.ip));
      const uniqueNew = newTargets.filter(t => !existingIPs.has(t.ip));
      setSettings(prev => ({
        ...prev,
        targets: [...(prev.targets || []), ...uniqueNew]
      }));
      setBulkImportText('');
      setShowBulkImport(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Radio className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Ubiquiti Access Points</h2>
            <p className="text-sm text-gray-500">Poll individual Ubiquiti UniFi devices directly</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleTest}
            disabled={testing || (settings.targets || []).length === 0}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            {testing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <TestTube className="w-4 h-4" />
            )}
            Test Connection
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Settings
          </button>
        </div>
      </div>

      {/* Test Result */}
      {testResult && (
        <div className={`p-4 rounded-lg flex items-start gap-3 ${
          testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          {testResult.success ? (
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className={`font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
              {testResult.message}
            </p>
            {testResult.details && (
              <p className="text-sm text-green-700 mt-1">
                Success: {testResult.details.success || 0}, Failed: {testResult.details.failed || 0}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Connection Status */}
      {status && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Connection Status</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2">
              {status.connected ? (
                <Wifi className="w-4 h-4 text-green-500" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <span className="text-sm text-gray-600">
                {status.connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {status.device_count !== undefined && (
              <div className="text-sm text-gray-600">
                <span className="text-gray-400">Devices:</span> {status.device_count}
              </div>
            )}
            {status.last_poll && (
              <div className="text-sm text-gray-600">
                <span className="text-gray-400">Last Poll:</span> {new Date(status.last_poll).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Settings Form */}
      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
        {/* Enable Toggle */}
        <div className="p-4 flex items-center justify-between">
          <div>
            <label className="text-sm font-medium text-gray-900">Enable Ubiquiti Monitoring</label>
            <p className="text-sm text-gray-500">Enable or disable device monitoring and alerts</p>
          </div>
          <button
            onClick={() => setSettings(prev => ({ ...prev, enabled: !prev.enabled }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.enabled ? 'bg-blue-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                settings.enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Default Credentials */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-3">Default Credentials</label>
          <p className="text-sm text-gray-500 mb-3">Used for devices without individual credentials</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Username</label>
              <input
                type="text"
                value={settings.default_username || ''}
                onChange={(e) => setSettings(prev => ({ ...prev, default_username: e.target.value }))}
                placeholder="ubnt"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={settings.default_password || ''}
                  onChange={(e) => setSettings(prev => ({ ...prev, default_password: e.target.value }))}
                  placeholder="Default password"
                  className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Poll Interval */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">Poll Interval (seconds)</label>
          <input
            type="number"
            min="30"
            max="3600"
            value={settings.poll_interval}
            onChange={(e) => setSettings(prev => ({ ...prev, poll_interval: parseInt(e.target.value) || 60 }))}
            className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-sm text-gray-500">How often to poll devices (minimum 30s)</p>
        </div>

        {/* Thresholds */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-3">Alert Thresholds</label>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">CPU Warning (%)</label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.thresholds?.cpu_warning || 80}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  thresholds: { ...prev.thresholds, cpu_warning: parseInt(e.target.value) || 80 }
                }))}
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Memory Warning (%)</label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.thresholds?.memory_warning || 80}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  thresholds: { ...prev.thresholds, memory_warning: parseInt(e.target.value) || 80 }
                }))}
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Signal Warning (dBm)</label>
              <input
                type="number"
                min="-100"
                max="0"
                value={settings.thresholds?.signal_warning || -70}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  thresholds: { ...prev.thresholds, signal_warning: parseInt(e.target.value) || -70 }
                }))}
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <p className="mt-2 text-sm text-gray-500">Generate alerts when resource usage exceeds these thresholds</p>
        </div>
      </div>

      {/* Device List */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-900">
            Devices ({(settings.targets || []).length})
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => setShowBulkImport(!showBulkImport)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
            >
              <Upload className="w-4 h-4" />
              Bulk Import
            </button>
            {(settings.targets || []).length > 0 && (
              <button
                onClick={() => setSettings(prev => ({ ...prev, targets: [] }))}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
              >
                <Trash2 className="w-4 h-4" />
                Clear All
              </button>
            )}
          </div>
        </div>

        {/* Bulk Import */}
        {showBulkImport && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-700 mb-2">
              Paste device list (one per line). Format: IP,Name,Username,Password (last two optional)
            </p>
            <textarea
              value={bulkImportText}
              onChange={(e) => setBulkImportText(e.target.value)}
              placeholder="10.1.2.3,AP-Office&#10;10.1.2.4,AP-Warehouse,admin,secret"
              rows={5}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
            />
            <button
              onClick={handleBulkImport}
              disabled={!bulkImportText.trim()}
              className="mt-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Import Devices
            </button>
          </div>
        )}

        {/* Device List */}
        {(settings.targets || []).length > 0 && (
          <div className="mb-4 max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
            {(settings.targets || []).map((device, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 border-b border-gray-100 last:border-0">
                <div>
                  <span className="font-mono text-sm text-gray-700">{device.ip}</span>
                  {device.name && <span className="text-gray-500 ml-2">({device.name})</span>}
                  {device.username && <span className="text-blue-500 ml-2 text-xs">[custom auth]</span>}
                </div>
                <button
                  onClick={() => removeDevice(idx)}
                  className="text-red-500 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add Single Device */}
        <div className="grid grid-cols-5 gap-2">
          <input
            type="text"
            placeholder="IP Address"
            value={newDevice.ip}
            onChange={(e) => setNewDevice(prev => ({ ...prev, ip: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <input
            type="text"
            placeholder="Name"
            value={newDevice.name}
            onChange={(e) => setNewDevice(prev => ({ ...prev, name: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <input
            type="text"
            placeholder="User (opt)"
            value={newDevice.username}
            onChange={(e) => setNewDevice(prev => ({ ...prev, username: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <input
            type="password"
            placeholder="Pass (opt)"
            value={newDevice.password}
            onChange={(e) => setNewDevice(prev => ({ ...prev, password: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <button
            onClick={addDevice}
            disabled={!newDevice.ip}
            className="flex items-center justify-center gap-1 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
        <p className="mt-2 text-sm text-gray-500">Leave username/password empty to use defaults</p>
      </div>

      {/* Alert Types Info */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="text-sm font-medium text-gray-900">Monitored Alert Types</h3>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          The connector polls devices directly via their local HTTP/HTTPS interface.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {[
            { type: 'device_offline', desc: 'Device unreachable' },
            { type: 'high_cpu', desc: 'CPU exceeds threshold' },
            { type: 'high_memory', desc: 'Memory exceeds threshold' },
            { type: 'signal_degraded', desc: 'Signal below threshold' },
          ].map(item => (
            <div key={item.type} className="bg-gray-50 rounded p-2">
              <p className="text-xs font-mono text-gray-700">{item.type}</p>
              <p className="text-xs text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
