import { useState, useMemo, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { DeviceTable } from "./components/DeviceTable";
import { ScanProgress } from "./components/ScanProgress";
import { GroupModal } from "./components/GroupModal";
import { SettingsModal } from "./components/SettingsModal";
import { DeviceDetail } from "./pages/DeviceDetail";
import { Settings } from "./pages/Settings";
import { Poller } from "./pages/Poller";
import { Topology } from "./pages/Topology";
import { PowerTrends } from "./pages/PowerTrends";
import { useDevices, useGroups, useScanProgress } from "./hooks/useDevices";
import { fetchApi } from "./lib/utils";

function AppContent() {
  const navigate = useNavigate();
  const { devices, loading: devicesLoading, refetch: refetchDevices } = useDevices();
  const { groups, loading: groupsLoading, createGroup, updateGroup, deleteGroup, refetch: refetchGroups } = useGroups();
  const { progress, startScan } = useScanProgress();

  // Load selected group from localStorage on mount
  const [selectedGroup, setSelectedGroup] = useState(() => {
    try {
      const saved = localStorage.getItem('selectedGroup');
      return saved ? JSON.parse(saved) : { type: "all", name: "All Devices" };
    } catch {
      return { type: "all", name: "All Devices" };
    }
  });
  
  // Save selected group to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem('selectedGroup', JSON.stringify(selectedGroup));
    } catch {
      // Ignore localStorage errors
    }
  }, [selectedGroup]);

  const [selectedDevices, setSelectedDevices] = useState(new Set());
  const [highlightedIps, setHighlightedIps] = useState([]);
  const [groupDevices, setGroupDevices] = useState([]);
  const [modifiedGroupDevices, setModifiedGroupDevices] = useState(new Set());
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // Load expanded sections from localStorage on mount
  const [expandedSections, setExpandedSections] = useState(() => {
    try {
      const saved = localStorage.getItem('sidebarExpandedSections');
      return saved ? JSON.parse(saved) : { custom: true, network: true };
    } catch {
      return { custom: true, network: true };
    }
  });
  
  // Save expanded sections to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('sidebarExpandedSections', JSON.stringify(expandedSections));
    } catch {
      // Ignore localStorage errors
    }
  }, [expandedSections]);
  
  // Always show all devices, filtering is handled in DeviceTable
  const filteredDevices = devices;

  const [modalState, setModalState] = useState({ isOpen: false, group: null });
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  // Calculate highlighted IPs based on selected group
  const highlightedIpsCalculated = useMemo(() => {
    if (selectedGroup.type === "all") {
      return new Set(devices.map((d) => d.ip_address));
    }
    if (selectedGroup.type === "network") {
      return new Set(
        devices
          .filter((d) => d.network_range === selectedGroup.name)
          .map((d) => d.ip_address)
      );
    }
    if (selectedGroup.type === "custom") {
      return new Set(
        groupDevices.map((d) => d.ip_address || d)
      );
    }
    return new Set();
  }, [selectedGroup, groupDevices, devices]);

  const handleSelectDevice = (ip, checked) => {
    // If a custom group is selected, track group device changes
    if (selectedGroup.type === "custom" && selectedGroup.id) {
      setModifiedGroupDevices((prev) => {
        const next = new Set(prev);
        if (checked) {
          next.add(ip);
        } else {
          next.delete(ip);
        }
        setHasUnsavedChanges(true);
        return next;
      });
    } else {
      // Normal device selection for other operations
      setSelectedDevices((prev) => {
        const next = new Set(prev);
        if (checked) {
          next.add(ip);
        } else {
          next.delete(ip);
        }
        return next;
      });
    }
  };

  const handleSelectAll = (pageDevices, checked) => {
    setSelectedDevices((prev) => {
      const next = new Set(prev);
      pageDevices.forEach((d) => {
        if (checked) {
          next.add(d.ip_address);
        } else {
          next.delete(d.ip_address);
        }
      });
      return next;
    });
  };

  const handleCreateGroup = () => {
    setModalState({ isOpen: true, group: null });
  };

  const handleEditGroup = (group) => {
    // Edit group name/description only (not devices)
    setModalState({ isOpen: true, group });
  };

  const handleDeleteGroup = async (group) => {
    if (group.type === "custom" && confirm("Delete this group?")) {
      await deleteGroup(group.id);
    }
  };

  const handleSaveGroup = async (groupData) => {
    try {
      if (groupData.id) {
        await updateGroup(groupData.id, groupData);
      } else {
        await createGroup(groupData);
      }
      
      // Force a refresh of groups
      await refetchGroups();
      
    } catch (error) {
      console.error("Error saving group:", error);
      alert("Error saving group: " + error.message);
    }
  };

  const handleRefresh = () => {
    refetchDevices();
    refetchGroups();
  };

  const handleShowDetail = (ip) => {
    navigate(`/device/${ip}`);
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
          body: JSON.stringify({ 
            devices: Array.from(selectedDevices) 
          }),
        });
        setSelectedDevices(new Set());
        refetchDevices();
      } catch (err) {
        alert('Error deleting devices: ' + err.message);
      }
    }
  };

  const handleAddSelectedToGroup = () => {
    if (selectedDevices.size === 0) return;
    setModalState({ isOpen: true, group: null });
  };

  const handleSaveSettings = async (settings) => {
    try {
      await fetchApi('/save_settings', {
        method: 'POST',
        body: JSON.stringify(settings),
      });
      setSettingsModalOpen(false);
    } catch (err) {
      alert('Error saving settings: ' + err.message);
    }
  };

  const handleTestSettings = async (settings) => {
    // Settings test would be implemented on backend
    console.log('Testing settings:', settings);
  };

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const onSelectGroup = async (group) => {
    setSelectedGroup(group);
    setHasUnsavedChanges(false);

    // If it's a custom group, fetch its devices
    if (group.type === "custom" && group.id) {
      try {
        const groupDeviceData = await fetchApi(`/device_groups/${group.id}/devices`);

        // Filter to only include devices that exist in the main devices array
        const deviceIpSet = new Set(devices.map(d => d.ip_address));
        const validGroupDevices = groupDeviceData.filter(device => deviceIpSet.has(device.ip_address));

        setGroupDevices(validGroupDevices);
        // Initialize modified devices with current group devices
        const deviceIps = new Set(validGroupDevices.map(d => d.ip_address));
        setModifiedGroupDevices(deviceIps);
      } catch (error) {
        setGroupDevices([]);
        setModifiedGroupDevices(new Set());
      }
    } else if (group.type === "network") {
      // For network groups, select all devices in that network
      const networkDevices = devices.filter(d => d.network_range === group.name);
      const deviceIps = new Set(networkDevices.map(d => d.ip_address));
      setModifiedGroupDevices(deviceIps);
      setGroupDevices(networkDevices);
    } else {
      // All devices or other types
      setGroupDevices([]);
      setModifiedGroupDevices(new Set());
    }
  };

  const handleSaveGroupChanges = async () => {
    
    if (selectedGroup.type !== "custom" || !selectedGroup.id) {
      return;
    }
    
    try {
      // Get current and new device sets
      const currentDeviceIps = new Set(groupDevices.map(d => d.ip_address));
      const newDeviceIps = modifiedGroupDevices;
      
      
      // Calculate devices to add and remove
      const toAdd = Array.from(newDeviceIps).filter(ip => !currentDeviceIps.has(ip));
      const toRemove = Array.from(currentDeviceIps).filter(ip => !newDeviceIps.has(ip));
      
      
      // Remove devices first
      for (const ip of toRemove) {
        await fetchApi(`/device_groups/${selectedGroup.id}/devices/${ip}`, {
          method: 'DELETE'
        });
      }
      
      // Add devices
      if (toAdd.length > 0) {
        const response = await fetchApi(`/device_groups/${selectedGroup.id}/devices`, {
          method: 'POST',
          body: JSON.stringify({ ip_addresses: toAdd })
        });
      }
      
      // Refresh group data
      const updatedDevices = await fetchApi(`/device_groups/${selectedGroup.id}/devices`);
      setGroupDevices(updatedDevices);
      setModifiedGroupDevices(new Set(updatedDevices.map(d => d.ip_address)));
      setHasUnsavedChanges(false);
      
      // Refresh groups list to update device counts in sidebar
      await refetchGroups();
      
      alert('Group changes saved successfully!');
    } catch (error) {
      alert('Error saving group changes: ' + error.message);
    }
  };

  return (
    <Routes>
      <Route path="/" element={
          <div className="flex h-screen bg-gray-100">
            <Sidebar
              key="sidebar"
              groups={groups}
              selectedGroup={selectedGroup}
              onSelectGroup={onSelectGroup}
              onCreateGroup={handleCreateGroup}
              onEditGroup={handleEditGroup}
              onDeleteGroup={handleDeleteGroup}
              expandedSections={expandedSections}
              toggleSection={toggleSection}
            />

            <div className="flex-1 flex flex-col overflow-hidden">
              <ScanProgress
                progress={progress}
                onStartScan={startScan}
                onRefresh={handleRefresh}
                onOpenSettings={() => setSettingsModalOpen(true)}
                onDeleteSelected={handleDeleteSelected}
              />

              <div className="flex-1 overflow-hidden bg-white m-4 rounded-xl shadow-sm border border-gray-200">
                {selectedGroup.type === "custom" && hasUnsavedChanges && (
                  <div className="m-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                    <span className="text-blue-800 font-medium">You have unsaved changes to this group</span>
                    <button
                      onClick={handleSaveGroupChanges}
                      className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Save Changes
                    </button>
                  </div>
                )}
                <DeviceTable
                  key={`${selectedGroup.type}-${selectedGroup.id || selectedGroup.name}`}
                  devices={filteredDevices}
                  selectedDevices={(() => {
                    const selected = (selectedGroup.type === "custom" || selectedGroup.type === "network") ? modifiedGroupDevices : selectedDevices;
                    return selected;
                  })()}
                  onSelectDevice={handleSelectDevice}
                  onSelectAll={handleSelectAll}
                  highlightedIps={highlightedIpsCalculated}
                  loading={devicesLoading}
                  onShowDetail={handleShowDetail}
                  onDeleteDevice={handleDeleteDevice}
                  onDeleteSelected={handleDeleteSelected}
                  onAddSelectedToGroup={handleAddSelectedToGroup}
                  selectedGroup={selectedGroup}
                  groupDevices={groupDevices}
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

            <SettingsModal
              isOpen={settingsModalOpen}
              onClose={() => setSettingsModalOpen(false)}
              onSave={handleSaveSettings}
              onTest={handleTestSettings}
            />
          </div>
        } />
        <Route path="/device/:ip" element={<DeviceDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/poller" element={<Poller />} />
        <Route path="/topology" element={<Topology />} />
        <Route path="/power-trends" element={<PowerTrends />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
