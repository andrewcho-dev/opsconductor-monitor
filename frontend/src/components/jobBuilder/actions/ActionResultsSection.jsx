import React from 'react';

const OPERATIONS = ['insert', 'update', 'upsert', 'replace'];
const PARSER_TYPES = ['regex', 'json', 'xml', 'csv', 'custom'];

export const ActionResultsSection = ({ action, actionIndex, updateAction }) => (
  <section className="space-y-2">
    <h4 className="text-xs font-bold uppercase tracking-wide text-gray-600">Results &amp; Storage</h4>
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
      <label className="flex flex-col gap-1 font-medium text-gray-600">
        Parser Type
        <select
          value={action.result_parsing?.parser_type || 'regex'}
          onChange={(e) => updateAction(actionIndex, 'result_parsing.parser_type', e.target.value)}
          className="p-1 border rounded bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
        >
          {PARSER_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.toUpperCase()}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 font-medium text-gray-600">
        Database Table
        <input
          type="text"
          value={action.database?.table || ''}
          onChange={(e) => updateAction(actionIndex, 'database.table', e.target.value)}
          className="p-1 border rounded bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
          placeholder="devices"
        />
      </label>

      <label className="flex flex-col gap-1 font-medium text-gray-600">
        Operation
        <select
          value={action.database?.operation || 'upsert'}
          onChange={(e) => updateAction(actionIndex, 'database.operation', e.target.value)}
          className="p-1 border rounded bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
        >
          {OPERATIONS.map((op) => (
            <option key={op} value={op}>
              {op.toUpperCase()}
            </option>
          ))}
        </select>
      </label>
    </div>
  </section>
);
