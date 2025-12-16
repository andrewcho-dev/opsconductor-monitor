import React, { useState, useEffect } from 'react';
import { 
  Shield, Plus, Search, Check, X, Pencil, Trash2, 
  ChevronDown, ChevronRight, Loader2, Users, Lock, Eye
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
  const { hasPermission, getAuthHeader } = useAuth();
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rolesRes, permsRes] = await Promise.all([
        fetchApi('/api/auth/roles', { headers: getAuthHeader() }),
        fetchApi('/api/auth/permissions', { headers: getAuthHeader() })
      ]);

      if (rolesRes.success) {
        setRoles(rolesRes.data.roles || []);
      }
      if (permsRes.success) {
        setPermissions(permsRes.data.permissions || []);
      }
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const canManageRoles = hasPermission('system.roles.manage');

  return (
    <PageLayout module="system">
      <PageHeader
        title="Roles & Permissions"
        description="Define roles with granular permission assignments"
      />
      <div className="p-6 space-y-6">
        {/* Header Actions */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            {roles.length} roles defined
          </div>
          {canManageRoles && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Create Role
            </button>
          )}
        </div>

        {/* Roles List */}
        <div className="grid gap-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : roles.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border">
              <Shield className="w-12 h-12 mx-auto text-gray-300 mb-3" />
              <p className="text-gray-500">No roles defined</p>
            </div>
          ) : (
            roles.map((role) => (
              <RoleCard
                key={role.id}
                role={role}
                onEdit={() => { setSelectedRole(role); setShowEditModal(true); }}
                canManage={canManageRoles}
              />
            ))
          )}
        </div>

        {/* Permission Reference */}
        <div className="bg-white rounded-xl border">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Permission Reference</h3>
            <p className="text-sm text-gray-500">All available permissions organized by module</p>
          </div>
          <div className="divide-y">
            {Object.entries(PERMISSION_MODULES).map(([key, module]) => (
              <PermissionModuleSection key={key} moduleKey={key} module={module} />
            ))}
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
          onClose={() => { setShowEditModal(false); setSelectedRole(null); }}
          onSave={() => { setShowEditModal(false); setSelectedRole(null); loadData(); }}
          getAuthHeader={getAuthHeader}
        />
      )}
    </PageLayout>
  );
}

function RoleCard({ role, onEdit, canManage }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div 
        className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center",
            role.is_system ? "bg-purple-100" : "bg-blue-100"
          )}>
            <Shield className={cn(
              "w-5 h-5",
              role.is_system ? "text-purple-600" : "text-blue-600"
            )} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-gray-900">{role.display_name}</h4>
              {role.is_system && (
                <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                  System
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">{role.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="flex items-center gap-1 text-sm text-gray-600">
              <Users className="w-4 h-4" />
              {role.user_count || 0} users
            </div>
            <div className="text-xs text-gray-400">
              {role.permission_count || 0} permissions
            </div>
          </div>
          {canManage && !role.is_system && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(); }}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <Pencil className="w-4 h-4 text-gray-500" />
            </button>
          )}
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>
      
      {expanded && (
        <div className="px-6 py-4 bg-gray-50 border-t">
          <h5 className="text-sm font-medium text-gray-700 mb-3">Assigned Permissions</h5>
          {role.permissions && role.permissions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {role.permissions.map((perm, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 text-xs bg-white border rounded-md text-gray-600"
                >
                  {perm}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No permissions assigned</p>
          )}
        </div>
      )}
    </div>
  );
}

function PermissionModuleSection({ moduleKey, module }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{module.icon}</span>
          <span className="font-medium text-gray-900">{module.label}</span>
          <span className="text-xs text-gray-400">({module.permissions.length} permissions)</span>
        </div>
        {expanded ? (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-gray-400" />
        )}
      </button>
      
      {expanded && (
        <div className="px-6 pb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="pb-2 font-medium">Permission</th>
                <th className="pb-2 font-medium">Code</th>
                <th className="pb-2 font-medium">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {module.permissions.map((perm) => (
                <tr key={perm.code}>
                  <td className="py-2 font-medium text-gray-900">{perm.label}</td>
                  <td className="py-2">
                    <code className="px-2 py-0.5 bg-gray-100 rounded text-xs">{perm.code}</code>
                  </td>
                  <td className="py-2 text-gray-500">{perm.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
      const endpoint = isEdit ? `/api/auth/roles/${role.id}` : '/api/auth/roles';
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
