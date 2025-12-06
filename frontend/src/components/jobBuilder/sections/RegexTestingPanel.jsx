import React from 'react';

export const RegexTestingPanel = ({
  testMode,
  setTestMode,
  testActionIndex,
  setTestActionIndex,
  testInput,
  setTestInput,
  testResults,
  actions
}) => (
  <div className="bg-white rounded shadow p-3">
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-lg font-bold">Regex Testing</h2>
      <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
        <input
          type="checkbox"
          checked={testMode}
          onChange={(e) => setTestMode(e.target.checked)}
          className="rounded"
        />
        Enable Test Mode
      </label>
    </div>

    {testMode ? (
      <div className="space-y-3 text-sm">
        <div>
          <label className="block text-xs font-medium mb-1">Test Action</label>
          <select
            value={testActionIndex}
            onChange={(e) => setTestActionIndex(parseInt(e.target.value, 10) || 0)}
            className="w-full p-2 border rounded text-xs bg-gray-100 focus:bg-white focus:ring-2 focus:ring-blue-300"
          >
            {actions.map((action, index) => (
              <option key={index} value={index}>
                Action {index + 1}: {action.type?.toUpperCase() || 'UNKNOWN'}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium mb-1">Sample Output</label>
          <textarea
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            rows={6}
            className="w-full p-2 border rounded font-mono text-xs bg-gray-100 focus:bg-white focus:ring-2 focus:ring-blue-300"
            placeholder="Enter sample command output…"
          />
        </div>

        <div>
          <h3 className="text-xs font-bold uppercase tracking-wide text-gray-600 mb-1">Results</h3>
          {testResults.length === 0 ? (
            <div className="text-xs text-gray-500 italic">
              No patterns to test. Add regex patterns to the selected action.
            </div>
          ) : (
            <div className="space-y-2">
              {testResults.map((result, index) => (
                <div key={index} className="border rounded p-2 bg-gray-50">
                  <div className="mb-2">
                    <h4 className="text-xs font-bold mb-1">Parsed Fields</h4>
                    <div className="bg-white border rounded p-2 font-mono text-[10px] space-y-1">
                      {Object.entries(result.parsedFields).map(([field, value]) => (
                        <div key={field}>
                          <span className="font-semibold">{field}:</span> {JSON.stringify(value)}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <h4 className="text-xs font-bold">Pattern Matches</h4>
                    {result.patterns.map((pattern, patternIndex) => (
                      <div
                        key={patternIndex}
                        className={`rounded border px-2 py-1 text-xs font-mono ${
                          pattern.success ? 'border-green-300 bg-green-50 text-green-800' : 'border-red-300 bg-red-50 text-red-700'
                        }`}
                      >
                        <div className="font-semibold">{pattern.patternName}</div>
                        <div className="break-all text-[10px]">{pattern.regex}</div>
                        {pattern.success ? (
                          <div>{pattern.matches.length} matches</div>
                        ) : (
                          <div>Error: {pattern.error}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    ) : (
      <div className="bg-gray-50 border-2 border-dashed border-gray-200 p-6 text-center text-sm text-gray-500">
        Enable test mode to validate regex patterns against sample outputs.
      </div>
    )}
  </div>
);
