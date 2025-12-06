import React, { useEffect, useState } from 'react';

const MODE_GROUPS = 'groups';
const MODE_MANUAL = 'manual';
const MODE_FILE = 'file';

const UnifiedTargetsModal = ({
  isOpen,
  action,
  availableTargets,
  loading,
  onRefresh,
  onClose,
  onSave
}) => {
  const [mode, setMode] = useState(MODE_GROUPS);
  const [selectedNetworkKeys, setSelectedNetworkKeys] = useState([]);
  const [selectedCustomKeys, setSelectedCustomKeys] = useState([]);
  const [manualText, setManualText] = useState('');
  const [filePath, setFilePath] = useState('');

  useEffect(() => {
    if (!isOpen || !action) return;

    const source = action.targeting?.source;
    if (source === 'target_list') {
      setMode(MODE_MANUAL);
    } else if (source === 'file') {
      setMode(MODE_FILE);
    } else {
      setMode(MODE_GROUPS);
    }

    const tgt = action.targeting || {};

    // Initialise group selections based on existing targeting
    const initialNetwork = (tgt.network_groups || []).map((g) => {
      if (!g) return '';
      if (g.network_range) return g.network_range;
      if (g.label) return g.label;
      if (typeof g === 'string') return g;
      return JSON.stringify(g);
    });
    const initialCustom = (tgt.custom_groups || []).map((g) => {
      if (!g) return '';
      if (g.id != null) return String(g.id);
      if (g.name) return g.name;
      if (g.label) return g.label;
      if (typeof g === 'string') return g;
      return JSON.stringify(g);
    });

    setSelectedNetworkKeys(initialNetwork.filter(Boolean));
    setSelectedCustomKeys(initialCustom.filter(Boolean));
    setManualText(tgt.target_list || '');
    setFilePath(tgt.file_path || '');
  }, [isOpen, action]);

  if (!isOpen || !action) return null;

  const networkOptions = (availableTargets.network_groups || []).map((g) => ({
    key: g.network_range,
    label: `${g.network_range}${g.device_count != null ? ` (${g.device_count} devices)` : ''}`,
    value: g
  }));

  const customOptions = (availableTargets.custom_groups || []).map((g) => ({
    key: String(g.id ?? g.name ?? g.label ?? ''),
    label: `${g.name || g.label || `Group ${g.id}`}${g.device_count != null ? ` (${g.device_count} devices)` : ''}`,
    value: g
  }));

  const toggleKey = (keys, setter, key) => {
    if (!key) return;
    if (keys.includes(key)) {
      setter(keys.filter((k) => k !== key));
    } else {
      setter([...keys, key]);
    }
  };

  const handleSave = () => {
    if (mode === MODE_MANUAL) {
      onSave({
        source: 'target_list',
        network_groups: [],
        custom_groups: [],
        target_list: manualText,
        file_path: ''
      });
      return;
    }

    if (mode === MODE_FILE) {
      onSave({
        source: 'file',
        network_groups: [],
        custom_groups: [],
        target_list: '',
        file_path: filePath
      });
      return;
    }

    // Groups mode
    const selectedNetwork = networkOptions
      .filter((opt) => selectedNetworkKeys.includes(opt.key))
      .map((opt) => opt.value);
    const selectedCustom = customOptions
      .filter((opt) => selectedCustomKeys.includes(opt.key))
      .map((opt) => opt.value);

    onSave({
      source: 'network_groups',
      network_groups: selectedNetwork,
      custom_groups: selectedCustom,
      target_list: '',
      file_path: ''
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div
        className="relative z-10 w-full max-w-3xl bg-white rounded-lg shadow-xl border border-gray-200 p-4 space-y-4"
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b pb-2">
          <h2 className="text-sm font-semibold">Select Targets</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            ✕
          </button>
        </div>

        {/* Mode selector */}
        <div className="flex items-center gap-2 text-xs font-medium text-gray-700">
          <span>Mode:</span>
          <div className="flex rounded bg-gray-100 p-1">
            <button
              type="button"
              className={`px-2 py-1 rounded ${
                mode === MODE_GROUPS ? 'bg-blue-500 text-white' : 'text-gray-700 hover:bg-gray-200'
              }`}
              onClick={() => setMode(MODE_GROUPS)}
            >
              👥 Groups
            </button>
            <button
              type="button"
              className={`px-2 py-1 rounded ${
                mode === MODE_MANUAL ? 'bg-blue-500 text-white' : 'text-gray-700 hover:bg-gray-200'
              }`}
              onClick={() => setMode(MODE_MANUAL)}
            >
              📝 Manual List
            </button>
            <button
              type="button"
              className={`px-2 py-1 rounded ${
                mode === MODE_FILE ? 'bg-blue-500 text-white' : 'text-gray-700 hover:bg-gray-200'
              }`}
              onClick={() => setMode(MODE_FILE)}
            >
              📁 File
            </button>
          </div>
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="ml-auto text-blue-600 hover:underline"
            >
              Refresh
            </button>
          )}
        </div>

        {/* Content for each mode */}
        {mode === MODE_GROUPS && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-2">
              <div className="font-semibold text-gray-700">Network Groups</div>
              <div className="h-56 overflow-y-auto border rounded divide-y">
                {loading ? (
                  <div className="p-3 text-gray-500">Loading network groups…</div>
                ) : networkOptions.length === 0 ? (
                  <div className="p-3 text-gray-500">No network groups found.</div>
                ) : (
                  networkOptions.map((opt) => (
                    <label
                      key={opt.key}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-blue-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedNetworkKeys.includes(opt.key)}
                        onChange={() => toggleKey(selectedNetworkKeys, setSelectedNetworkKeys, opt.key)}
                        className="rounded"
                      />
                      <span>{opt.label}</span>
                    </label>
                  ))
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="font-semibold text-gray-700">Custom Groups</div>
              <div className="h-56 overflow-y-auto border rounded divide-y">
                {loading ? (
                  <div className="p-3 text-gray-500">Loading custom groups…</div>
                ) : customOptions.length === 0 ? (
                  <div className="p-3 text-gray-500">No custom groups found.</div>
                ) : (
                  customOptions.map((opt) => (
                    <label
                      key={opt.key}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-blue-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedCustomKeys.includes(opt.key)}
                        onChange={() => toggleKey(selectedCustomKeys, setSelectedCustomKeys, opt.key)}
                        className="rounded"
                      />
                      <span>{opt.label}</span>
                    </label>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {mode === MODE_MANUAL && (
          <div className="space-y-2 text-xs">
            <div className="font-semibold text-gray-700">Manual Target List</div>
            <p className="text-gray-600">
              Enter one target per line (IP, hostname, etc.).
            </p>
            <textarea
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              rows={8}
              className="w-full p-2 border rounded font-mono text-xs bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
            />
          </div>
        )}

        {mode === MODE_FILE && (
          <div className="space-y-2 text-xs">
            <div className="font-semibold text-gray-700">Target File Path</div>
            <p className="text-gray-600">
              Specify a file path accessible to the job runner that contains your targets.
            </p>
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              className="w-full p-2 border rounded text-xs bg-gray-50 focus:bg-white focus:ring-1 focus:ring-blue-300"
              placeholder="/path/to/targets.txt"
            />
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t mt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-3 py-1 text-xs rounded bg-blue-500 text-white hover:bg-blue-600"
          >
            Save Targets
          </button>
        </div>
      </div>
    </div>
  );
};

export default UnifiedTargetsModal;
