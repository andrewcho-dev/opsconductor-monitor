import React, { useState, useEffect } from 'react';
import { 
  Save, RotateCcw, FileText, Database, Trash2, 
  AlertTriangle, Check, Loader2, RefreshCw
} from 'lucide-react';
import { fetchApi, cn } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

const LOG_LEVELS = [
  { value: 'DEBUG', label: 'Debug', description: 'Detailed diagnostic information' },
  { value: 'INFO', label: 'Info', description: 'General operational messages' },
  { value: 'WARNING', label: 'Warning', description: 'Potential issues that may need attention' },
  { value: 'ERROR', label: 'Error', description: 'Error conditions that need attention' },
  { value: 'CRITICAL', label: 'Critical', description: 'Severe errors requiring immediate action' },
];

const LOG_SOURCES = [
  { value: 'api', label: 'API' },
  { value: 'scheduler', label: 'Scheduler' },
  { value: 'worker', label: 'Worker' },
  { value: 'ssh', label: 'SSH' },
  { value: 'snmp', label: 'SNMP' },
  { value: 'database', label: 'Database' },
  { value: 'workflow', label: 'Workflow' },
  { value: 'system', label: 'System' },
  { value: 'notification', label: 'Notification' },
];

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
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [cleaning, setCleaning] = useState(false);
  const [message, setMessage] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  const canEdit = hasPermission('system.settings.edit');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [settingsRes, statsRes] = await Promise.all([
        fetchApi('/api/system/logging/settings', { headers: getAuthHeader() }).catch(() => null),
        fetchApi('/api/logs/stats', { headers: getAuthHeader() }).catch(() => null),
      ]);

      if (settingsRes?.success) {
        setSettings(prev => ({ ...prev, ...settingsRes.data }));
      }
      if (statsRes?.success) {
        setStats(statsRes.data);
      }
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
      const res = await fetchApi('/api/system/logging/settings', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });

      if (res.success) {
        setHasChanges(false);
        setMessage({ type: 'success', text: 'Logging settings saved successfully' });
      } else {
        setMessage({ type: 'error', text: res.error?.message || 'Failed to save settings' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleCleanup = async () => {
    if (!confirm(`This will delete logs older than ${settings.retention_days} days. Continue?`)) {
      return;
    }

    setCleaning(true);
    setMessage(null);

    try {
      const res = await fetchApi('/api/logs/cleanup', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ retention_days: settings.retention_days })
      });

      if (res.success) {
        setMessage({ type: 'success', text: `Cleaned up ${res.data?.deleted || 0} old log entries` });
        loadData();
      } else {
        setMessage({ type: 'error', text: res.error?.message || 'Cleanup failed' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Cleanup failed' });
    } finally {
      setCleaning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Logging Settings</h2>
          <p className="text-sm text-gray-500">Configure application logging and log retention</p>
        </div>
        {canEdit && hasChanges && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => { loadData(); setHasChanges(false); }}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg flex items-center gap-1"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Changes
            </button>
          </div>
        )}
      </div>

      {message && (
        <div className={cn(
          "p-3 rounded-lg flex items-center gap-2",
          message.type === 'success' ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"
        )}>
          {message.type === 'success' ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-500" />
          )}
          <p className={cn("text-sm", message.type === 'success' ? "text-green-600" : "text-red-600")}>
            {message.text}
          </p>
        </div>
      )}

      {/* Log Statistics */}
      {stats && (
        <div className="bg-white rounded-xl border p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Database className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Log Statistics</h3>
                <p className="text-sm text-gray-500">Last 24 hours</p>
              </div>
            </div>
            <button
              onClick={loadData}
              className="p-2 hover:bg-gray-100 rounded-lg"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>

          <div className="grid grid-cols-5 gap-4">
            {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map((level) => (
              <div key={level} className="text-center">
                <div className={cn(
                  "text-2xl font-bold",
                  level === 'DEBUG' ? "text-gray-500" :
                  level === 'INFO' ? "text-blue-600" :
                  level === 'WARNING' ? "text-amber-600" :
                  level === 'ERROR' ? "text-red-600" : "text-red-800"
                )}>
                  {stats.by_level?.[level] || 0}
                </div>
                <div className="text-xs text-gray-500">{level}</div>
              </div>
            ))}
          </div>

          {stats.recent_errors?.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Recent Errors</h4>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {stats.recent_errors.slice(0, 5).map((err, idx) => (
                  <div key={idx} className="text-xs text-gray-600 truncate">
                    <span className="text-gray-400">{new Date(err.timestamp).toLocaleTimeString()}</span>
                    {' - '}
                    <span className="text-red-600">[{err.source}]</span>
                    {' '}
                    {err.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Log Level */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-100 rounded-lg">
            <FileText className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Log Level</h3>
            <p className="text-sm text-gray-500">Minimum severity level to capture</p>
          </div>
        </div>

        <div className="space-y-2">
          {LOG_LEVELS.map((level) => (
            <label
              key={level.value}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors",
                settings.log_level === level.value
                  ? "bg-purple-50 border border-purple-200"
                  : "bg-gray-50 border border-gray-200 hover:border-gray-300"
              )}
            >
              <input
                type="radio"
                name="log_level"
                value={level.value}
                checked={settings.log_level === level.value}
                onChange={(e) => handleChange('log_level', e.target.value)}
                disabled={!canEdit}
                className="text-purple-600"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-900">{level.label}</div>
                <div className="text-xs text-gray-500">{level.description}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Output Destinations */}
      <div className="bg-white rounded-xl border p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Output Destinations</h3>

        <div className="space-y-4">
          <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Console Output</div>
              <div className="text-xs text-gray-500">Write logs to stdout/stderr</div>
            </div>
            <input
              type="checkbox"
              checked={settings.console_logging_enabled}
              onChange={(e) => handleChange('console_logging_enabled', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
          </label>

          <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">File Logging</div>
              <div className="text-xs text-gray-500">Write logs to rotating text files</div>
            </div>
            <input
              type="checkbox"
              checked={settings.file_logging_enabled}
              onChange={(e) => handleChange('file_logging_enabled', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
          </label>

          <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">JSON File Logging</div>
              <div className="text-xs text-gray-500">Write structured JSON logs for parsing</div>
            </div>
            <input
              type="checkbox"
              checked={settings.json_logging_enabled}
              onChange={(e) => handleChange('json_logging_enabled', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
          </label>

          <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <div className="font-medium text-gray-900">Database Logging</div>
              <div className="text-xs text-gray-500">Store logs in database for querying</div>
            </div>
            <input
              type="checkbox"
              checked={settings.database_logging_enabled}
              onChange={(e) => handleChange('database_logging_enabled', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
          </label>
        </div>
      </div>

      {/* File Rotation */}
      <div className="bg-white rounded-xl border p-6">
        <h3 className="font-semibold text-gray-900 mb-4">File Rotation</h3>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max File Size (MB)
            </label>
            <input
              type="number"
              value={settings.max_file_size_mb}
              onChange={(e) => handleChange('max_file_size_mb', parseInt(e.target.value) || 10)}
              min={1}
              max={100}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
            <p className="text-xs text-gray-500 mt-1">Rotate log files when they reach this size</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Backup Count
            </label>
            <input
              type="number"
              value={settings.backup_count}
              onChange={(e) => handleChange('backup_count', parseInt(e.target.value) || 10)}
              min={1}
              max={50}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
            <p className="text-xs text-gray-500 mt-1">Number of rotated files to keep</p>
          </div>
        </div>
      </div>

      {/* Retention & Cleanup */}
      <div className="bg-white rounded-xl border p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Database Log Retention</h3>

        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Retention Period (days)
            </label>
            <input
              type="number"
              value={settings.retention_days}
              onChange={(e) => handleChange('retention_days', parseInt(e.target.value) || 30)}
              min={1}
              max={365}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
            <p className="text-xs text-gray-500 mt-1">Logs older than this will be eligible for cleanup</p>
          </div>
          {canEdit && (
            <button
              onClick={handleCleanup}
              disabled={cleaning}
              className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50 disabled:opacity-50"
            >
              {cleaning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Clean Up Now
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default LoggingSettings;
