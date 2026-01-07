import React, { useState, useEffect } from 'react';
import { 
  Shield, Plus, Check, X, Pencil, 
  ChevronDown, ChevronRight, Loader2, Users,
  UserPlus, UserMinus
} from 'lucide-react';
import { PageLayout, PageHeader } from '../../components/layout';
import { fetchApi, cn } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';

const PERMISSION_MODULES = {
  devices: {
    label: 'Devices & Inventory',
    icon: '🖥️',
    permissions: [
      { code: 'devices.device.view', label: 'View Devices', description: 'View device list and details' },
      { code: 'devices.device.create', label: 'Create Devices', description: 'Add new devices to inventory' },
      { code: 'devices.device.edit', label: 'Edit Devices', description: 'Modify device properties' },
      { code: 'devices.device.delete', label: 'Delete Devices', description: 'Remove devices from inventory' },
      { code: 'devices.device.connect', label: 'Connect to Devices', description: 'Establish SSH/console connections' },
      { code: 'devices.group.manage', label: 'Manage Groups', description: 'Create and manage device groups' },
    ]
  },
  jobs: {
    label: 'Jobs & Workflows',
    icon: '⚡',
    permissions: [
      { code: 'jobs.job.view', label: 'View Jobs', description: 'View job definitions and history' },
      { code: 'jobs.job.create', label: 'Create Jobs', description: 'Create new job definitions' },
      { code: 'jobs.job.edit', label: 'Edit Jobs', description: 'Modify existing jobs' },
      { code: 'jobs.job.delete', label: 'Delete Jobs', description: 'Remove job definitions' },
      { code: 'jobs.job.run', label: 'Run Jobs', description: 'Execute jobs on devices' },
      { code: 'jobs.job.cancel', label: 'Cancel Jobs', description: 'Stop running jobs' },
      { code: 'jobs.schedule.manage', label: 'Manage Schedules', description: 'Create and manage job schedules' },
      { code: 'jobs.template.manage', label: 'Manage Templates', description: 'Create and manage job templates' },
    ]
  },
  credentials: {
    label: 'Credentials',
    icon: '🔑',
    permissions: [
      { code: 'credentials.credential.view', label: 'View Credentials', description: 'View credential list (not secrets)' },
      { code: 'credentials.credential.create', label: 'Create Credentials', description: 'Add new credentials' },
      { code: 'credentials.credential.edit', label: 'Edit Credentials', description: 'Modify credential properties' },
      { code: 'credentials.credential.delete', label: 'Delete Credentials', description: 'Remove credentials' },
      { code: 'credentials.credential.reveal', label: 'Reveal Secrets', description: 'View credential passwords/keys' },
      { code: 'credentials.credential.use', label: 'Use Credentials', description: 'Use credentials in jobs' },
      { code: 'credentials.group.manage', label: 'Manage Groups', description: 'Manage credential groups' },
      { code: 'credentials.enterprise.manage', label: 'Manage Enterprise Auth', description: 'Configure LDAP/AD/RADIUS' },
    ]
  },
  system: {
    label: 'System Administration',
    icon: '⚙️',
    permissions: [
      { code: 'system.settings.view', label: 'View Settings', description: 'View system configuration' },
      { code: 'system.settings.edit', label: 'Edit Settings', description: 'Modify system configuration' },
      { code: 'system.users.view', label: 'View Users', description: 'View user accounts' },
      { code: 'system.users.create', label: 'Create Users', description: 'Add new user accounts' },
      { code: 'system.users.edit', label: 'Edit Users', description: 'Modify user accounts' },
      { code: 'system.users.delete', label: 'Delete Users', description: 'Remove user accounts' },
      { code: 'system.roles.manage', label: 'Manage Roles', description: 'Create and manage roles' },
      { code: 'system.audit.view', label: 'View Audit Logs', description: 'Access audit and system logs' },
      { code: 'system.backup.manage', label: 'Manage Backups', description: 'Create and restore backups' },
    ]
  },
  reports: {
    label: 'Reports',
    icon: '📊',
    permissions: [
      { code: 'reports.report.view', label: 'View Reports', description: 'Access reports and dashboards' },
      { code: 'reports.report.create', label: 'Create Reports', description: 'Generate new reports' },
      { code: 'reports.report.export', label: 'Export Reports', description: 'Export reports to files' },
    ]
  }
};

