import React, { useState, useEffect } from 'react';
import { 
  Save, RotateCcw, FileText, Trash2, Loader2
} from 'lucide-react';
import { fetchApi, cn } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

export function LoggingSettings() {
  const { getAuthHeader, hasPermission } = useAuth();
  const [settings, setSettings] = useState({
    log_level: 'INFO',
    file_logging_enabled: true,
    database_logging_enabled: true,
    json_logging_enabled: true,
    max_file_size_mb: 10,
    backup_count: 10,
    retention_days: 30,
    console_logging_enabled: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [cleaning, setCleaning] = useState(false);
  const [message, setMessage] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  const canEdit = hasPermission('system.settings.edit');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchApi('/system/v1/logging/settings', { headers: getAuthHeader() }).catch(() => null);
      if (res?.success) setSettings(prev => ({ ...prev, ...res.data }));
    } catch (err) {
      console.error('Failed to load logging settings:', err);
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
      const res = await fetchApi('/system/v1/logging/settings', {
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

  const handleCleanup = async () => {
    if (!confirm(`Delete logs older than ${settings.retention_days} days?`)) return;
    setCleaning(true);
    try {
      const res = await fetchApi('/system/v1/logs/cleanup', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ retention_days: settings.retention_days })
      });
      setMessage({ type: res.success ? 'success' : 'error', text: res.success ? `Cleaned ${res.data?.deleted || 0} entries` : 'Cleanup failed' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Cleanup failed' });
    } finally {
      setCleaning(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-gray-400" /></div>;
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Logging Settings</h2>
          <p className="text-xs text-gray-500">Configure log levels, outputs, and retention</p>
        </div>
        <div className="flex items-center gap-2">
          {message && (
            <span className={cn("text-xs px-2 py-1 rounded", message.type === 'success' ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600")}>
              {message.text}
            </span>
          )}
          {canEdit && hasChanges && (
            <>
              <button onClick={() => { loadData(); setHasChanges(false); }} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
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
        {/* Log Level */}
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-purple-600" />
            <span className="text-xs font-semibold text-gray-900">Log Level</span>
          </div>
          <select
            value={settings.log_level}
            onChange={(e) => handleChange('log_level', e.target.value)}
            disabled={!canEdit}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
          >
            {LOG_LEVELS.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-2">Minimum severity to capture</p>
        </div>

        {/* Output Destinations */}
        <div className="border rounded-lg p-4">
          <span className="text-xs font-semibold text-gray-900 mb-3 block">Output Destinations</span>
          <div className="space-y-2">
            <label className="flex items-center justify-between text-xs text-gray-700">
              <span>Console</span>
              <input type="checkbox" checked={settings.console_logging_enabled} onChange={(e) => handleChange('console_logging_enabled', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
            </label>
            <label className="flex items-center justify-between text-xs text-gray-700">
              <span>File</span>
              <input type="checkbox" checked={settings.file_logging_enabled} onChange={(e) => handleChange('file_logging_enabled', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
            </label>
            <label className="flex items-center justify-between text-xs text-gray-700">
              <span>JSON File</span>
              <input type="checkbox" checked={settings.json_logging_enabled} onChange={(e) => handleChange('json_logging_enabled', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
            </label>
            <label className="flex items-center justify-between text-xs text-gray-700">
              <span>Database</span>
              <input type="checkbox" checked={settings.database_logging_enabled} onChange={(e) => handleChange('database_logging_enabled', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
            </label>
          </div>
        </div>

        {/* File Rotation */}
        <div className="border rounded-lg p-4">
          <span className="text-xs font-semibold text-gray-900 mb-3 block">File Rotation</span>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Max Size (MB)</label>
              <input type="number" value={settings.max_file_size_mb} onChange={(e) => handleChange('max_file_size_mb', parseInt(e.target.value) || 10)} min={1} max={100} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Backup Count</label>
              <input type="number" value={settings.backup_count} onChange={(e) => handleChange('backup_count', parseInt(e.target.value) || 10)} min={1} max={50} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
          </div>
        </div>

        {/* Retention */}
        <div className="border rounded-lg p-4">
          <span className="text-xs font-semibold text-gray-900 mb-3 block">Database Retention</span>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-600 mb-1">Keep logs (days)</label>
              <input type="number" value={settings.retention_days} onChange={(e) => handleChange('retention_days', parseInt(e.target.value) || 30)} min={1} max={365} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
            {canEdit && (
              <button onClick={handleCleanup} disabled={cleaning} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 disabled:opacity-50">
                {cleaning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                Cleanup
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoggingSettings;
