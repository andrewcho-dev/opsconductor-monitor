import React, { useState } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { Key, Plus, Edit, Trash2, Eye, EyeOff, Shield } from 'lucide-react';

export function CredentialsPage() {
  const [credentials, setCredentials] = useState([
    { id: 1, name: 'Ciena Default', type: 'SSH', username: 'su', usedBy: 3 },
    { id: 2, name: 'Cisco Admin', type: 'SSH', username: 'admin', usedBy: 1 },
    { id: 3, name: 'SNMP Community', type: 'SNMP', username: '—', usedBy: 2 },
    { id: 4, name: 'API Token', type: 'API Key', username: '—', usedBy: 0 },
  ]);

  const [groups, setGroups] = useState([
    { id: 1, name: 'Production Devices', credentials: ['Ciena Default', 'SNMP Community'] },
    { id: 2, name: 'Lab Devices', credentials: ['Cisco Admin'] },
  ]);

  const typeColors = {
    'SSH': 'bg-blue-100 text-blue-700 border-blue-200',
    'SNMP': 'bg-green-100 text-green-700 border-green-200',
    'API Key': 'bg-purple-100 text-purple-700 border-purple-200',
  };

  return (
    <PageLayout module="system">
      <PageHeader
        title="Credential Vault"
        description="Securely manage credentials for device access"
        icon={Key}
        actions={
          <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            <Plus className="w-4 h-4" />
            Add Credential
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Security Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <Shield className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-blue-900">Credentials are encrypted at rest</h3>
            <p className="text-sm text-blue-700 mt-1">
              All credentials are stored using AES-256 encryption. They are only decrypted when needed for job execution.
            </p>
          </div>
        </div>

        {/* Credentials Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Stored Credentials
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Username</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Used By</th>
                  <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {credentials.map((cred) => (
                  <tr key={cred.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-gray-400" />
                        <span className="font-medium text-gray-900">{cred.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${typeColors[cred.type]}`}>
                        {cred.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono">{cred.username}</td>
                    <td className="px-4 py-3 text-gray-600">{cred.usedBy} jobs</td>
                    <td className="px-4 py-3 text-right">
                      <button className="p-1 text-gray-500 hover:text-gray-700" title="Edit">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button className="p-1 text-red-500 hover:text-red-700 ml-1" title="Delete">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Credential Groups */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Credential Groups
            </h2>
            <button className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50">
              <Plus className="w-3 h-3" />
              New Group
            </button>
          </div>
          <div className="p-4 space-y-3">
            {groups.map((group) => (
              <div key={group.id} className="border border-gray-200 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">{group.name}</div>
                  <div className="text-sm text-gray-500">{group.credentials.join(', ')}</div>
                </div>
                <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
                  <Edit className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default CredentialsPage;
