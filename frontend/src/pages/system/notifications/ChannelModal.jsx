/**
 * ChannelModal Component
 * 
 * Modal for creating and editing notification channels.
 */

import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function ChannelModal({ channel, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: channel?.name || '',
    channel_type: channel?.channel_type || 'slack',
    enabled: channel?.enabled ?? true,
    config: channel?.config || {}
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (channel) {
        await fetchApi(`/notifications/v1/channels/${channel.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      } else {
        await fetchApi('/notifications/v1/channels', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      onSave();
    } catch (err) {
      alert('Error saving channel: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const updateConfig = (key, value) => {
    setFormData(prev => ({
      ...prev,
      config: { ...prev.config, [key]: value }
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">{channel ? 'Edit Channel' : 'Add Channel'}</h2>
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
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="My Slack Channel"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={formData.channel_type}
              onChange={(e) => setFormData(prev => ({ ...prev, channel_type: e.target.value, config: {} }))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="slack">Slack</option>
              <option value="email">Email (SMTP)</option>
              <option value="webhook">Webhook</option>
              <option value="teams">Microsoft Teams</option>
              <option value="discord">Discord</option>
              <option value="pagerduty">PagerDuty</option>
            </select>
          </div>

          {/* Slack config */}
          {formData.channel_type === 'slack' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={formData.config.webhook || ''}
                onChange={(e) => updateConfig('webhook', e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="https://hooks.slack.com/services/..."
              />
            </div>
          )}

          {/* Email config */}
          {formData.channel_type === 'email' && (
            <>
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700 mb-2">
                <strong>Note:</strong> The "To Address" below is used <strong>only for testing</strong> this channel. Actual notification recipients are configured in notification rules.
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Server</label>
                  <input
                    type="text"
                    value={formData.config.server || ''}
                    onChange={(e) => updateConfig('server', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="smtp.gmail.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    value={formData.config.port || '587'}
                    onChange={(e) => updateConfig('port', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="587"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Security</label>
                <select
                  value={formData.config.secure || 'starttls'}
                  onChange={(e) => updateConfig('secure', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="starttls">STARTTLS (Port 587) - Recommended</option>
                  <option value="ssl">SSL/TLS (Port 465)</option>
                  <option value="none">None (Port 25) - Not recommended</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  STARTTLS is recommended for most providers (Gmail, Office 365, etc.)
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.config.username || ''}
                    onChange={(e) => updateConfig('username', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="your-email@gmail.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Password / App Password</label>
                  <input
                    type="password"
                    value={formData.config.password || ''}
                    onChange={(e) => updateConfig('password', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="App password for Gmail"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">From Address</label>
                  <input
                    type="email"
                    value={formData.config.from || ''}
                    onChange={(e) => updateConfig('from', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="alerts@company.com"
                  />
                  <p className="text-xs text-gray-500 mt-1">Sender address shown in emails</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Test Address <span className="text-red-500">*</span></label>
                  <input
                    type="email"
                    value={formData.config.to || ''}
                    onChange={(e) => updateConfig('to', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="your-email@company.com"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Used only for testing this channel</p>
                </div>
              </div>
            </>
          )}

          {/* Webhook config */}
          {formData.channel_type === 'webhook' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={formData.config.url || ''}
                onChange={(e) => updateConfig('url', e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="https://example.com/webhook"
              />
            </div>
          )}

          {/* Teams config */}
          {formData.channel_type === 'teams' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={formData.config.webhook || ''}
                onChange={(e) => updateConfig('webhook', e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="https://outlook.office.com/webhook/..."
              />
            </div>
          )}

          {/* Discord config */}
          {formData.channel_type === 'discord' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={formData.config.webhook || ''}
                onChange={(e) => updateConfig('webhook', e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="https://discord.com/api/webhooks/..."
              />
            </div>
          )}

          {/* PagerDuty config */}
          {formData.channel_type === 'pagerduty' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Integration Key</label>
              <input
                type="text"
                value={formData.config.integration_key || ''}
                onChange={(e) => updateConfig('integration_key', e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="Your PagerDuty integration key"
              />
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData(prev => ({ ...prev, enabled: e.target.checked }))}
              className="rounded"
            />
            <label htmlFor="enabled" className="text-sm text-gray-700">Enabled</label>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {channel ? 'Save Changes' : 'Create Channel'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
