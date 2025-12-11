import React, { useState } from 'react';
import { Save, RotateCcw, TestTube, Database } from 'lucide-react';

export function DatabaseSettings() {
  const [settings, setSettings] = useState({
    db_host: 'localhost',
    db_port: 5432,
    db_name: 'opsconductor',
    db_username: 'postgres',
    db_password: '',
    db_ssl_mode: 'prefer',
    pool_min: 2,
    pool_max: 20,
    connection_timeout: 30,
  });
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState(null);

  const testConnection = async () => {
    setTesting(true);
    setMessage(null);
    // Simulate test
    setTimeout(() => {
      setMessage({ type: 'success', text: 'Database connection successful' });
      setTesting(false);
    }, 1000);
  };

  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Database Settings</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure PostgreSQL database connection
          </p>
        </div>

        <div className="p-6 space-y-6">
          {message && (
            <div className={`p-3 rounded-lg text-sm ${
              message.type === 'success' 
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}>
              {message.text}
            </div>
          )}

          {/* Connection Settings */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-4">PostgreSQL Connection</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Host</label>
                <input
                  type="text"
                  value={settings.db_host}
                  onChange={(e) => setSettings({ ...settings, db_host: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
                <input
                  type="number"
                  value={settings.db_port}
                  onChange={(e) => setSettings({ ...settings, db_port: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Database</label>
                <input
                  type="text"
                  value={settings.db_name}
                  onChange={(e) => setSettings({ ...settings, db_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
                <input
                  type="text"
                  value={settings.db_username}
                  onChange={(e) => setSettings({ ...settings, db_username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
                <input
                  type="password"
                  value={settings.db_password}
                  onChange={(e) => setSettings({ ...settings, db_password: e.target.value })}
                  placeholder="Enter password"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">SSL Mode</label>
                <select
                  value={settings.db_ssl_mode}
                  onChange={(e) => setSettings({ ...settings, db_ssl_mode: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="disable">Disable</option>
                  <option value="allow">Allow</option>
                  <option value="prefer">Prefer</option>
                  <option value="require">Require</option>
                </select>
              </div>
            </div>
          </div>

          {/* Connection Pool */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Connection Pool</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Min Connections</label>
                <input
                  type="number"
                  value={settings.pool_min}
                  onChange={(e) => setSettings({ ...settings, pool_min: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Max Connections</label>
                <input
                  type="number"
                  value={settings.pool_max}
                  onChange={(e) => setSettings({ ...settings, pool_max: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timeout (s)</label>
                <input
                  type="number"
                  value={settings.connection_timeout}
                  onChange={(e) => setSettings({ ...settings, connection_timeout: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Maintenance */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Maintenance</h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={testConnection}
                disabled={testing}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                <TestTube className="w-4 h-4" />
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                <Database className="w-4 h-4" />
                Run Migrations
              </button>
              <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                Vacuum Database
              </button>
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

export default DatabaseSettings;
