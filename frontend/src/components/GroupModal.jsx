import { useState, useEffect } from "react";
import { X } from "lucide-react";

export function GroupModal({
  isOpen,
  onClose,
  onSave,
  group,
  devices,
  selectedDevices,
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [deviceIps, setDeviceIps] = useState(new Set());

  useEffect(() => {
    if (group) {
      setName(group.group_name || group.name || "");
      setDescription(group.description || "");
      setDeviceIps(new Set(group.devices?.map((d) => d.ip_address || d) || []));
    } else {
      setName("");
      setDescription("");
      setDeviceIps(new Set(selectedDevices));
    }
  }, [group, selectedDevices]);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    const groupData = {
      id: group?.id,
      name,
      description,
      devices: Array.from(deviceIps),
    };
    
    onSave(groupData);
    onClose();
  };

  const toggleDevice = (ip) => {
    setDeviceIps((prev) => {
      const next = new Set(prev);
      if (next.has(ip)) {
        next.delete(ip);
      } else {
        next.add(ip);
      }
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">
            {group ? "Edit Group" : "Create Group"}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Group Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter group name"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter group description (optional)"
                rows={3}
              />
            </div>

            {!group && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select Devices
                </label>
                <div className="border border-gray-200 rounded-lg max-h-60 overflow-y-auto">
                  {devices.map((device) => (
                    <label
                      key={device.ip_address}
                      className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                    >
                      <input
                        type="checkbox"
                        checked={deviceIps.has(device.ip_address)}
                        onChange={() => toggleDevice(device.ip_address)}
                        className="mr-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">
                        {device.ip_address}
                        {device.snmp_hostname && ` (${device.snmp_hostname})`}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              {group ? "Save Changes" : "Create Group"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
