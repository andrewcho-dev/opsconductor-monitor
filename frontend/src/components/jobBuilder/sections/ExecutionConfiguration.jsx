import React from 'react';

const numberValue = (value) => (value === '' || value === undefined ? '' : Number(value));

export const ExecutionConfiguration = ({ currentJob, setCurrentJob }) => {
  const config = currentJob.config || {};

  const updateConfig = (field, value) => {
    setCurrentJob((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        [field]: value
      }
    }));
  };

  return (
    <div className="bg-white rounded shadow p-3 mb-2">
      <h2 className="text-lg font-bold mb-2">
        EXECUTION CONFIGURATION
        <span className="text-xs font-normal text-gray-600 ml-2">
          (Global run settings)
        </span>
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium mb-1">Parallel Threads</label>
          <input
            type="number"
            value={numberValue(config.parallel_threads)}
            onChange={(e) => updateConfig('parallel_threads', parseInt(e.target.value, 10) || 0)}
            className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Batch Size</label>
          <input
            type="number"
            value={numberValue(config.batch_size)}
            onChange={(e) => updateConfig('batch_size', parseInt(e.target.value, 10) || 0)}
            className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Timeout (seconds)</label>
          <input
            type="number"
            value={numberValue(config.timeout_seconds)}
            onChange={(e) => updateConfig('timeout_seconds', parseInt(e.target.value, 10) || 0)}
            className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Retry Attempts</label>
          <input
            type="number"
            value={numberValue(config.retry_attempts)}
            onChange={(e) => updateConfig('retry_attempts', parseInt(e.target.value, 10) || 0)}
            className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Error Handling</label>
          <select
            value={config.error_handling || 'continue'}
            onChange={(e) => updateConfig('error_handling', e.target.value)}
            className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
          >
            <option value="continue">Continue</option>
            <option value="stop">Stop</option>
            <option value="retry">Retry</option>
          </select>
        </div>
        <div className="sm:col-span-2 lg:col-span-1">
          <label className="block text-xs font-medium mb-1">Network Scope</label>
          <input
            type="text"
            value={config.network || ''}
            onChange={(e) => updateConfig('network', e.target.value)}
            className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
            placeholder="10.0.0.0/24"
          />
        </div>
      </div>
    </div>
  );
};
