import { useState, useEffect, useMemo } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { fetchApi } from '../../lib/utils';
import {
  Activity,
  RefreshCw,
  Play,
  Pause,
  Settings,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Plus,
  Trash2,
  Edit,
  ChevronDown,
  ChevronRight,
  Loader2,
  Radio,
  Server,
  Zap,
  History,
  Filter,
  Search,
  X
} from 'lucide-react';
import { cn } from '../../lib/utils';

export default function PollingPage() {
  const [configs, setConfigs] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [pollTypes, setPollTypes] = useState([]);
  const [targetTypes, setTargetTypes] = useState([]);

  // Filter state
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Load data
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [configsRes, statusRes, execRes, typesRes, targetsRes] = await Promise.all([
        fetchApi('/monitoring/v1/polling/configs'),
        fetchApi('/monitoring/v1/polling/status'),
        fetchApi('/monitoring/v1/polling/executions?limit=20'),
        fetchApi('/monitoring/v1/polling/poll-types'),
        fetchApi('/monitoring/v1/polling/target-types')
      ]);

      // Handle both wrapped and direct response formats
      const configData = configsRes?.data || configsRes;
      const statusData = statusRes?.data || statusRes;
      const execData = execRes?.data || execRes;
      const typesData = typesRes?.data || typesRes;
      const targetsData = targetsRes?.data || targetsRes;
      
      setConfigs(configData?.configs || (Array.isArray(configData) ? configData : []));
      setStatus(statusData || {});
      setExecutions(execData?.executions || (Array.isArray(execData) ? execData : []));
      setPollTypes(typesData?.poll_types || (Array.isArray(typesData) ? typesData : []));
      setTargetTypes(targetsData?.target_types || (Array.isArray(targetsData) ? targetsData : []));
    } catch (err) {
      console.error('Failed to load polling data:', err);
      setError(err.message || 'Failed to load polling data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filter configs
  const filteredConfigs = useMemo(() => {
    let filtered = configs;

    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(c =>
        c.name?.toLowerCase().includes(searchLower) ||
        c.poll_type?.toLowerCase().includes(searchLower) ||
        (c.tags || []).some(t => t.toLowerCase().includes(searchLower))
      );
    }

    if (statusFilter === 'enabled') {
      filtered = filtered.filter(c => c.enabled);
    } else if (statusFilter === 'disabled') {
      filtered = filtered.filter(c => !c.enabled);
    }

    return filtered;
  }, [configs, search, statusFilter]);

  // Toggle config enabled
  const handleToggle = async (config, e) => {
    e?.stopPropagation();
    try {
      await fetchApi(`/monitoring/v1/polling/configs/${config.id}/toggle`, { method: 'POST' });
      await loadData();
    } catch (err) {
      console.error('Failed to toggle config:', err);
      setError(err.message);
    }
  };

  // Run config now
  const handleRunNow = async (config, e) => {
    e?.stopPropagation();
    try {
      const result = await fetchApi(`/monitoring/v1/polling/configs/${config.id}/run`, { method: 'POST' });
      alert(`Polling triggered: ${result.message || 'Success'}`);
      await loadData();
    } catch (err) {
      console.error('Failed to run config:', err);
      setError(err.message);
    }
  };

  // Delete config
  const handleDelete = async (config, e) => {
    e?.stopPropagation();
    if (!window.confirm(`Delete polling config "${config.name}"?`)) return;
    try {
      await fetchApi(`/monitoring/v1/polling/configs/${config.id}`, { method: 'DELETE' });
      if (selectedConfig?.id === config.id) setSelectedConfig(null);
      await loadData();
    } catch (err) {
      console.error('Failed to delete config:', err);
      setError(err.message);
    }
  };

  // Format interval
  const formatInterval = (seconds) => {
    if (!seconds) return '—';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
  };

  // Format time ago
  const formatTimeAgo = (isoString) => {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  };

  // Get poll type info
  const getPollTypeInfo = (typeId) => {
    return pollTypes.find(t => t.id === typeId) || { name: typeId, description: '' };
  };

  // Get target type info
  const getTargetTypeInfo = (typeId) => {
    return targetTypes.find(t => t.id === typeId) || { name: typeId, description: '' };
  };

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="Polling Management"
        description="Configure and monitor SNMP polling schedules"
      />

      <div className="p-6 space-y-6">
        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Polling Configs List */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Polling Configurations
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4" />
                  Add
                </button>
                <button
                  onClick={loadData}
                  disabled={loading}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                </button>
              </div>
            </div>

            {/* Filters */}
            <div className="px-4 py-2 border-b border-gray-100 flex items-center gap-3 bg-gray-50">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search configs..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="enabled">Enabled</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>

            {error && (
              <div className="px-4 py-3 bg-red-50 border-b border-red-200 text-red-700 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {error}
                <button onClick={() => setError(null)} className="ml-auto">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Config Table */}
            <div className="max-h-[500px] overflow-y-auto">
              {loading && filteredConfigs.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                  Loading configurations...
                </div>
              ) : filteredConfigs.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-400">
                  {configs.length === 0 ? 'No polling configurations yet' : 'No configs match your filters'}
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr className="text-left text-xs text-gray-500 uppercase">
                      <th className="px-3 py-2 font-medium">Status</th>
                      <th className="px-3 py-2 font-medium">Name</th>
                      <th className="px-3 py-2 font-medium">Interval</th>
                      <th className="px-3 py-2 font-medium">Target</th>
                      <th className="px-3 py-2 font-medium">Last Run</th>
                      <th className="px-3 py-2 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredConfigs.map((config) => (
                      <tr
                        key={config.id}
                        onClick={() => setSelectedConfig(config)}
                        className={cn(
                          "hover:bg-gray-50 cursor-pointer",
                          selectedConfig?.id === config.id && "bg-blue-50"
                        )}
                      >
                        <td className="px-3 py-2">
                          <span className={cn(
                            "px-2 py-1 text-xs font-bold rounded",
                            config.enabled ? "bg-green-600 text-white" : "bg-red-600 text-white"
                          )}>
                            {config.enabled ? "ACTIVE" : "INACTIVE"}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-medium text-gray-900">{config.name}</td>
                        <td className="px-3 py-2 text-gray-600">{formatInterval(config.interval_seconds)}</td>
                        <td className="px-3 py-2 text-gray-600">
                          {config.target_manufacturer || config.target_role || config.target_type || 'All'}
                        </td>
                        <td className="px-3 py-2 text-gray-500">
                          {config.last_run_at ? formatTimeAgo(config.last_run_at) : 'Never'}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={(e) => { e.stopPropagation(); setEditingConfig(config); }}
                              className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                              title="Edit"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleRunNow(config, e)}
                              className="p-1.5 text-blue-600 hover:bg-blue-100 rounded"
                              title="Run Now"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleToggle(config, e)}
                              className={cn(
                                "p-1.5 rounded",
                                config.enabled
                                  ? "text-orange-600 hover:bg-orange-100"
                                  : "text-green-600 hover:bg-green-100"
                              )}
                              title={config.enabled ? "Disable" : "Enable"}
                            >
                              {config.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                            </button>
                            <button
                              onClick={(e) => handleDelete(config, e)}
                              className="p-1.5 text-red-600 hover:bg-red-100 rounded"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Right Panel - Details or Recent Executions */}
          <div className="space-y-6">
            {/* Selected Config Details */}
            {selectedConfig && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">Configuration Details</h3>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setEditingConfig(selectedConfig)}
                      className="p-1.5 text-blue-600 hover:bg-blue-100 rounded"
                      title="Edit Configuration"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setSelectedConfig(null)}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>
                </div>
                <div className="p-4 space-y-4 text-sm">
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Name</div>
                    <div className="font-medium text-gray-900">{selectedConfig.name}</div>
                  </div>
                  {selectedConfig.description && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Description</div>
                      <div className="text-gray-700">{selectedConfig.description}</div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Poll Type</div>
                      <div className="text-gray-900">{getPollTypeInfo(selectedConfig.poll_type).name}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Interval</div>
                      <div className="text-gray-900">{formatInterval(selectedConfig.interval_seconds)}</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Target Type</div>
                      <div className="text-gray-900">{getTargetTypeInfo(selectedConfig.target_type).name}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 uppercase">SNMP Community</div>
                      <div className="text-gray-900 font-mono">{selectedConfig.snmp_community || 'public'}</div>
                    </div>
                  </div>
                  {(selectedConfig.target_manufacturer || selectedConfig.target_role || selectedConfig.target_site_name) && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Target Filter</div>
                      <div className="text-gray-900">
                        {selectedConfig.target_manufacturer && `Manufacturer: ${selectedConfig.target_manufacturer}`}
                        {selectedConfig.target_role && `Role: ${selectedConfig.target_role}`}
                        {selectedConfig.target_site_name && `Site: ${selectedConfig.target_site_name}`}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Last Run</div>
                      <div className="text-gray-900">{formatTimeAgo(selectedConfig.last_run_at)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Last Status</div>
                      <div className={cn(
                        "font-medium",
                        selectedConfig.last_run_status === 'success' && "text-green-600",
                        selectedConfig.last_run_status === 'failed' && "text-red-600"
                      )}>
                        {selectedConfig.last_run_status || '—'}
                      </div>
                    </div>
                  </div>
                  {selectedConfig.last_run_devices_polled && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Last Run Stats</div>
                      <div className="text-gray-900">
                        {selectedConfig.last_run_devices_success}/{selectedConfig.last_run_devices_polled} devices successful
                        {selectedConfig.last_run_duration_ms && ` (${selectedConfig.last_run_duration_ms}ms)`}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Recent Executions */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-200">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Recent Executions
                </h3>
              </div>
              <div className="divide-y divide-gray-100 max-h-[300px] overflow-y-auto">
                {executions.length === 0 ? (
                  <div className="px-4 py-6 text-center text-gray-400 text-sm">
                    No recent executions
                  </div>
                ) : (
                  executions.map((exec) => (
                    <div key={exec.id} className="px-3 py-2 hover:bg-gray-50 grid grid-cols-[16px_1fr_60px_70px] gap-2 items-center text-xs">
                      <span>
                        {exec.status === 'success' && <CheckCircle className="w-4 h-4 text-green-500" />}
                        {exec.status === 'failed' && <XCircle className="w-4 h-4 text-red-500" />}
                        {exec.status === 'running' && <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />}
                        {exec.status === 'partial' && <AlertCircle className="w-4 h-4 text-yellow-500" />}
                      </span>
                      <span className="font-medium text-gray-900 truncate">{exec.config_name || 'Unknown'}</span>
                      <span className="text-gray-500 text-right tabular-nums">{exec.devices_success}/{exec.devices_polled}</span>
                      <span className="text-gray-400 text-right tabular-nums">{Math.round(exec.duration_ms || 0)}ms</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Create Config Modal */}
      {showCreateModal && (
        <CreateConfigModal
          pollTypes={pollTypes}
          targetTypes={targetTypes}
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false);
            loadData();
          }}
        />
      )}

      {/* Edit Config Modal */}
      {editingConfig && (
        <EditConfigModal
          config={editingConfig}
          pollTypes={pollTypes}
          targetTypes={targetTypes}
          onClose={() => setEditingConfig(null)}
          onSaved={() => {
            setEditingConfig(null);
            setSelectedConfig(null);
            loadData();
          }}
        />
      )}
    </PageLayout>
  );
}

// Create Config Modal Component
function CreateConfigModal({ pollTypes, targetTypes, onClose, onCreated }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    poll_type: 'snmp_ciena_full',
    target_type: 'manufacturer',
    target_manufacturer: 'Ciena',
    target_role: '',
    target_site_name: '',
    interval_seconds: 300,
    snmp_community: 'public',
    enabled: true,
    tags: []
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      await fetchApi('/monitoring/v1/polling/configs', {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      onCreated();
    } catch (err) {
      setError(err.message || 'Failed to create config');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Create Polling Configuration</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="My Polling Config"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Poll Type *</label>
              <select
                value={formData.poll_type}
                onChange={(e) => setFormData({ ...formData, poll_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select poll type...</option>
                {pollTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
              {formData.poll_type && pollTypes.find(t => t.id === formData.poll_type)?.description && (
                <p className="mt-1 text-xs text-gray-500">
                  {pollTypes.find(t => t.id === formData.poll_type)?.description}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Interval</label>
              <select
                value={formData.interval_seconds}
                onChange={(e) => setFormData({ ...formData, interval_seconds: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={60}>1 minute</option>
                <option value={300}>5 minutes</option>
                <option value={600}>10 minutes</option>
                <option value={900}>15 minutes</option>
                <option value={1800}>30 minutes</option>
                <option value={3600}>1 hour</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Type *</label>
              <select
                value={formData.target_type}
                onChange={(e) => setFormData({ ...formData, target_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {targetTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">SNMP Community</label>
              <input
                type="text"
                value={formData.snmp_community}
                onChange={(e) => setFormData({ ...formData, snmp_community: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="public"
              />
            </div>
          </div>

          {formData.target_type === 'manufacturer' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturer</label>
              <input
                type="text"
                value={formData.target_manufacturer}
                onChange={(e) => setFormData({ ...formData, target_manufacturer: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Ciena"
              />
            </div>
          )}

          {formData.target_type === 'role' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Device Role</label>
              <input
                type="text"
                value={formData.target_role}
                onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Backbone Switch"
              />
            </div>
          )}

          {formData.target_type === 'site' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Site Name</label>
              <input
                type="text"
                value={formData.target_site_name}
                onChange={(e) => setFormData({ ...formData, target_site_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Main Office"
              />
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="enabled" className="text-sm text-gray-700">Enable immediately</label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !formData.name}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                  Creating...
                </>
              ) : (
                'Create Configuration'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Edit Config Modal Component
function EditConfigModal({ config, pollTypes, targetTypes, onClose, onSaved }) {
  const [formData, setFormData] = useState({
    name: config.name || '',
    description: config.description || '',
    poll_type: config.poll_type || 'snmp_ciena_full',
    target_type: config.target_type || 'manufacturer',
    target_manufacturer: config.target_manufacturer || '',
    target_role: config.target_role || '',
    target_site_name: config.target_site_name || '',
    interval_seconds: config.interval_seconds || 300,
    snmp_community: config.snmp_community || 'public',
    snmp_timeout: config.snmp_timeout || 5,
    snmp_retries: config.snmp_retries || 2,
    max_concurrent: config.max_concurrent || 50,
    batch_size: config.batch_size || 25,
    enabled: config.enabled ?? true,
    tags: config.tags || []
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      await fetchApi(`/monitoring/v1/polling/configs/${config.id}`, {
        method: 'PUT',
        body: JSON.stringify(formData)
      });
      onSaved();
    } catch (err) {
      setError(err.message || 'Failed to update config');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white">
          <h2 className="text-lg font-semibold text-gray-900">Edit Polling Configuration</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Polling Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Poll Type</label>
                <select
                  value={formData.poll_type}
                  onChange={(e) => setFormData({ ...formData, poll_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select poll type...</option>
                  {pollTypes.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Interval</label>
                <select
                  value={formData.interval_seconds}
                  onChange={(e) => setFormData({ ...formData, interval_seconds: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={30}>30 seconds</option>
                  <option value={60}>1 minute</option>
                  <option value={120}>2 minutes</option>
                  <option value={300}>5 minutes</option>
                  <option value={600}>10 minutes</option>
                  <option value={900}>15 minutes</option>
                  <option value={1800}>30 minutes</option>
                  <option value={3600}>1 hour</option>
                </select>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Target Selection</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Target Type</label>
                <select
                  value={formData.target_type}
                  onChange={(e) => setFormData({ ...formData, target_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {targetTypes.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              {formData.target_type === 'manufacturer' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturer</label>
                  <input
                    type="text"
                    value={formData.target_manufacturer}
                    onChange={(e) => setFormData({ ...formData, target_manufacturer: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Ciena"
                  />
                </div>
              )}

              {formData.target_type === 'role' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Device Role</label>
                  <input
                    type="text"
                    value={formData.target_role}
                    onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Backbone Switch"
                  />
                </div>
              )}

              {formData.target_type === 'site' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Site Name</label>
                  <input
                    type="text"
                    value={formData.target_site_name}
                    onChange={(e) => setFormData({ ...formData, target_site_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Main Office"
                  />
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">SNMP Settings</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Community String</label>
                <input
                  type="text"
                  value={formData.snmp_community}
                  onChange={(e) => setFormData({ ...formData, snmp_community: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="public"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (sec)</label>
                <input
                  type="number"
                  value={formData.snmp_timeout}
                  onChange={(e) => setFormData({ ...formData, snmp_timeout: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min={1}
                  max={30}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Retries</label>
                <input
                  type="number"
                  value={formData.snmp_retries}
                  onChange={(e) => setFormData({ ...formData, snmp_retries: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min={0}
                  max={5}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Performance</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Concurrent</label>
                <input
                  type="number"
                  value={formData.max_concurrent}
                  onChange={(e) => setFormData({ ...formData, max_concurrent: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min={1}
                  max={200}
                />
                <p className="text-xs text-gray-500 mt-1">Max simultaneous SNMP queries</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Batch Size</label>
                <input
                  type="number"
                  value={formData.batch_size}
                  onChange={(e) => setFormData({ ...formData, batch_size: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min={1}
                  max={100}
                />
                <p className="text-xs text-gray-500 mt-1">Devices per batch</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="edit-enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="edit-enabled" className="text-sm text-gray-700">Enabled</label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !formData.name}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
