import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { 
  Bell, 
  Plus, 
  Mail, 
  MessageSquare, 
  Phone,
  Edit,
  Trash2,
  TestTube,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Webhook,
  X,
  Loader2,
  FileText,
  Eye
} from 'lucide-react';
import { fetchApi } from '../../lib/utils';

export function NotificationsPage() {
  const [activeTab, setActiveTab] = useState('channels');
  const [channels, setChannels] = useState([]);
  const [rules, setRules] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editingChannel, setEditingChannel] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [testingChannel, setTestingChannel] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [channelsRes, rulesRes, templatesRes] = await Promise.all([
        fetchApi('/api/notifications/channels'),
        fetchApi('/api/notifications/rules'),
        fetchApi('/api/notifications/templates')
      ]);
      setChannels(channelsRes.data?.channels || []);
      setRules(rulesRes.data?.rules || []);
      setTemplates(templatesRes.data?.templates || []);
    } catch (err) {
      console.error('Failed to load notifications data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestChannel = async (channelId) => {
    setTestingChannel(channelId);
    try {
      const res = await fetchApi(`/api/notifications/channels/${channelId}/test`, { method: 'POST' });
      if (res.success) {
        alert('Test notification sent successfully!');
      } else {
        alert('Failed to send test notification: ' + (res.error || 'Unknown error'));
      }
      loadData(); // Refresh to get updated test status
    } catch (err) {
      alert('Error testing channel: ' + err.message);
    } finally {
      setTestingChannel(null);
    }
  };

  const handleDeleteChannel = async (channelId) => {
    if (!confirm('Delete this notification channel?')) return;
    try {
      await fetchApi(`/api/notifications/channels/${channelId}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting channel: ' + err.message);
    }
  };

  const handleToggleChannel = async (channel) => {
    try {
      await fetchApi(`/api/notifications/channels/${channel.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !channel.enabled })
      });
      loadData();
    } catch (err) {
      alert('Error updating channel: ' + err.message);
    }
  };

  const channelIcons = {
    email: Mail,
    slack: MessageSquare,
    pagerduty: Phone,
    webhook: Webhook,
    teams: MessageSquare,
    discord: MessageSquare,
  };

  const channelTypeLabels = {
    email: 'Email (SMTP)',
    slack: 'Slack',
    webhook: 'Webhook',
    pagerduty: 'PagerDuty',
    teams: 'Microsoft Teams',
    discord: 'Discord',
  };

  const severityColors = {
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    critical: 'bg-red-100 text-red-700 border-red-200',
    info: 'bg-blue-100 text-blue-700 border-blue-200',
  };

  // Get channel names for rule display
  const getChannelNames = (channelIds) => {
    if (!channelIds || !Array.isArray(channelIds)) return '—';
    return channelIds
      .map(id => channels.find(c => c.id === id)?.name || `#${id}`)
      .join(', ');
  };

  if (loading) {
    return (
      <PageLayout module="system">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </PageLayout>
    );
  }

  const handleDeleteRule = async (ruleId) => {
    if (!confirm('Delete this notification rule?')) return;
    try {
      await fetchApi(`/api/notifications/rules/${ruleId}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting rule: ' + err.message);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!confirm('Delete this template?')) return;
    try {
      await fetchApi(`/api/notifications/templates/${templateId}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting template: ' + err.message);
    }
  };

  const tabs = [
    { id: 'channels', label: 'Channels', count: channels.length },
    { id: 'rules', label: 'Rules', count: rules.length },
    { id: 'templates', label: 'Templates', count: templates.length },
  ];

  return (
    <PageLayout module="system">
      <PageHeader
        title="Notifications"
        description="Configure notification channels, rules, and templates"
        icon={Bell}
        actions={
          activeTab === 'channels' ? (
            <button 
              onClick={() => { setEditingChannel(null); setShowChannelModal(true); }}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Channel
            </button>
          ) : activeTab === 'rules' ? (
            <button 
              onClick={() => { setEditingRule(null); setShowRuleModal(true); }}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Rule
            </button>
          ) : (
            <button 
              onClick={() => { setEditingTemplate(null); setShowTemplateModal(true); }}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Template
            </button>
          )
        }
      />

      {/* Tabs */}
      <div className="px-6 pt-4">
        <div className="flex gap-1 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Channels Tab */}
        {activeTab === 'channels' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Notification Channels
            </h2>
          </div>
          {channels.length === 0 ? (
            <div className="p-8 text-center">
              <Bell className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No notification channels configured</p>
              <button 
                onClick={() => { setEditingChannel(null); setShowChannelModal(true); }}
                className="mt-3 text-sm text-blue-600 hover:underline"
              >
                Add your first channel
              </button>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {channels.map((channel) => {
                const Icon = channelIcons[channel.channel_type] || Bell;
                const configDisplay = channel.config ? 
                  Object.entries(channel.config)
                    .filter(([k]) => !k.includes('password') && !k.includes('key') && !k.includes('token'))
                    .map(([k, v]) => `${k}: ${typeof v === 'string' && v.length > 30 ? v.slice(0, 30) + '...' : v}`)
                    .join(' | ') 
                  : '';
                return (
                  <div key={channel.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          channel.enabled ? 'bg-blue-100' : 'bg-gray-100'
                        }`}>
                          <Icon className={`w-5 h-5 ${channel.enabled ? 'text-blue-600' : 'text-gray-400'}`} />
                        </div>
                        <div>
                          <div className="font-medium text-gray-900">{channel.name}</div>
                          <div className="text-xs text-gray-400">{channelTypeLabels[channel.channel_type] || channel.channel_type}</div>
                          {configDisplay && (
                            <div className="text-sm text-gray-500 truncate max-w-md">{configDisplay}</div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {channel.last_test_at && (
                          <span className={`text-xs ${channel.last_test_success ? 'text-green-600' : 'text-red-600'}`}>
                            {channel.last_test_success ? '✓ Tested' : '✗ Test failed'}
                          </span>
                        )}
                        <button
                          onClick={() => handleToggleChannel(channel)}
                          className={`px-2 py-1 text-xs font-medium rounded-full cursor-pointer ${
                            channel.enabled 
                              ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                          }`}
                        >
                          {channel.enabled ? 'ON' : 'OFF'}
                        </button>
                        <button 
                          onClick={() => { setEditingChannel(channel); setShowChannelModal(true); }}
                          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleTestChannel(channel.id)}
                          disabled={testingChannel === channel.id}
                          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                        >
                          {testingChannel === channel.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <TestTube className="w-4 h-4" />
                          )}
                        </button>
                        <button 
                          onClick={() => handleDeleteChannel(channel.id)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        )}

        {/* Rules Tab */}
        {activeTab === 'rules' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Notification Rules
            </h2>
          </div>
          {rules.length === 0 ? (
            <div className="p-8 text-center">
              <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No notification rules configured</p>
              <p className="text-xs text-gray-400 mt-1">Rules determine when to send notifications based on alerts</p>
              <button 
                onClick={() => { setEditingRule(null); setShowRuleModal(true); }}
                className="mt-3 text-sm text-blue-600 hover:underline"
              >
                Create your first rule
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Rule</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Channels</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Template</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{rule.name}</td>
                      <td className="px-4 py-3 text-gray-600">{rule.trigger_type}</td>
                      <td className="px-4 py-3 text-gray-600">{getChannelNames(rule.channel_ids)}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {templates.find(t => t.id === rule.template_id)?.name || '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`flex items-center gap-1 text-xs ${rule.enabled ? 'text-green-600' : 'text-gray-400'}`}>
                          {rule.enabled ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          {rule.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button 
                          onClick={() => { setEditingRule(rule); setShowRuleModal(true); }}
                          className="p-1 text-gray-500 hover:text-gray-700"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleDeleteRule(rule.id)}
                          className="p-1 text-red-500 hover:text-red-700 ml-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Notification Templates
            </h2>
          </div>
          {templates.length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No templates configured</p>
              <button 
                onClick={() => { setEditingTemplate(null); setShowTemplateModal(true); }}
                className="mt-3 text-sm text-blue-600 hover:underline"
              >
                Create your first template
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {templates.map((template) => (
                <div key={template.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{template.name}</span>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          template.template_type === 'system' 
                            ? 'bg-blue-100 text-blue-700' 
                            : 'bg-purple-100 text-purple-700'
                        }`}>
                          {template.template_type}
                        </span>
                        {template.is_default && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                            Default
                          </span>
                        )}
                      </div>
                      {template.description && (
                        <p className="text-sm text-gray-500 mt-1">{template.description}</p>
                      )}
                      <div className="mt-2 text-xs text-gray-400 font-mono bg-gray-50 p-2 rounded">
                        <div><strong>Title:</strong> {template.title_template}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 ml-4">
                      <button 
                        onClick={() => { setEditingTemplate(template); setShowTemplateModal(true); }}
                        className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      {!template.is_default && (
                        <button 
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        )}
      </div>

      {/* Channel Modal */}
      {showChannelModal && (
        <ChannelModal
          channel={editingChannel}
          onClose={() => setShowChannelModal(false)}
          onSave={() => { setShowChannelModal(false); loadData(); }}
        />
      )}

      {/* Rule Modal */}
      {showRuleModal && (
        <RuleModal
          rule={editingRule}
          channels={channels}
          templates={templates}
          onClose={() => setShowRuleModal(false)}
          onSave={() => { setShowRuleModal(false); loadData(); }}
        />
      )}

      {/* Template Modal */}
      {showTemplateModal && (
        <TemplateModal
          template={editingTemplate}
          onClose={() => setShowTemplateModal(false)}
          onSave={() => { setShowTemplateModal(false); loadData(); }}
        />
      )}
    </PageLayout>
  );
}

function ChannelModal({ channel, onClose, onSave }) {
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
        await fetchApi(`/api/notifications/channels/${channel.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      } else {
        await fetchApi('/api/notifications/channels', {
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

          {/* Type-specific config fields */}
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

function RuleModal({ rule, channels, templates, onClose, onSave }) {
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
        await fetchApi(`/api/notifications/rules/${rule.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetchApi('/api/notifications/rules', {
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

function TemplateModal({ template, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: template?.name || '',
    description: template?.description || '',
    template_type: template?.template_type || 'system',
    title_template: template?.title_template || '',
    body_template: template?.body_template || '',
    available_variables: template?.available_variables || []
  });
  const [saving, setSaving] = useState(false);
  const [newVariable, setNewVariable] = useState('');

  const systemVariables = [
    'alert.title', 'alert.message', 'alert.severity', 'alert.category', 'alert.triggered_at', 'alert.details'
  ];
  const jobVariables = [
    'job.name', 'job.id', 'job.status', 'job.duration', 'job.started_at', 'job.finished_at', 
    'job.error', 'job.summary', 'job.results', 'workflow.name', 'workflow.variables'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (template) {
        await fetchApi(`/api/notifications/templates/${template.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      } else {
        await fetchApi('/api/notifications/templates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      onSave();
    } catch (err) {
      alert('Error saving template: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const insertVariable = (variable) => {
    const textarea = document.getElementById('body-template');
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = formData.body_template;
      const newText = text.substring(0, start) + `{{${variable}}}` + text.substring(end);
      setFormData(prev => ({ ...prev, body_template: newText }));
    } else {
      setFormData(prev => ({ ...prev, body_template: prev.body_template + `{{${variable}}}` }));
    }
  };

  const suggestedVariables = formData.template_type === 'system' ? systemVariables : jobVariables;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{template ? 'Edit Template' : 'Add Template'}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="My Template"
                required
                disabled={template?.is_default}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={formData.template_type}
                onChange={(e) => setFormData(prev => ({ ...prev, template_type: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                disabled={template?.is_default}
              >
                <option value="system">System (Alerts)</option>
                <option value="job">Job (Workflows)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Optional description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title Template</label>
            <input
              type="text"
              value={formData.title_template}
              onChange={(e) => setFormData(prev => ({ ...prev, title_template: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
              placeholder="[{{alert.severity}}] {{alert.title}}"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Body Template</label>
            <textarea
              id="body-template"
              value={formData.body_template}
              onChange={(e) => setFormData(prev => ({ ...prev, body_template: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-40"
              placeholder="{{alert.message}}&#10;&#10;Severity: {{alert.severity}}"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Available Variables (click to insert)</label>
            <div className="flex gap-1 flex-wrap">
              {suggestedVariables.map((variable) => (
                <button
                  key={variable}
                  type="button"
                  onClick={() => insertVariable(variable)}
                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded font-mono"
                >
                  {`{{${variable}}}`}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {template ? 'Save Changes' : 'Create Template'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default NotificationsPage;
