/**
 * NodeEditor Component
 * 
 * Modal for editing node parameters.
 * Renders form fields based on node definition.
 */

import React, { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronRight, AlertCircle, HelpCircle, Loader2, Link2 } from 'lucide-react';
import { cn } from '../../../lib/utils';
import NetBoxDeviceSelector from './NetBoxDeviceSelector';
import { NetBoxSiteSelector, NetBoxRoleSelector, NetBoxDeviceTypeSelector, NetBoxTagsSelector } from './NetBoxSelectors';
import DataMappingPanel from './DataMappingPanel';
import ExpressionInput from './ExpressionInput';

const NodeEditor = ({
  isOpen,
  node,
  nodeDefinition,
  formData,
  errors,
  onClose,
  onSave,
  onDelete,
  updateField,
  shouldShowParameter,
  allNodes,
  edges,
  onMapInput,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [activeTab, setActiveTab] = useState('parameters');
  const [tables, setTables] = useState([]);
  const [tableColumns, setTableColumns] = useState({});
  const [loadingTables, setLoadingTables] = useState(false);
  const [loadingColumns, setLoadingColumns] = useState(false);
  const [inputFields, setInputFields] = useState(null);

  // Fetch available tables when component mounts
  useEffect(() => {
    if (isOpen) {
      fetchTables();
      fetchInputFields();
    }
  }, [isOpen]);

  // Fetch columns when table selection changes
  useEffect(() => {
    const selectedTable = formData.table;
    if (selectedTable && selectedTable !== 'custom' && !tableColumns[selectedTable]) {
      fetchTableColumns(selectedTable);
    }
  }, [formData.table]);

  const fetchTables = async () => {
    setLoadingTables(true);
    try {
      const response = await fetch('/system/v1/schema/tables');
      const data = await response.json();
      if (data.success) {
        setTables(data.tables);
      }
    } catch (error) {
      console.error('Failed to fetch tables:', error);
    }
    setLoadingTables(false);
  };

  const fetchTableColumns = async (tableName) => {
    setLoadingColumns(true);
    try {
      const response = await fetch(`/system/v1/schema/tables/${tableName}/columns`);
      const data = await response.json();
      if (data.success) {
        setTableColumns(prev => ({ ...prev, [tableName]: data.columns }));
      }
    } catch (error) {
      console.error('Failed to fetch columns:', error);
    }
    setLoadingColumns(false);
  };

  const fetchInputFields = async () => {
    try {
      const response = await fetch('/system/v1/schema/input-fields');
      const data = await response.json();
      if (data.success) {
        setInputFields(data.node_outputs);
      }
    } catch (error) {
      console.error('Failed to fetch input fields:', error);
    }
  };

  if (!isOpen || !node || !nodeDefinition) return null;

  const handleSave = () => {
    onSave();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  // Render a parameter field based on its type
  const renderField = (param) => {
    if (!shouldShowParameter(param)) return null;

    const value = formData[param.id];
    const error = errors[param.id];
    const fieldId = `field-${param.id}`;

    const commonProps = {
      id: fieldId,
      value: value ?? param.default ?? '',
      onChange: (e) => updateField(param.id, e.target.value),
      className: cn(
        'w-full px-3 py-2 border rounded-md text-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        error ? 'border-red-300 bg-red-50' : 'border-gray-300'
      ),
    };

    return (
      <div key={param.id} className="mb-4">
        <label htmlFor={fieldId} className="flex items-center gap-1 text-sm font-medium text-gray-700 mb-1">
          {param.label}
          {param.required && <span className="text-red-500">*</span>}
          {param.help && (
            <span className="group relative">
              <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help" />
              <span className="absolute left-0 bottom-full mb-1 hidden group-hover:block w-48 p-2 text-xs bg-gray-900 text-white rounded shadow-lg z-10">
                {param.help}
              </span>
            </span>
          )}
        </label>

        {/* Text Input */}
        {param.type === 'text' && (
          <input
            type="text"
            placeholder={param.placeholder}
            {...commonProps}
          />
        )}

        {/* Expression Input with autocomplete */}
        {param.type === 'expression' && (
          <ExpressionInput
            value={value}
            onChange={(val) => updateField(param.id, val)}
            placeholder={param.placeholder || '{{nodeId.output}}'}
            currentNodeId={node?.id}
            allNodes={allNodes}
            edges={edges}
          />
        )}

        {/* Password Input */}
        {param.type === 'password' && (
          <input
            type="password"
            placeholder={param.placeholder}
            {...commonProps}
          />
        )}

        {/* Number Input */}
        {param.type === 'number' && (
          <input
            type="number"
            min={param.min}
            max={param.max}
            step={param.step || 1}
            {...commonProps}
            onChange={(e) => updateField(param.id, Number(e.target.value))}
          />
        )}

        {/* Textarea */}
        {(param.type === 'textarea' || param.type === 'code') && (
          <textarea
            rows={param.rows || 4}
            placeholder={param.placeholder}
            {...commonProps}
            className={cn(commonProps.className, param.type === 'code' && 'font-mono text-xs')}
          />
        )}

        {/* Select */}
        {param.type === 'select' && (
          <select {...commonProps}>
            {param.options?.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}

        {/* Checkbox */}
        {param.type === 'checkbox' && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={value ?? param.default ?? false}
              onChange={(e) => updateField(param.id, e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-600">{param.checkboxLabel || 'Enable'}</span>
          </label>
        )}

        {/* Multi-Select (checkbox group) */}
        {param.type === 'multi-select' && (
          <div className="space-y-1.5 p-2 bg-gray-50 rounded-lg border border-gray-200">
            {param.options?.map(opt => {
              const selected = Array.isArray(value) ? value : (param.default || []);
              const isChecked = selected.includes(opt.value);
              return (
                <label key={opt.value} className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={(e) => {
                      const current = Array.isArray(value) ? [...value] : [...(param.default || [])];
                      if (e.target.checked) {
                        if (!current.includes(opt.value)) current.push(opt.value);
                      } else {
                        const idx = current.indexOf(opt.value);
                        if (idx >= 0) current.splice(idx, 1);
                      }
                      updateField(param.id, current);
                    }}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">{opt.label}</span>
                </label>
              );
            })}
          </div>
        )}

        {/* Key-Value pairs */}
        {param.type === 'key-value' && (
          <div className="space-y-2">
            {Object.entries(value || {}).map(([k, v], idx) => (
              <div key={idx} className="flex gap-2">
                <input
                  type="text"
                  value={k}
                  placeholder="Key"
                  className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                  onChange={(e) => {
                    const newValue = { ...value };
                    delete newValue[k];
                    newValue[e.target.value] = v;
                    updateField(param.id, newValue);
                  }}
                />
                <input
                  type="text"
                  value={v}
                  placeholder="Value"
                  className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                  onChange={(e) => {
                    updateField(param.id, { ...value, [k]: e.target.value });
                  }}
                />
                <button
                  onClick={() => {
                    const newValue = { ...value };
                    delete newValue[k];
                    updateField(param.id, newValue);
                  }}
                  className="px-2 text-red-500 hover:text-red-700"
                >
                  ×
                </button>
              </div>
            ))}
            <button
              onClick={() => updateField(param.id, { ...value, '': '' })}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              + Add
            </button>
          </div>
        )}

        {/* Column Mapping (n8n-style) - "Values to Send" */}
        {param.type === 'column-mapping' && (
          <div className="space-y-2">
            {/* Column mapping rows - n8n style */}
            {(Array.isArray(value) ? value : []).map((mapping, idx) => (
              <div key={idx} className="flex gap-2 items-center bg-gray-50 p-2 rounded border border-gray-200">
                {/* Column dropdown */}
                <div className="flex-1">
                  {formData.table && tableColumns[formData.table] ? (
                    <select
                      value={mapping.target || ''}
                      onChange={(e) => {
                        const newValue = [...(value || [])];
                        newValue[idx] = { ...newValue[idx], target: e.target.value };
                        updateField(param.id, newValue);
                      }}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm bg-white"
                    >
                      <option value="">Column...</option>
                      {tableColumns[formData.table].map(col => (
                        <option key={col.name} value={col.name}>
                          {col.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={mapping.target || ''}
                      placeholder="column"
                      onChange={(e) => {
                        const newValue = [...(value || [])];
                        newValue[idx] = { ...newValue[idx], target: e.target.value };
                        updateField(param.id, newValue);
                      }}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                    />
                  )}
                </div>
                
                <span className="text-gray-400 text-sm">=</span>
                
                {/* Value input with expression support */}
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={mapping.source || ''}
                    placeholder="{{ $json.field }}"
                    onChange={(e) => {
                      const newValue = [...(value || [])];
                      newValue[idx] = { ...newValue[idx], source: e.target.value };
                      updateField(param.id, newValue);
                    }}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm font-mono text-orange-600 bg-orange-50"
                  />
                </div>
                
                <button
                  onClick={() => {
                    const newValue = [...(value || [])];
                    newValue.splice(idx, 1);
                    updateField(param.id, newValue);
                  }}
                  className="p-1 text-gray-400 hover:text-red-500 rounded"
                  title="Remove"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
            
            {/* Add button */}
            <button
              onClick={() => updateField(param.id, [...(value || []), { source: '', target: '' }])}
              className="w-full py-1.5 px-3 border border-dashed border-gray-300 rounded text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50"
            >
              + Add Value
            </button>
            
            {/* Available fields hint */}
            {inputFields && inputFields['network:ping'] && (
              <div className="text-xs text-gray-500 pt-1">
                <span className="font-medium">Available fields: </span>
                {inputFields['network:ping'].fields.map((f, i) => (
                  <span key={f.name}>
                    <button
                      onClick={() => {
                        // Add this field if not already mapped
                        const alreadyMapped = (value || []).some(m => m.source === f.name);
                        if (!alreadyMapped) {
                          updateField(param.id, [...(value || []), { source: f.name, target: f.name }]);
                        }
                      }}
                      className="text-blue-600 hover:underline"
                    >
                      {f.name}
                    </button>
                    {i < inputFields['network:ping'].fields.length - 1 && ', '}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Device Group Selector (placeholder - would connect to API) */}
        {param.type === 'device-group-selector' && (
          <select {...commonProps}>
            <option value="">Select a device group...</option>
            <option value="all-devices">All Devices</option>
            <option value="switches">Switches</option>
            <option value="routers">Routers</option>
          </select>
        )}

        {/* NetBox Device Selector */}
        {param.type === 'netbox-device-selector' && (
          <NetBoxDeviceSelector
            value={value || param.default || {}}
            onChange={(newValue) => updateField(param.id, newValue)}
          />
        )}

        {/* NetBox Site Selector */}
        {param.type === 'netbox-site-selector' && (
          <NetBoxSiteSelector
            value={value}
            onChange={(val) => updateField(param.id, val)}
            required={param.required}
          />
        )}

        {/* NetBox Role Selector */}
        {param.type === 'netbox-role-selector' && (
          <NetBoxRoleSelector
            value={value}
            onChange={(val) => updateField(param.id, val)}
            required={param.required}
          />
        )}

        {/* NetBox Device Type Selector */}
        {param.type === 'netbox-device-type-selector' && (
          <NetBoxDeviceTypeSelector
            value={value}
            onChange={(val) => updateField(param.id, val)}
            required={param.required}
          />
        )}

        {/* NetBox Tags Selector */}
        {param.type === 'netbox-tags-selector' && (
          <NetBoxTagsSelector
            value={value}
            onChange={(val) => updateField(param.id, val)}
          />
        )}

        {/* Table Selector - Dynamic from API */}
        {param.type === 'table-selector' && (
          <div>
            <div className="flex items-center gap-2">
              <select {...commonProps} className={cn(commonProps.className, 'flex-1')}>
                {loadingTables ? (
                  <option value="">Loading tables...</option>
                ) : tables.length > 0 ? (
                  <>
                    {tables.map(table => (
                      <option key={table.name} value={table.name}>
                        {table.label} ({table.column_count} columns)
                      </option>
                    ))}
                    <option value="custom">Custom Table...</option>
                  </>
                ) : (
                  <>
                    <option value="scan_results">Scan Results (Devices)</option>
                    <option value="interfaces">Interfaces</option>
                    <option value="optical_power_readings">Optical Power Readings</option>
                    <option value="custom">Custom...</option>
                  </>
                )}
              </select>
              {loadingTables && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
            </div>
            {/* Show available columns for selected table */}
            {formData.table && tableColumns[formData.table] && (
              <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded text-xs">
                <div className="font-medium text-gray-600 mb-1">Available columns:</div>
                <div className="flex flex-wrap gap-1">
                  {tableColumns[formData.table].map(col => (
                    <span 
                      key={col.name} 
                      className="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-gray-700"
                      title={`Type: ${col.type}${col.nullable ? ' (nullable)' : ''}`}
                    >
                      {col.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {loadingColumns && (
              <div className="mt-2 flex items-center gap-1 text-xs text-gray-500">
                <Loader2 className="w-3 h-3 animate-spin" />
                Loading columns...
              </div>
            )}
          </div>
        )}

        {/* OID Selector (placeholder) */}
        {param.type === 'oid-selector' && (
          <div>
            <input
              type="text"
              placeholder="Enter OID or select preset"
              {...commonProps}
            />
            {param.presets && (
              <div className="mt-1 flex flex-wrap gap-1">
                {param.presets.map(preset => (
                  <button
                    key={preset.value}
                    onClick={() => updateField(param.id, preset.value)}
                    className="text-xs px-2 py-0.5 bg-gray-100 hover:bg-gray-200 rounded"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Cron Expression */}
        {param.type === 'cron' && (
          <div>
            <input
              type="text"
              placeholder="*/5 * * * *"
              {...commonProps}
            />
            <div className="mt-1 flex flex-wrap gap-1">
              <button
                onClick={() => updateField(param.id, '*/5 * * * *')}
                className="text-xs px-2 py-0.5 bg-gray-100 hover:bg-gray-200 rounded"
              >
                Every 5 min
              </button>
              <button
                onClick={() => updateField(param.id, '0 * * * *')}
                className="text-xs px-2 py-0.5 bg-gray-100 hover:bg-gray-200 rounded"
              >
                Hourly
              </button>
              <button
                onClick={() => updateField(param.id, '0 0 * * *')}
                className="text-xs px-2 py-0.5 bg-gray-100 hover:bg-gray-200 rounded"
              >
                Daily
              </button>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mt-1 flex items-center gap-1 text-xs text-red-600">
            <AlertCircle className="w-3 h-3" />
            {error}
          </div>
        )}
      </div>
    );
  };

  const parameters = nodeDefinition.parameters || [];
  const advancedParams = nodeDefinition.advanced || [];

  // n8n-style slide-in panel from right
  return (
    <>
      {/* Backdrop */}
      <div 
        className={cn(
          "fixed inset-0 z-40 bg-black/20 transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />
      
      {/* Side Panel */}
      <div 
        className={cn(
          "fixed top-0 right-0 z-50 h-full w-[420px] bg-white shadow-2xl flex flex-col",
          "transform transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
        onKeyDown={handleKeyDown}
      >
        {/* Header - n8n style */}
        <div className="flex-shrink-0 border-b border-gray-200">
          <div 
            className="px-4 py-3 flex items-center gap-3"
            style={{ backgroundColor: nodeDefinition.color || '#6366F1' }}
          >
            <span className="text-2xl">{nodeDefinition.icon}</span>
            <div className="flex-1 min-w-0">
              <h2 className="text-base font-semibold text-white truncate">
                {formData.label || nodeDefinition.name}
              </h2>
              <p className="text-xs text-white/80 truncate">{nodeDefinition.description}</p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {/* Tabs - n8n style */}
          <div className="flex border-b border-gray-100">
            <button 
              onClick={() => setActiveTab('parameters')}
              className={cn(
                'flex-1 px-4 py-2.5 text-sm font-medium transition-colors',
                activeTab === 'parameters' 
                  ? 'text-gray-900 border-b-2 border-blue-500 bg-blue-50/50' 
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              )}
            >
              Parameters
            </button>
            <button 
              onClick={() => setActiveTab('data')}
              className={cn(
                'flex-1 px-4 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5',
                activeTab === 'data' 
                  ? 'text-gray-900 border-b-2 border-blue-500 bg-blue-50/50' 
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              )}
            >
              <Link2 className="w-4 h-4" />
              Data
            </button>
            <button 
              onClick={() => setActiveTab('settings')}
              className={cn(
                'flex-1 px-4 py-2.5 text-sm font-medium transition-colors',
                activeTab === 'settings' 
                  ? 'text-gray-900 border-b-2 border-blue-500 bg-blue-50/50' 
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              )}
            >
              Settings
            </button>
          </div>
        </div>

        {/* Body - Scrollable */}
        <div className="flex-1 overflow-y-auto">
          {/* Parameters Tab */}
          {activeTab === 'parameters' && (
            <>
              {/* Node Name & Description */}
              <div className="px-4 py-4 border-b border-gray-100 bg-gray-50/50">
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    value={formData.label || ''}
                    onChange={(e) => updateField('label', e.target.value)}
                    placeholder={nodeDefinition.name}
                    className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={formData.description || ''}
                    onChange={(e) => updateField('description', e.target.value)}
                    placeholder="Add a note..."
                    className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Parameters Section */}
              {parameters.length > 0 && (
                <div className="px-4 py-4">
                  {parameters.map(renderField)}
                </div>
              )}

              {/* Advanced Section */}
              {advancedParams.length > 0 && (
                <div className="px-4 py-4 border-t border-gray-100">
                  <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 mb-3 w-full"
                  >
                    {showAdvanced ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    <span>Options</span>
                  </button>
                  
                  {showAdvanced && (
                    <div className="space-y-4">
                      {advancedParams.map(renderField)}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Data Tab - Data Mapping */}
          {activeTab === 'data' && (
            <div className="px-4 py-4">
              <DataMappingPanel
                currentNode={node}
                currentNodeDef={nodeDefinition}
                allNodes={allNodes}
                edges={edges}
                onMapInput={onMapInput}
                mappedInputs={formData._inputMappings || {}}
              />
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="px-4 py-4">
              <div className="text-sm text-gray-500">
                <h4 className="font-medium text-gray-700 mb-2">Node Information</h4>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Node ID:</span>
                    <span className="font-mono text-gray-700">{node?.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Type:</span>
                    <span className="font-mono text-gray-700">{node?.data?.nodeType}</span>
                  </div>
                  {nodeDefinition.execution && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Executor:</span>
                      <span className="font-mono text-gray-700">{nodeDefinition.execution.executor}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer - n8n style */}
        <div className="flex-shrink-0 px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <button
            onClick={onDelete}
            className="px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
          >
            Delete
          </button>
          
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default NodeEditor;
