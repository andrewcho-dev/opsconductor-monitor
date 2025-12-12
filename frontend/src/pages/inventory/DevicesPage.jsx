import React, { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageLayout, PageHeader } from "../../components/layout";
import { DeviceTable } from "../../components/DeviceTable";
import { GroupModal } from "../../components/GroupModal";
import { useDevices, useGroups } from "../../hooks/useDevices";
import { fetchApi } from "../../lib/utils";
import { Server, RefreshCw } from "lucide-react";

export function DevicesPage() {
  const navigate = useNavigate();
  const { devices, loading: devicesLoading, refetch: refetchDevices } = useDevices();
  const { groups, createGroup, updateGroup, refetch: refetchGroups } = useGroups();

  // Filter state
  const [currentFilter, setCurrentFilter] = useState({ type: "all", label: "All Devices" });
  const [customGroupDeviceIps, setCustomGroupDeviceIps] = useState(new Set());

  const [selectedDevices, setSelectedDevices] = useState(new Set());
  const [modalState, setModalState] = useState({ isOpen: false, group: null });

  // Load custom group devices when a custom group is selected
  useEffect(() => {
    if (currentFilter.type === "custom" && currentFilter.id) {
      loadCustomGroupDevices(currentFilter.id);
    } else {
      setCustomGroupDeviceIps(new Set());
    }
  }, [currentFilter]);

  const loadCustomGroupDevices = async (groupId) => {
    try {
      const response = await fetchApi(`/api/device_groups/${groupId}/devices`);
      const data = response.data || response;
      const ips = new Set((data || []).map(d => d.ip_address || d));
      setCustomGroupDeviceIps(ips);
    } catch (err) {
      console.error("Failed to load group devices:", err);
      setCustomGroupDeviceIps(new Set());
    }
  };

  // Filter devices based on selection
  const filteredDevices = useMemo(() => {
    if (currentFilter.type === "all") return devices;
    if (currentFilter.type === "network" && currentFilter.id) {
      return devices.filter(d => d.network_range === currentFilter.id);
    }
    if (currentFilter.type === "custom" && currentFilter.id) {
      return devices.filter(d => customGroupDeviceIps.has(d.ip_address));
    }
    return devices;
  }, [devices, currentFilter, customGroupDeviceIps]);

  // Filter options for DeviceTable
  const filterOptions = useMemo(() => ({
    totalCount: devices.length,
    customGroups: groups.custom || [],
    networkGroups: groups.network || [],
  }), [devices.length, groups]);

  const handleSelectDevice = (ip, checked) => {
    setSelectedDevices((prev) => {
      const next = new Set(prev);
      if (checked) next.add(ip);
      else next.delete(ip);
      return next;
    });
  };

  const handleSelectAll = (pageDevices, checked) => {
    setSelectedDevices((prev) => {
      const next = new Set(prev);
      pageDevices.forEach((d) => {
        if (checked) next.add(d.ip_address);
        else next.delete(d.ip_address);
      });
      return next;
    });
  };

  const handleShowDetail = (ip) => {
    // Strip /32 suffix if present for URL
    const cleanIp = ip?.replace(/\/\d+$/, '');
    navigate(`/inventory/devices/${cleanIp}`);
  };

  const handleDeleteDevice = async (ip) => {
    if (confirm(`Delete device ${ip}?`)) {
      try {
        await fetchApi(`/delete_device`, {
          method: 'POST',
          body: JSON.stringify({ ip_address: ip }),
        });
        refetchDevices();
      } catch (err) {
        alert('Error deleting device: ' + err.message);
      }
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedDevices.size === 0) return;
    if (confirm(`Delete ${selectedDevices.size} selected devices?`)) {
      try {
        await fetchApi('/delete_selected', {
          method: 'POST',
          body: JSON.stringify({ devices: Array.from(selectedDevices) }),
        });
        setSelectedDevices(new Set());
        refetchDevices();
      } catch (err) {
        alert('Error deleting devices: ' + err.message);
      }
    }
  };

  const handleSaveGroup = async (groupData) => {
    try {
      if (groupData.id) {
        await updateGroup(groupData.id, groupData);
      } else {
        await createGroup(groupData);
      }
      await refetchGroups();
      setModalState({ isOpen: false, group: null });
    } catch (error) {
      alert("Error saving group: " + error.message);
    }
  };

  return (
    <PageLayout module="inventory">
      <PageHeader
        title="Device Inventory"
        description={`${filteredDevices.length} of ${devices.length} devices`}
        icon={Server}
        actions={
          <button
            onClick={() => { refetchDevices(); refetchGroups(); }}
            disabled={devicesLoading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className={`w-4 h-4 ${devicesLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        }
      />

      <div className="p-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <DeviceTable
            devices={filteredDevices}
            selectedDevices={selectedDevices}
            onSelectDevice={handleSelectDevice}
            onSelectAll={handleSelectAll}
            highlightedIps={new Set(filteredDevices.map(d => d.ip_address))}
            loading={devicesLoading}
            onShowDetail={handleShowDetail}
            onDeleteDevice={handleDeleteDevice}
            onDeleteSelected={handleDeleteSelected}
            onAddSelectedToGroup={() => setModalState({ isOpen: true, group: null })}
            filterOptions={filterOptions}
            currentFilter={currentFilter}
            onFilterChange={setCurrentFilter}
          />
        </div>
      </div>

      <GroupModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState({ isOpen: false, group: null })}
        onSave={handleSaveGroup}
        group={modalState.group}
        devices={devices}
        selectedDevices={selectedDevices}
      />
    </PageLayout>
  );
}

export default DevicesPage;
