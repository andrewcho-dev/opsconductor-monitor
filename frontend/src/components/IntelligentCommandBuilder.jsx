import React, { useState, useEffect } from 'react';
import { COMMAND_LIBRARIES, getCommandLibrary, getAvailablePlatforms, getCommand } from '../data/commandLibraries';

console.log('IntelligentCommandBuilder component loading...');

// Map many low-level categories into a smaller set of logical groups for the UI
const RAW_CATEGORY_TO_GROUP = {
  discovery: 'discovery_scanning',
  scanning: 'discovery_scanning',
  system: 'system_processes',
  processes: 'system_processes',
  networking: 'networking_diagnostics',
  'network-diagnostics': 'networking_diagnostics',
  security: 'security_monitoring',
  monitoring: 'security_monitoring',
  storage: 'storage_files',
  'file-management': 'storage_files',
  logging: 'text_logs',
  'text-processing': 'text_logs',
  services: 'services_scheduling',
  scheduling: 'services_scheduling',
  packages: 'packages_software',
  'user-management': 'users_access',
  web: 'web_apis',
  other: 'other'
};

const CATEGORY_GROUP_META = {
  discovery_scanning: { label: 'Discovery & Scanning', icon: '🔍' },
  system_processes: { label: 'System & Processes', icon: '💻' },
  networking_diagnostics: { label: 'Networking & Diagnostics', icon: '🌐' },
  security_monitoring: { label: 'Security & Monitoring', icon: '🔒' },
  storage_files: { label: 'Storage & Files', icon: '💾' },
  services_scheduling: { label: 'Services & Scheduling', icon: '🛠️' },
  packages_software: { label: 'Packages & Software', icon: '📦' },
  text_logs: { label: 'Text & Logs', icon: '📝' },
  users_access: { label: 'Users & Access', icon: '👤' },
  web_apis: { label: 'Web & APIs', icon: '🌍' },
  other: { label: 'Other', icon: '📋' }
};

const mapCategoryToGroup = (rawCategory) => {
  if (!rawCategory) return 'other';
  return RAW_CATEGORY_TO_GROUP[rawCategory] || 'other';
};

const getCategoryLabel = (categoryKey) => {
  const meta = CATEGORY_GROUP_META[categoryKey];
  if (meta) return meta.label;
  return (categoryKey || 'other').replace(/[_-]/g, ' ').toUpperCase();
};

const getCategoryIcon = (categoryKey) => {
  const meta = CATEGORY_GROUP_META[categoryKey];
  if (meta) return meta.icon;
  return '📋';
};

