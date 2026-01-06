/**
 * RuleModal Component
 * 
 * Modal for creating and editing notification rules.
 */

import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function RuleModal({ rule, channels, templates, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: rule?.name || '',
    description: rule?.description || '',
    trigger_type: rule?.trigger_type || 'alert',
    channel_ids: rule?.channel_ids || [],
    template_id: rule?.template_id || null,
    severity_filter: rule?.severity_filter || [],
    enabled: rule?.enabled ?? true,
    cooldown_minutes: rule?.cooldown_minutes || 5
  });
  const [saving, setSaving] = useState(false);

  const severityOptions = ['info', 'warning', 'error', 'critical'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...formData,
        severity_filter: formData.severity_filter.length > 0 ? formData.severity_filter : null
      };
      
      if (rule) {
        await fetchApi(`/notifications/v1/rules/${rule.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetchApi('/notifications/v1/rules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      onSave();
    } catch (err) {
      alert('Error saving rule: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleChannel = (channelId) => {
    setFormData(prev => ({
      ...prev,
      channel_ids: prev.channel_ids.includes(channelId)
        ? prev.channel_ids.filter(id => id !== channelId)
        : [...prev.channel_ids, channelId]
    }));
  };

  const toggleSeverity = (severity) => {
    setFormData(prev => ({
      ...prev,
      severity_filter: prev.severity_filter.includes(severity)
        ? prev.severity_filter.filter(s => s !== severity)
        : [...prev.severity_filter, severity]
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{rule ? 'Edit Rule' : 'Add Rule'}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Alert Notifications"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Trigger Type</label>
            <select
              value={formData.trigger_type}
              onChange={(e) => setFormData(prev => ({ ...prev, trigger_type: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="alert">System Alert</option>
              <option value="job_completed">Job Completed</option>
              <option value="job_failed">Job Failed</option>
              <option value="workflow_step">Workflow Step</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Channels</label>
            <div className="space-y-2 max-h-32 overflow-y-auto border rounded-lg p-2">
              {channels.length === 0 ? (
                <p className="text-sm text-gray-500">No channels configured</p>
              ) : (
                channels.map((channel) => (
                  <label key={channel.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.channel_ids.includes(channel.id)}
                      onChange={() => toggleChannel(channel.id)}
                      className="rounded"
                    />
                    <span className="text-sm">{channel.name}</span>
                    <span className="text-xs text-gray-400">({channel.channel_type})</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Template</label>
            <select
              value={formData.template_id || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, template_id: e.target.value ? parseInt(e.target.value) : null }))}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">Default (no template)</option>
              {templates
                .filter(t => formData.trigger_type === 'alert' ? t.template_type === 'system' : t.template_type === 'job')
                .map((template) => (
                  <option key={template.id} value={template.id}>{template.name}</option>
                ))
              }
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Severity Filter (leave empty for all)</label>
            <div className="flex gap-2 flex-wrap">
              {severityOptions.map((severity) => (
                <button
                  key={severity}
                  type="button"
                  onClick={() => toggleSeverity(severity)}
                  className={`px-3 py-1 text-xs rounded-full border ${
                    formData.severity_filter.includes(severity)
                      ? 'bg-blue-100 border-blue-300 text-blue-700'
                      : 'bg-gray-50 border-gray-200 text-gray-600'
                  }`}
                >
                  {severity}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cooldown (minutes)</label>
            <input
              type="number"
              value={formData.cooldown_minutes}
              onChange={(e) => setFormData(prev => ({ ...prev, cooldown_minutes: parseInt(e.target.value) || 5 }))}
              className="w-full px-3 py-2 border rounded-lg"
              min="0"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="rule-enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData(prev => ({ ...prev, enabled: e.target.checked }))}
              className="rounded"
            />
            <label htmlFor="rule-enabled" className="text-sm text-gray-700">Enabled</label>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || formData.channel_ids.length === 0}
              className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {rule ? 'Save Changes' : 'Create Rule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
