/**
 * Normalization Rules Management Page
 * 
 * Configure alert normalization rules for connectors.
 */

import { useState } from 'react';
import { 
  Settings, Plus, Edit, Trash2, Save, X,
  AlertTriangle, Check, Filter, RefreshCw
} from 'lucide-react';
import { PageLayout } from '../components/layout/PageLayout';
import { 
  useSeverityMappings, 
  useCategoryMappings, 
  usePriorityRules,
  useAlertTypeTemplates 
} from '../hooks/useNormalizationRules';

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical', color: 'text-red-600' },
  { value: 'major', label: 'Major', color: 'text-orange-600' },
  { value: 'minor', label: 'Minor', color: 'text-yellow-600' },
  { value: 'warning', label: 'Warning', color: 'text-blue-600' },
  { value: 'info', label: 'Info', color: 'text-gray-600' },
  { value: 'clear', label: 'Clear', color: 'text-green-600' },
];

const CATEGORY_OPTIONS = [
  'network', 'power', 'video', 'wireless', 'security',
  'environment', 'compute', 'storage', 'application', 'unknown'
];

const PRIORITY_OPTIONS = ['P1', 'P2', 'P3', 'P4', 'P5'];
const IMPACT_OPTIONS = ['high', 'medium', 'low'];
const URGENCY_OPTIONS = ['high', 'medium', 'low'];

