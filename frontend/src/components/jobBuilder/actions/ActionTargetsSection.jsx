import React from 'react';

const SOURCE_OPTIONS = [
  { value: 'network_range', label: '🌐 Network Range' },
  { value: 'target_list', label: '📝 Target List' },
  { value: 'file', label: '📁 File Upload' },
  { value: 'custom_groups', label: '👥 Custom Groups' },
  { value: 'network_groups', label: '🔗 Network Groups' }
];

const DATABASE_SOURCES = new Set(['network_range', 'custom_groups', 'network_groups']);

const formatCurrentSelection = (action) => {
  const source = action.targeting?.source;
  if (source === 'network_range') {
    return action.targeting?.network_range || 'None selected';
  }
  if (source === 'custom_groups' || source === 'network_groups') {
    const groups = action.targeting?.[source];
    if (Array.isArray(groups) && groups.length > 0) {
      return `${groups.length} selected`;
    }
    return 'None selected';
  }
  if (source === 'target_list') {
    const list = action.targeting?.target_list || '';
    const count = list.trim() ? list.trim().split(/\n+/).length : 0;
    return `${count} entries`;
  }
  if (source === 'file') {
    return action.targeting?.file_path || 'No file selected';
  }
  return 'No selection';
};

export const ActionTargetsSection = ({
  action,
  actionIndex,
  updateAction,
  onSourceChange,
  onOpenModal
}) => {
  const source = action.targeting?.source || 'network_range';
  const groupFilter = action.targeting?.group_filter || {};

  const handleNumericChange = (path, value) => {
    const numeric = value === '' ? '' : Number(value);
    updateAction(actionIndex, path, Number.isNaN(numeric) ? 0 : numeric);
  };

  const tagFilterValue = Array.isArray(groupFilter.tag_filter)
    ? groupFilter.tag_filter.join(', ')
    : '';

  return (
    <section className="space-y-2">
      <h4 className="text-xs font-bold uppercase tracking-wide text-gray-600">Targets</h4>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="text-xs font-medium flex flex-col gap-1">
          Target Source
          <select
            value={source}
            onChange={(e) => onSourceChange(actionIndex, e.target.value)}
            className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
          >
            {SOURCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs font-medium flex flex-col gap-1">
          Max Concurrent
          <input
            type="number"
            value={action.targeting?.max_concurrent ?? 0}
            onChange={(e) => handleNumericChange('targeting.max_concurrent', e.target.value)}
            className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
          />
        </label>

        <label className="text-xs font-medium flex flex-col gap-1">
          Retry Count
          <input
            type="number"
            value={action.targeting?.retry_count ?? 0}
            onChange={(e) => handleNumericChange('targeting.retry_count', e.target.value)}
            className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
          />
        </label>

        <label className="text-xs font-medium flex flex-col gap-1">
          Retry Delay (seconds)
          <input
            type="number"
            value={action.targeting?.retry_delay ?? 0}
            onChange={(e) => handleNumericChange('targeting.retry_delay', e.target.value)}
            className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
          />
        </label>
      </div>

      {DATABASE_SOURCES.has(source) ? (
        <div className="flex flex-col gap-2 rounded border border-dashed border-blue-300 bg-blue-50 p-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-700">Current Selection</span>
            <button
              onClick={() => onOpenModal(actionIndex, source)}
              className="px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
              type="button"
            >
              Manage Selection
            </button>
          </div>
          <div className="text-gray-600">
            {formatCurrentSelection(action)}
          </div>
        </div>
      ) : null}

      {source === 'target_list' ? (
        <label className="text-xs font-medium flex flex-col gap-1">
          Target List (one per line)
          <textarea
            value={action.targeting?.target_list || ''}
            onChange={(e) => updateAction(actionIndex, 'targeting.target_list', e.target.value)}
            rows={4}
            className="w-full p-2 border rounded text-xs font-mono bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
          />
        </label>
      ) : null}

      {source === 'file' ? (
        <label className="text-xs font-medium flex flex-col gap-1">
          Target File Path
          <input
            type="text"
            value={action.targeting?.file_path || ''}
            onChange={(e) => updateAction(actionIndex, 'targeting.file_path', e.target.value)}
            className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
            placeholder="/path/to/targets.txt"
          />
        </label>
      ) : null}

      <label className="text-xs font-medium flex flex-col gap-1">
        Exclude List (optional)
        <textarea
          value={action.targeting?.exclude_list || ''}
          onChange={(e) => updateAction(actionIndex, 'targeting.exclude_list', e.target.value)}
          rows={3}
          className="w-full p-2 border rounded text-xs font-mono bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
        />
      </label>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <label className="flex items-center gap-2 font-medium text-gray-600">
          <input
            type="checkbox"
            checked={groupFilter.include_empty ?? true}
            onChange={(e) => updateAction(actionIndex, 'targeting.group_filter.include_empty', e.target.checked)}
            className="rounded"
          />
          Include Empty Groups
        </label>

        <label className="flex flex-col gap-1 font-medium text-gray-600">
          Status Filter
          <select
            value={groupFilter.status_filter || 'all'}
            onChange={(e) => updateAction(actionIndex, 'targeting.group_filter.status_filter', e.target.value)}
            className="p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
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
            className="p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-1 focus:ring-blue-300"
            placeholder="critical, windows"
          />
        </label>
      </div>
    </section>
  );
};
