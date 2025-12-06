import React from 'react';

export const JobHeader = ({ testMode, onToggleTestMode, onBack, onTest, onSave, currentJob }) => (
  <div className="bg-white rounded shadow p-3 mb-2">
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-bold tracking-wide">COMPLETE JOB DEFINITION</h1>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={testMode}
            onChange={(e) => onToggleTestMode(e.target.checked)}
            className="rounded"
          />
          Test Mode
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={onBack} className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600">
          Back
        </button>
        <button onClick={() => onTest(currentJob)} className="px-3 py-1 bg-green-500 text-white rounded text-sm">
          Test
        </button>
        <button onClick={() => onSave(currentJob)} className="px-3 py-1 bg-blue-500 text-white rounded text-sm">
          Save
        </button>
      </div>
    </div>
  </div>
);