const IntelligentCommandBuilder = ({ action, actionIndex, updateAction, children }) => {
  const [selectedPlatform, setSelectedPlatform] = useState('ubuntu-20.04');
  const [selectedCommand, setSelectedCommand] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [commandData, setCommandData] = useState({});
  const [validationResults, setValidationResults] = useState({});
  const [showPreview, setShowPreview] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showOriginPicker, setShowOriginPicker] = useState(false);
  const [showCommandPicker, setShowCommandPicker] = useState(false);

  // Initialize platform and command from existing action
  useEffect(() => {
    if (action.login_method?.platform) {
      setSelectedPlatform(action.login_method.platform);
    }
    if (action.login_method?.command_id) {
      setSelectedCommand(action.login_method.command_id);
    }
  }, [action]);

  // Update command data when platform or command changes
  useEffect(() => {
    const library = getCommandLibrary(selectedPlatform);
    const command = library?.commands?.[selectedCommand];
    setCommandData(command || {});

    // Initialize parameter values
    if (command && !action.login_method?.parameters) {
      const initialParams = {};
      Object.entries(command.parameters || {}).forEach(([key, param]) => {
        initialParams[key] = param.default || '';
      });
      updateAction(actionIndex, 'login_method.parameters', initialParams);
    }
  }, [selectedPlatform, selectedCommand]);

  // Validate all parameters in real-time
  useEffect(() => {
    if (commandData.parameters) {
      const results = {};
      Object.entries(commandData.parameters).forEach(([key, param]) => {
        const value = action.login_method?.parameters?.[key] || '';
        results[key] = validateParameter(param, value);
      });
      setValidationResults(results);
    }
  }, [action.login_method?.parameters, commandData]);

  const validateParameter = (param, value) => {
    const result = {
      status: 'empty',
      message: '',
      warnings: [],
      errors: []
    };

    if (param.required && (!value || value === '')) {
      result.status = 'error';
      result.errors.push('This field is required');
      return result;
    }

    if (!value || value === '') {
      return result;
    }

    // Pattern validation
    if (param.validation?.pattern && !param.validation.pattern.test(value)) {
      result.status = 'error';
      result.errors.push(param.validation.message || 'Invalid format');
    }

    // Range validation
    if (param.type === 'number') {
      const numValue = parseFloat(value);
      if (param.min !== undefined && numValue < param.min) {
        result.status = 'error';
        result.errors.push(`Must be at least ${param.min}`);
      }
      if (param.max !== undefined && numValue > param.max) {
        result.status = 'error';
        result.errors.push(`Must be no more than ${param.max}`);
      }

      // Warnings
      if (param.validation?.warning?.min && numValue >= param.validation.warning.min) {
        result.warnings.push(param.validation.warning.message);
        if (result.status === 'empty') result.status = 'warning';
      }
    }

    if (result.status === 'empty' && value !== '') {
      result.status = 'valid';
    }

    return result;
  };

  const handlePlatformChange = (platform) => {
    setSelectedPlatform(platform);
    setSelectedCommand('');
    updateAction(actionIndex, 'login_method.platform', platform);
    updateAction(actionIndex, 'login_method.command_id', '');
    updateAction(actionIndex, 'login_method.parameters', {});
  };

  const handleCommandChange = (commandId) => {
    setSelectedCommand(commandId);
    const command = getCommand(selectedPlatform, commandId);

    updateAction(actionIndex, 'login_method.platform', selectedPlatform);
    updateAction(actionIndex, 'login_method.command_id', commandId);
    updateAction(actionIndex, 'login_method.command_template', command?.syntax || '');

    // Auto-update action type based on command
    const actionType = commandId.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    updateAction(actionIndex, 'type', actionType);

    // Initialize parameters
    if (command?.parameters) {
      const initialParams = {};
      Object.entries(command.parameters).forEach(([key, param]) => {
        initialParams[key] = param.default || '';
      });
      updateAction(actionIndex, 'login_method.parameters', initialParams);
    }
  };

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
    setSelectedCommand(''); // Reset command when category changes
  };

  const handleParameterChange = (key, value) => {
    const newParams = { ...action.login_method?.parameters };
    newParams[key] = value;
    updateAction(actionIndex, 'login_method.parameters', newParams);
  };

  const generateCommandPreview = () => {
    if (!commandData.syntax) return '';

    let command = commandData.syntax;
    const params = action.login_method?.parameters || {};

    // Replace parameter placeholders
    Object.entries(params).forEach(([key, value]) => {
      command = command.replace(new RegExp(`{${key}}`, 'g'), value || `{${key}}`);
    });

    // Replace variable placeholders
    command = command.replace('{target}', '{target}');

    return command;
  };

  const getValidationIcon = (status) => {
    switch (status) {
      case 'valid': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      case 'required': return '🔴';
      default: return '⚪';
    }
  };

  const getValidationColor = (status) => {
    switch (status) {
      case 'valid': return 'border-green-500 bg-green-50';
      case 'warning': return 'border-yellow-500 bg-yellow-50';
      case 'error': return 'border-red-500 bg-red-50';
      default: return 'border-gray-300 bg-gray-50';
    }
  };

  const platforms = getAvailablePlatforms();
  const currentLibrary = getCommandLibrary(selectedPlatform);
  const availableCommands = Object.entries(currentLibrary?.commands || {});

  // Group commands by consolidated category groups for a simpler UI
  const commandsByCategory = availableCommands.reduce((groups, [id, command]) => {
    const rawCategory = command.category || 'other';
    const groupKey = mapCategoryToGroup(rawCategory);
    if (!groups[groupKey]) groups[groupKey] = [];
    groups[groupKey].push({ id, ...command, rawCategory, category: groupKey });
    return groups;
  }, {});

  const allCommandsFlat = Object.entries(commandsByCategory).flatMap(([groupKey, cmds]) =>
    cmds.map((cmd) => ({ ...cmd, category: groupKey }))
  );

  const visibleCommands =
    selectedCategory === 'all'
      ? allCommandsFlat
      : allCommandsFlat.filter((cmd) => cmd.category === selectedCategory);

  const currentPlatform =
    platforms.find((platform) => platform.id === selectedPlatform) || platforms[0] || null;
  const originSummary = currentPlatform
    ? `${currentPlatform.icon ? `${currentPlatform.icon} ` : ''}${currentPlatform.name || currentPlatform.id}`
    : 'Select origin';

  const commandSummary =
    selectedCommand && commandData?.name
      ? commandData.name
      : selectedCommand
      ? selectedCommand
      : 'Select command';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 items-stretch">
        {/* Origin (Execution Platform) */}
        <div className="bg-white rounded shadow p-4 h-full">
          <h4 className="text-sm font-bold mb-3 flex items-center gap-2">
            <span>🌐</span> ORIGIN
          </h4>

          <button
            type="button"
            onClick={() => setShowOriginPicker(true)}
            className="w-full text-left text-xs px-2 py-2 border rounded bg-gray-200 hover:bg-white focus:bg-white focus:ring-1 focus:ring-blue-300"
          >
            <span className="block text-gray-800 truncate">{originSummary}</span>
          </button>
        </div>

        {/* Command - COMPACT VERSION */}
        <div className="bg-white rounded shadow p-3 h-full">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-bold flex items-center gap-2">
              <span>⚡</span> COMMAND
            </h4>
            <button
              type="button"
              onClick={() => setShowAdvanced(true)}
              disabled={!selectedCommand}
              className="p-1 rounded-full text-blue-600 hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed"
              title="Advanced command settings"
            >
              ⚙️
            </button>
          </div>

          <button
            type="button"
            onClick={() => setShowCommandPicker(true)}
            className="w-full text-left text-xs px-2 py-2 border rounded bg-gray-200 hover:bg-white focus:bg-white focus:ring-1 focus:ring-blue-300"
          >
            <span className="block text-gray-800 truncate">{commandSummary}</span>
          </button>

          {/* Compact Command Info: show ONLY the concrete command that will run */}
          {selectedCommand && commandData.syntax && (
            <div className="mt-2 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-[11px] font-mono text-green-400 overflow-x-auto whitespace-nowrap">
              {generateCommandPreview()}
            </div>
          )}
        </div>

        {children && (
          <div>{children}</div>
        )}
      </div>

      {showOriginPicker && (
        <div className="fixed inset-0 z-40 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowOriginPicker(false)} />
          <div className="relative z-50 w-full max-w-md bg-white rounded-lg shadow-xl border border-gray-200 p-4 space-y-3">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="text-sm font-bold flex items-center gap-2">
                <span>🌐</span> Select Origin
              </h4>
              <button
                type="button"
                onClick={() => setShowOriginPicker(false)}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1 text-sm">
              {platforms.map((platform) => (
                <button
                  key={platform.id}
                  type="button"
                  onClick={() => {
                    handlePlatformChange(platform.id);
                    setShowOriginPicker(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded border mb-1 ${
                    platform.id === selectedPlatform
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <span className="truncate">
                    {platform.icon} {platform.name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {showCommandPicker && (
        <div className="fixed inset-0 z-40 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setShowCommandPicker(false)}
          />
          <div className="relative z-50 w-full max-w-6xl bg-white rounded-lg shadow-xl border border-gray-200 p-4 space-y-3 max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="text-sm font-bold flex items-center gap-2">
                <span>⚡</span> Select Command
              </h4>
              <button
                type="button"
                onClick={() => setShowCommandPicker(false)}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="space-y-1 h-full flex flex-col">
                <div className="text-xs font-semibold text-gray-600">Categories</div>
                <div className="border rounded p-2 h-[60vh] overflow-y-auto pr-1 flex flex-col gap-1">
                  <button
                    type="button"
                    onClick={() => setSelectedCategory('all')}
                    className={`px-2 py-1 text-left text-xs rounded border ${
                      selectedCategory === 'all'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <span>📋 All</span>
                  </button>
                  {Object.keys(commandsByCategory).map((category) => (
                    <button
                      key={category}
                      type="button"
                      onClick={() => setSelectedCategory(category)}
                      className={`px-2 py-1 text-left text-xs rounded border ${
                        selectedCategory === category
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <span>
                        {getCategoryIcon(category)} {getCategoryLabel(category)}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="md:col-span-3 flex flex-col h-full">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-xs font-semibold text-gray-600">Commands</div>
                </div>
                <div className="border rounded p-2 h-[60vh] overflow-y-auto space-y-1 text-xs">
                  {visibleCommands.map((cmd) => (
                    <button
                      key={cmd.id}
                      type="button"
                      onClick={() => {
                        handleCommandChange(cmd.id);
                        setShowCommandPicker(false);
                      }}
                      className={`w-full text-left px-3 py-1 rounded border ${
                        cmd.id === selectedCommand
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-2 w-full">
                        <span
                          className="text-xs font-semibold text-gray-900 truncate w-44"
                          title={cmd.description || ''}
                        >
                          {cmd.name}
                        </span>
                        {cmd.description && (
                          <span className="text-[11px] text-gray-600 truncate flex-1">
                            {cmd.description}
                          </span>
                        )}
                        <span className="text-[10px] uppercase text-gray-500 whitespace-nowrap">
                          {getCategoryLabel(cmd.category || 'other')}
                        </span>
                      </div>
                    </button>
                  ))}
                  {visibleCommands.length === 0 && (
                    <div className="text-xs text-gray-500">No commands available for this category.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Advanced modal for command parameters + preview */}
      {showAdvanced && selectedCommand && commandData.name && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowAdvanced(false)} />
          <div className="relative z-10 w-full max-w-3xl bg-white rounded-lg shadow-xl border border-gray-200 p-4 space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="text-sm font-bold flex items-center gap-2">
                <span>⚙️</span> Advanced Command Settings
                <span className="text-xs font-normal text-gray-600 ml-1">
                  {commandData.name}
                </span>
              </h4>
              <button
                type="button"
                onClick={() => setShowAdvanced(false)}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                ✕
              </button>
            </div>

            {/* Command Configuration (moved into modal) */}
            {commandData.warnings && commandData.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-2">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-yellow-600">⚠️</span>
                  <span className="text-sm font-medium text-yellow-800">Important Notes</span>
                </div>
                <ul className="text-xs text-yellow-700 space-y-1">
                  {commandData.warnings.map((warning, index) => (
                    <li key={index}>• {warning}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(commandData.parameters || {}).map(([key, param]) => {
                const validation = validationResults[key] || {};
                const value = action.login_method?.parameters?.[key] || '';

                return (
                  <div key={key} className="space-y-1">
                    <label className="block text-xs font-medium flex items-center gap-1">
                      {param.label}
                      {param.required && <span className="text-red-500">*</span>}
                      <span className="text-gray-400">{getValidationIcon(validation.status)}</span>
                    </label>

                    {param.type === 'select' ? (
                      <select
                        value={value}
                        onChange={(e) => handleParameterChange(key, e.target.value)}
                        className={`w-full p-2 border rounded text-sm ${getValidationColor(
                          validation.status
                        )} focus:bg-white focus:ring-2 focus:ring-blue-300`}
                      >
                        {param.options?.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : param.type === 'checkbox' ? (
                      <label className="flex items-center gap-2 p-2 border rounded text-sm bg-gray-50">
                        <input
                          type="checkbox"
                          checked={value}
                          onChange={(e) => handleParameterChange(key, e.target.checked)}
                          className="rounded"
                        />
                        <span className="text-xs">{param.label}</span>
                      </label>
                    ) : (
                      <input
                        type={param.type || 'text'}
                        value={value}
                        onChange={(e) => handleParameterChange(key, e.target.value)}
                        placeholder={param.placeholder || ''}
                        className={`w-full p-2 border rounded text-sm ${getValidationColor(
                          validation.status
                        )} focus:bg-white focus:ring-2 focus:ring-blue-300`}
                      />
                    )}

                    {/* Validation Messages */}
                    <div className="space-y-1">
                      {validation.errors?.map((error, index) => (
                        <div key={index} className="text-xs text-red-600 flex items-center gap-1">
                          <span>❌</span> {error}
                        </div>
                      ))}
                      {validation.warnings?.map((warning, index) => (
                        <div key={index} className="text-xs text-yellow-600 flex items-center gap-1">
                          <span>⚠️</span> {warning}
                        </div>
                      ))}
                      {validation.status === 'valid' && (
                        <div className="text-xs text-green-600 flex items-center gap-1">
                          <span>✅</span> Valid
                        </div>
                      )}
                    </div>

                    {/* Help Text */}
                    {param.help && (
                      <div className="text-xs text-blue-600 flex items-start gap-1">
                        <span>ℹ️</span>
                        <span>{param.help}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Command Preview (moved into modal) */}
            {commandData.syntax && (
              <div className="bg-gray-900 rounded shadow p-4 mt-2">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-green-400 flex items-center gap-2">
                    <span>👁️</span> COMMAND PREVIEW
                  </h4>
                  <button
                    onClick={() => setShowPreview(!showPreview)}
                    className="text-xs text-gray-400 hover:text-white"
                  >
                    {showPreview ? 'Hide' : 'Show'}
                  </button>
                </div>

                {showPreview && (
                  <div className="space-y-3">
                    <div className="font-mono text-sm text-green-400 bg-black rounded p-3">
                      {generateCommandPreview()}
                    </div>

                    {/* Variables */}
                    <div className="text-xs text-gray-400">
                      <div className="font-medium mb-2">Variables:</div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <code className="bg-gray-800 px-1 py-0.5 rounded">{'{target}'}</code>
                          <span>- Will be replaced with actual target addresses</span>
                        </div>
                      </div>
                    </div>

                    {/* Examples */}
                    {commandData.examples && commandData.examples.length > 0 && (
                      <div className="text-xs text-gray-400">
                        <div className="font-medium mb-2">Examples:</div>
                        <div className="space-y-2">
                          {commandData.examples.map((example, index) => (
                            <div key={index} className="bg-gray-800 rounded p-2">
                              <div className="font-mono text-green-300">{example.command}</div>
                              <div className="text-gray-500 mt-1">{example.description}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2 border-t mt-2">
              <button
                type="button"
                onClick={() => setShowAdvanced(false)}
                className="px-3 py-1 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IntelligentCommandBuilder;
