import React from 'react';

export const RawJsonPanel = ({ currentJob }) => (
  <details className="bg-gray-800 text-green-400 rounded shadow p-3 border-2 border-gray-600">
    <summary className="cursor-pointer font-bold text-green-300 flex items-center gap-2">
      <span role="img" aria-label="clipboard">📋</span>
      RAW JSON DEFINITION
      <span className="text-xs font-normal text-gray-400">(Read Only)</span>
    </summary>
    <div className="mt-2 space-y-2">
      <div className="text-xs text-gray-400 font-mono">
        // Complete job configuration. Copy to backup or share your job definition.
      </div>
      <textarea
        value={JSON.stringify(currentJob, null, 2)}
        readOnly
        className="w-full p-3 bg-gray-900 text-green-400 border border-gray-600 rounded font-mono text-xs focus:outline-none"
        rows={12}
        style={{ resize: 'vertical' }}
      />
    </div>
  </details>
);
