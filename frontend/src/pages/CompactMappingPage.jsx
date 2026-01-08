/**
 * Compact Mapping Table Page
 * 
 * Dense, space-efficient mapping view
 */

import { useState } from 'react';
import { 
  Plus, Edit, Trash2, Save, X,
  RefreshCw
} from 'lucide-react';
import { PageLayout } from '../components/layout/PageLayout';
import { fetchApi } from '../lib/utils';

export default function CompactMappingPage() {
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

  const loadMappings = async () => {
    setLoading(true);
    setError(null);

    try {
      const severityResponse = await fetchApi(`/api/v1/normalization/severity-mappings?connector_type=${selectedConnector}`);
      const severityData = severityResponse.success ? severityResponse.data || [] : [];

      const categoryResponse = await fetchApi(`/api/v1/normalization/category-mappings?connector_type=${selectedConnector}`);
      const categoryData = categoryResponse.success ? categoryResponse.data || [] : [];

      const combined = [
        ...severityData.map(m => ({ ...m, type: 'severity' })),
        ...categoryData.map(m => ({ ...m, type: 'category' }))
      ].sort((a, b) => {
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
    if (!confirm(`Delete mapping?`)) return;
    
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
        <div className="mb-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Alert Mappings
            </h1>
          </div>
          <div className="flex gap-2">
            <select
              value={selectedConnector}
              onChange={(e) => setSelectedConnector(e.target.value)}
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
            >
              {connectors.map(conn => (
                <option key={conn.value} value={conn.value}>{conn.label}</option>
              ))}
            </select>
            <button
              onClick={() => setCreating(true)}
              className="flex items-center gap-1 px-2 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
            >
              <Plus className="h-3 w-3" />
              Add
            </button>
            <button
              onClick={loadMappings}
              className="p-1 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <RefreshCw className="h-3 w-3" />
            </button>
          </div>
        </div>

        {/* Create/Edit Form */}
        {(editing || creating) && (
          <div className="mb-4 bg-gray-50 dark:bg-gray-800 p-3 rounded border">
            <div className="grid grid-cols-6 gap-2 text-xs">
              <select
                id="mapping-type"
                defaultValue={editing?.type || 'severity'}
                className="px-2 py-1 border rounded text-xs"
              >
                <option value="severity">Severity</option>
                <option value="category">Category</option>
              </select>
              
              <input
                type="text"
                placeholder="Source value"
                defaultValue={editing?.source_value || ''}
                id="source-value"
                className="px-2 py-1 border rounded text-xs"
              />
              
              <select
                id="source-field"
                defaultValue={editing?.source_field || 'status'}
                className="px-2 py-1 border rounded text-xs"
              >
                <option value="status">Status</option>
                <option value="status_text">Status Text</option>
                <option value="type">Type</option>
              </select>

              <div id="target-field-container">
                {/* Populated by JS */}
              </div>

              <input
                type="number"
                placeholder="Priority"
                defaultValue={editing?.priority || 100}
                id="priority"
                className="px-2 py-1 border rounded text-xs w-16"
              />
              
              <div className="flex gap-1">
                <button
                  onClick={() => {
                    const mapping = {
                      type: document.getElementById('mapping-type').value,
                      source_value: document.getElementById('source-value').value,
                      source_field: document.getElementById('source-field').value,
                      target_value: document.getElementById('target-value').value,
                      priority: parseInt(document.getElementById('priority').value) || 100,
                    };
                    handleSave(mapping);
                  }}
                  className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditing(null);
                    setCreating(false);
                  }}
                  className="px-2 py-1 bg-gray-600 text-white rounded text-xs hover:bg-gray-700"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Compact Table */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900 border-b">
                <th className="px-2 py-1 text-left">Type</th>
                <th className="px-2 py-1 text-left">Source</th>
                <th className="px-2 py-1 text-left">→</th>
                <th className="px-2 py-1 text-left">Target</th>
                <th className="px-2 py-1 text-left">Priority</th>
                <th className="px-2 py-1 text-left">On</th>
                <th className="px-2 py-1 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {mappings.map((mapping) => (
                <tr key={mapping.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-2 py-1">
                    <span className={`px-1 py-0.5 rounded text-xs ${
                      mapping.type === 'severity' 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {mapping.type[0].toUpperCase()}
                    </span>
                  </td>
                  <td className="px-2 py-1">
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">{mapping.source_field}:</span>
                      <span className="font-mono">{mapping.source_value}</span>
                    </div>
                  </td>
                  <td className="px-2 py-1 text-center">→</td>
                  <td className="px-2 py-1">
                    {mapping.type === 'severity' ? (
                      <span className={`px-1 py-0.5 rounded text-xs ${
                        mapping.target_severity === 'critical' ? 'bg-red-100 text-red-800' :
                        mapping.target_severity === 'major' ? 'bg-orange-100 text-orange-800' :
                        mapping.target_severity === 'minor' ? 'bg-yellow-100 text-yellow-800' :
                        mapping.target_severity === 'warning' ? 'bg-blue-100 text-blue-800' :
                        mapping.target_severity === 'info' ? 'bg-gray-100 text-gray-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {mapping.target_severity}
                      </span>
                    ) : (
                      <span className="px-1 py-0.5 rounded text-xs bg-green-100 text-green-800">
                        {mapping.target_category}
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1">{mapping.priority}</td>
                  <td className="px-2 py-1">
                    <input
                      type="checkbox"
                      checked={mapping.enabled}
                      onChange={() => toggleEnabled(mapping)}
                      className="w-3 h-3"
                    />
                  </td>
                  <td className="px-2 py-1">
                    <div className="flex gap-1">
                      <button
                        onClick={() => setEditing(mapping)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <Edit className="h-3 w-3" />
                      </button>
                      <button
                        onClick={() => handleDelete(mapping)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {mappings.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-2">No mappings configured</div>
            <button
              onClick={() => setCreating(true)}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
            >
              Add First Mapping
            </button>
          </div>
        )}
      </div>
    </PageLayout>
  );
}

// Dynamic target field
document.addEventListener('DOMContentLoaded', () => {
  const mappingTypeSelect = document.getElementById('mapping-type');
  const targetFieldContainer = document.getElementById('target-field-container');
  
  if (mappingTypeSelect && targetFieldContainer) {
    const updateTargetField = () => {
      const type = mappingTypeSelect.value;
      
      if (type === 'severity') {
        targetFieldContainer.innerHTML = `
          <select id="target-value" class="px-2 py-1 border rounded text-xs">
            <option value="critical">Critical</option>
            <option value="major">Major</option>
            <option value="minor">Minor</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
            <option value="clear">Clear</option>
          </select>
        `;
      } else {
        targetFieldContainer.innerHTML = `
          <select id="target-value" class="px-2 py-1 border rounded text-xs">
            <option value="network">Network</option>
            <option value="power">Power</option>
            <option value="video">Video</option>
            <option value="wireless">Wireless</option>
            <option value="security">Security</option>
            <option value="environment">Environment</option>
            <option value="compute">Compute</option>
            <option value="storage">Storage</option>
            <option value="application">Application</option>
            <option value="unknown">Unknown</option>
          </select>
        `;
      }
    };
    
    mappingTypeSelect.addEventListener('change', updateTargetField);
    updateTargetField();
  }
});