export function RolesPage() {
  console.log('RolesPage component mounting...');
  const { hasPermission, getAuthHeader } = useAuth();
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [permissions, setPermissions] = useState([]);
  const [loadingPermissions, setLoadingPermissions] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      console.log('Loading roles...');
      const rolesRes = await fetchApi('/identity/v1/roles', { headers: getAuthHeader() });
      console.log('Roles response:', rolesRes);
      // Handle both wrapped and direct array format
      const rolesList = rolesRes?.data || (Array.isArray(rolesRes) ? rolesRes : []);
      console.log('Setting roles:', rolesList);
      setRoles(rolesList);
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const canManageRoles = hasPermission('system.roles.manage');

  const loadMembers = async (roleId) => {
    setLoadingMembers(true);
    try {
      const res = await fetchApi(`/identity/v1/roles/${roleId}/members`, { headers: getAuthHeader() });
      // New API returns { local_users: [], enterprise_users: [], total: n }
      const localUsers = (res?.local_users || []).map(u => ({ ...u, type: 'local' }));
      const enterpriseUsers = (res?.enterprise_users || []).map(u => ({ ...u, type: 'enterprise' }));
      setMembers([...localUsers, ...enterpriseUsers]);
    } catch (err) {
      console.error('Error loading members:', err);
      setMembers([]);
    } finally {
      setLoadingMembers(false);
    }
  };

  const loadPermissions = async (roleId) => {
    setLoadingPermissions(true);
    try {
      const res = await fetchApi(`/identity/v1/roles/${roleId}/permissions`, { headers: getAuthHeader() });
      // API returns array of permission objects
      setPermissions(Array.isArray(res) ? res : []);
    } catch (err) {
      console.error('Error loading permissions:', err);
      setPermissions([]);
    } finally {
      setLoadingPermissions(false);
    }
  };

  const handleSelectRole = (role) => {
    setSelectedRole(role);
    loadMembers(role.id);
    loadPermissions(role.id);
  };

  // Auto-select first role on load
  useEffect(() => {
    if (roles.length > 0 && !selectedRole) {
      handleSelectRole(roles[0]);
    }
  }, [roles]);

  return (
    <PageLayout module="system">
      <PageHeader
        title="Roles & Permissions"
        description="Manage role-based access control"
      />
      <div className="p-4">
        <div className="flex gap-4 h-[calc(100vh-180px)]">
          {/* Left Panel - Roles List */}
          <div className="w-72 flex-shrink-0 bg-white rounded-lg border overflow-hidden flex flex-col">
            <div className="p-3 border-b bg-gray-50 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Roles ({roles.length})</span>
              {canManageRoles && (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="p-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
                  title="Create Role"
                >
                  <Plus className="w-4 h-4" />
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                </div>
              ) : (
                <div className="divide-y">
                  {roles.map((role) => (
                    <button
                      key={role.id}
                      onClick={() => handleSelectRole(role)}
                      className={cn(
                        "w-full text-left px-3 py-2.5 hover:bg-gray-50 transition-colors",
                        selectedRole?.id === role.id && "bg-blue-50 border-l-2 border-blue-600"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Shield className={cn(
                          "w-4 h-4",
                          role.is_system ? "text-purple-600" : "text-blue-600"
                        )} />
                        <span className="font-medium text-sm text-gray-900">{role.display_name}</span>
                        {role.is_system && (
                          <span className="px-1.5 py-0.5 text-[10px] bg-purple-100 text-purple-700 rounded">
                            System
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 ml-6">
                        <span>{role.user_count || 0} users</span>
                        <span>{role.permission_count || 0} perms</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Role Details */}
          <div className="flex-1 bg-white rounded-lg border overflow-hidden flex flex-col">
            {selectedRole ? (
              <>
                {/* Role Header */}
                <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">{selectedRole.display_name}</h3>
                    <p className="text-sm text-gray-500">{selectedRole.description}</p>
                  </div>
                  {canManageRoles && !selectedRole.is_system && (
                    <button
                      onClick={() => setShowEditModal(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-100"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      Edit
                    </button>
                  )}
                </div>

                {/* Two Column Layout */}
                <div className="flex-1 overflow-hidden flex">
                  {/* Members Column */}
                  <div className="w-1/2 border-r flex flex-col">
                    <div className="px-4 py-2 border-b bg-gray-50">
                      <span className="text-sm font-medium text-gray-700">Members ({members.length})</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3">
                      <RoleMembersPanel
                        roleId={selectedRole.id}
                        members={members}
                        loading={loadingMembers}
                        canManage={canManageRoles}
                        getAuthHeader={getAuthHeader}
                        onRefresh={() => { loadMembers(selectedRole.id); loadData(); }}
                      />
                    </div>
                  </div>

                  {/* Permissions Column */}
                  <div className="w-1/2 flex flex-col">
                    <div className="px-4 py-2 border-b bg-gray-50">
                      <span className="text-sm font-medium text-gray-700">Permissions ({permissions.length})</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3">
                      {loadingPermissions ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                        </div>
                      ) : permissions.length > 0 ? (
                        <div className="space-y-3">
                          {/* Group permissions by module */}
                          {Object.entries(
                            permissions.reduce((acc, p) => {
                              const mod = p.module || 'other';
                              if (!acc[mod]) acc[mod] = [];
                              acc[mod].push(p);
                              return acc;
                            }, {})
                          ).map(([module, perms]) => (
                            <div key={module}>
                              <div className="text-xs font-semibold text-gray-500 uppercase mb-1">
                                {module}
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {perms.map((perm) => (
                                  <span
                                    key={perm.id}
                                    className="px-2 py-0.5 text-xs bg-gray-100 rounded text-gray-700"
                                    title={perm.description}
                                  >
                                    {perm.display_name || perm.code}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400 text-center py-4">No permissions assigned</p>
                      )}
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <Shield className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>Select a role to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Role Modal */}
      {showCreateModal && (
        <RoleModal
          onClose={() => setShowCreateModal(false)}
          onSave={() => { setShowCreateModal(false); loadData(); }}
          getAuthHeader={getAuthHeader}
        />
      )}

      {/* Edit Role Modal */}
      {showEditModal && selectedRole && (
        <RoleModal
          role={selectedRole}
          onClose={() => { setShowEditModal(false); }}
          onSave={() => { setShowEditModal(false); loadData(); }}
          getAuthHeader={getAuthHeader}
        />
      )}
    </PageLayout>
  );
}

// Compact members panel component
function RoleMembersPanel({ roleId, members, loading, canManage, getAuthHeader, onRefresh }) {
  const [showAddMember, setShowAddMember] = useState(false);
  const [newMember, setNewMember] = useState({ username: '', type: 'enterprise', display_name: '' });
  const [addingMember, setAddingMember] = useState(false);
  const [memberError, setMemberError] = useState('');

  const handleAddMember = async () => {
    if (!newMember.username.trim()) {
      setMemberError('Username required');
      return;
    }
    setMemberError('');
    setAddingMember(true);
    try {
      const res = await fetchApi(`/identity/v1/roles/${roleId}/members`, {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newMember.username,
          auth_type: newMember.type,
          display_name: newMember.display_name || newMember.username
        })
      });
      if (res.success) {
        setNewMember({ username: '', type: 'enterprise', display_name: '' });
        setShowAddMember(false);
        onRefresh();
      } else {
        setMemberError(res.error?.message || 'Failed');
      }
    } catch (err) {
      setMemberError(err.message || 'Failed');
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (username, type) => {
    if (!confirm(`Remove ${username}?`)) return;
    try {
      await fetchApi(`/identity/v1/roles/${roleId}/members/${encodeURIComponent(username)}?auth_type=${type}`, {
        method: 'DELETE',
        headers: getAuthHeader()
      });
      onRefresh();
    } catch (err) {
      console.error('Error:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Add Member */}
      {canManage && (
        <div className="mb-3">
          {!showAddMember ? (
            <button
              onClick={() => setShowAddMember(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
            >
              <UserPlus className="w-3.5 h-3.5" />
              Add Member
            </button>
          ) : (
            <div className="p-2.5 bg-gray-50 rounded-lg space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newMember.username}
                  onChange={(e) => setNewMember(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="Username"
                  className="flex-1 px-2 py-1.5 text-xs border rounded"
                />
                <select
                  value={newMember.type}
                  onChange={(e) => setNewMember(prev => ({ ...prev, type: e.target.value }))}
                  className="px-2 py-1.5 text-xs border rounded"
                >
                  <option value="enterprise">AD</option>
                  <option value="local">Local</option>
                </select>
              </div>
              {memberError && <p className="text-xs text-red-600">{memberError}</p>}
              <div className="flex gap-1.5">
                <button
                  onClick={handleAddMember}
                  disabled={addingMember}
                  className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {addingMember ? '...' : 'Add'}
                </button>
                <button
                  onClick={() => { setShowAddMember(false); setMemberError(''); }}
                  className="px-2 py-1 text-xs text-gray-600 hover:bg-gray-200 rounded"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Members List */}
      {members.length === 0 ? (
        <div className="text-center py-4 text-gray-400 text-sm">
          No members
        </div>
      ) : (
        members.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between p-2 bg-gray-50 rounded"
          >
            <div className="flex items-center gap-2">
              <div className={cn(
                "w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium",
                member.type === 'enterprise' ? "bg-purple-500" : "bg-blue-500"
              )}>
                {(member.display_name || member.username || '?')[0].toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium text-gray-900">
                    {member.display_name || member.username}
                  </span>
                  <span className={cn(
                    "px-1 py-0.5 text-[10px] rounded",
                    member.type === 'enterprise'
                      ? "bg-purple-100 text-purple-700"
                      : "bg-blue-100 text-blue-700"
                  )}>
                    {member.type === 'enterprise' ? 'AD' : 'Local'}
                  </span>
                </div>
                <span className="text-xs text-gray-500">@{member.username}</span>
              </div>
            </div>
            {canManage && (
              <button
                onClick={() => handleRemoveMember(member.username, member.type)}
                className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                title="Remove"
              >
                <UserMinus className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function RoleModal({ role, onClose, onSave, getAuthHeader }) {
  const isEdit = !!role;
  const [formData, setFormData] = useState({
    name: role?.name || '',
    display_name: role?.display_name || '',
    description: role?.description || '',
  });
  const [selectedPermissions, setSelectedPermissions] = useState(
    new Set(role?.permissions || [])
  );
  const [expandedModules, setExpandedModules] = useState(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const toggleModule = (moduleKey) => {
    setExpandedModules(prev => {
      const next = new Set(prev);
      if (next.has(moduleKey)) {
        next.delete(moduleKey);
      } else {
        next.add(moduleKey);
      }
      return next;
    });
  };

  const togglePermission = (code) => {
    setSelectedPermissions(prev => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const toggleAllInModule = (moduleKey) => {
    const module = PERMISSION_MODULES[moduleKey];
    const allCodes = module.permissions.map(p => p.code);
    const allSelected = allCodes.every(code => selectedPermissions.has(code));
    
    setSelectedPermissions(prev => {
      const next = new Set(prev);
      if (allSelected) {
        allCodes.forEach(code => next.delete(code));
      } else {
        allCodes.forEach(code => next.add(code));
      }
      return next;
    });
  };

  const handleSave = async () => {
    setError('');
    
    if (!formData.name || !formData.display_name) {
      setError('Name and display name are required');
      return;
    }

    setSaving(true);
    try {
      const endpoint = isEdit ? `/identity/v1/roles/${role.id}` : '/identity/v1/roles';
      const method = isEdit ? 'PUT' : 'POST';
      
      const res = await fetchApi(endpoint, {
        method,
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          permissions: Array.from(selectedPermissions)
        })
      });

      if (res.success) {
        onSave();
      } else {
        setError(res.error?.message || 'Failed to save role');
      }
    } catch (err) {
      setError(err.message || 'Failed to save role');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0">
          <h2 className="text-lg font-semibold">{isEdit ? 'Edit Role' : 'Create Role'}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role Name (internal) *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value.toLowerCase().replace(/\s+/g, '_') }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., network_operator"
                  disabled={isEdit}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name *
                </label>
                <input
                  type="text"
                  value={formData.display_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., Network Operator"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                rows={2}
                placeholder="Describe what this role is for..."
              />
            </div>

            {/* Permissions */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900">Permissions</h3>
                <span className="text-sm text-gray-500">
                  {selectedPermissions.size} selected
                </span>
              </div>
              
              <div className="border rounded-lg divide-y">
                {Object.entries(PERMISSION_MODULES).map(([key, module]) => {
                  const allCodes = module.permissions.map(p => p.code);
                  const selectedCount = allCodes.filter(c => selectedPermissions.has(c)).length;
                  const allSelected = selectedCount === allCodes.length;
                  const someSelected = selectedCount > 0 && selectedCount < allCodes.length;
                  const isExpanded = expandedModules.has(key);

                  return (
                    <div key={key}>
                      <div className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                        <button
                          type="button"
                          onClick={() => toggleModule(key)}
                          className="flex items-center gap-3 flex-1"
                        >
                          <span className="text-lg">{module.icon}</span>
                          <span className="font-medium">{module.label}</span>
                          <span className="text-xs text-gray-400">
                            ({selectedCount}/{allCodes.length})
                          </span>
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => toggleAllInModule(key)}
                          className={cn(
                            "px-3 py-1 text-xs rounded-full",
                            allSelected
                              ? "bg-blue-100 text-blue-700"
                              : someSelected
                              ? "bg-blue-50 text-blue-600"
                              : "bg-gray-100 text-gray-600"
                          )}
                        >
                          {allSelected ? 'Deselect All' : 'Select All'}
                        </button>
                      </div>
                      
                      {isExpanded && (
                        <div className="px-4 pb-3 bg-gray-50">
                          <div className="grid grid-cols-2 gap-2">
                            {module.permissions.map((perm) => (
                              <label
                                key={perm.code}
                                className={cn(
                                  "flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors",
                                  selectedPermissions.has(perm.code)
                                    ? "bg-blue-50 border border-blue-200"
                                    : "bg-white border border-gray-200 hover:border-gray-300"
                                )}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedPermissions.has(perm.code)}
                                  onChange={() => togglePermission(perm.code)}
                                  className="mt-0.5 rounded"
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-sm text-gray-900">
                                    {perm.label}
                                  </div>
                                  <div className="text-xs text-gray-500 mt-0.5">
                                    {perm.description}
                                  </div>
                                </div>
                              </label>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t flex-shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Role'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default RolesPage;
