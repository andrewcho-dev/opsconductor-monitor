import React, { useState, useEffect } from 'react';
import { COMMAND_LIBRARIES, getCommandLibrary, getAvailablePlatforms, getCommand } from '../data/commandLibraries';

console.log('IntelligentCommandBuilder component loading...');

const IntelligentCommandBuilder = ({ action, actionIndex, updateAction }) => {
  const [selectedPlatform, setSelectedPlatform] = useState('ubuntu-20.04');
  const [selectedCommand, setSelectedCommand] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [commandData, setCommandData] = useState({});
  const [validationResults, setValidationResults] = useState({});
  const [showPreview, setShowPreview] = useState(true);

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

  const getCategoryIcon = (category) => {
    const icons = {
      'discovery': '🔍',
      'scanning': '📡',
      'system': '💻',
      'networking': '🌐',
      'processes': '⚙️',
      'security': '🔒',
      'monitoring': '📊',
      'storage': '💾',
      'services': '🛠️',
      'logging': '📝',
      'packages': '📦',
      'text-processing': '📝',
      'file-management': '📁',
      'user-management': '👤',
      'network-diagnostics': '🩺',
      'performance': '⚡',
      'scheduling': '⏰',
      'web': '🌍',
      'other': '📋'
    };
    return icons[category] || '📋';
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

  const currentLibrary = getCommandLibrary(selectedPlatform);
  const availableCommands = Object.entries(currentLibrary?.commands || {});

  // Group commands by category
  const commandsByCategory = availableCommands.reduce((groups, [id, command]) => {
    const category = command.category || 'other';
    if (!groups[category]) groups[category] = [];
    groups[category].push({ id, ...command });
    return groups;
  }, {});

  return (
    <div className="space-y-4">
      {/* Platform Selection */}
      <div className="bg-white rounded shadow p-4">
        <h4 className="text-sm font-bold mb-3 flex items-center gap-2">
          <span>🌐</span> EXECUTION PLATFORM
          <span className="text-xs font-normal text-gray-600 ml-1">
            (Where this command will run)
          </span>
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium mb-1">Platform</label>
            <select
              value={selectedPlatform}
              onChange={(e) => handlePlatformChange(e.target.value)}
              className="w-full p-2 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
            >
              {getAvailablePlatforms().map(platform => (
                <option key={platform.id} value={platform.id}>
                  {platform.icon} {platform.name}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-xs font-medium mb-1">Platform Info</label>
            <div className="w-full p-2 border rounded text-sm bg-gray-100 text-gray-600">
              {currentLibrary?.description}
            </div>
          </div>
        </div>
      </div>

      {/* Command Selection - COMPACT VERSION */}
      <div className="bg-white rounded shadow p-3">
        <h4 className="text-sm font-bold mb-2 flex items-center gap-2">
          <span>⚡</span> COMMAND SELECTION
          <span className="text-xs font-normal text-gray-600 ml-1">
            (What to execute)
          </span>
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-2">
          <div>
            <label className="block text-xs font-medium mb-1">Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
            >
              <option value="all">📋 All Categories</option>
              {Object.keys(commandsByCategory).map(category => (
                <option key={category} value={category}>
                  {getCategoryIcon(category)} {category.replace(/_/g, ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-xs font-medium mb-1">Command</label>
            <select
              value={selectedCommand}
              onChange={(e) => handleCommandChange(e.target.value)}
              className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
            >
              <option value="">Select a command...</option>
              {selectedCategory === 'all' 
                ? Object.values(commandsByCategory).flat().map(command => (
                    <option key={command.id} value={command.id}>
                      {command.name}
                    </option>
                  ))
                : commandsByCategory[selectedCategory]?.map(command => (
                    <option key={command.id} value={command.id}>
                      {command.name}
                    </option>
                  ))
              }
            </select>
          </div>
        </div>

        {/* Compact Command Info */}
        {selectedCommand && commandData.name && (
          <div className="bg-blue-50 border border-blue-200 rounded p-2 text-xs">
            <div className="flex items-start gap-2">
              <span className="text-blue-600">ℹ️</span>
              <div className="flex-1">
                <div className="font-medium text-blue-800">{commandData.name}</div>
                <div className="text-blue-600 mt-1">{commandData.description}</div>
                {commandData.syntax && (
                  <div className="mt-1 font-mono text-blue-700 bg-blue-100 p-1 rounded">
                    Syntax: {commandData.syntax}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Compact Command List for Quick Reference */}
        {selectedCategory === 'all' && (
          <div className="mt-2">
            <div className="text-xs font-medium text-gray-600 mb-1">Quick Reference:</div>
            <div className="max-h-32 overflow-y-auto border rounded bg-gray-50 p-1">
              <div className="grid grid-cols-2 gap-1 text-xs">
                {Object.entries(commandsByCategory).slice(0, 4).map(([category, commands]) => (
                  <div key={category} className="col-span-1">
                    <div className="font-medium text-gray-700 mb-1">
                      {getCategoryIcon(category)} {category.replace(/_/g, ' ')}
                    </div>
                    {commands.slice(0, 3).map(command => (
                      <button
                        key={command.id}
                        onClick={() => handleCommandChange(command.id)}
                        className={`block w-full text-left p-1 rounded border transition-colors ${
                          selectedCommand === command.id
                            ? 'bg-blue-500 text-white border-blue-600'
                            : 'bg-white hover:bg-gray-100 border-gray-200'
                        }`}
                      >
                        <div className="font-medium">{command.name}</div>
                      </button>
                    ))}
                    {commands.length > 3 && (
                      <div className="text-xs text-gray-500 italic p-1">
                        +{commands.length - 3} more...
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Command Configuration */}
      {commandData.name && (
        <div className="bg-white rounded shadow p-4">
          <h4 className="text-sm font-bold mb-3 flex items-center gap-2">
            <span>⚙️</span> COMMAND CONFIGURATION
            <span className="text-xs font-normal text-gray-600 ml-1">
              (Parameters for {commandData.name})
            </span>
          </h4>
          
          {commandData.warnings && commandData.warnings.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
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
                      className={`w-full p-2 border rounded text-sm ${getValidationColor(validation.status)} focus:bg-white focus:ring-2 focus:ring-blue-300`}
                    >
                      {param.options?.map(option => (
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
                      className={`w-full p-2 border rounded text-sm ${getValidationColor(validation.status)} focus:bg-white focus:ring-2 focus:ring-blue-300`}
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
        </div>
      )}

      {/* Command Preview */}
      {commandData.syntax && (
        <div className="bg-gray-900 rounded shadow p-4">
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
    </div>
  );
};

export default IntelligentCommandBuilder;
