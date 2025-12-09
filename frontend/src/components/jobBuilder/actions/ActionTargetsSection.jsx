import React from 'react';

const SOURCE_OPTIONS = [
  { value: 'network_groups', label: '🔗 Network Groups' },
  { value: 'custom_groups', label: '👥 Custom Groups' },
  { value: 'target_list', label: '📝 Target List' },
  { value: 'file', label: '📁 File Upload' }
];

const DATABASE_SOURCES = new Set(['custom_groups', 'network_groups']);

const formatCurrentSelection = (action) => {
  const source = action.targeting?.source;

  // Groups mode (network or custom) – show a combined summary of both
  if (source === 'network_groups' || source === 'custom_groups' || source === undefined) {
    const networkGroups = Array.isArray(action.targeting?.network_groups)
      ? action.targeting.network_groups
      : [];
    const customGroups = Array.isArray(action.targeting?.custom_groups)
      ? action.targeting.custom_groups
      : [];

    const groups = [...networkGroups, ...customGroups];
    if (groups.length > 0) {
      const names = groups
        .map((g) => {
          if (!g) return '';
          if (typeof g === 'string') return g;
          if (g.name) return g.name;
          if (g.group_name) return g.group_name;
          if (g.network_range) return g.network_range;
          if (g.label) return g.label;
          return '';
        })
        .filter(Boolean);

      if (names.length === 0) return 'None selected';
      if (names.length <= 3) return names.join(', ');
      return `${names.slice(0, 3).join(', ')} + ${names.length - 3} more`;
    }
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
  onOpenModal,
  onOpenAdvanced
}) => {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-bold flex items-center gap-2">
          <span>🎯</span>
          <span>TARGETS</span>
        </h4>
        {onOpenAdvanced && (
          <button
            type="button"
            onClick={onOpenAdvanced}
            className="p-1 rounded-full text-blue-600 hover:bg-blue-50"
            title="Advanced target settings"
          >
            ⚙️
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={() => onOpenModal(actionIndex)}
        className="w-full text-left text-xs px-2 py-2 border rounded bg-gray-200 hover:bg-white focus:bg-white focus:ring-1 focus:ring-blue-300"
      >
        <span className="block text-gray-800 truncate">{formatCurrentSelection(action)}</span>
      </button>
    </section>
  );
};
