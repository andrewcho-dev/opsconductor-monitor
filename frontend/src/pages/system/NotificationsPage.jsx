/**
 * NotificationsPage
 * 
 * Main page for managing notification channels, rules, and templates.
 * Modal components are extracted to ./notifications/ for maintainability.
 */

import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { 
  Bell, Plus, Mail, MessageSquare, Phone, Edit, Trash2, TestTube,
  CheckCircle, XCircle, AlertTriangle, Webhook, Loader2, FileText
} from 'lucide-react';
import { fetchApi } from '../../lib/utils';
import { ChannelModal, RuleModal, TemplateModal } from './notifications';

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
        fetchApi('/notifications/v1/channels'),
        fetchApi('/notifications/v1/rules'),
        fetchApi('/notifications/v1/templates')
      ]);
      // Handle both wrapped and direct response formats
      const channelsData = channelsRes?.data || channelsRes;
      const rulesData = rulesRes?.data || rulesRes;
      const templatesData = templatesRes?.data || templatesRes;
      setChannels(channelsData?.channels || (Array.isArray(channelsData) ? channelsData : []));
      setRules(rulesData?.rules || (Array.isArray(rulesData) ? rulesData : []));
      setTemplates(templatesData?.templates || (Array.isArray(templatesData) ? templatesData : []));
    } catch (err) {
      // Error loading data
    } finally {
      setLoading(false);
    }
  };

  const handleTestChannel = async (channelId) => {
    setTestingChannel(channelId);
    try {
      const res = await fetchApi(`/notifications/v1/channels/${channelId}/test`, { method: 'POST' });
      if (res.success) {
        alert('Test notification sent successfully!');
      } else {
        alert('Failed to send test notification: ' + (res.error || 'Unknown error'));
      }
      loadData();
    } catch (err) {
      alert('Error testing channel: ' + err.message);
    } finally {
      setTestingChannel(null);
    }
  };

  const handleDeleteChannel = async (channelId) => {
    if (!confirm('Delete this notification channel?')) return;
    try {
      await fetchApi(`/notifications/v1/channels/${channelId}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting channel: ' + err.message);
    }
  };

  const handleToggleChannel = async (channel) => {
    try {
      await fetchApi(`/notifications/v1/channels/${channel.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !channel.enabled })
      });
      loadData();
    } catch (err) {
      alert('Error updating channel: ' + err.message);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!confirm('Delete this notification rule?')) return;
    try {
      await fetchApi(`/notifications/v1/rules/${ruleId}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting rule: ' + err.message);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!confirm('Delete this template?')) return;
    try {
      await fetchApi(`/notifications/v1/templates/${templateId}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting template: ' + err.message);
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

export default NotificationsPage;
