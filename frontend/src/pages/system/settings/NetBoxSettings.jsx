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
    default_site_id: '',
    default_role_id: '',
    default_device_type_id: '',
  });
  const [lookups, setLookups] = useState({
    sites: [],
    roles: [],
    deviceTypes: [],
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
          default_site_id: res.data.default_site_id || '',
          default_role_id: res.data.default_role_id || '',
          default_device_type_id: res.data.default_device_type_id || '',
        }));
        
        // If configured, load lookups
        if (res.data.url && res.data.token_configured) {
          loadLookups();
        }
      }
    } catch (err) {
      console.error('Failed to load NetBox settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadLookups = async () => {
    try {
      const [sitesRes, rolesRes, typesRes] = await Promise.all([
        fetchApi('/api/netbox/sites', { headers: getAuthHeader() }).catch(() => ({ data: [] })),
        fetchApi('/api/netbox/device-roles', { headers: getAuthHeader() }).catch(() => ({ data: [] })),
        fetchApi('/api/netbox/device-types', { headers: getAuthHeader() }).catch(() => ({ data: [] })),
      ]);
      
      setLookups({
        sites: sitesRes.data || [],
        roles: rolesRes.data || [],
        deviceTypes: typesRes.data || [],
      });
    } catch (err) {
      console.error('Failed to load NetBox lookups:', err);
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
        loadLookups();
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

        {/* Discovery Defaults */}
        <div className="col-span-2 border rounded-lg p-4">
          <span className="text-xs font-semibold text-gray-900 mb-3 block">Discovery Defaults</span>
          <p className="text-xs text-gray-500 mb-3">
            Default values used when discovery jobs create new devices in NetBox.
          </p>
          
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Default Site</label>
              <select
                value={settings.default_site_id}
                onChange={(e) => handleChange('default_site_id', e.target.value)}
                disabled={!canEdit || lookups.sites.length === 0}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
              >
                <option value="">Select site...</option>
                {lookups.sites.map(site => (
                  <option key={site.id} value={site.id}>{site.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Default Role</label>
              <select
                value={settings.default_role_id}
                onChange={(e) => handleChange('default_role_id', e.target.value)}
                disabled={!canEdit || lookups.roles.length === 0}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
              >
                <option value="">Select role...</option>
                {lookups.roles.map(role => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Default Device Type</label>
              <select
                value={settings.default_device_type_id}
                onChange={(e) => handleChange('default_device_type_id', e.target.value)}
                disabled={!canEdit || lookups.deviceTypes.length === 0}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
              >
                <option value="">Select type...</option>
                {lookups.deviceTypes.map(type => (
                  <option key={type.id} value={type.id}>{type.manufacturer?.name} - {type.model}</option>
                ))}
              </select>
            </div>
          </div>
          
          {lookups.sites.length === 0 && settings.url && (
            <p className="mt-3 text-xs text-amber-600">
              Connect to NetBox to load available sites, roles, and device types.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default NetBoxSettings;
