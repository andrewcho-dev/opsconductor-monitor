import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, Plus, Trash2, TestTube } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function NetworkSettings() {
  const [settings, setSettings] = useState({
    discovery_networks: ['10.127.0.0/24'],
    ping_timeout: 2,
    ping_retries: 3,
    concurrent_pings: 50,
    snmp_community: '',
    snmp_version: 'v2c',
    snmp_port: 161,
  });
  const [newNetwork, setNewNetwork] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/get_settings');
      if (data) {
        setSettings(prev => ({
          ...prev,
          discovery_networks: data.network ? [data.network] : prev.discovery_networks,
          ping_timeout: data.ping_timeout || prev.ping_timeout,
          ping_retries: data.ping_retries || prev.ping_retries,
          concurrent_pings: data.concurrent_pings || prev.concurrent_pings,
          snmp_community: data.snmp_community || prev.snmp_community,
        }));
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);
      await fetchApi('/save_settings', {
        method: 'POST',
        body: JSON.stringify({
          network: settings.discovery_networks[0],
          ping_timeout: settings.ping_timeout,
          ping_retries: settings.ping_retries,
          concurrent_pings: settings.concurrent_pings,
          snmp_community: settings.snmp_community,
        }),
      });
      setMessage({ type: 'success', text: 'Network settings saved successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const addNetwork = () => {
    if (newNetwork && !settings.discovery_networks.includes(newNetwork)) {
      setSettings({
        ...settings,
        discovery_networks: [...settings.discovery_networks, newNetwork]
      });
      setNewNetwork('');
    }
  };

  const removeNetwork = (network) => {
    setSettings({
      ...settings,
      discovery_networks: settings.discovery_networks.filter(n => n !== network)
    });
  };

  const testPing = async () => {
    try {
      setTesting(true);
      setMessage(null);
      // Test ping to first IP in network
      const network = settings.discovery_networks[0];
      const baseIp = network.split('/')[0].split('.').slice(0, 3).join('.') + '.1';
      
      const response = await fetch('/ping_device', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip_address: baseIp }),
      });
      const data = await response.json();
      
      if (data.status === 'online') {
        setMessage({ type: 'success', text: `Ping test successful: ${baseIp} is reachable` });
      } else {
        setMessage({ type: 'warning', text: `Ping test: ${baseIp} is not reachable` });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Ping test failed: ${err.message}` });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Network Settings</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure network discovery and connectivity settings
          </p>
        </div>

        <div className="p-6 space-y-6">
          {message && (
            <div className={`p-3 rounded-lg text-sm ${
              message.type === 'success' 
                ? 'bg-green-50 border border-green-200 text-green-800'
                : message.type === 'warning'
                ? 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}>
              {message.text}
            </div>
          )}

          {/* Discovery Networks */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Discovery Networks
            </label>
            <div className="space-y-2 mb-2">
              {settings.discovery_networks.map((network) => (
                <div key={network} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={network}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                  />
                  <button
                    onClick={() => removeNetwork(network)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    title="Remove network"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newNetwork}
                onChange={(e) => setNewNetwork(e.target.value)}
                placeholder="e.g., 192.168.1.0/24"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={addNetwork}
                className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50"
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              CIDR notation networks to scan during discovery
            </p>
          </div>

          {/* Ping Settings */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Ping Settings</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timeout (seconds)
                </label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={settings.ping_timeout}
                  onChange={(e) => setSettings({ ...settings, ping_timeout: parseInt(e.target.value) || 2 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Retry Count
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={settings.ping_retries}
                  onChange={(e) => setSettings({ ...settings, ping_retries: parseInt(e.target.value) || 3 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Concurrent Pings
                </label>
                <input
                  type="number"
                  min="1"
                  max="200"
                  value={settings.concurrent_pings}
                  onChange={(e) => setSettings({ ...settings, concurrent_pings: parseInt(e.target.value) || 50 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* SNMP Settings */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">SNMP Settings</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Community String
                </label>
                <input
                  type="password"
                  value={settings.snmp_community}
                  onChange={(e) => setSettings({ ...settings, snmp_community: e.target.value })}
                  placeholder="Enter SNMP community string"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Version
                </label>
                <select
                  value={settings.snmp_version}
                  onChange={(e) => setSettings({ ...settings, snmp_version: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="v1">v1</option>
                  <option value="v2c">v2c</option>
                  <option value="v3">v3</option>
                </select>
              </div>
            </div>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Port
              </label>
              <input
                type="number"
                value={settings.snmp_port}
                onChange={(e) => setSettings({ ...settings, snmp_port: parseInt(e.target.value) || 161 })}
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl flex items-center justify-between">
          <button
            onClick={testPing}
            disabled={testing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <TestTube className="w-4 h-4" />
            {testing ? 'Testing...' : 'Test Connectivity'}
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={loadSettings}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default NetworkSettings;
