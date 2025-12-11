import React, { useState } from 'react';
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
  AlertTriangle
} from 'lucide-react';

export function NotificationsPage() {
  const [channels, setChannels] = useState([
    { 
      id: 1, 
      type: 'email', 
      name: 'Email - SMTP', 
      config: { server: 'smtp.gmail.com:587', from: 'alerts@company.com' },
      enabled: true 
    },
    { 
      id: 2, 
      type: 'slack', 
      name: 'Slack - Webhook', 
      config: { channel: '#network-alerts', webhook: 'https://hooks.slack...' },
      enabled: true 
    },
    { 
      id: 3, 
      type: 'pagerduty', 
      name: 'PagerDuty', 
      config: { integration_key: 'Not configured' },
      enabled: false 
    },
  ]);

  const [rules, setRules] = useState([
    { id: 1, name: 'Optical Power Low', channels: ['Email', 'Slack'], severity: 'warning', active: true },
    { id: 2, name: 'Device Unreachable', channels: ['Slack'], severity: 'critical', active: true },
    { id: 3, name: 'Job Failure', channels: ['Email'], severity: 'error', active: true },
    { id: 4, name: 'Temperature High', channels: ['PagerDuty'], severity: 'critical', active: false },
  ]);

  const channelIcons = {
    email: Mail,
    slack: MessageSquare,
    pagerduty: Phone,
  };

  const severityColors = {
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    critical: 'bg-red-100 text-red-700 border-red-200',
    info: 'bg-blue-100 text-blue-700 border-blue-200',
  };

  return (
    <PageLayout module="system">
      <PageHeader
        title="Notifications"
        description="Configure notification channels and alert rules"
        icon={Bell}
        actions={
          <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            <Plus className="w-4 h-4" />
            Add Channel
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Notification Channels */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Notification Channels
            </h2>
          </div>
          <div className="p-4 space-y-3">
            {channels.map((channel) => {
              const Icon = channelIcons[channel.type] || Bell;
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
                        <div className="text-sm text-gray-500">
                          {Object.entries(channel.config).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        channel.enabled 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {channel.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                      <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
                        <TestTube className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Notification Rules */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Notification Rules
            </h2>
            <button className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50">
              <Plus className="w-3 h-3" />
              Add Rule
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Rule</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Channels</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Severity</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{rule.name}</td>
                    <td className="px-4 py-3 text-gray-600">{rule.channels.join(', ')}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${severityColors[rule.severity]}`}>
                        {rule.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1 text-xs ${rule.active ? 'text-green-600' : 'text-gray-400'}`}>
                        {rule.active ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                        {rule.active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="p-1 text-gray-500 hover:text-gray-700">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button className="p-1 text-red-500 hover:text-red-700 ml-1">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default NotificationsPage;
