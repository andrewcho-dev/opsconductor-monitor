import React from 'react';

const TargetsAdvancedModal = ({
  isOpen,
  onClose,
  action,
  actionIndex,
  updateAction
}) => {
  if (!isOpen || !action) return null;

  const groupFilter = action.targeting?.group_filter || {};

  const handleNumericChange = (path, value) => {
    const numeric = value === '' ? '' : Number(value);
    updateAction(actionIndex, path, Number.isNaN(numeric) ? 0 : numeric);
  };

  const tagFilterValue = Array.isArray(groupFilter.tag_filter)
    ? groupFilter.tag_filter.join(', ')
    : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg bg-white rounded-lg shadow-xl border border-gray-200 p-4 space-y-4">
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-sm font-semibold">Advanced Target Settings</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            ✕
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <label className="flex flex-col gap-1 font-medium text-gray-700">
            Max Concurrent
            <input
              type="number"
              value={action.targeting?.max_concurrent ?? 0}
              onChange={(e) => handleNumericChange('targeting.max_concurrent', e.target.value)}
              className="p-1 border rounded bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
            />
          </label>

          <label className="flex flex-col gap-1 font-medium text-gray-700">
            Retry Count
            <input
              type="number"
              value={action.targeting?.retry_count ?? 0}
              onChange={(e) => handleNumericChange('targeting.retry_count', e.target.value)}
              className="p-1 border rounded bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
            />
          </label>

          <label className="flex flex-col gap-1 font-medium text-gray-700">
            Retry Delay (seconds)
            <input
              type="number"
              value={action.targeting?.retry_delay ?? 0}
              onChange={(e) => handleNumericChange('targeting.retry_delay', e.target.value)}
              className="p-1 border rounded bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
            />
          </label>
        </div>

        <div className="space-y-2 text-xs">
          <div className="font-semibold text-gray-700">Group Filter</div>
          <label className="flex items-center gap-2 font-medium text-gray-600">
            <input
              type="checkbox"
              checked={groupFilter.include_empty ?? true}
              onChange={(e) => updateAction(
                actionIndex,
                'targeting.group_filter.include_empty',
                e.target.checked
              )}
              className="rounded"
            />
            Include Empty Groups
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="flex flex-col gap-1 font-medium text-gray-600">
              Status Filter
              <select
                value={groupFilter.status_filter || 'all'}
                onChange={(e) => updateAction(
                  actionIndex,
                  'targeting.group_filter.status_filter',
                  e.target.value
                )}
                className="p-1 border rounded bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
              >
                <option value="all">All</option>
                <option value="online">Online</option>
                <option value="offline">Offline</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 font-medium text-gray-600">
              Tag Filter (comma separated)
              <input
                type="text"
                value={tagFilterValue}
                onChange={(e) => {
                  const tags = e.target.value
                    .split(',')
                    .map((tag) => tag.trim())
                    .filter(Boolean);
                  updateAction(actionIndex, 'targeting.group_filter.tag_filter', tags);
                }}
                className="p-1 border rounded bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
                placeholder="critical, windows"
              />
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TargetsAdvancedModal;
