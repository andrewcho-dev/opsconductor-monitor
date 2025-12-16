import React, { useState, useEffect } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { 
  Plus, Search, Filter, RefreshCw, Download, Upload,
  Key, KeyRound, Terminal, Shield, FileKey, Clock,
  AlertTriangle, CheckCircle, XCircle, Eye, EyeOff,
  Pencil, Trash2, History, MoreVertical, Copy,
  FolderOpen, Calendar, User, Server, Activity
} from 'lucide-react';
import { PageLayout } from '../../components/layout/PageLayout';
import { fetchApi } from '../../lib/api';
import { cn } from '../../lib/utils';

const CREDENTIAL_TYPES = {
  ssh: { label: 'SSH', icon: Terminal, color: 'bg-blue-100 text-blue-700 border-blue-200' },
  winrm: { label: 'WinRM', icon: Shield, color: 'bg-cyan-100 text-cyan-700 border-cyan-200' },
  snmp: { label: 'SNMP', icon: Server, color: 'bg-green-100 text-green-700 border-green-200' },
  api_key: { label: 'API Key', icon: Key, color: 'bg-purple-100 text-purple-700 border-purple-200' },
  password: { label: 'Password', icon: KeyRound, color: 'bg-orange-100 text-orange-700 border-orange-200' },
  certificate: { label: 'Certificate', icon: FileKey, color: 'bg-pink-100 text-pink-700 border-pink-200' },
  pki: { label: 'PKI', icon: FileKey, color: 'bg-rose-100 text-rose-700 border-rose-200' },
};

const STATUS_COLORS = {
  active: 'bg-green-100 text-green-700',
  disabled: 'bg-gray-100 text-gray-600',
  expired: 'bg-red-100 text-red-700',
  expiring_soon: 'bg-amber-100 text-amber-700',
  revoked: 'bg-red-100 text-red-700',
};

