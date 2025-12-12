/**
 * NodeEditor Component
 * 
 * Modal for editing node parameters.
 * Renders form fields based on node definition.
 */

import React, { useState } from 'react';
import { X, ChevronDown, ChevronRight, AlertCircle, HelpCircle } from 'lucide-react';
import { cn } from '../../../lib/utils';

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
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

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
        {(param.type === 'text' || param.type === 'expression') && (
          <input
            type="text"
            placeholder={param.placeholder}
            {...commonProps}
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

        {/* Device Group Selector (placeholder - would connect to API) */}
        {param.type === 'device-group-selector' && (
          <select {...commonProps}>
            <option value="">Select a device group...</option>
            <option value="all-devices">All Devices</option>
            <option value="switches">Switches</option>
            <option value="routers">Routers</option>
          </select>
        )}

        {/* Table Selector (placeholder) */}
        {param.type === 'table-selector' && (
          <select {...commonProps}>
            <option value="devices">devices</option>
            <option value="interfaces">interfaces</option>
            <option value="optical_power_readings">optical_power_readings</option>
            <option value="scan_results">scan_results</option>
            <option value="custom">Custom...</option>
          </select>
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

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div 
        className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div 
          className="px-6 py-4 border-b border-gray-200 flex items-center justify-between"
          style={{ backgroundColor: `${nodeDefinition.color}10` }}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">{nodeDefinition.icon}</span>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Edit: {nodeDefinition.name}
              </h2>
              <p className="text-sm text-gray-500">{nodeDefinition.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* General Section */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">
              General
            </h3>
            
            {/* Node Label */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Node Name
              </label>
              <input
                type="text"
                value={formData.label || ''}
                onChange={(e) => updateField('label', e.target.value)}
                placeholder={nodeDefinition.name}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Node Description */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                value={formData.description || ''}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="Optional description"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Parameters Section */}
          {parameters.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">
                Parameters
              </h3>
              {parameters.map(renderField)}
            </div>
          )}

          {/* Advanced Section */}
          {advancedParams.length > 0 && (
            <div className="mb-6">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900 mb-3"
              >
                {showAdvanced ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                Advanced Settings
              </button>
              
              {showAdvanced && (
                <div className="pl-4 border-l-2 border-gray-200">
                  {advancedParams.map(renderField)}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-gray-50 rounded-b-xl">
          <button
            onClick={onDelete}
            className="px-3 py-2 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md"
          >
            Delete Node
          </button>
          
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NodeEditor;
