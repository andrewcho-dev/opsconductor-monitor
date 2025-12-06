import React, { useState } from 'react';
import { Plus, Trash2, TestTube, Save, Play, Settings, ChevronDown, ChevronRight } from 'lucide-react';

const GenericJobBuilder = ({ job, onSave, onTest, onBack }) => {
  const [currentJob, setCurrentJob] = useState(job || {
    job_id: 'custom_job',
    name: 'Custom Job',
    description: '',
    actions: [],
    config: {
      network: '10.127.0.0/24',
      parallel_threads: 20,
      batch_size: 50
    }
  });
  const [expandedActions, setExpandedActions] = useState({});
  const [expandedSections, setExpandedSections] = useState({});

  const toggleAction = (actionId) => {
    setExpandedActions(prev => ({
      ...prev,
      [actionId]: !prev[actionId]
    }));
  };

  const toggleSection = (actionId, section) => {
    setExpandedSections(prev => ({
      ...prev,
      [`${actionId}_${section}`]: !prev[`${actionId}_${section}`]
    }));
  };

  const updateAction = (actionId, field, value) => {
    setCurrentJob(prev => ({
      ...prev,
      actions: prev.actions.map((action, index) => 
        index === actionId ? { ...action, [field]: value } : action
      )
    }));
  };

  const addAction = () => {
    const newAction = {
      type: 'custom_scan',
      login_method: 'ping',
      command: 'ping -c 1 {target}',
      target_source: 'network_range',
      result_parser: 'ping_result',
      database_table: 'devices',
      timeout: 5,
      enabled: true
    };
    setCurrentJob(prev => ({
      ...prev,
      actions: [...prev.actions, newAction]
    }));
  };

  const deleteAction = (actionId) => {
    setCurrentJob(prev => ({
      ...prev,
      actions: prev.actions.filter((_, index) => index !== actionId)
    }));
  };

  const testAction = (actionId) => {
    const action = currentJob.actions[actionId];
    console.log('Testing action:', action);
    // TODO: Implement actual action testing
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Poller Jobs
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">Job Builder</h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onTest(currentJob)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <TestTube className="w-4 h-4" />
              Test Job
            </button>
            <button
              onClick={() => onSave(currentJob)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Save className="w-4 h-4" />
              Save Job
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6 max-w-6xl mx-auto">
        {/* Job Information */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Job Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job Name</label>
              <input
                type="text"
                value={currentJob?.name || ''}
                onChange={(e) => setCurrentJob(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter job name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job ID</label>
              <input
                type="text"
                value={currentJob?.job_id || ''}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                readOnly
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={currentJob?.description || ''}
                onChange={(e) => setCurrentJob(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="Describe what this job does"
              />
            </div>
          </div>
        </div>

        {/* Configuration */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            ⚙️ Configuration
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Network Range</label>
              <input
                type="text"
                value={currentJob?.config?.network || '10.127.0.0/24'}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, network: e.target.value }
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="10.127.0.0/24"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Parallel Threads</label>
              <input
                type="number"
                value={currentJob?.config?.parallel_threads || 20}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, parallel_threads: parseInt(e.target.value) }
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min="1"
                max="100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Batch Size</label>
              <input
                type="number"
                value={currentJob?.config?.batch_size || 50}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, batch_size: parseInt(e.target.value) }
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min="1"
                max="200"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              🚀 Actions ({currentJob?.actions?.length || 0} actions)
            </h2>
            <button
              onClick={addAction}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add New Action
            </button>
          </div>

          <div className="space-y-4">
            {currentJob?.actions?.map((action, index) => (
              <div key={index} className="border border-gray-200 rounded-lg">
                {/* Action Header */}
                <div
                  onClick={() => toggleAction(index)}
                  className="flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 cursor-pointer border-b border-gray-200"
                >
                  <div className="flex items-center gap-3">
                    {expandedActions[index] ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                    <span className="font-medium text-gray-800">
                      Action {index + 1}: {action.type?.replace('_', ' ').toUpperCase()}
                    </span>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={action.enabled !== false}
                        onChange={(e) => updateAction(index, 'enabled', e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-600">Enabled</span>
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        testAction(index);
                      }}
                      className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                      title="Test Action"
                    >
                      <TestTube className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteAction(index);
                      }}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete Action"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Action Details */}
                {expandedActions[index] && (
                  <div className="p-4 space-y-4">
                    {/* Action Type */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Action Type</label>
                      <select
                        value={action.type || ''}
                        onChange={(e) => updateAction(index, 'type', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="ping_scan">Ping Scan</option>
                        <option value="snmp_scan">SNMP Scan</option>
                        <option value="ssh_scan">SSH Scan</option>
                        <option value="rdp_scan">RDP Scan</option>
                        <option value="custom">Custom Command</option>
                      </select>
                    </div>

                    {/* Login Method Section */}
                    <div className="border border-gray-200 rounded-lg">
                      <div
                        onClick={() => toggleSection(index, 'login')}
                        className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 cursor-pointer border-b border-gray-200"
                      >
                        {expandedSections[`${index}_login`] ? (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500" />
                        )}
                        <span className="font-medium text-gray-700">🔐 Login Method</span>
                      </div>
                      {expandedSections[`${index}_login`] && (
                        <div className="p-3 space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Method</label>
                            <select
                              value={action.login_method || ''}
                              onChange={(e) => updateAction(index, 'login_method', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="ping">Ping</option>
                              <option value="snmp">SNMP</option>
                              <option value="ssh_port">SSH Port Check</option>
                              <option value="rdp_port">RDP Port Check</option>
                              <option value="ssh_command">SSH Command</option>
                              <option value="http_request">HTTP Request</option>
                              <option value="custom">Custom Script</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Command Template</label>
                            <input
                              type="text"
                              value={action.command || ''}
                              onChange={(e) => updateAction(index, 'command', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              placeholder="ping -c 1 -W 1 {target}"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                              Use {target}, {port}, {timeout} as variables
                            </p>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (seconds)</label>
                            <input
                              type="number"
                              value={action.timeout || 5}
                              onChange={(e) => updateAction(index, 'timeout', parseInt(e.target.value))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              min="1"
                              max="300"
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Targeting Section */}
                    <div className="border border-gray-200 rounded-lg">
                      <div
                        onClick={() => toggleSection(index, 'targeting')}
                        className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 cursor-pointer border-b border-gray-200"
                      >
                        {expandedSections[`${index}_targeting`] ? (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500" />
                        )}
                        <span className="font-medium text-gray-700">🎯 Targeting</span>
                      </div>
                      {expandedSections[`${index}_targeting`] && (
                        <div className="p-3 space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Target Source</label>
                            <select
                              value={action.target_source || ''}
                              onChange={(e) => updateAction(index, 'target_source', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="network_range">Network Range</option>
                              <option value="device_list">All Devices</option>
                              <option value="ssh_devices">SSH-Accessible Devices</option>
                              <option value="custom_list">Custom List</option>
                              <option value="database_query">Database Query</option>
                            </select>
                          </div>
                          {action.target_source === 'network_range' && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Network</label>
                              <input
                                type="text"
                                value={job?.config?.network || '10.127.0.0/24'}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                placeholder="10.127.0.0/24"
                              />
                            </div>
                          )}
                          {action.target_source === 'custom_list' && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Custom Targets</label>
                              <textarea
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                rows={4}
                                placeholder="192.168.1.1&#10;192.168.1.10&#10;server.example.com"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Results Section */}
                    <div className="border border-gray-200 rounded-lg">
                      <div
                        onClick={() => toggleSection(index, 'results')}
                        className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 cursor-pointer border-b border-gray-200"
                      >
                        {expandedSections[`${index}_results`] ? (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500" />
                        )}
                        <span className="font-medium text-gray-700">📊 Results</span>
                      </div>
                      {expandedSections[`${index}_results`] && (
                        <div className="p-3 space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Result Parser</label>
                            <select
                              value={action.result_parser || ''}
                              onChange={(e) => updateAction(index, 'result_parser', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="ping_result">Ping Result</option>
                              <option value="snmp_result">SNMP Result</option>
                              <option value="port_result">Port Result</option>
                              <option value="hostname_result">Hostname Result</option>
                              <option value="custom">Custom Parser</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Store in Database Table</label>
                            <select
                              value={action.database_table || ''}
                              onChange={(e) => updateAction(index, 'database_table', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="devices">Devices</option>
                              <option value="interfaces">Interfaces</option>
                              <option value="optical">Optical Power</option>
                              <option value="custom">Custom Table</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Expected Fields</label>
                            <div className="flex flex-wrap gap-2">
                              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">ip_address</span>
                              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">ping_status</span>
                              <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">last_seen</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors text-sm">
                              <Settings className="w-4 h-4" />
                              Configure Parser
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GenericJobBuilder;