export function CredentialVaultPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Determine active view from path
  const getActiveView = () => {
    if (location.pathname.includes('/groups')) return 'groups';
    if (location.pathname.includes('/expiring')) return 'expiring';
    if (location.pathname.includes('/audit')) return 'audit';
    return 'credentials';
  };
  
  const [activeView, setActiveView] = useState(getActiveView());
  const [credentials, setCredentials] = useState([]);
  const [groups, setGroups] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingCredential, setEditingCredential] = useState(null);
  const [selectedCredential, setSelectedCredential] = useState(null);

  useEffect(() => {
    setActiveView(getActiveView());
  }, [location.pathname]);

  useEffect(() => {
    loadData();
  }, [activeView, typeFilter, statusFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Always load statistics
      const statsRes = await fetchApi('/api/credentials/statistics');
      if (statsRes.success) {
        setStatistics(statsRes.data.statistics);
      }

      if (activeView === 'credentials' || activeView === 'expiring') {
        let url = '/api/credentials';
        const params = new URLSearchParams();
        if (typeFilter) params.append('type', typeFilter);
        if (statusFilter) params.append('status', statusFilter);
        if (activeView === 'expiring') {
          url = '/api/credentials/expiring?days=30';
        } else if (params.toString()) {
          url += '?' + params.toString();
        }
        
        const res = await fetchApi(url);
        if (res.success) {
          setCredentials(activeView === 'expiring' ? res.data.expiring : res.data.credentials);
        }
      } else if (activeView === 'groups') {
        const res = await fetchApi('/api/credentials/groups');
        if (res.success) {
          setGroups(res.data.groups);
        }
      } else if (activeView === 'audit') {
        const res = await fetchApi('/api/credentials/audit?limit=100');
        if (res.success) {
          setAuditLog(res.data.entries);
        }
      }
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this credential?')) return;
    try {
      await fetchApi(`/api/credentials/${id}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting credential: ' + err.message);
    }
  };

  const filteredCredentials = credentials.filter(cred => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      cred.name?.toLowerCase().includes(query) ||
      cred.description?.toLowerCase().includes(query) ||
      cred.username?.toLowerCase().includes(query) ||
      cred.owner?.toLowerCase().includes(query)
    );
  });

  return (
    <PageLayout module="credentials">
      <div className="p-6 space-y-6">
        {/* Header with Stats */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Credential Vault</h1>
            <p className="text-sm text-gray-500 mt-1">
              Secure storage for all authentication credentials
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="Refresh"
            >
              <RefreshCw className={cn("w-5 h-5", loading && "animate-spin")} />
            </button>
            <button
              onClick={() => { setEditingCredential(null); setShowModal(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Credential
            </button>
          </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <StatCard
              label="Total"
              value={statistics.total}
              icon={KeyRound}
              color="blue"
            />
            <StatCard
              label="Active"
              value={statistics.by_status?.active || 0}
              icon={CheckCircle}
              color="green"
            />
            <StatCard
              label="Expiring Soon"
              value={statistics.expiration?.expiring_30_days || 0}
              icon={Clock}
              color="amber"
            />
            <StatCard
              label="Expired"
              value={statistics.expiration?.expired || 0}
              icon={XCircle}
              color="red"
            />
            <StatCard
              label="Used (30d)"
              value={statistics.usage?.used_last_30_days || 0}
              icon={Activity}
              color="purple"
            />
            <StatCard
              label="Unused (90d)"
              value={statistics.usage?.unused_90_days || 0}
              icon={AlertTriangle}
              color="gray"
            />
          </div>
        )}

        {/* Filters */}
        {activeView === 'credentials' && (
          <div className="flex flex-wrap items-center gap-4 bg-white p-4 rounded-lg border">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search credentials..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg"
                />
              </div>
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg"
            >
              <option value="">All Types</option>
              {Object.entries(CREDENTIAL_TYPES).map(([key, { label }]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
        )}

        {/* Main Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : activeView === 'credentials' || activeView === 'expiring' ? (
          <CredentialsList
            credentials={filteredCredentials}
            onEdit={(cred) => { setEditingCredential(cred); setShowModal(true); }}
            onDelete={handleDelete}
            onViewHistory={(cred) => setSelectedCredential(cred)}
            isExpiring={activeView === 'expiring'}
          />
        ) : activeView === 'groups' ? (
          <GroupsList groups={groups} onRefresh={loadData} />
        ) : activeView === 'audit' ? (
          <AuditLogView entries={auditLog} />
        ) : null}
      </div>

      {/* Credential Modal */}
      {showModal && (
        <CredentialModal
          credential={editingCredential}
          onClose={() => setShowModal(false)}
          onSave={() => { setShowModal(false); loadData(); }}
        />
      )}

      {/* History Modal */}
      {selectedCredential && (
        <CredentialHistoryModal
          credential={selectedCredential}
          onClose={() => setSelectedCredential(null)}
        />
      )}
    </PageLayout>
  );
}

function StatCard({ label, value, icon: Icon, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    amber: 'bg-amber-50 text-amber-600 border-amber-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
    gray: 'bg-gray-50 text-gray-600 border-gray-200',
  };
  
  return (
    <div className={cn("p-4 rounded-lg border", colors[color])}>
      <div className="flex items-center justify-between">
        <Icon className="w-5 h-5 opacity-70" />
        <span className="text-2xl font-bold">{value}</span>
      </div>
      <p className="text-sm mt-1 opacity-80">{label}</p>
    </div>
  );
}

function CredentialsList({ credentials, onEdit, onDelete, onViewHistory, isExpiring }) {
  if (credentials.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border">
        <KeyRound className="w-12 h-12 mx-auto text-gray-300" />
        <p className="mt-4 text-gray-500">
          {isExpiring ? 'No credentials expiring soon' : 'No credentials found'}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Username</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Expiration</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Last Used</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {credentials.map((cred) => {
            const typeInfo = CREDENTIAL_TYPES[cred.credential_type] || CREDENTIAL_TYPES.password;
            const TypeIcon = typeInfo.icon;
            
            return (
              <tr key={cred.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{cred.name}</div>
                  {cred.description && (
                    <div className="text-sm text-gray-500 truncate max-w-xs">{cred.description}</div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", typeInfo.color)}>
                    <TypeIcon className="w-3 h-3" />
                    {typeInfo.label}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  {cred.username || '-'}
                </td>
                <td className="px-4 py-3">
                  <span className={cn("px-2 py-1 rounded-full text-xs font-medium", STATUS_COLORS[cred.status] || STATUS_COLORS.active)}>
                    {cred.status || 'active'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  {cred.valid_until ? (
                    <div className={cn(
                      cred.expiration_status === 'expired' && 'text-red-600',
                      cred.expiration_status === 'expiring_soon' && 'text-amber-600'
                    )}>
                      <div>{new Date(cred.valid_until).toLocaleDateString()}</div>
                      {cred.days_until_expiration !== null && (
                        <div className="text-xs">
                          {cred.days_until_expiration < 0 
                            ? `Expired ${Math.abs(cred.days_until_expiration)} days ago`
                            : `${cred.days_until_expiration} days left`}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400">No expiration</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {cred.last_used_at 
                    ? new Date(cred.last_used_at).toLocaleDateString()
                    : 'Never'}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => onViewHistory(cred)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                      title="View History"
                    >
                      <History className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onEdit(cred)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                      title="Edit"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(cred.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function GroupsList({ groups, onRefresh }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {groups.length === 0 ? (
        <div className="col-span-full text-center py-12 bg-white rounded-lg border">
          <FolderOpen className="w-12 h-12 mx-auto text-gray-300" />
          <p className="mt-4 text-gray-500">No credential groups</p>
        </div>
      ) : (
        groups.map((group) => (
          <div key={group.id} className="bg-white rounded-lg border p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{group.name}</h3>
                {group.description && (
                  <p className="text-sm text-gray-500 mt-1">{group.description}</p>
                )}
              </div>
              <FolderOpen className="w-5 h-5 text-gray-400" />
            </div>
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-gray-500">
                {group.credentials?.length || 0} credentials
              </p>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function AuditLogView({ entries }) {
  const getActionColor = (action) => {
    switch (action) {
      case 'created': return 'bg-green-100 text-green-700';
      case 'updated': return 'bg-blue-100 text-blue-700';
      case 'deleted': return 'bg-red-100 text-red-700';
      case 'accessed': return 'bg-purple-100 text-purple-700';
      case 'used': return 'bg-cyan-100 text-cyan-700';
      case 'expired': return 'bg-amber-100 text-amber-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Time</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Action</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Credential</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Performed By</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Target</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-gray-500">
                  No audit entries found
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                    {new Date(entry.performed_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("px-2 py-1 rounded-full text-xs font-medium", getActionColor(entry.action))}>
                      {entry.action}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{entry.credential_name}</div>
                    <div className="text-xs text-gray-500">{entry.credential_type}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {entry.performed_by || 'system'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {entry.target_device || '-'}
                  </td>
                  <td className="px-4 py-3">
                    {entry.success ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" title={entry.error_message} />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
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
    domain: '',
    winrm_transport: 'ntlm',
    winrm_port: 5985,
    certificate: '',
    ca_certificate: '',
    valid_until: credential?.valid_until ? credential.valid_until.split('T')[0] : '',
    category: credential?.category || '',
    environment: credential?.environment || '',
    owner: credential?.owner || '',
    notes: credential?.notes || '',
  });
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...formData };
      if (payload.valid_until) {
        payload.valid_until = new Date(payload.valid_until).toISOString();
      }
      
      if (credential) {
        await fetchApi(`/api/credentials/${credential.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetchApi('/api/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
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
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{credential ? 'Edit Credential' : 'Add Credential'}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <XCircle className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="e.g., Production SSH Key"
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
                {Object.entries(CREDENTIAL_TYPES).map(([key, { label }]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="">Select category</option>
                <option value="network">Network</option>
                <option value="server">Server</option>
                <option value="cloud">Cloud</option>
                <option value="database">Database</option>
                <option value="application">Application</option>
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

          {/* Type-specific fields */}
          {(formData.credential_type === 'ssh' || formData.credential_type === 'password') && (
            <>
              <div className="grid grid-cols-2 gap-4">
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
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg pr-10"
                      placeholder={credential ? '(unchanged)' : ''}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
              {formData.credential_type === 'ssh' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Private Key</label>
                  <textarea
                    value={formData.private_key}
                    onChange={(e) => setFormData(prev => ({ ...prev, private_key: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-24"
                    placeholder="-----BEGIN RSA PRIVATE KEY-----"
                  />
                </div>
              )}
            </>
          )}

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
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
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
            </>
          )}

          {(formData.credential_type === 'certificate' || formData.credential_type === 'pki') && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Certificate (PEM)</label>
                <textarea
                  value={formData.certificate}
                  onChange={(e) => setFormData(prev => ({ ...prev, certificate: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-32"
                  placeholder="-----BEGIN CERTIFICATE-----"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Private Key (PEM)</label>
                <textarea
                  value={formData.private_key}
                  onChange={(e) => setFormData(prev => ({ ...prev, private_key: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-32"
                  placeholder="-----BEGIN PRIVATE KEY-----"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Key Passphrase (optional)</label>
                <input
                  type="password"
                  value={formData.passphrase}
                  onChange={(e) => setFormData(prev => ({ ...prev, passphrase: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </>
          )}

          {formData.credential_type === 'api_key' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  type="password"
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
            </div>
          )}

          {/* Metadata */}
          <div className="border-t pt-4 mt-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Metadata</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Environment</label>
                <select
                  value={formData.environment}
                  onChange={(e) => setFormData(prev => ({ ...prev, environment: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="">Select environment</option>
                  <option value="production">Production</option>
                  <option value="staging">Staging</option>
                  <option value="development">Development</option>
                  <option value="testing">Testing</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expiration Date</label>
                <input
                  type="date"
                  value={formData.valid_until}
                  onChange={(e) => setFormData(prev => ({ ...prev, valid_until: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
                <input
                  type="text"
                  value={formData.owner}
                  onChange={(e) => setFormData(prev => ({ ...prev, owner: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., Network Team"
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg h-20"
                placeholder="Additional notes..."
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : credential ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CredentialHistoryModal({ credential, onClose }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, [credential.id]);

  const loadHistory = async () => {
    try {
      const res = await fetchApi(`/api/credentials/${credential.id}/history`);
      if (res.success) {
        setHistory(res.data.history);
      }
    } catch (err) {
      console.error('Error loading history:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">Credential History</h2>
            <p className="text-sm text-gray-500">{credential.name}</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <XCircle className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No history found</p>
          ) : (
            <div className="space-y-4">
              {history.map((entry) => (
                <div key={entry.id} className="flex gap-4 pb-4 border-b last:border-0">
                  <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-blue-500" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">{entry.action}</span>
                      {!entry.success && (
                        <span className="text-xs text-red-600">Failed</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{entry.action_detail}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <span>{new Date(entry.performed_at).toLocaleString()}</span>
                      <span>by {entry.performed_by || 'system'}</span>
                      {entry.target_device && <span>→ {entry.target_device}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CredentialVaultPage;
