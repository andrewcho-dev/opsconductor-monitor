/**
 * Two-Column Mapping Page
 * 
 * PRTG values on left, OpsConductor values on right, organized by sections
 */

import { useState, useEffect } from 'react';
import { 
  Plus, Edit, Trash2, Save, X,
  RefreshCw
} from 'lucide-react';
import { PageLayout } from '../components/layout/PageLayout';
import { fetchApi } from '../lib/utils';

// Content component without PageLayout (for use in ConnectorsLayout)
export function NormalizationContent() {
  const [selectedConnector, setSelectedConnector] = useState('prtg');
  const [selectedVendor, setSelectedVendor] = useState('');
  const [vendors, setVendors] = useState([]);
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
    { value: 'ubiquiti', label: 'Ubiquiti' },
    { value: 'cisco_asa', label: 'Cisco ASA' },
  ];

  // Load vendors for snmp_trap connector
  const loadVendors = async () => {
    if (selectedConnector === 'snmp_trap') {
      try {
        const response = await fetchApi(`/api/v1/normalization/vendors?connector_type=${selectedConnector}`);
        if (response.success) {
          setVendors(response.data || []);
        }
      } catch (err) {
        console.error('Failed to load vendors:', err);
      }
    } else {
      setVendors([]);
      setSelectedVendor('');
    }
  };

  const loadMappings = async () => {
    setLoading(true);
    setError(null);

    try {
      // Build query params with optional vendor filter
      let queryParams = `connector_type=${selectedConnector}`;
      if (selectedVendor) {
        queryParams += `&vendor=${selectedVendor}`;
      }

      const severityResponse = await fetchApi(`/api/v1/normalization/severity-mappings?${queryParams}`);
      const severityData = severityResponse.success ? severityResponse.data || [] : [];

      const categoryResponse = await fetchApi(`/api/v1/normalization/category-mappings?${queryParams}`);
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

  // Load vendors when connector changes
  useEffect(() => {
    loadVendors();
  }, [selectedConnector]);

  // Load mappings when connector or vendor changes
  useEffect(() => {
    loadMappings();
  }, [selectedConnector, selectedVendor]);

  // Group mappings by logical sections
  const groupMappings = (mappings) => {
    const groups = {
      'Critical Alerts': [],
      'Warning Alerts': [],
      'Info Alerts': [],
      'Network Devices': [],
      'Compute Resources': [],
      'Storage Systems': [],
      'Power & Environment': [],
      'Security & Access': [],
      'Applications': [],
      'Other': []
    };

    mappings.forEach(mapping => {
      if (mapping.type === 'severity') {
        if (['critical', 'major'].includes(mapping.target_severity)) {
          groups['Critical Alerts'].push(mapping);
        } else if (['warning', 'minor'].includes(mapping.target_severity)) {
          groups['Warning Alerts'].push(mapping);
        } else {
          groups['Info Alerts'].push(mapping);
        }
      } else {
        if (['network', 'wireless'].includes(mapping.target_category)) {
          groups['Network Devices'].push(mapping);
        } else if (['compute'].includes(mapping.target_category)) {
          groups['Compute Resources'].push(mapping);
        } else if (['storage'].includes(mapping.target_category)) {
          groups['Storage Systems'].push(mapping);
        } else if (['power', 'environment'].includes(mapping.target_category)) {
          groups['Power & Environment'].push(mapping);
        } else if (['security'].includes(mapping.target_category)) {
          groups['Security & Access'].push(mapping);
        } else if (['application'].includes(mapping.target_category)) {
          groups['Applications'].push(mapping);
        } else {
          groups['Other'].push(mapping);
        }
      }
    });

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) delete groups[key];
    });

    return groups;
  };

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
    <div className="p-6"><RefreshCw className="h-6 w-6 animate-spin" /></div>
  );

  if (error) return (
    <div className="p-6 text-red-600">Error: {error}</div>
  );

  const groupedMappings = groupMappings(mappings);

  return (
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
              onChange={(e) => {
                setSelectedConnector(e.target.value);
                setSelectedVendor('');
              }}
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
            >
              {connectors.map(conn => (
                <option key={conn.value} value={conn.value}>{conn.label}</option>
              ))}
            </select>
            
            {/* Vendor filter - only show for snmp_trap */}
            {selectedConnector === 'snmp_trap' && vendors.length > 0 && (
              <select
                value={selectedVendor}
                onChange={(e) => setSelectedVendor(e.target.value)}
                className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900"
              >
                <option value="">All Vendors</option>
                {vendors.map(v => (
                  <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
                ))}
              </select>
            )}
            
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
          <div className="mb-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3 rounded">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {/* Left Column - Source */}
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  {connectors.find(c => c.value === selectedConnector)?.label || 'Source'} Source
                </h4>
                <div className="space-y-2">
                  <select
                    id="mapping-type"
                    defaultValue={editing?.type || 'severity'}
                    className="w-full px-2 py-1 border rounded text-sm"
                  >
                    <option value="severity">Severity</option>
                    <option value="category">Category</option>
                  </select>
                  
                  <input
                    type="text"
                    placeholder="Source value (e.g., down, cpu, 5)"
                    defaultValue={editing?.source_value || ''}
                    id="source-value"
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                  
                  <select
                    id="source-field"
                    defaultValue={editing?.source_field || 'status'}
                    className="w-full px-2 py-1 border rounded text-sm"
                  >
                    <option value="status">Status (numeric)</option>
                    <option value="status_text">Status Text</option>
                    <option value="type">Type/Sensor</option>
                  </select>
                </div>
              </div>

              {/* Right Column - OpsConductor */}
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">OpsConductor Target</h4>
                <div className="space-y-2">
                  <div id="target-field-container">
                    {/* Populated by JS */}
                  </div>

                  <input
                    type="number"
                    placeholder="Priority"
                    defaultValue={editing?.priority || 100}
                    id="priority"
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                  
                  <div className="flex gap-2">
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
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditing(null);
                        setCreating(false);
                      }}
                      className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Two-Column Layout with Section Headers */}
        <div className="grid grid-cols-2 gap-4">
          {/* Left Column - Source Values */}
          <div className="bg-gray-50 dark:bg-gray-800 rounded p-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              {connectors.find(c => c.value === selectedConnector)?.label || 'Source'} Values
            </h2>
            <div className="space-y-4">
              {Object.entries(groupedMappings).map(([section, sectionMappings]) => (
                <div key={section}>
                  <h3 className="font-bold text-sm text-gray-900 dark:text-white mb-2">
                    {section}
                  </h3>
                  <div className="bg-white dark:bg-gray-700 rounded border p-2">
                    {sectionMappings.map((mapping) => (
                      <div key={mapping.id} className="py-1 flex items-center justify-between border-b last:border-b-0">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="text-xs text-gray-500 shrink-0">{mapping.source_field}:</span>
                          <span className="font-mono text-sm font-medium shrink-0">{mapping.source_value}</span>
                          {mapping.description && (
                            <span 
                              className="text-xs text-gray-400 dark:text-gray-500 italic truncate" 
                              title={mapping.description}
                            >
                              — {mapping.description.length > 50 ? mapping.description.substring(0, 50) + '...' : mapping.description}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <input
                            type="checkbox"
                            checked={mapping.enabled}
                            onChange={() => toggleEnabled(mapping)}
                            className="w-3 h-3"
                          />
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
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column - OpsConductor Values */}
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              OpsConductor Normalized Values
            </h2>
            <div className="space-y-4">
              {Object.entries(groupedMappings).map(([section, sectionMappings]) => (
                <div key={section}>
                  <h3 className="font-bold text-sm text-gray-900 dark:text-white mb-2">
                    {section}
                  </h3>
                  <div className="bg-white dark:bg-gray-700 rounded border p-2">
                    {sectionMappings.map((mapping) => (
                      <div key={mapping.id} className="py-1 flex items-center justify-between border-b last:border-b-0">
                        <div className="flex items-center gap-2">
                          <span className="px-1 py-0.5 text-xs rounded bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                            {mapping.type[0].toUpperCase()}
                          </span>
                          {mapping.type === 'severity' ? (
                            <span className={`px-1 py-0.5 text-xs rounded ${
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
                            <span className="px-1 py-0.5 text-xs rounded bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                              {mapping.target_category}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          Priority: {mapping.priority}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
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
  );
}

// Standalone page with PageLayout
export default function ColumnMappingPage() {
  return (
    <PageLayout module="connectors">
      <NormalizationContent />
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
          <select id="target-value" class="w-full px-2 py-1 border rounded text-sm">
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
          <select id="target-value" class="w-full px-2 py-1 border rounded text-sm">
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
