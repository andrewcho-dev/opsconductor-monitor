import React from 'react';

export const ActionPatternsEditor = ({ patterns = [], onAddPattern, onUpdatePattern, onRemovePattern }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between text-xs font-medium text-gray-600">
      <span>Parsing Patterns</span>
      <button
        type="button"
        onClick={onAddPattern}
        className="px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600"
      >
        Add Pattern
      </button>
    </div>

    {patterns.length === 0 ? (
      <div className="p-2 text-xs text-gray-500 bg-gray-50 border border-dashed border-gray-300 rounded">
        No parsing patterns defined yet.
      </div>
    ) : (
      <div className="space-y-2">
        {patterns.map((pattern, index) => (
          <div key={index} className="border rounded p-2 text-xs space-y-2 bg-white shadow-sm">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <label className="flex flex-col gap-1">
                Pattern Name
                <input
                  type="text"
                  value={pattern.name || ''}
                  onChange={(e) => onUpdatePattern(index, 'name', e.target.value)}
                  className="p-1 border rounded bg-gray-100 focus:bg-white focus:ring-1 focus:ring-blue-300"
                  placeholder="ping_success"
                />
              </label>
              <label className="flex flex-col gap-1">
                Regex Pattern
                <input
                  type="text"
                  value={pattern.regex || ''}
                  onChange={(e) => onUpdatePattern(index, 'regex', e.target.value)}
                  className="p-1 border rounded bg-gray-100 font-mono focus:bg-white focus:ring-1 focus:ring-blue-300"
                  placeholder="bytes from .*"
                />
              </label>
            </div>

            <label className="flex flex-col gap-1">
              Field Mapping (JSON)
              <textarea
                value={JSON.stringify(pattern.field_mapping || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value || '{}');
                    onUpdatePattern(index, 'field_mapping', parsed);
                  } catch (err) {
                    // swallow parse errors to allow editing
                  }
                }}
                rows={2}
                className="p-2 border rounded bg-gray-100 font-mono focus:bg-white focus:ring-1 focus:ring-blue-300"
              />
            </label>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => onRemovePattern(index)}
                className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
              >
                Remove Pattern
              </button>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);
