import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { Key, Plus, Edit, Trash2, Eye, EyeOff, Shield, Loader2, X, RefreshCw } from 'lucide-react';
import { fetchApi } from '../../lib/utils';

export function CredentialsPage() {
  const [credentials, setCredentials] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCredentialModal, setShowCredentialModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingCredential, setEditingCredential] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);

  const typeColors = {
    'ssh': 'bg-blue-100 text-blue-700 border-blue-200',
    'snmp': 'bg-green-100 text-green-700 border-green-200',
    'api_key': 'bg-purple-100 text-purple-700 border-purple-200',
    'password': 'bg-orange-100 text-orange-700 border-orange-200',
    'winrm': 'bg-cyan-100 text-cyan-700 border-cyan-200',
  };

  const typeLabels = {
    'ssh': 'SSH',
    'snmp': 'SNMP',
    'api_key': 'API Key',
    'password': 'Password',
    'winrm': 'WinRM',
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [credResponse, groupResponse] = await Promise.all([
        fetchApi('/api/credentials'),
        fetchApi('/api/credentials/groups')
      ]);
      setCredentials(credResponse.data?.credentials || []);
      setGroups(groupResponse.data?.groups || []);
    } catch (err) {
      console.error('Error loading credentials:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCredential = async (id) => {
    if (!confirm('Are you sure you want to delete this credential?')) return;
    try {
      await fetchApi(`/api/credentials/${id}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting credential: ' + err.message);
    }
  };

  const handleDeleteGroup = async (id) => {
    if (!confirm('Are you sure you want to delete this group?')) return;
    try {
      await fetchApi(`/api/credentials/groups/${id}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting group: ' + err.message);
    }
  };

  const handleEditCredential = (cred) => {
    setEditingCredential(cred);
    setShowCredentialModal(true);
  };

  const handleAddCredential = () => {
    setEditingCredential(null);
    setShowCredentialModal(true);
  };

  const handleEditGroup = (group) => {
    setEditingGroup(group);
    setShowGroupModal(true);
  };

  const handleAddGroup = () => {
    setEditingGroup(null);
    setShowGroupModal(true);
  };

  const handleCredentialSaved = () => {
    setShowCredentialModal(false);
    setEditingCredential(null);
    loadData();
  };

  const handleGroupSaved = () => {
    setShowGroupModal(false);
    setEditingGroup(null);
    loadData();
  };

  return (
    <PageLayout module="system">
      <PageHeader
        title="Credential Vault"
        description="Securely manage credentials for device access"
        icon={Key}
        actions={
          <div className="flex items-center gap-2">
            <button 
              onClick={loadData}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button 
              onClick={handleAddCredential}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Credential
            </button>
          </div>
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
                {loading ? (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading credentials...
                    </td>
                  </tr>
                ) : credentials.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
                      No credentials stored yet. Click "Add Credential" to create one.
                    </td>
                  </tr>
                ) : credentials.map((cred) => (
                  <tr key={cred.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-gray-400" />
                        <span className="font-medium text-gray-900">{cred.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${typeColors[cred.credential_type] || 'bg-gray-100 text-gray-700 border-gray-200'}`}>
                        {typeLabels[cred.credential_type] || cred.credential_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono">{cred.username || '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{cred.used_by_count || 0} uses</td>
                    <td className="px-4 py-3 text-right">
                      <button 
                        onClick={() => handleEditCredential(cred)}
                        className="p-1 text-gray-500 hover:text-gray-700" 
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => handleDeleteCredential(cred.id)}
                        className="p-1 text-red-500 hover:text-red-700 ml-1" 
                        title="Delete"
                      >
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
            <button 
              onClick={handleAddGroup}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50"
            >
              <Plus className="w-3 h-3" />
              New Group
            </button>
          </div>
          <div className="p-4 space-y-3">
            {groups.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No credential groups yet.</p>
            ) : groups.map((group) => (
              <div key={group.id} className="border border-gray-200 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">{group.name}</div>
                  <div className="text-sm text-gray-500">
                    {group.credentials?.length > 0 
                      ? group.credentials.map(c => c.name).join(', ')
                      : 'No credentials assigned'}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button 
                    onClick={() => handleEditGroup(group)}
                    className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => handleDeleteGroup(group.id)}
                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Credential Modal */}
      {showCredentialModal && (
        <CredentialModal
          credential={editingCredential}
          onClose={() => setShowCredentialModal(false)}
          onSave={handleCredentialSaved}
        />
      )}

      {/* Group Modal */}
      {showGroupModal && (
        <GroupModal
          group={editingGroup}
          credentials={credentials}
          onClose={() => setShowGroupModal(false)}
          onSave={handleGroupSaved}
        />
      )}
    </PageLayout>
  );
}

function CredentialModal({ credential, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: credential?.name || '',
    description: credential?.description || '',
    credential_type: credential?.credential_type || 'ssh',
    username: credential?.username || '',
    password: '',
    private_key: '',
    passphrase: '',
    port: 22,
    community: '',
    snmp_version: '2c',
    security_name: '',
    auth_protocol: '',
    auth_password: '',
    priv_protocol: '',
    priv_password: '',
    api_key: '',
    api_secret: '',
    token: '',
    // WinRM fields
    domain: '',
    winrm_transport: 'ntlm',
    winrm_port: 5985,
  });
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (credential) {
        await fetchApi(`/api/credentials/${credential.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      } else {
        await fetchApi('/api/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      onSave();
    } catch (err) {
      alert('Error saving credential: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{credential ? 'Edit Credential' : 'Add Credential'}</h2>
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
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="e.g., Cisco Admin SSH"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={formData.credential_type}
              onChange={(e) => setFormData(prev => ({ ...prev, credential_type: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
              disabled={!!credential}
            >
              <option value="ssh">SSH</option>
              <option value="snmp">SNMP</option>
              <option value="winrm">WinRM (Windows)</option>
              <option value="api_key">API Key</option>
              <option value="password">Password</option>
            </select>
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

          {/* SSH Fields */}
          {formData.credential_type === 'ssh' && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="admin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData(prev => ({ ...prev, port: parseInt(e.target.value) || 22 }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg pr-10"
                    placeholder={credential ? '(unchanged)' : 'Enter password'}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Private Key (optional)</label>
                <textarea
                  value={formData.private_key}
                  onChange={(e) => setFormData(prev => ({ ...prev, private_key: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-24"
                  placeholder="-----BEGIN RSA PRIVATE KEY-----"
                />
              </div>
            </>
          )}

          {/* WinRM Fields */}
          {formData.credential_type === 'winrm' && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="Administrator"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
                  <input
                    type="text"
                    value={formData.domain}
                    onChange={(e) => setFormData(prev => ({ ...prev, domain: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="DOMAIN (optional)"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg pr-10"
                    placeholder={credential ? '(unchanged)' : 'Enter password'}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Transport</label>
                  <select
                    value={formData.winrm_transport}
                    onChange={(e) => setFormData(prev => ({ ...prev, winrm_transport: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="ntlm">NTLM</option>
                    <option value="kerberos">Kerberos</option>
                    <option value="basic">Basic</option>
                    <option value="credssp">CredSSP</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <select
                    value={formData.winrm_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, winrm_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="5985">5985 (HTTP)</option>
                    <option value="5986">5986 (HTTPS)</option>
                  </select>
                </div>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                <strong>Note:</strong> WinRM must be enabled on the target Windows machine. 
                Run <code className="bg-amber-100 px-1 rounded">winrm quickconfig</code> on the target to enable it.
              </div>
            </>
          )}

          {/* SNMP Fields */}
          {formData.credential_type === 'snmp' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SNMP Version</label>
                <select
                  value={formData.snmp_version}
                  onChange={(e) => setFormData(prev => ({ ...prev, snmp_version: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="1">v1</option>
                  <option value="2c">v2c</option>
                  <option value="3">v3</option>
                </select>
              </div>
              {(formData.snmp_version === '1' || formData.snmp_version === '2c') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Community String</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.community}
                    onChange={(e) => setFormData(prev => ({ ...prev, community: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="public"
                  />
                </div>
              )}
              {formData.snmp_version === '3' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Security Name</label>
                    <input
                      type="text"
                      value={formData.security_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, security_name: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Auth Protocol</label>
                      <select
                        value={formData.auth_protocol}
                        onChange={(e) => setFormData(prev => ({ ...prev, auth_protocol: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      >
                        <option value="">None</option>
                        <option value="MD5">MD5</option>
                        <option value="SHA">SHA</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Auth Password</label>
                      <input
                        type="password"
                        value={formData.auth_password}
                        onChange={(e) => setFormData(prev => ({ ...prev, auth_password: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Privacy Protocol</label>
                      <select
                        value={formData.priv_protocol}
                        onChange={(e) => setFormData(prev => ({ ...prev, priv_protocol: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      >
                        <option value="">None</option>
                        <option value="DES">DES</option>
                        <option value="AES">AES</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Privacy Password</label>
                      <input
                        type="password"
                        value={formData.priv_password}
                        onChange={(e) => setFormData(prev => ({ ...prev, priv_password: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      />
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* API Key Fields */}
          {formData.credential_type === 'api_key' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.api_key}
                  onChange={(e) => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Secret (optional)</label>
                <input
                  type="password"
                  value={formData.api_secret}
                  onChange={(e) => setFormData(prev => ({ ...prev, api_secret: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </>
          )}

          {/* Password Fields */}
          {formData.credential_type === 'password' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </>
          )}

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
              {credential ? 'Save Changes' : 'Create Credential'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function GroupModal({ group, credentials, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: group?.name || '',
    description: group?.description || '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (group) {
        // Update not implemented yet - just close
        onSave();
      } else {
        await fetchApi('/api/credentials/groups', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        onSave();
      }
    } catch (err) {
      alert('Error saving group: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">{group ? 'Edit Group' : 'Add Group'}</h2>
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
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="e.g., Production Devices"
              required
            />
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
              {group ? 'Save Changes' : 'Create Group'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CredentialsPage;
