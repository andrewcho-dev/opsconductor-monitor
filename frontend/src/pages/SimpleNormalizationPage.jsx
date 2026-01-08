/**
 * Simple Normalization Rules Page
 * 
 * All mappings in one unified table - easier to understand and manage.
 */

import { useState } from 'react';
import { 
  Settings, Plus, Edit, Trash2, Save, X,
  AlertTriangle, Check, Filter, RefreshCw
} from 'lucide-react';
import { PageLayout } from '../components/layout/PageLayout';
import { fetchApi } from '../lib/utils';

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical', color: 'text-red-600 bg-red-100' },
  { value: 'major', label: 'Major', color: 'text-orange-600 bg-orange-100' },
  { value: 'minor', label: 'Minor', color: 'text-yellow-600 bg-yellow-100' },
  { value: 'warning', label: 'Warning', color: 'text-blue-600 bg-blue-100' },
  { value: 'info', label: 'Info', color: 'text-gray-600 bg-gray-100' },
  { value: 'clear', label: 'Clear', color: 'text-green-600 bg-green-100' },
];

const CATEGORY_OPTIONS = [
  'network', 'power', 'video', 'wireless', 'security',
  'environment', 'compute', 'storage', 'application', 'unknown'
];

const PRIORITY_OPTIONS = ['P1', 'P2', 'P3', 'P4', 'P5'];

