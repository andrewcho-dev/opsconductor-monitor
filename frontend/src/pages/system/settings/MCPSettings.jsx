import { useState, useEffect } from 'react';
import { 
  Network, 
  Save, 
  TestTube, 
  RefreshCw, 
  CheckCircle, 
  XCircle,
  Eye,
  EyeOff,
  ExternalLink,
  Server,
  Cpu,
  Cable,
  HardDrive,
  ArrowRightLeft
} from 'lucide-react';
import { fetchApi } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export default function MCPSettings() {
  const { getAuthHeader } = useAuth();
  const [settings, setSettings] = useState({
    url: '',
    username: '',
    password: '',
    verify_ssl: false
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [summary, setSummary] = useState(null);
  const [syncing, setSyncing] = useState({ devices: false, equipment: false });
  const [syncResult, setSyncResult] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await fetchApi('/api/mcp/settings', { headers: getAuthHeader() });
      if (data.success) {
        setSettings(prev => ({ 
          ...prev, 
          ...data.data,
          password: data.data.password_configured ? '••••••••' : ''
        }));
      }
    } catch (error) {
      console.error('Error fetching MCP settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await fetchApi('/api/mcp/settings', {
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
      const data = await fetchApi('/api/mcp/test', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (data.success && data.data.success) {
        setTestResult({ 
          success: true, 
          message: 'Connected to Ciena MCP'
        });
        setSummary(data.data.summary);
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

  const handleSyncDevices = async () => {
    setSyncing(prev => ({ ...prev, devices: true }));
    setSyncResult(null);
    try {
      const data = await fetchApi('/api/mcp/sync/netbox', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ create_missing: false })
      });
      if (data.success) {
        setSyncResult({
          type: 'devices',
          success: true,
          message: `Synced ${data.data.updated} devices, ${data.data.created} created, ${data.data.skipped} skipped`
        });
      } else {
        setSyncResult({ type: 'devices', success: false, message: data.error || 'Sync failed' });
      }
    } catch (error) {
      setSyncResult({ type: 'devices', success: false, message: error.message });
    } finally {
      setSyncing(prev => ({ ...prev, devices: false }));
    }
  };

  const handleSyncEquipment = async () => {
    setSyncing(prev => ({ ...prev, equipment: true }));
    setSyncResult(null);
    try {
      const data = await fetchApi('/api/mcp/sync/equipment', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
      });
      if (data.success) {
        setSyncResult({
          type: 'equipment',
          success: true,
          message: `Synced ${data.data.created} inventory items, ${data.data.updated} updated, ${data.data.skipped} skipped`
        });
      } else {
        setSyncResult({ type: 'equipment', success: false, message: data.error || 'Sync failed' });
      }
    } catch (error) {
      setSyncResult({ type: 'equipment', success: false, message: error.message });
    } finally {
      setSyncing(prev => ({ ...prev, equipment: false }));
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
          <div className="p-2 bg-indigo-100 rounded-lg">
            <Network className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Ciena MCP Integration</h2>
            <p className="text-sm text-gray-500">Connect to Ciena MCP for device inventory and equipment tracking</p>
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
          <p className={`font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
            {testResult.message}
          </p>
        </div>
      )}

      {/* Connection Summary */}
      {summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">MCP Inventory Summary</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-indigo-50 rounded-lg p-3 text-center">
              <Server className="w-6 h-6 text-indigo-500 mx-auto mb-1" />
              <p className="text-2xl font-semibold text-indigo-600">{summary.devices || 0}</p>
              <p className="text-sm text-gray-500">Devices</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-3 text-center">
              <Cpu className="w-6 h-6 text-purple-500 mx-auto mb-1" />
              <p className="text-2xl font-semibold text-purple-600">{summary.equipment || 0}</p>
              <p className="text-sm text-gray-500">Equipment/SFPs</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <Cable className="w-6 h-6 text-blue-500 mx-auto mb-1" />
              <p className="text-2xl font-semibold text-blue-600">{summary.links || 0}</p>
              <p className="text-sm text-gray-500">Network Links</p>
            </div>
          </div>
        </div>
      )}

      {/* Settings Form */}
      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
        {/* MCP URL */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">MCP Server URL</label>
          <input
            type="url"
            value={settings.url}
            onChange={(e) => setSettings(prev => ({ ...prev, url: e.target.value }))}
            placeholder="https://mcp.example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-sm text-gray-500">The URL of your Ciena MCP server (without trailing slash)</p>
        </div>

        {/* Username */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">Username</label>
          <input
            type="text"
            value={settings.username}
            onChange={(e) => setSettings(prev => ({ ...prev, username: e.target.value }))}
            placeholder="Enter MCP username"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Password */}
        <div className="p-4">
          <label className="block text-sm font-medium text-gray-900 mb-1">Password</label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={settings.password}
              onChange={(e) => setSettings(prev => ({ ...prev, password: e.target.value }))}
              placeholder="Enter password"
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

      {/* NetBox Sync */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-4">
          <ArrowRightLeft className="w-5 h-5 text-blue-500" />
          <h3 className="text-sm font-medium text-gray-900">Sync to NetBox</h3>
        </div>
        
        <p className="text-sm text-gray-600 mb-4">
          Sync MCP inventory data to NetBox. Devices will be updated with serial numbers and software versions.
          Equipment (SFPs, cards) will be added as inventory items.
        </p>

        {/* Sync Result */}
        {syncResult && (
          <div className={`mb-4 p-3 rounded-lg flex items-start gap-2 ${
            syncResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          }`}>
            {syncResult.success ? (
              <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <p className={`text-sm ${syncResult.success ? 'text-green-700' : 'text-red-700'}`}>
              {syncResult.message}
            </p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleSyncDevices}
            disabled={syncing.devices || !summary}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {syncing.devices ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Server className="w-4 h-4" />
            )}
            Sync Devices ({summary?.devices || 0})
          </button>
          <button
            onClick={handleSyncEquipment}
            disabled={syncing.equipment || !summary}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {syncing.equipment ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <HardDrive className="w-4 h-4" />
            )}
            Sync Equipment ({summary?.equipment || 0})
          </button>
        </div>
      </div>

      {/* API Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-800 mb-2">Available MCP Data</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• <strong>Devices:</strong> Managed network elements with serial numbers, software versions</li>
          <li>• <strong>Equipment:</strong> SFPs, cards, and pluggable modules with part numbers</li>
          <li>• <strong>Links:</strong> Network topology and connections between devices</li>
        </ul>
        <p className="mt-3 text-sm text-blue-600">
          Use the workflow builder to create automated sync workflows with MCP data.
        </p>
      </div>
    </div>
  );
}
