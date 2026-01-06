import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, TestTube, Database } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

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

  // Load current settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetchApi('/system/v1/settings/database');
        if (response.data) {
          setSettings(prev => ({ ...prev, ...response.data }));
        }
      } catch (err) {
        // Use defaults if API not available
      }
    };
    loadSettings();
  }, []);

  const testConnection = async () => {
    setTesting(true);
    setMessage(null);
    try {
      const response = await fetchApi('/system/v1/settings/database/test', { method: 'POST' });
      if (response.success) {
        setMessage({ type: 'success', text: 'Database connection successful' });
      } else {
        setMessage({ type: 'error', text: response.error || 'Connection failed' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Connection test failed' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Database Settings</h2>
          <p className="text-xs text-gray-500">Configure PostgreSQL database connection</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            <Save className="w-3.5 h-3.5" />
            Save
          </button>
        </div>
      </div>

      <div className="p-5">
        {message && (
          <div className={`mb-4 p-2 rounded text-xs ${
            message.type === 'success' 
              ? 'bg-green-50 border border-green-200 text-green-700'
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}>
            {message.text}
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Host</label>
            <input
              type="text"
              value={settings.db_host}
              onChange={(e) => setSettings({ ...settings, db_host: e.target.value })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Port</label>
            <input
              type="number"
              value={settings.db_port}
              onChange={(e) => setSettings({ ...settings, db_port: parseInt(e.target.value) })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Database</label>
            <input
              type="text"
              value={settings.db_name}
              onChange={(e) => setSettings({ ...settings, db_name: e.target.value })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={settings.db_username}
              onChange={(e) => setSettings({ ...settings, db_username: e.target.value })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={settings.db_password}
              onChange={(e) => setSettings({ ...settings, db_password: e.target.value })}
              placeholder="••••••••"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">SSL Mode</label>
            <select
              value={settings.db_ssl_mode}
              onChange={(e) => setSettings({ ...settings, db_ssl_mode: e.target.value })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            >
              <option value="disable">Disable</option>
              <option value="allow">Allow</option>
              <option value="prefer">Prefer</option>
              <option value="require">Require</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-6 pt-4 border-t border-gray-200">
          <div className="flex-1">
            <span className="text-xs font-medium text-gray-700">Connection Pool</span>
            <div className="flex items-center gap-4 mt-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Min:</label>
                <input
                  type="number"
                  value={settings.pool_min}
                  onChange={(e) => setSettings({ ...settings, pool_min: parseInt(e.target.value) })}
                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Max:</label>
                <input
                  type="number"
                  value={settings.pool_max}
                  onChange={(e) => setSettings({ ...settings, pool_max: parseInt(e.target.value) })}
                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Timeout:</label>
                <input
                  type="number"
                  value={settings.connection_timeout}
                  onChange={(e) => setSettings({ ...settings, connection_timeout: parseInt(e.target.value) })}
                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-xs text-gray-400">sec</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={testConnection}
              disabled={testing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              <TestTube className="w-3.5 h-3.5" />
              {testing ? 'Testing...' : 'Test'}
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
              <Database className="w-3.5 h-3.5" />
              Migrate
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DatabaseSettings;
