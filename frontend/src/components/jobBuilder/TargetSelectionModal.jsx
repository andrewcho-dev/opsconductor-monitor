import React, { useMemo, useState } from 'react';

const SOURCE_LABELS = {
  network_range: 'Network Range',
  custom_groups: 'Custom Group',
  network_groups: 'Network Group'
};

const normalizeItems = (items) =>
  items.map((item) =>
    typeof item === 'string'
      ? { label: item, value: item }
      : {
          label: item.label || item.name || item.id || JSON.stringify(item),
          value: item.value ?? item
        }
  );

const isValueSelected = (candidateValue, selectedValue) => {
  if (Array.isArray(selectedValue)) {
    return selectedValue.includes(candidateValue);
  }
  return selectedValue === candidateValue;
};

const TargetSelectionModal = ({
  isOpen,
  sourceType,
  items = [],
  selectedValue,
  onSelect,
  onCustomSubmit,
  onClose,
  loading,
  onRefresh
}) => {
  const [useExisting, setUseExisting] = useState(true);
  const [customValue, setCustomValue] = useState('');
  const [search, setSearch] = useState('');

  const normalizedItems = useMemo(() => normalizeItems(items), [items]);

  const filteredItems = useMemo(() => {
    if (!search) return normalizedItems;
    return normalizedItems.filter((item) =>
      item.label.toLowerCase().includes(search.toLowerCase())
    );
  }, [normalizedItems, search]);

  if (!isOpen) return null;

  const label = SOURCE_LABELS[sourceType] || 'Target';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative z-10 w-full max-w-2xl bg-white rounded-lg shadow-xl border border-gray-200"
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold">Select {label}</h2>
          <button
            onClick={() => {
              setSearch('');
              setCustomValue('');
              onClose();
            }}
            className="text-gray-500 hover:text-gray-700"
            aria-label="Close target selection modal"
          >
            ✕
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div className="flex items-center gap-3 text-xs font-medium text-gray-600">
            <span>Source:</span>
            <div className="flex rounded bg-gray-100 p-1">
              <button
                className={`px-2 py-1 rounded ${useExisting ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                onClick={() => setUseExisting(true)}
              >
                📋 Pick Existing
              </button>
              <button
                className={`px-2 py-1 rounded ${!useExisting ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                onClick={() => setUseExisting(false)}
              >
                ✏️ Create New
              </button>
            </div>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="ml-auto text-blue-600 hover:underline"
              >
                Refresh
              </button>
            )}
          </div>

          {useExisting ? (
            <div className="space-y-3">
              <div className="relative">
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={`Search ${label.toLowerCase()}s...`}
                  className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-300"
                />
              </div>

              <div className="h-64 overflow-y-auto border rounded divide-y">
                {loading ? (
                  <div className="p-4 text-sm text-gray-500">Loading available options…</div>
                ) : filteredItems.length > 0 ? (
                  filteredItems.map((item) => (
                    <button
                      key={item.label}
                      onClick={() => onSelect(item.value)}
                      className={`w-full text-left px-4 py-3 text-sm hover:bg-blue-50 ${
                        isValueSelected(item.value, selectedValue) ? 'bg-blue-100 font-semibold' : 'bg-white'
                      }`}
                    >
                      {item.label}
                    </button>
                  ))
                ) : (
                  <div className="p-4 text-sm text-gray-500">
                    No {label.toLowerCase()}s found. Try creating a new one.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-gray-600">
                Enter a new {label.toLowerCase()} value. For groups you can provide a JSON array or one per line.
              </p>
              {sourceType === 'network_range' ? (
                <input
                  type="text"
                  value={customValue}
                  onChange={(e) => setCustomValue(e.target.value)}
                  placeholder="e.g., 192.168.1.0/24"
                  className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-300"
                />
              ) : (
                <textarea
                  value={customValue}
                  onChange={(e) => setCustomValue(e.target.value)}
                  rows={4}
                  className="w-full p-2 border rounded text-sm font-mono focus:ring-2 focus:ring-blue-300"
                  placeholder='["Production Servers", "DMZ"] or one per line'
                />
              )}
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => onCustomSubmit(customValue)}
                  className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                >
                  Save Value
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TargetSelectionModal;