export default function SimpleNormalizationPage() {
  const [selectedConnector, setSelectedConnector] = useState('prtg');
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const connectors = [
    { value: 'prtg', label: 'PRTG' },
    { value: 'mcp', label: 'MCP' },
    { value: 'snmp_trap', label: 'SNMP Traps' },
    { value: 'snmp_poll', label: 'SNMP Polling' },
    { value: 'eaton', label: 'Eaton UPS (SNMP)' },
    { value: 'eaton_rest', label: 'Eaton UPS (REST)' },
    { value: 'axis', label: 'Axis Cameras' },
    { value: 'milestone', label: 'Milestone VMS' },
    { value: 'cradlepoint', label: 'Cradlepoint' },
    { value: 'siklu', label: 'Siklu' },
    { value: 'ubiquiti', label: 'Ubiquiti' },
    { value: 'cisco_asa', label: 'Cisco ASA' },
  ];

  // Load all mappings for the selected connector
  const loadMappings = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load severity mappings
      const severityResponse = await fetchApi(`/api/v1/normalization/severity-mappings?connector_type=${selectedConnector}`);
      const severityData = severityResponse.success ? severityResponse.data || [] : [];

      // Load category mappings
      const categoryResponse = await fetchApi(`/api/v1/normalization/category-mappings?connector_type=${selectedConnector}`);
      const categoryData = categoryResponse.success ? categoryResponse.data || [] : [];

      // Combine into unified format
      const combined = [
        ...severityData.map(m => ({ ...m, type: 'severity' })),
        ...categoryData.map(m => ({ ...m, type: 'category' }))
      ].sort((a, b) => {
        // Sort by type first, then by priority
        if (a.type !== b.type) return a.type === 'severity' ? -1 : 1;
        return b.priority - a.priority;
      });

      setMappings(combined);
    } catch (err) {
      setError(err.message || 'Failed to load mappings');
    } finally {
      setLoading(false);
    }
  };

  // Load mappings when connector changes
  useState(() => {
    loadMappings();
  }, [selectedConnector]);

  const handleSave = async (mapping) => {
    try {
      const endpoint = mapping.type === 'severity' 
        ? '/api/v1/normalization/severity-mappings'
        : '/api/v1/normalization/category-mappings';
      
      const payload = {
        connector_type: selectedConnector,
        source_value: mapping.source_value,
        source_field: mapping.source_field,
        ...(mapping.type === 'severity' 
          ? { target_severity: mapping.target_value }
          : { target_category: mapping.target_value }
        ),
        priority: mapping.priority || 100,
        description: mapping.description,
      };

      if (editing) {
        await fetchApi(`${endpoint}/${editing.id}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
        setEditing(null);
      } else if (creating) {
        await fetchApi(endpoint, {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        setCreating(false);
      }
      
      await loadMappings();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleDelete = async (mapping) => {
    if (!confirm(`Delete this ${mapping.type} mapping?`)) return;
    
    try {
      const endpoint = mapping.type === 'severity'
        ? `/api/v1/normalization/severity-mappings/${mapping.id}`
        : `/api/v1/normalization/category-mappings/${mapping.id}`;
      
      await fetchApi(endpoint, { method: 'DELETE' });
      await loadMappings();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const toggleEnabled = async (mapping) => {
    try {
      const endpoint = mapping.type === 'severity'
        ? `/api/v1/normalization/severity-mappings/${mapping.id}`
        : `/api/v1/normalization/category-mappings/${mapping.id}`;
      
      await fetchApi(endpoint, {
        method: 'PUT',
        body: JSON.stringify({ enabled: !mapping.enabled }),
      });
      
      await loadMappings();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) return (
    <PageLayout module="system">
      <div className="p-6"><RefreshCw className="h-6 w-6 animate-spin" /></div>
    </PageLayout>
  );

  if (error) return (
    <PageLayout module="system">
      <div className="p-6 text-red-600">Error: {error}</div>
    </PageLayout>
  );

  return (
    <PageLayout module="system">
      <div className="p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Alert Normalization Rules
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Map source alerts to standard severity and category
          </p>
        </div>

        {/* Controls */}
        <div className="mb-6 flex gap-4">
          <select
            value={selectedConnector}
            onChange={(e) => setSelectedConnector(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          >
            {connectors.map(conn => (
              <option key={conn.value} value={conn.value}>{conn.label}</option>
            ))}
          </select>

          <button
            onClick={() => setCreating(true)}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Add Rule
          </button>

          <button
            onClick={loadMappings}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Create/Edit Form */}
        {(editing || creating) && (
          <div className="mb-6 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            <h3 className="text-lg font-medium mb-4">
              {editing ? 'Edit Rule' : 'Add New Rule'}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <select
                id="mapping-type"
                defaultValue={editing?.type || 'severity'}
                className="px-3 py-2 border rounded"
              >
                <option value="severity">Severity Mapping</option>
                <option value="category">Category Mapping</option>
              </select>
              
              <input
                type="text"
                placeholder="Source Value (e.g., 'down', '5', 'cpu')"
                defaultValue={editing?.source_value || ''}
                id="source-value"
                className="px-3 py-2 border rounded"
              />
              
              <select
                id="source-field"
                defaultValue={editing?.source_field || 'status'}
                className="px-3 py-2 border rounded"
              >
                <option value="status">Status</option>
                <option value="status_text">Status Text</option>
                <option value="type">Type/Sensor</option>
              </select>

              {/* Target field depends on mapping type */}
              <div id="target-field-container">
                {/* Will be populated by JavaScript */}
              </div>

              <input
                type="number"
                placeholder="Priority"
                defaultValue={editing?.priority || 100}
                id="priority"
                className="px-3 py-2 border rounded"
              />
              
              <input
                type="text"
                placeholder="Description"
                defaultValue={editing?.description || ''}
                id="description"
                className="px-3 py-2 border rounded"
              />
              
              <div className="flex gap-2 lg:col-span-2">
                <button
                  onClick={() => {
                    const type = document.getElementById('mapping-type').value;
                    const mapping = {
                      type,
                      source_value: document.getElementById('source-value').value,
                      source_field: document.getElementById('source-field').value,
                      target_value: document.getElementById('target-value').value,
                      priority: parseInt(document.getElementById('priority').value) || 100,
                      description: document.getElementById('description').value,
                    };
                    handleSave(mapping);
                  }}
                  className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  <Save className="h-4 w-4" />
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditing(null);
                    setCreating(false);
                  }}
                  className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  <X className="h-4 w-4" />
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Mappings Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden">
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {/* Header */}
            <div className="px-6 py-3 bg-gray-50 dark:bg-gray-900">
              <div className="grid grid-cols-7 gap-4 text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                <div>Type</div>
                <div>Source</div>
                <div>Target</div>
                <div>Priority</div>
                <div>Description</div>
                <div>Enabled</div>
                <div>Actions</div>
              </div>
            </div>

            {/* Rows */}
            {mappings.map((mapping) => (
              <div key={mapping.id} className="px-6 py-4">
                <div className="grid grid-cols-7 gap-4 items-center">
                  {/* Type */}
                  <div>
                    <span className={`px-2 py-1 text-xs rounded ${
                      mapping.type === 'severity' 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {mapping.type}
                    </span>
                  </div>

                  {/* Source */}
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {mapping.source_value}
                    </div>
                    <div className="text-sm text-gray-500">
                      {mapping.source_field}
                    </div>
                  </div>

                  {/* Target */}
                  <div>
                    {mapping.type === 'severity' ? (
                      <span className={`px-2 py-1 text-xs rounded ${
                        SEVERITY_OPTIONS.find(s => s.value === mapping.target_severity)?.color || 'text-gray-600'
                      }`}>
                        {mapping.target_severity}
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                        {mapping.target_category}
                      </span>
                    )}
                  </div>

                  {/* Priority */}
                  <div className="text-sm text-gray-900 dark:text-white">
                    {mapping.priority}
                  </div>

                  {/* Description */}
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {mapping.description || '-'}
                  </div>

                  {/* Enabled */}
                  <div>
                    <input
                      type="checkbox"
                      checked={mapping.enabled}
                      onChange={() => toggleEnabled(mapping)}
                      className="rounded border-gray-300"
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditing(mapping)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(mapping)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Empty State */}
        {mappings.length === 0 && (
          <div className="text-center py-12">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No mappings found
            </h3>
            <p className="text-gray-500 mb-4">
              Get started by adding your first normalization rule
            </p>
            <button
              onClick={() => setCreating(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Add First Rule
            </button>
          </div>
        )}
      </div>
    </PageLayout>
  );
}

// Dynamic target field selector
document.addEventListener('DOMContentLoaded', () => {
  const mappingTypeSelect = document.getElementById('mapping-type');
  const targetFieldContainer = document.getElementById('target-field-container');
  
  if (mappingTypeSelect && targetFieldContainer) {
    const updateTargetField = () => {
      const type = mappingTypeSelect.value;
      
      if (type === 'severity') {
        targetFieldContainer.innerHTML = `
          <select id="target-value" class="px-3 py-2 border rounded">
            ${SEVERITY_OPTIONS.map(opt => 
              `<option value="${opt.value}">${opt.label}</option>`
            ).join('')}
          </select>
        `;
      } else {
        targetFieldContainer.innerHTML = `
          <select id="target-value" class="px-3 py-2 border rounded">
            ${CATEGORY_OPTIONS.map(cat => 
              `<option value="${cat}">${cat}</option>`
            ).join('')}
          </select>
        `;
      }
    };
    
    mappingTypeSelect.addEventListener('change', updateTargetField);
    updateTargetField(); // Initial setup
  }
});