function SeverityMappingTable({ connectorType }) {
  const { mappings, loading, error, refresh, createMapping, updateMapping, deleteMapping } = 
    useSeverityMappings(connectorType);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const handleSave = async (mapping) => {
    try {
      if (editing) {
        await updateMapping(editing.id, mapping);
        setEditing(null);
      } else if (creating) {
        await createMapping({ ...mapping, connector_type: connectorType });
        setCreating(false);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleDelete = async (mappingId) => {
    if (!confirm('Delete this mapping?')) return;
    
    try {
      await deleteMapping(mappingId);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) return <div className="p-6"><RefreshCw className="h-6 w-6 animate-spin" /></div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Severity Mappings
        </h3>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Add Mapping
        </button>
      </div>

      {/* Create/Edit Form */}
      {(editing || creating) && (
        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <input
              type="text"
              placeholder="Source Value (e.g., 'down', '5')"
              defaultValue={editing?.source_value || ''}
              id="severity-source-value"
              className="px-3 py-2 border rounded"
            />
            <select
              id="severity-source-field"
              defaultValue={editing?.source_field || 'status'}
              className="px-3 py-2 border rounded"
            >
              <option value="status">Status</option>
              <option value="status_text">Status Text</option>
            </select>
            <select
              id="severity-target"
              defaultValue={editing?.target_severity || ''}
              className="px-3 py-2 border rounded"
            >
              {SEVERITY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Priority"
              defaultValue={editing?.priority || 100}
              id="severity-priority"
              className="px-3 py-2 border rounded"
            />
            <input
              type="text"
              placeholder="Description"
              defaultValue={editing?.description || ''}
              id="severity-description"
              className="px-3 py-2 border rounded"
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  const mapping = {
                    source_value: document.getElementById('severity-source-value').value,
                    source_field: document.getElementById('severity-source-field').value,
                    target_severity: document.getElementById('severity-target').value,
                    priority: parseInt(document.getElementById('severity-priority').value) || 100,
                    description: document.getElementById('severity-description').value,
                  };
                  handleSave(mapping);
                }}
                className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <Save className="h-4 w-4" />
              </button>
              <button
                onClick={() => {
                  setEditing(null);
                  setCreating(false);
                }}
                className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mappings Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Target
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Enabled
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mappings.map((mapping) => (
              <tr key={mapping.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  <div>
                    <div className="font-medium">{mapping.source_value}</div>
                    <div className="text-gray-500">{mapping.source_field}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs rounded ${
                    SEVERITY_OPTIONS.find(s => s.value === mapping.target_severity)?.color || 'text-gray-600'
                  }`}>
                    {mapping.target_severity}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {mapping.priority}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={mapping.enabled}
                    onChange={async (e) => {
                      await updateMapping(mapping.id, { enabled: e.target.checked });
                    }}
                    className="rounded border-gray-300"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditing(mapping)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(mapping.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CategoryMappingTable({ connectorType }) {
  const { mappings, loading, error, refresh, createMapping, updateMapping, deleteMapping } = 
    useCategoryMappings(connectorType);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const handleSave = async (mapping) => {
    try {
      if (editing) {
        await updateMapping(editing.id, mapping);
        setEditing(null);
      } else if (creating) {
        await createMapping({ ...mapping, connector_type: connectorType });
        setCreating(false);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleDelete = async (mappingId) => {
    if (!confirm('Delete this mapping?')) return;
    
    try {
      await deleteMapping(mappingId);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) return <div className="p-6"><RefreshCw className="h-6 w-6 animate-spin" /></div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Category Mappings
        </h3>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Add Mapping
        </button>
      </div>

      {/* Create/Edit Form */}
      {(editing || creating) && (
        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <input
              type="text"
              placeholder="Source Value (e.g., 'ping', 'cpu')"
              defaultValue={editing?.source_value || ''}
              id="category-source-value"
              className="px-3 py-2 border rounded"
            />
            <select
              id="category-source-field"
              defaultValue={editing?.source_field || 'type'}
              className="px-3 py-2 border rounded"
            >
              <option value="type">Type</option>
              <option value="sensor">Sensor</option>
            </select>
            <select
              id="category-target"
              defaultValue={editing?.target_category || ''}
              className="px-3 py-2 border rounded"
            >
              {CATEGORY_OPTIONS.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Priority"
              defaultValue={editing?.priority || 100}
              id="category-priority"
              className="px-3 py-2 border rounded"
            />
            <input
              type="text"
              placeholder="Description"
              defaultValue={editing?.description || ''}
              id="category-description"
              className="px-3 py-2 border rounded"
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  const mapping = {
                    source_value: document.getElementById('category-source-value').value,
                    source_field: document.getElementById('category-source-field').value,
                    target_category: document.getElementById('category-target').value,
                    priority: parseInt(document.getElementById('category-priority').value) || 100,
                    description: document.getElementById('category-description').value,
                  };
                  handleSave(mapping);
                }}
                className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <Save className="h-4 w-4" />
              </button>
              <button
                onClick={() => {
                  setEditing(null);
                  setCreating(false);
                }}
                className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mappings Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Target
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Enabled
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mappings.map((mapping) => (
              <tr key={mapping.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  <div>
                    <div className="font-medium">{mapping.source_value}</div>
                    <div className="text-gray-500">{mapping.source_field}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                    {mapping.target_category}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {mapping.priority}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={mapping.enabled}
                    onChange={async (e) => {
                      await updateMapping(mapping.id, { enabled: e.target.checked });
                    }}
                    className="rounded border-gray-300"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditing(mapping)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(mapping.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PriorityRulesTable({ connectorType }) {
  const { rules, loading, error, refresh, createRule } = usePriorityRules(connectorType);
  const [creating, setCreating] = useState(false);

  const handleSave = async (rule) => {
    try {
      await createRule({ ...rule, connector_type: connectorType });
      setCreating(false);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) return <div className="p-6"><RefreshCw className="h-6 w-6 animate-spin" /></div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Priority Rules (ITIL Matrix)
        </h3>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Add Rule
        </button>
      </div>

      {/* Create Form */}
      {creating && (
        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <select id="priority-category" className="px-3 py-2 border rounded">
              {CATEGORY_OPTIONS.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <select id="priority-severity" className="px-3 py-2 border rounded">
              {SEVERITY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <select id="priority-impact" className="px-3 py-2 border rounded">
              {IMPACT_OPTIONS.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            <select id="priority-urgency" className="px-3 py-2 border rounded">
              {URGENCY_OPTIONS.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            <select id="priority-priority" className="px-3 py-2 border rounded">
              {PRIORITY_OPTIONS.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Description"
              id="priority-description"
              className="px-3 py-2 border rounded"
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  const rule = {
                    category: document.getElementById('priority-category').value,
                    severity: document.getElementById('priority-severity').value,
                    impact: document.getElementById('priority-impact').value,
                    urgency: document.getElementById('priority-urgency').value,
                    priority: document.getElementById('priority-priority').value,
                    description: document.getElementById('priority-description').value,
                  };
                  handleSave(rule);
                }}
                className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <Save className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCreating(false)}
                className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rules Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Category
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Severity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Impact
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Urgency
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Enabled
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {rules.map((rule) => (
              <tr key={rule.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                    {rule.category}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs rounded ${
                    SEVERITY_OPTIONS.find(s => s.value === rule.severity)?.color || 'text-gray-600'
                  }`}>
                    {rule.severity}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {rule.impact}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {rule.urgency}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs rounded bg-purple-100 text-purple-800">
                    {rule.priority}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    className="rounded border-gray-300"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function NormalizationRulesPage() {
  const [selectedConnector, setSelectedConnector] = useState('prtg');
  const [activeTab, setActiveTab] = useState('severity');

  const connectors = [
    { value: 'prtg', label: 'PRTG' },
    { value: 'mcp', label: 'MCP' },
    { value: 'snmp_trap', label: 'SNMP Traps' },
    { value: 'snmp_poll', label: 'SNMP Polling' },
    { value: 'eaton', label: 'Eaton UPS' },
    { value: 'axis', label: 'Axis Cameras' },
    { value: 'milestone', label: 'Milestone VMS' },
    { value: 'cradlepoint', label: 'Cradlepoint' },
    { value: 'siklu', label: 'Siklu' },
    { value: 'ubiquiti', label: 'Ubiquiti' },
  ];

  return (
    <PageLayout module="system">
      <div className="p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Normalization Rules
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Configure alert classification and priority rules
          </p>
        </div>

        {/* Controls */}
        <div className="mb-6 flex flex-wrap gap-4">
          <select
            value={selectedConnector}
            onChange={(e) => setSelectedConnector(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
          >
            {connectors.map(conn => (
              <option key={conn.value} value={conn.value}>{conn.label}</option>
            ))}
          </select>

          <div className="flex border border-gray-300 dark:border-gray-600 rounded">
            {['severity', 'category', 'priority'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 ${
                  activeTab === tab
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {activeTab === 'severity' && <SeverityMappingTable connectorType={selectedConnector} />}
          {activeTab === 'category' && <CategoryMappingTable connectorType={selectedConnector} />}
          {activeTab === 'priority' && <PriorityRulesTable connectorType={selectedConnector} />}
        </div>
      </div>
    </PageLayout>
  );
}
