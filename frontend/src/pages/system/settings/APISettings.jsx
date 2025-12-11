import React, { useState } from 'react';
import { Save, RotateCcw, Plus, Trash2, Copy, Eye, EyeOff } from 'lucide-react';

export function APISettings() {
  const [settings, setSettings] = useState({
    bind_address: '0.0.0.0',
    port: 5000,
    workers: 4,
    timeout: 120,
    cors_origins: '*',
    cors_credentials: true,
    rate_limit_enabled: true,
    rate_limit_requests: 100,
    rate_limit_burst: 20,
  });
  
  const [apiKeys, setApiKeys] = useState([
    { id: 1, name: 'Frontend', key: 'sk_live_xxxx...4f2a', created: '2025-12-01' },
    { id: 2, name: 'External API', key: 'sk_live_xxxx...8b3c', created: '2025-12-05' },
  ]);

  const generateApiKey = () => {
    const newKey = {
      id: Date.now(),
      name: 'New API Key',
      key: 'sk_live_' + Math.random().toString(36).substring(2, 15),
      created: new Date().toISOString().split('T')[0],
    };
    setApiKeys([...apiKeys, newKey]);
  };

  const revokeKey = (id) => {
    if (window.confirm('Are you sure you want to revoke this API key?')) {
      setApiKeys(apiKeys.filter(k => k.id !== id));
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">API Settings</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure API server and access control
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Server Configuration */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Server Configuration</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Bind Address</label>
                <input
                  type="text"
                  value={settings.bind_address}
                  onChange={(e) => setSettings({ ...settings, bind_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
                <input
                  type="number"
                  value={settings.port}
                  onChange={(e) => setSettings({ ...settings, port: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Workers</label>
                <input
                  type="number"
                  value={settings.workers}
                  onChange={(e) => setSettings({ ...settings, workers: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timeout (s)</label>
                <input
                  type="number"
                  value={settings.timeout}
                  onChange={(e) => setSettings({ ...settings, timeout: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* CORS Settings */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">CORS Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Allowed Origins</label>
                <input
                  type="text"
                  value={settings.cors_origins}
                  onChange={(e) => setSettings({ ...settings, cors_origins: e.target.value })}
                  placeholder="* or comma-separated origins"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">Use * for all origins or specify comma-separated list</p>
              </div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.cors_credentials}
                  onChange={(e) => setSettings({ ...settings, cors_credentials: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm font-medium text-gray-700">Allow Credentials</span>
              </label>
            </div>
          </div>

          {/* Rate Limiting */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Rate Limiting</h3>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.rate_limit_enabled}
                  onChange={(e) => setSettings({ ...settings, rate_limit_enabled: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm font-medium text-gray-700">Enable Rate Limiting</span>
              </label>
              {settings.rate_limit_enabled && (
                <div className="grid grid-cols-2 gap-4 ml-7">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Requests per Minute</label>
                    <input
                      type="number"
                      value={settings.rate_limit_requests}
                      onChange={(e) => setSettings({ ...settings, rate_limit_requests: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Burst Limit</label>
                    <input
                      type="number"
                      value={settings.rate_limit_burst}
                      onChange={(e) => setSettings({ ...settings, rate_limit_burst: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* API Keys */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900">API Keys</h3>
              <button
                onClick={generateApiKey}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50"
              >
                <Plus className="w-3 h-3" />
                Generate New Key
              </button>
            </div>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Key</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Created</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {apiKeys.map((key) => (
                    <tr key={key.id}>
                      <td className="px-4 py-2 font-medium text-gray-900">{key.name}</td>
                      <td className="px-4 py-2 font-mono text-gray-600">{key.key}</td>
                      <td className="px-4 py-2 text-gray-600">{key.created}</td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => revokeKey(key.id)}
                          className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded"
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl flex items-center justify-end gap-2">
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default APISettings;
