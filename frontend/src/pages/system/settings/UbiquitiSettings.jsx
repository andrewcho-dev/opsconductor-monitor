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
  Server,
  Wifi,
  WifiOff
} from 'lucide-react';
import { fetchApi } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export default function UbiquitiSettings() {
  const { getAuthHeader } = useAuth();
  const [settings, setSettings] = useState({
    url: '',
    api_token: '',
    enabled: false,
    poll_interval: 60,
    include_device_types: [],
    thresholds: {
      cpu_warning: 80,
      memory_warning: 80,
    }
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showToken, setShowToken] = useState(false);
  const [status, setStatus] = useState(null);

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
          message: data.data.message || 'Connected to UISP',
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
            <h2 className="text-lg font-semibold text-gray-900">Ubiquiti UISP Integration</h2>
            <p className="text-sm text-gray-500">Connect to Ubiquiti UISP for device monitoring and alerts</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleTest}
            disabled={testing || !settings.url}
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
                Devices: {testResult.details.device_count || 0}
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
            <label className="text-sm font-medium text-gray-900">Enable Ubiquiti UISP Integration</label>
            <p className="text-sm text-gray-500">Enable or disable UISP monitoring and alerts</p>
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

        {/* UISP URL */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">UISP Server URL</label>
          <input
            type="url"
            value={settings.url}
            onChange={(e) => setSettings(prev => ({ ...prev, url: e.target.value }))}
            placeholder="https://uisp.example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-sm text-gray-500">The URL of your UISP server (without trailing slash)</p>
        </div>

        {/* API Token */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">API Token</label>
          <div className="relative">
            <input
              type={showToken ? 'text' : 'password'}
              value={settings.api_token}
              onChange={(e) => setSettings(prev => ({ ...prev, api_token: e.target.value }))}
              placeholder="Enter API token"
              className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showToken ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Generate in UISP: Settings → Users → Your User → API Tokens
          </p>
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
          <p className="mt-1 text-sm text-gray-500">How often to poll UISP for device status (minimum 30s)</p>
        </div>

        {/* Thresholds */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-3">Alert Thresholds</label>
          <div className="grid grid-cols-2 gap-4">
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
          </div>
          <p className="mt-2 text-sm text-gray-500">Generate alerts when resource usage exceeds these thresholds</p>
        </div>
      </div>

      {/* Alert Types Info */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="text-sm font-medium text-gray-900">Monitored Alert Types</h3>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          The Ubiquiti UISP connector monitors for the following alert types. Configure severity and category mappings in the Alert Normalization settings.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {[
            { type: 'device_offline', desc: 'Device is offline or unreachable' },
            { type: 'device_online', desc: 'Device came back online (clear)' },
            { type: 'high_cpu', desc: 'CPU usage exceeds threshold' },
            { type: 'high_memory', desc: 'Memory usage exceeds threshold' },
            { type: 'signal_degraded', desc: 'Wireless signal below -70 dBm' },
            { type: 'outage', desc: 'Network outage detected' },
            { type: 'firmware_update', desc: 'Firmware update available' },
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
