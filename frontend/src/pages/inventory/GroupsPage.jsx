import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageLayout, PageHeader } from "../../components/layout";
import { useDevices, useGroups } from "../../hooks/useDevices";
import { fetchApi } from "../../lib/utils";
import { 
  FolderOpen, 
  Plus, 
  Edit, 
  Trash2, 
  Users,
  Server,
  ChevronRight,
  Save,
  X
} from "lucide-react";
import { cn } from "../../lib/utils";

export function GroupsPage() {
  const navigate = useNavigate();
  const { devices } = useDevices();
  const { groups, createGroup, updateGroup, deleteGroup, refetch: refetchGroups } = useGroups();

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupDevices, setGroupDevices] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [selectedDevicesForGroup, setSelectedDevicesForGroup] = useState(new Set());
  const [saving, setSaving] = useState(false);

  // Load group devices when a group is selected
  useEffect(() => {
    if (selectedGroup) {
      loadGroupDevices(selectedGroup.id);
      setEditName(selectedGroup.group_name);
      setEditDescription(selectedGroup.description || "");
    } else {
      setGroupDevices([]);
      setEditMode(false);
    }
  }, [selectedGroup]);

  const loadGroupDevices = async (groupId) => {
    try {
      const response = await fetchApi(`/api/device_groups/${groupId}/devices`);
      const data = response.data || response || [];
      setGroupDevices(data);
      setSelectedDevicesForGroup(new Set(data.map(d => d.ip_address || d)));
    } catch (err) {
      console.error("Failed to load group devices:", err);
      setGroupDevices([]);
    }
  };

  const handleCreateGroup = async () => {
    const name = prompt("Enter group name:");
    if (!name?.trim()) return;
    
    try {
      await createGroup({ group_name: name.trim(), description: "" });
      await refetchGroups();
    } catch (err) {
      alert("Error creating group: " + err.message);
    }
  };

  const handleDeleteGroup = async (group) => {
    if (!confirm(`Delete group "${group.group_name}"? This cannot be undone.`)) return;
    
    try {
      await deleteGroup(group.id);
      if (selectedGroup?.id === group.id) {
        setSelectedGroup(null);
      }
      await refetchGroups();
    } catch (err) {
      alert("Error deleting group: " + err.message);
    }
  };

  const handleSaveGroup = async () => {
    if (!selectedGroup) return;
    
    try {
      setSaving(true);
      
      // Update group name/description
      await updateGroup(selectedGroup.id, {
        group_name: editName,
        description: editDescription,
      });

      // Update group devices
      const currentIps = new Set(groupDevices.map(d => d.ip_address || d));
      const newIps = selectedDevicesForGroup;
      
      const toAdd = Array.from(newIps).filter(ip => !currentIps.has(ip));
      const toRemove = Array.from(currentIps).filter(ip => !newIps.has(ip));

      // Remove devices
      for (const ip of toRemove) {
        await fetchApi(`/api/device_groups/${selectedGroup.id}/devices/${ip}`, { method: 'DELETE' });
      }
      
      // Add devices
      if (toAdd.length > 0) {
        await fetchApi(`/api/device_groups/${selectedGroup.id}/devices`, {
          method: 'POST',
          body: JSON.stringify({ ip_addresses: toAdd })
        });
      }

      await refetchGroups();
      await loadGroupDevices(selectedGroup.id);
      setEditMode(false);
    } catch (err) {
      alert("Error saving group: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleDeviceInGroup = (ip) => {
    setSelectedDevicesForGroup(prev => {
      const next = new Set(prev);
      if (next.has(ip)) {
        next.delete(ip);
      } else {
        next.add(ip);
      }
      return next;
    });
  };

  return (
    <PageLayout module="inventory">
      <PageHeader
        title="Device Groups"
        description={`${groups.custom?.length || 0} custom groups`}
        icon={FolderOpen}
        actions={
          <button
            onClick={handleCreateGroup}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            New Group
          </button>
        }
      />

      <div className="p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Groups List */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Custom Groups
              </h2>
            </div>
            <div className="divide-y divide-gray-100">
              {groups.custom?.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <FolderOpen className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm">No custom groups yet</p>
                  <button
                    onClick={handleCreateGroup}
                    className="mt-3 text-sm text-blue-600 hover:underline"
                  >
                    Create your first group
                  </button>
                </div>
              ) : (
                groups.custom?.map((group) => (
                  <div
                    key={group.id}
                    className={cn(
                      "flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50 transition-colors",
                      selectedGroup?.id === group.id && "bg-blue-50"
                    )}
                    onClick={() => setSelectedGroup(group)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <FolderOpen className="w-4 h-4 text-blue-600" />
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">{group.group_name}</div>
                        <div className="text-xs text-gray-500">{group.device_count || 0} devices</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteGroup(group); }}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Group Details */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm">
            {selectedGroup ? (
              <>
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <div>
                    {editMode ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="text-lg font-semibold text-gray-900 border-b-2 border-blue-500 focus:outline-none"
                      />
                    ) : (
                      <h2 className="text-lg font-semibold text-gray-900">{selectedGroup.group_name}</h2>
                    )}
                    <p className="text-sm text-gray-500">{groupDevices.length} devices in this group</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {editMode ? (
                      <>
                        <button
                          onClick={() => { setEditMode(false); loadGroupDevices(selectedGroup.id); }}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                        >
                          <X className="w-4 h-4" />
                          Cancel
                        </button>
                        <button
                          onClick={handleSaveGroup}
                          disabled={saving}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        >
                          <Save className="w-4 h-4" />
                          {saving ? "Saving..." : "Save"}
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setEditMode(true)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </button>
                    )}
                  </div>
                </div>

                {editMode ? (
                  <div className="p-4">
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                      <textarea
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        rows={2}
                        placeholder="Optional description..."
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select Devices ({selectedDevicesForGroup.size} selected)
                      </label>
                      <div className="border border-gray-200 rounded-lg max-h-96 overflow-y-auto">
                        {devices.map((device) => (
                          <label
                            key={device.ip_address}
                            className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0"
                          >
                            <input
                              type="checkbox"
                              checked={selectedDevicesForGroup.has(device.ip_address)}
                              onChange={() => toggleDeviceInGroup(device.ip_address)}
                              className="w-4 h-4 text-blue-600 rounded"
                            />
                            <Server className="w-4 h-4 text-gray-400" />
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-900">{device.ip_address}</div>
                              <div className="text-xs text-gray-500">{device.snmp_hostname || "No hostname"}</div>
                            </div>
                            <span className={cn(
                              "text-xs px-2 py-0.5 rounded-full",
                              device.ping_status === "online" 
                                ? "bg-green-100 text-green-700" 
                                : "bg-gray-100 text-gray-500"
                            )}>
                              {device.ping_status}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4">
                    {groupDevices.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p className="text-sm">No devices in this group</p>
                        <button
                          onClick={() => setEditMode(true)}
                          className="mt-3 text-sm text-blue-600 hover:underline"
                        >
                          Add devices
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {groupDevices.map((device) => {
                          const fullDevice = devices.find(d => d.ip_address === (device.ip_address || device));
                          return (
                            <div
                              key={device.ip_address || device}
                              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                              onClick={() => navigate(`/inventory/devices/${device.ip_address || device}`)}
                            >
                              <Server className="w-4 h-4 text-gray-400" />
                              <div className="flex-1">
                                <div className="text-sm font-medium text-gray-900">
                                  {device.ip_address || device}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {fullDevice?.snmp_hostname || "No hostname"}
                                </div>
                              </div>
                              <span className={cn(
                                "text-xs px-2 py-0.5 rounded-full",
                                fullDevice?.ping_status === "online" 
                                  ? "bg-green-100 text-green-700" 
                                  : "bg-gray-100 text-gray-500"
                              )}>
                                {fullDevice?.ping_status || "unknown"}
                              </span>
                              <ChevronRight className="w-4 h-4 text-gray-400" />
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                <div className="text-center">
                  <FolderOpen className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm">Select a group to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default GroupsPage;
