import React, { useState, useEffect } from 'react';
import { Save, RotateCcw } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function GeneralSettings() {
  const [settings, setSettings] = useState({
    app_name: 'OpsConductor Monitor',
    timezone: 'America/Los_Angeles',
    date_format: 'YYYY-MM-DD',
    theme: 'light',
    auto_refresh_interval: 30,
    session_timeout: 3600,
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/get_settings');
      if (data) {
        setSettings(prev => ({ ...prev, ...data }));
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
        body: JSON.stringify(settings),
      });
      setMessage({ type: 'success', text: 'Settings saved successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">General Settings</h2>
          <p className="text-xs text-gray-500">Configure basic application settings</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadSettings}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? 'Saving...' : 'Save'}
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

        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Application Name</label>
            <input
              type="text"
              value={settings.app_name}
              onChange={(e) => setSettings({ ...settings, app_name: e.target.value })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Timezone</label>
            <select
              value={settings.timezone}
              onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            >
              <option value="America/Los_Angeles">Pacific Time (US)</option>
              <option value="America/Denver">Mountain Time (US)</option>
              <option value="America/Chicago">Central Time (US)</option>
              <option value="America/New_York">Eastern Time (US)</option>
              <option value="UTC">UTC</option>
              <option value="Europe/London">London</option>
              <option value="Europe/Paris">Paris</option>
              <option value="Asia/Tokyo">Tokyo</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Date Format</label>
            <div className="flex gap-3">
              {['YYYY-MM-DD', 'MM/DD/YYYY', 'DD/MM/YYYY'].map((format) => (
                <label key={format} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="date_format"
                    value={format}
                    checked={settings.date_format === format}
                    onChange={(e) => setSettings({ ...settings, date_format: e.target.value })}
                    className="w-3.5 h-3.5 text-blue-600"
                  />
                  <span className="text-xs text-gray-700">{format}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Theme</label>
            <div className="flex gap-3">
              {['light', 'dark', 'system'].map((theme) => (
                <label key={theme} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="theme"
                    value={theme}
                    checked={settings.theme === theme}
                    onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
                    className="w-3.5 h-3.5 text-blue-600"
                  />
                  <span className="text-xs text-gray-700 capitalize">{theme}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Auto Refresh (seconds)</label>
            <input
              type="number"
              min="5"
              max="300"
              value={settings.auto_refresh_interval}
              onChange={(e) => setSettings({ ...settings, auto_refresh_interval: parseInt(e.target.value) || 30 })}
              className="w-24 px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
            <span className="ml-2 text-xs text-gray-500">5-300</span>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Session Timeout (seconds)</label>
            <input
              type="number"
              min="300"
              max="86400"
              value={settings.session_timeout}
              onChange={(e) => setSettings({ ...settings, session_timeout: parseInt(e.target.value) || 3600 })}
              className="w-24 px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            />
            <span className="ml-2 text-xs text-gray-500">300-86400</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GeneralSettings;
