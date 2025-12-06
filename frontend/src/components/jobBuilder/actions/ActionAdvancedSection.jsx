import React from 'react';
import { ActionPatternsEditor } from './ActionPatternsEditor';

const jsonString = (value) => JSON.stringify(value ?? {}, null, 2);

const noop = () => {};

export const ActionAdvancedSection = ({
  action,
  onUpdateAction,
  onAddPattern = noop,
  onUpdatePattern = noop,
  onRemovePattern = noop
}) => (
  <details className="text-xs">
    <summary className="cursor-pointer font-bold mb-1">Advanced Configuration</summary>
    <div className="mt-3 space-y-3">
      <ActionPatternsEditor
        patterns={action.result_parsing?.patterns || []}
        onAddPattern={onAddPattern}
        onUpdatePattern={(index, field, value) => onUpdatePattern(index, field, value)}
        onRemovePattern={onRemovePattern}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          Command Parameters (JSON)
          <textarea
            value={jsonString(action.login_method?.parameters)}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value || '{}');
                onUpdateAction('login_method.parameters', parsed);
              } catch (err) {
                /* ignore parse error */
              }
            }}
            rows={3}
            className="p-2 border rounded font-mono bg-gray-100 focus:bg-white focus:ring-1 focus:ring-blue-300"
          />
        </label>

        <label className="flex flex-col gap-1">
          Success Criteria (JSON)
          <textarea
            value={jsonString(action.login_method?.success_criteria)}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value || '{}');
                onUpdateAction('login_method.success_criteria', parsed);
              } catch (err) {
                /* ignore parse error */
              }
            }}
            rows={3}
            className="p-2 border rounded font-mono bg-gray-100 focus:bg-white focus:ring-1 focus:ring-blue-300"
          />
        </label>
      </div>

      <label className="flex flex-col gap-1">
        Default Values (JSON)
        <textarea
          value={jsonString(action.result_parsing?.default_values)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value || '{}');
              onUpdateAction('result_parsing.default_values', parsed);
            } catch (err) {
              /* ignore parse error */
            }
          }}
          rows={3}
          className="p-2 border rounded font-mono bg-gray-100 focus:bg-white focus:ring-1 focus:ring-blue-300"
        />
      </label>

      <label className="flex flex-col gap-1">
        Database Config (JSON)
        <textarea
          value={JSON.stringify(
            {
              key_fields: action.database?.key_fields ?? [],
              field_types: action.database?.field_types ?? {},
              indexes: action.database?.indexes ?? []
            },
            null,
            2
          )}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value || '{}');
              onUpdateAction('database.key_fields', parsed.key_fields ?? []);
              onUpdateAction('database.field_types', parsed.field_types ?? {});
              onUpdateAction('database.indexes', parsed.indexes ?? []);
            } catch (err) {
              /* ignore parse error */
            }
          }}
          rows={3}
          className="p-2 border rounded font-mono bg-gray-100 focus:bg-white focus:ring-1 focus:ring-blue-300"
        />
      </label>
    </div>
  </details>
);
