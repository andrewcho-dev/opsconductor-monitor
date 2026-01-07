/**
 * Dependencies Management Page
 * 
 * Manage device dependency relationships for alert correlation.
 */

import { useState, useCallback } from 'react';
import { 
  RefreshCw, Plus, Trash2, Network, Zap, Server, 
  ArrowRight, Search, X
} from 'lucide-react';
import { useDependencies, useDependencyActions } from '../hooks/useDependencies';

const DEPENDENCY_TYPES = [
  { value: 'network', label: 'Network', icon: Network, description: 'Network path dependency' },
  { value: 'power', label: 'Power', icon: Zap, description: 'Power supply dependency' },
  { value: 'service', label: 'Service', icon: Server, description: 'Service dependency' },
];

function AddDependencyModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    device_ip: '',
    depends_on_ip: '',
    dependency_type: 'network',
    description: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.device_ip || !formData.depends_on_ip) {
      setError('Both device IPs are required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await onCreate(formData);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Add Dependency
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded text-red-700 dark:text-red-300 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Device IP (depends on upstream)
            </label>
            <input
              type="text"
              value={formData.device_ip}
              onChange={(e) => setFormData({ ...formData, device_ip: e.target.value })}
              placeholder="10.1.1.10"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>

          <div className="flex items-center justify-center">
            <div className="flex items-center gap-2 text-gray-400">
              <span className="text-sm">depends on</span>
              <ArrowRight className="h-4 w-4" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Upstream Device IP
            </label>
            <input
              type="text"
              value={formData.depends_on_ip}
              onChange={(e) => setFormData({ ...formData, depends_on_ip: e.target.value })}
              placeholder="10.1.1.1"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Dependency Type
            </label>
            <div className="grid grid-cols-3 gap-2">
              {DEPENDENCY_TYPES.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFormData({ ...formData, dependency_type: value })}
                  className={`flex flex-col items-center gap-1 p-3 rounded border ${
                    formData.dependency_type === value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-sm">{label}</span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description (optional)
            </label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="e.g., Connected via Switch-1"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Creating...' : 'Create Dependency'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DependencyRow({ dependency, onDelete, deleting }) {
  const typeInfo = DEPENDENCY_TYPES.find(t => t.value === dependency.dependency_type) || DEPENDENCY_TYPES[0];
  const TypeIcon = typeInfo.icon;

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <TypeIcon className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
            {dependency.dependency_type}
          </span>
        </div>
      </td>
      <td className="px-4 py-3">
        <div>
          <p className="font-mono text-sm text-gray-900 dark:text-white">
            {dependency.device_ip}
          </p>
          {dependency.device_name && (
            <p className="text-xs text-gray-500">{dependency.device_name}</p>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-center">
        <ArrowRight className="h-4 w-4 text-gray-400 mx-auto" />
      </td>
      <td className="px-4 py-3">
        <div>
          <p className="font-mono text-sm text-gray-900 dark:text-white">
            {dependency.depends_on_ip}
          </p>
          {dependency.depends_on_name && (
            <p className="text-xs text-gray-500">{dependency.depends_on_name}</p>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        {dependency.description || '-'}
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={() => onDelete(dependency.id)}
          disabled={deleting === dependency.id}
          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded disabled:opacity-50"
          title="Delete"
        >
          {deleting === dependency.id ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
        </button>
      </td>
    </tr>
  );
}

export function DependenciesPage() {
  const { dependencies, loading, error, filters, setFilters, pagination, setPage, refresh } = useDependencies();
  const { createDependency, deleteDependency } = useDependencyActions();
  
  const [showAddModal, setShowAddModal] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [searchValue, setSearchValue] = useState('');

  const handleCreate = async (data) => {
    await createDependency(data);
    refresh();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this dependency?')) return;
    
    setDeleting(id);
    try {
      await deleteDependency(id);
      refresh();
    } catch (err) {
      console.error('Failed to delete:', err);
    } finally {
      setDeleting(null);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setFilters({ device_ip: searchValue || null });
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Dependencies
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manage device relationships for alert correlation
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Add Dependency
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="mb-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                placeholder="Filter by device IP..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Filter
            </button>
            {filters.device_ip && (
              <button
                type="button"
                onClick={() => {
                  setSearchValue('');
                  setFilters({ device_ip: null });
                }}
                className="px-4 py-2 text-gray-500 hover:text-gray-700"
              >
                Clear
              </button>
            )}
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        {/* Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {loading && dependencies.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : dependencies.length === 0 ? (
            <div className="text-center py-12">
              <Network className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No dependencies configured</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="mt-3 text-blue-600 hover:underline"
              >
                Add your first dependency
              </button>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-12"></th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Depends On</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase w-16">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {dependencies.map((dep) => (
                  <DependencyRow
                    key={dep.id}
                    dependency={dep}
                    onDelete={handleDelete}
                    deleting={deleting}
                  />
                ))}
              </tbody>
            </table>
          )}

          {/* Pagination */}
          {pagination.pages > 1 && (
            <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <span className="text-sm text-gray-500">
                {pagination.total} dependencies
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(pagination.page - 1)}
                  disabled={pagination.page <= 1}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm">
                  Page {pagination.page} of {pagination.pages}
                </span>
                <button
                  onClick={() => setPage(pagination.page + 1)}
                  disabled={pagination.page >= pagination.pages}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Add Modal */}
        {showAddModal && (
          <AddDependencyModal
            onClose={() => setShowAddModal(false)}
            onCreate={handleCreate}
          />
        )}
      </div>
    </div>
  );
}

export default DependenciesPage;
