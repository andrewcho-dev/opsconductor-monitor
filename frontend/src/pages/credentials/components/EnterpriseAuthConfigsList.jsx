/**
 * EnterpriseAuthConfigsList Component
 * 
 * Displays and manages enterprise authentication configurations.
 */

import React, { useState, useEffect } from 'react';
import { Plus, Server, User, Pencil, Trash2, XCircle } from 'lucide-react';
import { fetchApi, cn } from '../../../lib/utils';
import { AUTH_TYPE_LABELS } from './constants';

export function EnterpriseAuthConfigsList({ configs, credentials, onRefresh }) {
  const [showServerModal, setShowServerModal] = useState(false);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [selectedServer, setSelectedServer] = useState(null);
  const [editingServer, setEditingServer] = useState(null);
  const [users, setUsers] = useState([]);
  const [serverForm, setServerForm] = useState({
    name: '',
    auth_type: 'tacacs',
    server: '',
    port: '',
    secret_key: '',
    is_default: false,
    domain: '',
    use_ssl: true,
    base_dn: '',
  });
  const [accountForm, setAccountForm] = useState({
    name: '',
    auth_config_id: '',
    username: '',
    password: '',
    description: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const res = await fetchApi('/credentials/v1/credentials/enterprise/users');
      if (res.success) {
        setUsers(res.data.users || []);
      }
    } catch (err) {
      // Error loading users
    }
  };

  const handleOpenEditServer = async (config) => {
    setEditingServer(config);
    try {
      const credRes = await fetchApi(`/credentials/v1/credentials/${config.credential_id}`);
      const cred = credRes.data?.credential || {};
      const secretData = cred.secret_data || {};
      
      setServerForm({
        name: config.name,
        auth_type: config.auth_type,
        server: secretData.server || secretData.host || secretData.domain_controller || '',
        port: secretData.port || '',
        secret_key: '',
        is_default: config.is_default || false,
        domain: secretData.domain || '',
        use_ssl: secretData.use_ssl !== false,
        base_dn: secretData.base_dn || '',
      });
      setShowServerModal(true);
    } catch (err) {
      alert('Error loading server details: ' + err.message);
    }
  };

  const handleCloseServerModal = () => {
    setShowServerModal(false);
    setEditingServer(null);
    setServerForm({ name: '', auth_type: 'tacacs', server: '', port: '', secret_key: '', is_default: false, domain: '', use_ssl: true, base_dn: '' });
  };

  const getDefaultPort = (authType) => {
    switch (authType) {
      case 'tacacs': return 49;
      case 'radius': return 1812;
      case 'ldap': return 389;
      case 'active_directory': return 389;
      default: return 0;
    }
  };

  const handleSaveServer = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const isAD = serverForm.auth_type === 'active_directory';
      const isLDAP = serverForm.auth_type === 'ldap';
      
      const credentialData = isAD ? {
        name: `${serverForm.name} - Server Config`,
        credential_type: 'active_directory',
        description: `Server configuration for ${serverForm.name}`,
        host: serverForm.server,
        domain: serverForm.domain,
        port: parseInt(serverForm.port) || 636,
        use_ssl: serverForm.use_ssl,
        base_dn: serverForm.base_dn,
        password: serverForm.secret_key || undefined,
      } : isLDAP ? {
        name: `${serverForm.name} - Server Config`,
        credential_type: 'ldap',
        description: `Server configuration for ${serverForm.name}`,
        ldap_server: serverForm.server,
        ldap_port: parseInt(serverForm.port) || 389,
        ldap_use_ssl: serverForm.use_ssl,
        base_dn: serverForm.base_dn,
        bind_password: serverForm.secret_key || undefined,
      } : {
        name: `${serverForm.name} - Server Config`,
        credential_type: serverForm.auth_type,
        description: `Server configuration for ${serverForm.name}`,
        [`${serverForm.auth_type}_server`]: serverForm.server,
        [`${serverForm.auth_type}_port`]: parseInt(serverForm.port) || getDefaultPort(serverForm.auth_type),
        [`${serverForm.auth_type}_secret`]: serverForm.secret_key || undefined,
      };

      if (editingServer) {
        if (serverForm.secret_key) {
          await fetchApi(`/credentials/v1/credentials/${editingServer.credential_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentialData),
          });
        }
      } else {
        const credRes = await fetchApi('/credentials/v1/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(credentialData),
        });

        if (!credRes.success) {
          throw new Error(credRes.error?.message || 'Failed to create credential');
        }

        await fetchApi('/credentials/v1/credentials/enterprise/configs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: serverForm.name,
            auth_type: serverForm.auth_type,
            credential_id: credRes.data.credential.id,
            is_default: serverForm.is_default,
          }),
        });
      }

      handleCloseServerModal();
      onRefresh();
    } catch (err) {
      alert('Error saving server: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await fetchApi('/credentials/v1/credentials/enterprise/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...accountForm,
          is_service_account: true,
        }),
      });
      setShowAccountModal(false);
      setAccountForm({ name: '', auth_config_id: '', username: '', password: '', description: '' });
      loadUsers();
    } catch (err) {
      alert('Error creating account: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteServer = async (id) => {
    if (!confirm('Delete this auth server and all associated accounts?')) return;
    try {
      await fetchApi(`/credentials/v1/credentials/enterprise/configs/${id}`, { method: 'DELETE' });
      onRefresh();
      loadUsers();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  const handleDeleteAccount = async (id) => {
    if (!confirm('Delete this service account?')) return;
    try {
      await fetchApi(`/credentials/v1/credentials/enterprise/users/${id}`, { method: 'DELETE' });
      loadUsers();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  const getUsersForConfig = (configId) => users.filter(u => u.auth_config_id === configId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Enterprise Authentication</h2>
          <p className="text-sm text-gray-500">
            Configure TACACS+, RADIUS, LDAP, or Active Directory for device authentication
          </p>
        </div>
        <button
          onClick={() => setShowServerModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          Add Auth Server
        </button>
      </div>

      {/* Empty State */}
      {configs.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-xl border-2 border-dashed">
          <Server className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-700">No Auth Servers Configured</h3>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            Add a TACACS+, RADIUS, LDAP, or Active Directory server to enable 
            enterprise authentication for your scheduled jobs.
          </p>
          <button
            onClick={() => setShowServerModal(true)}
            className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Add Your First Auth Server
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {configs.map((config) => {
            const typeInfo = AUTH_TYPE_LABELS[config.auth_type] || { label: config.auth_type, color: 'bg-gray-100 text-gray-700', icon: Server };
            const TypeIcon = typeInfo.icon;
            const configUsers = getUsersForConfig(config.id);

            return (
              <div key={config.id} className="bg-white border rounded-xl overflow-hidden">
                {/* Server Header */}
                <div className="p-4 bg-gray-50 border-b flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-lg", typeInfo.color)}>
                      <TypeIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{config.name}</span>
                        <span className={cn("px-2 py-0.5 text-xs rounded-full", typeInfo.color)}>
                          {typeInfo.label}
                        </span>
                        {config.is_default && (
                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">Default</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => { setSelectedServer(config); setAccountForm(prev => ({ ...prev, auth_config_id: config.id })); setShowAccountModal(true); }}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg"
                    >
                      <Plus className="w-4 h-4" />
                      Add Account
                    </button>
                    <button
                      onClick={() => handleOpenEditServer(config)}
                      className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                      title="Edit Server"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteServer(config.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                      title="Delete Server"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Service Accounts */}
                <div className="p-4">
                  {configUsers.length === 0 ? (
                    <div className="text-center py-6 text-gray-500">
                      <User className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                      <p className="text-sm">No service accounts configured</p>
                      <button
                        onClick={() => { setSelectedServer(config); setAccountForm(prev => ({ ...prev, auth_config_id: config.id })); setShowAccountModal(true); }}
                        className="text-blue-600 text-sm mt-1 hover:underline"
                      >
                        Add a service account
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Service Accounts</p>
                      {configUsers.map(user => (
                        <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <User className="w-4 h-4 text-gray-400" />
                            <div>
                              <span className="font-medium text-sm">{user.name}</span>
                              <span className="text-gray-500 text-sm ml-2">({user.username})</span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeleteAccount(user.id)}
                            className="p-1.5 text-red-500 hover:bg-red-100 rounded"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add/Edit Server Modal */}
      {showServerModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">{editingServer ? 'Edit Auth Server' : 'Add Auth Server'}</h2>
              <button onClick={handleCloseServerModal} className="p-1 hover:bg-gray-100 rounded">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSaveServer} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Server Name *</label>
                <input
                  type="text"
                  value={serverForm.name}
                  onChange={(e) => setServerForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., Primary TACACS Server"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Auth Type *</label>
                <select
                  value={serverForm.auth_type}
                  onChange={(e) => setServerForm(prev => ({ ...prev, auth_type: e.target.value, port: '' }))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="tacacs">TACACS+</option>
                  <option value="radius">RADIUS</option>
                  <option value="ldap">LDAP</option>
                  <option value="active_directory">Active Directory</option>
                </select>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Server Address *</label>
                  <input
                    type="text"
                    value={serverForm.server}
                    onChange={(e) => setServerForm(prev => ({ ...prev, server: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="192.168.1.100 or hostname"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    value={serverForm.port}
                    onChange={(e) => setServerForm(prev => ({ ...prev, port: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder={String(getDefaultPort(serverForm.auth_type))}
                  />
                </div>
              </div>
              {/* AD/LDAP specific fields */}
              {(serverForm.auth_type === 'active_directory' || serverForm.auth_type === 'ldap') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {serverForm.auth_type === 'active_directory' ? 'Domain' : 'Base DN'} *
                    </label>
                    <input
                      type="text"
                      value={serverForm.auth_type === 'active_directory' ? serverForm.domain : serverForm.base_dn}
                      onChange={(e) => setServerForm(prev => ({ 
                        ...prev, 
                        [serverForm.auth_type === 'active_directory' ? 'domain' : 'base_dn']: e.target.value 
                      }))}
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder={serverForm.auth_type === 'active_directory' ? 'corp.example.com' : 'dc=example,dc=com'}
                      required
                    />
                  </div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={serverForm.use_ssl}
                      onChange={(e) => setServerForm(prev => ({ ...prev, use_ssl: e.target.checked }))}
                      className="rounded"
                    />
                    <span className="text-sm text-gray-700">Use SSL/TLS (LDAPS)</span>
                  </label>
                </>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {serverForm.auth_type === 'ldap' || serverForm.auth_type === 'active_directory' ? 'Bind Password' : 'Shared Secret'} {editingServer ? '(leave blank to keep current)' : '*'}
                </label>
                <input
                  type="password"
                  value={serverForm.secret_key}
                  onChange={(e) => setServerForm(prev => ({ ...prev, secret_key: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  required={!editingServer}
                  placeholder={editingServer ? '••••••••' : ''}
                />
              </div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={serverForm.is_default}
                  onChange={(e) => setServerForm(prev => ({ ...prev, is_default: e.target.checked }))}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">Set as default for this auth type</span>
              </label>
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button type="button" onClick={handleCloseServerModal} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {saving ? 'Saving...' : (editingServer ? 'Save Changes' : 'Create Server')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Account Modal */}
      {showAccountModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">Add Service Account</h2>
              <button onClick={() => setShowAccountModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateAccount} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Account Name *</label>
                <input
                  type="text"
                  value={accountForm.name}
                  onChange={(e) => setAccountForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., Network Automation"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Auth Server *</label>
                <select
                  value={accountForm.auth_config_id}
                  onChange={(e) => setAccountForm(prev => ({ ...prev, auth_config_id: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  required
                >
                  <option value="">Select server...</option>
                  {configs.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({AUTH_TYPE_LABELS[c.auth_type]?.label})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
                <input
                  type="text"
                  value={accountForm.username}
                  onChange={(e) => setAccountForm(prev => ({ ...prev, username: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
                <input
                  type="password"
                  value={accountForm.password}
                  onChange={(e) => setAccountForm(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={accountForm.description}
                  onChange={(e) => setAccountForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="Optional"
                />
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button type="button" onClick={() => setShowAccountModal(false)} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {saving ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export function EnterpriseAuthUsersList({ users, configs, onRefresh }) {
  return <EnterpriseAuthConfigsList configs={configs} credentials={[]} onRefresh={onRefresh} />;
}
