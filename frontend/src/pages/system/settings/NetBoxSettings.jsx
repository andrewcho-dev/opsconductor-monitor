import React, { useState, useEffect } from 'react';
import { 
  Save, RotateCcw, TestTube, Server, Check, AlertTriangle, Loader2, ExternalLink
} from 'lucide-react';
import { fetchApi, cn } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export function NetBoxSettings() {
  const { getAuthHeader, hasPermission } = useAuth();
  const [settings, setSettings] = useState({
    url: '',
    token: '',
    verify_ssl: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  const canEdit = hasPermission('system.settings.edit');

  useEffect(() => { loadSettings(); }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await fetchApi('/api/netbox/settings', { headers: getAuthHeader() });
      if (res.success) {
        setSettings(prev => ({
          ...prev,
          url: res.data.url || '',
          token: res.data.token || '',
          verify_ssl: res.data.verify_ssl !== 'false',
        }));
      }
    } catch (err) {
      console.error('Failed to load NetBox settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
    setMessage(null);
  };

  const handleSave = async () => {
    setMessage(null);
    setSaving(true);
    try {
      const res = await fetchApi('/api/netbox/settings', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.success) {
        setHasChanges(false);
        setMessage({ type: 'success', text: 'Settings saved' });
      } else {
        setMessage({ type: 'error', text: res.error?.message || 'Failed to save' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setConnectionStatus(null);
    try {
      const res = await fetchApi('/api/netbox/test', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: settings.url,
          token: settings.token,
          verify_ssl: settings.verify_ssl,
        })
      });
      
      if (res.success) {
        setConnectionStatus({
          connected: true,
          version: res.data.netbox_version,
        });
        loadLookups();
      } else {
        setConnectionStatus({
          connected: false,
          error: res.error?.message || 'Connection failed',
        });
      }
    } catch (err) {
      setConnectionStatus({
        connected: false,
        error: err.message || 'Connection failed',
      });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-gray-400" /></div>;
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">NetBox Integration</h2>
          <p className="text-xs text-gray-500">Connect to NetBox for device inventory management</p>
        </div>
        <div className="flex items-center gap-2">
          {message && (
            <span className={cn("text-xs px-2 py-1 rounded", message.type === 'success' ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600")}>
              {message.text}
            </span>
          )}
          {canEdit && hasChanges && (
            <>
              <button onClick={loadSettings} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                <RotateCcw className="w-3.5 h-3.5" />Reset
              </button>
              <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}Save
              </button>
            </>
          )}
        </div>
      </div>

      <div className="p-5 grid grid-cols-2 gap-5">
        {/* Connection */}
        <div className="col-span-2 border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-gray-900">Connection</span>
            {connectionStatus && (
              <span className={cn("ml-auto text-xs px-2 py-0.5 rounded-full", connectionStatus.connected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700")}>
                {connectionStatus.connected ? `Connected (v${connectionStatus.version})` : 'Disconnected'}
              </span>
            )}
          </div>
          
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs text-gray-600 mb-1">NetBox URL</label>
              <input
                type="url"
                value={settings.url}
                onChange={(e) => handleChange('url', e.target.value)}
                placeholder="https://netbox.example.com"
                disabled={!canEdit}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleTest}
                disabled={testing || !settings.url}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <TestTube className="w-3.5 h-3.5" />}
                Test
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">API Token</label>
              <input
                type="password"
                value={settings.token}
                onChange={(e) => handleChange('token', e.target.value)}
                placeholder="Enter API token"
                disabled={!canEdit}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="flex items-center gap-2 text-xs text-gray-700">
                <input
                  type="checkbox"
                  checked={settings.verify_ssl}
                  onChange={(e) => handleChange('verify_ssl', e.target.checked)}
                  disabled={!canEdit}
                  className="rounded w-3.5 h-3.5"
                />
                Verify SSL
              </label>
              {settings.url && (
                <a
                  href={`${settings.url}/api/docs/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                >
                  API Docs <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
          
          {connectionStatus && !connectionStatus.connected && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
              {connectionStatus.error}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="col-span-2 border rounded-lg p-4 bg-blue-50 border-blue-200">
          <p className="text-xs text-blue-700">
            <strong>Note:</strong> Discovery jobs will find active devices on your network. 
            Discovered device information (IP, hostname, SNMP data) will be stored locally. 
            You can then manually add devices to NetBox with the correct site, role, and device type.
          </p>
        </div>
      </div>
    </div>
  );
}

export default NetBoxSettings;
