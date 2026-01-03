import { useState, useEffect } from 'react';
import { 
  Activity, 
  Save, 
  TestTube, 
  RefreshCw, 
  CheckCircle, 
  XCircle,
  Eye,
  EyeOff,
  ExternalLink,
  AlertTriangle,
  Server,
  Gauge
} from 'lucide-react';
import { fetchApi } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export default function PRTGSettings() {
  const { getAuthHeader } = useAuth();
  const [settings, setSettings] = useState({
    url: '',
    api_token: '',
    username: '',
    passhash: '',
    verify_ssl: true,
    enabled: false,
    sync_interval: 300
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showToken, setShowToken] = useState(false);
  const [status, setStatus] = useState(null);
  const [syncPreview, setSyncPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    fetchSettings();
    fetchStatus();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await fetchApi('/api/prtg/settings', { headers: getAuthHeader() });
      if (data.success) {
        setSettings(prev => ({ ...prev, ...data.data }));
      }
    } catch (error) {
      console.error('Error fetching PRTG settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const data = await fetchApi('/api/prtg/status', { headers: getAuthHeader() });
      setStatus(data.data);
    } catch (error) {
      console.error('Error fetching PRTG status:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await fetchApi('/api/prtg/settings', {
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
      const data = await fetchApi('/api/prtg/test-connection', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (data.success && data.data.connected) {
        setTestResult({ 
          success: true, 
          message: `Connected to PRTG ${data.data.version || ''}`,
          details: data.data
        });
        setStatus(data.data);
      } else {
        setTestResult({ 
          success: false, 
          message: data.data?.error || data.error || 'Connection failed'
        });
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setTesting(false);
    }
  };

  const handlePreviewSync = async () => {
    setLoadingPreview(true);
    try {
      const data = await fetchApi('/api/prtg/sync/preview', { headers: getAuthHeader() });
      if (data.success) {
        setSyncPreview(data.data);
      }
    } catch (error) {
      console.error('Error fetching sync preview:', error);
    } finally {
      setLoadingPreview(false);
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
          <div className="p-2 bg-green-100 rounded-lg">
            <Activity className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">PRTG Integration</h2>
            <p className="text-sm text-gray-500">Connect to PRTG Network Monitor for alerts and device sync</p>
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
                Alarms: {testResult.details.alarms || 0} | 
                New Alarms: {testResult.details.new_alarms || 0}
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
              <div className={`w-2 h-2 rounded-full ${status.connected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-600">
                {status.connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {status.version && (
              <div className="text-sm text-gray-600">
                <span className="text-gray-400">Version:</span> {status.version}
              </div>
            )}
            {status.alarms !== undefined && (
              <div className="text-sm text-gray-600">
                <span className="text-gray-400">Active Alarms:</span> {status.alarms}
              </div>
            )}
            {status.new_alarms !== undefined && (
              <div className="text-sm text-gray-600">
                <span className="text-gray-400">New Alarms:</span> {status.new_alarms}
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
            <label className="text-sm font-medium text-gray-900">Enable PRTG Integration</label>
            <p className="text-sm text-gray-500">Enable or disable PRTG integration features</p>
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

        {/* PRTG URL */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">PRTG Server URL</label>
          <input
            type="url"
            value={settings.url}
            onChange={(e) => setSettings(prev => ({ ...prev, url: e.target.value }))}
            placeholder="https://prtg.example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-sm text-gray-500">The URL of your PRTG server (without trailing slash)</p>
        </div>

        {/* API Token */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">API Token (Recommended)</label>
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
            Generate in PRTG: Setup → Account Settings → API Keys
          </p>
        </div>

        {/* Alternative: Username/Passhash */}
        <div className="p-4 bg-gray-50">
          <p className="text-sm font-medium text-gray-700 mb-3">Alternative Authentication (Legacy)</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Username</label>
              <input
                type="text"
                value={settings.username}
                onChange={(e) => setSettings(prev => ({ ...prev, username: e.target.value }))}
                placeholder="prtgadmin"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Passhash</label>
              <input
                type="password"
                value={settings.passhash}
                onChange={(e) => setSettings(prev => ({ ...prev, passhash: e.target.value }))}
                placeholder="Enter passhash"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Find passhash in PRTG: Setup → Account Settings → Show Passhash
          </p>
        </div>

        {/* SSL Verification */}
        <div className="p-4 flex items-center justify-between">
          <div>
            <label className="text-sm font-medium text-gray-900">Verify SSL Certificate</label>
            <p className="text-sm text-gray-500">Disable if using self-signed certificates</p>
          </div>
          <button
            onClick={() => setSettings(prev => ({ ...prev, verify_ssl: !prev.verify_ssl }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.verify_ssl ? 'bg-blue-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                settings.verify_ssl ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Webhook Configuration */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="text-sm font-medium text-gray-900">Webhook Configuration for Real-Time Alerts</h3>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          To receive real-time alerts from PRTG, configure an HTTP notification in PRTG to send alerts to:
        </p>
        <div className="bg-gray-100 rounded-lg p-3 font-mono text-sm break-all">
          {window.location.origin}/api/prtg/webhook
        </div>
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm font-medium text-blue-800 mb-2">PRTG Setup Instructions:</p>
          <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
            <li>Go to PRTG → Setup → Account Settings → Notification Templates</li>
            <li>Click "Add Notification Template"</li>
            <li>Select "Execute HTTP Action"</li>
            <li>Set URL to the webhook URL above</li>
            <li>Set Method to POST</li>
            <li>Add POST data with sensor variables (see documentation)</li>
            <li>Assign this notification to sensors/devices you want to monitor</li>
          </ol>
        </div>
      </div>

      {/* NetBox Sync Preview */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-blue-500" />
            <h3 className="text-sm font-medium text-gray-900">NetBox Sync Preview</h3>
          </div>
          <button
            onClick={handlePreviewSync}
            disabled={loadingPreview || !status?.connected}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
          >
            {loadingPreview ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
            Preview Sync
          </button>
        </div>

        {syncPreview && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <Server className="w-6 h-6 text-gray-400 mx-auto mb-1" />
                <p className="text-2xl font-semibold text-gray-900">{syncPreview.total_prtg_devices}</p>
                <p className="text-sm text-gray-500">PRTG Devices</p>
              </div>
              <div className="bg-green-50 rounded-lg p-3 text-center">
                <CheckCircle className="w-6 h-6 text-green-500 mx-auto mb-1" />
                <p className="text-2xl font-semibold text-green-600">{syncPreview.existing_in_netbox}</p>
                <p className="text-sm text-gray-500">In NetBox</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <Gauge className="w-6 h-6 text-blue-500 mx-auto mb-1" />
                <p className="text-2xl font-semibold text-blue-600">{syncPreview.to_create}</p>
                <p className="text-sm text-gray-500">To Create</p>
              </div>
            </div>

            {syncPreview.devices_to_create?.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Devices to Create in NetBox:</p>
                <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Name</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Host</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Group</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {syncPreview.devices_to_create.slice(0, 20).map((device, idx) => (
                        <tr key={idx}>
                          <td className="px-3 py-2 text-sm text-gray-900">{device.name}</td>
                          <td className="px-3 py-2 text-sm text-gray-500">{device.host}</td>
                          <td className="px-3 py-2 text-sm text-gray-500">{device.group}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {syncPreview.devices_to_create.length > 20 && (
                    <p className="px-3 py-2 text-sm text-gray-500 bg-gray-50">
                      ... and {syncPreview.devices_to_create.length - 20} more
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {!syncPreview && !loadingPreview && (
          <p className="text-sm text-gray-500">
            Click "Preview Sync" to see which PRTG devices would be synced to NetBox.
          </p>
        )}
      </div>
    </div>
  );
}
