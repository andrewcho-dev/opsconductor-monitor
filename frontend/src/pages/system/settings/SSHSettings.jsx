import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, Eye, EyeOff, TestTube } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function SSHSettings() {
  const [settings, setSettings] = useState({
    ssh_username: '',
    ssh_password: '',
    ssh_port: 22,
    ssh_timeout: 30,
    ssh_success_status: 'YES',
    ssh_prompt_pattern: '>|#|$',
    ssh_known_hosts_check: false,
    ssh_host_key_algorithm: 'auto',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testIp, setTestIp] = useState('');
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
          ssh_username: data.ssh_username || prev.ssh_username,
          ssh_password: data.ssh_password || prev.ssh_password,
          ssh_port: data.ssh_port || prev.ssh_port,
          ssh_timeout: data.ssh_timeout || prev.ssh_timeout,
          ssh_success_status: data.ssh_success_status || prev.ssh_success_status,
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
          ssh_username: settings.ssh_username,
          ssh_password: settings.ssh_password,
          ssh_port: settings.ssh_port,
          ssh_timeout: settings.ssh_timeout,
          ssh_success_status: settings.ssh_success_status,
        }),
      });
      setMessage({ type: 'success', text: 'SSH settings saved successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const testSSH = async () => {
    if (!testIp) {
      setMessage({ type: 'error', text: 'Please enter an IP address to test' });
      return;
    }
    
    try {
      setTesting(true);
      setMessage(null);
      
      const data = await fetchApi('/test_ssh', {
        method: 'POST',
        body: JSON.stringify({
          ip_address: testIp,
          username: settings.ssh_username,
          password: settings.ssh_password,
          port: settings.ssh_port,
        }),
      });
      
      if (data.success) {
        setMessage({ type: 'success', text: `SSH test successful: Connected to ${testIp}` });
      } else {
        setMessage({ type: 'error', text: `SSH test failed: ${data.error || 'Connection refused'}` });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `SSH test failed: ${err.message}` });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">SSH Settings</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure SSH credentials and connection parameters
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

          {/* Default Credentials */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Default Credentials</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={settings.ssh_username}
                  onChange={(e) => setSettings({ ...settings, ssh_username: e.target.value })}
                  placeholder="Enter SSH username"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={settings.ssh_password}
                    onChange={(e) => setSettings({ ...settings, ssh_password: e.target.value })}
                    placeholder="Enter SSH password"
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-700"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Connection Settings */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Connection Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Port
                </label>
                <input
                  type="number"
                  value={settings.ssh_port}
                  onChange={(e) => setSettings({ ...settings, ssh_port: parseInt(e.target.value) || 22 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timeout (seconds)
                </label>
                <input
                  type="number"
                  min="5"
                  max="120"
                  value={settings.ssh_timeout}
                  onChange={(e) => setSettings({ ...settings, ssh_timeout: parseInt(e.target.value) || 30 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Success Indicators */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Success Indicators</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Success Status Value
                </label>
                <input
                  type="text"
                  value={settings.ssh_success_status}
                  onChange={(e) => setSettings({ ...settings, ssh_success_status: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Value stored in ssh_status when connection succeeds
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Prompt Pattern (regex)
                </label>
                <input
                  type="text"
                  value={settings.ssh_prompt_pattern}
                  onChange={(e) => setSettings({ ...settings, ssh_prompt_pattern: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Regex pattern to detect command prompt
                </p>
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Advanced Options</h3>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.ssh_known_hosts_check}
                  onChange={(e) => setSettings({ ...settings, ssh_known_hosts_check: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <div>
                  <span className="text-sm font-medium text-gray-700">Enable Known Hosts Check</span>
                  <p className="text-xs text-gray-500">Verify host keys against known_hosts file</p>
                </div>
              </label>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Host Key Algorithm
                </label>
                <select
                  value={settings.ssh_host_key_algorithm}
                  onChange={(e) => setSettings({ ...settings, ssh_host_key_algorithm: e.target.value })}
                  className="w-48 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="auto">Auto</option>
                  <option value="ssh-rsa">RSA</option>
                  <option value="ssh-ed25519">Ed25519</option>
                  <option value="ecdsa-sha2-nistp256">ECDSA</option>
                </select>
              </div>
            </div>
          </div>

          {/* Test Connection */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Test Connection</h3>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={testIp}
                onChange={(e) => setTestIp(e.target.value)}
                placeholder="Enter IP address to test"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={testSSH}
                disabled={testing || !testIp}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                <TestTube className="w-4 h-4" />
                {testing ? 'Testing...' : 'Test SSH'}
              </button>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl flex items-center justify-end gap-2">
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
  );
}

export default SSHSettings;
