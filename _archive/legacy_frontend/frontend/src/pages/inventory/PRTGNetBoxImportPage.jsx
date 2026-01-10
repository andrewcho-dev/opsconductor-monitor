import React, { useState, useEffect, useCallback, useMemo } from "react";
import { PageLayout, PageHeader } from "../../components/layout";
import { fetchApi } from "../../lib/utils";
import {
  Download,
  RefreshCw,
  Server,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Play,
  Eye,
  ArrowRight,
  Folder,
  FolderOpen,
  Monitor,
  Circle,
  CheckSquare,
  Square,
  AlertCircle,
} from "lucide-react";

// ============================================================================
// LEFT COLUMN: PRTG Device List (Tree View by Group)
// ============================================================================
function PRTGDeviceList({ 
  devices, 
  groups, 
  selectedIds, 
  onSelectChange, 
  selectedDevice, 
  onDeviceClick,
  searchTerm,
  onSearchChange,
  loading,
  onRefresh 
}) {
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [groupFilter, setGroupFilter] = useState("");

  // Group devices by PRTG group
  const devicesByGroup = useMemo(() => {
    const grouped = {};
    devices.forEach(d => {
      const group = d.prtg_group || "Ungrouped";
      if (!grouped[group]) grouped[group] = [];
      grouped[group].push(d);
    });
    return grouped;
  }, [devices]);

  // Get groups that have devices
  const activeGroups = useMemo(() => {
    return groups.filter(g => devicesByGroup[g]?.length > 0);
  }, [groups, devicesByGroup]);

  // Filter groups
  const filteredGroups = useMemo(() => {
    return activeGroups.filter(g => 
      g.toLowerCase().includes(groupFilter.toLowerCase())
    );
  }, [activeGroups, groupFilter]);

  const toggleGroup = (group) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(group)) {
      newExpanded.delete(group);
    } else {
      newExpanded.add(group);
    }
    setExpandedGroups(newExpanded);
  };

  const toggleGroupSelection = (group, e) => {
    e.stopPropagation();
    const groupDevices = devicesByGroup[group] || [];
    const groupIps = groupDevices.map(d => d.ip_address);
    const allSelected = groupIps.every(ip => selectedIds.has(ip));
    
    const newSet = new Set(selectedIds);
    if (allSelected) {
      groupIps.forEach(ip => newSet.delete(ip));
    } else {
      groupIps.forEach(ip => newSet.add(ip));
    }
    onSelectChange(newSet);
  };

  const toggleDevice = (ip, e) => {
    e.stopPropagation();
    const newSet = new Set(selectedIds);
    if (newSet.has(ip)) {
      newSet.delete(ip);
    } else {
      newSet.add(ip);
    }
    onSelectChange(newSet);
  };

  const selectAll = () => {
    onSelectChange(new Set(devices.map(d => d.ip_address)));
  };

  const selectNone = () => {
    onSelectChange(new Set());
  };

  const expandAll = () => {
    setExpandedGroups(new Set(filteredGroups));
  };

  const collapseAll = () => {
    setExpandedGroups(new Set());
  };

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Header */}
      <div className="p-3 border-b border-gray-200 bg-blue-50">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-blue-800 uppercase tracking-wide flex items-center gap-2">
            <Server className="w-4 h-4" />
            PRTG Devices
          </h2>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1.5 text-blue-600 hover:bg-blue-100 rounded"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        
        {/* Search */}
        <div className="relative mb-2">
          <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search devices..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Group filter */}
        <div className="relative">
          <Filter className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Filter groups..."
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Selection controls */}
        <div className="flex items-center justify-between mt-2 text-xs">
          <span className="text-blue-700 font-medium">
            {selectedIds.size} / {devices.length} selected
          </span>
          <div className="flex gap-2">
            <button onClick={selectAll} className="text-blue-600 hover:underline">All</button>
            <span className="text-gray-300">|</span>
            <button onClick={selectNone} className="text-blue-600 hover:underline">None</button>
            <span className="text-gray-300">|</span>
            <button onClick={expandAll} className="text-blue-600 hover:underline">Expand</button>
            <span className="text-gray-300">|</span>
            <button onClick={collapseAll} className="text-blue-600 hover:underline">Collapse</button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-2 pt-2 border-t border-gray-200 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-green-100 border border-green-400 rounded" />
            <span className="text-green-700">In NetBox ({devices.filter(d => d.in_netbox).length})</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-white border border-gray-300 rounded" />
            <span className="text-gray-600">Not in NetBox ({devices.filter(d => !d.in_netbox).length})</span>
          </div>
        </div>
      </div>

      {/* Device Tree */}
      <div className="flex-1 overflow-y-auto">
        {filteredGroups.map(group => {
          const groupDevices = devicesByGroup[group] || [];
          if (groupDevices.length === 0) return null;
          
          const isExpanded = expandedGroups.has(group);
          const groupIps = groupDevices.map(d => d.ip_address);
          const selectedCount = groupIps.filter(ip => selectedIds.has(ip)).length;
          const allSelected = selectedCount === groupDevices.length;
          const someSelected = selectedCount > 0 && !allSelected;

          return (
            <div key={group} className="border-b border-gray-100">
              {/* Group Header */}
              <div
                className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                onClick={() => toggleGroup(group)}
              >
                <button
                  onClick={(e) => toggleGroupSelection(group, e)}
                  className="flex-shrink-0"
                >
                  {allSelected ? (
                    <CheckSquare className="w-4 h-4 text-blue-600" />
                  ) : someSelected ? (
                    <div className="w-4 h-4 border-2 border-blue-600 rounded bg-blue-100 flex items-center justify-center">
                      <div className="w-2 h-0.5 bg-blue-600" />
                    </div>
                  ) : (
                    <Square className="w-4 h-4 text-gray-400" />
                  )}
                </button>
                {isExpanded ? (
                  <FolderOpen className="w-4 h-4 text-yellow-600 flex-shrink-0" />
                ) : (
                  <Folder className="w-4 h-4 text-yellow-600 flex-shrink-0" />
                )}
                <span className="text-sm text-gray-700 truncate flex-1 font-medium">{group}</span>
                <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                  {selectedCount}/{groupDevices.length}
                </span>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
              </div>

              {/* Devices in Group */}
              {isExpanded && (
                <div className="bg-gray-50/50">
                  {groupDevices.map(device => {
                    const isSelected = selectedIds.has(device.ip_address);
                    const isActive = selectedDevice?.ip_address === device.ip_address;
                    
                    return (
                      <div
                        key={device.ip_address}
                        className={`flex items-center gap-2 pl-9 pr-3 py-1.5 cursor-pointer border-l-2 ${
                          isActive 
                            ? 'bg-blue-100 border-l-blue-500' 
                            : device.in_netbox
                              ? 'bg-green-50 hover:bg-green-100 border-l-green-400'
                              : 'hover:bg-gray-100 border-l-transparent'
                        }`}
                        onClick={() => onDeviceClick(device)}
                        title={device.in_netbox ? 'Already in NetBox' : 'Not in NetBox'}
                      >
                        <button
                          onClick={(e) => toggleDevice(device.ip_address, e)}
                          className="flex-shrink-0"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Square className="w-4 h-4 text-gray-400" />
                          )}
                        </button>
                        <Circle className={`w-2 h-2 flex-shrink-0 ${
                          device.prtg_status === 'Up' ? 'text-green-500 fill-green-500' :
                          device.prtg_status === 'Down' ? 'text-red-500 fill-red-500' :
                          'text-yellow-500 fill-yellow-500'
                        }`} />
                        <Monitor className={`w-3.5 h-3.5 flex-shrink-0 ${device.in_netbox ? 'text-green-600' : 'text-gray-400'}`} />
                        <div className="flex-1 min-w-0">
                          <div className={`text-xs font-medium truncate ${device.in_netbox ? 'text-green-700' : 'text-gray-700'}`}>
                            {device.prtg_name}
                            {device.in_netbox && (
                              <span className="ml-1.5 text-[10px] bg-green-200 text-green-800 px-1 py-0.5 rounded font-semibold">
                                IN NETBOX
                              </span>
                            )}
                          </div>
                          <div className={`text-xs font-mono ${device.in_netbox ? 'text-green-500' : 'text-gray-400'}`}>
                            {device.ip_address}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {devices.length === 0 && !loading && (
          <div className="p-8 text-center text-gray-500 text-sm">
            <Server className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p>No devices loaded.</p>
            <p className="text-xs mt-1">Use filters above to search PRTG.</p>
          </div>
        )}

        {loading && (
          <div className="p-8 text-center">
            <RefreshCw className="w-8 h-8 text-blue-500 mx-auto mb-2 animate-spin" />
            <p className="text-sm text-gray-500">Loading devices...</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// RIGHT COLUMN: NetBox Mapped Fields
// ============================================================================
function NetBoxMappingPanel({ 
  device, 
  netboxOptions, 
  mapping, 
  setMapping,
  onRefreshOptions 
}) {
  const [showCreateSite, setShowCreateSite] = useState(false);
  const [showCreateType, setShowCreateType] = useState(false);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [newSiteName, setNewSiteName] = useState("");
  const [newTypeName, setNewTypeName] = useState("");
  const [newRoleName, setNewRoleName] = useState("");
  const [creating, setCreating] = useState(false);

  const createSite = async () => {
    if (!newSiteName.trim()) return;
    setCreating(true);
    try {
      const res = await fetchApi("/integrations/v1/import/create-site", {
        method: "POST",
        body: JSON.stringify({ name: newSiteName.trim() })
      });
      if (res.success) {
        setMapping({ ...mapping, site_id: res.site.id.toString() });
        setNewSiteName("");
        setShowCreateSite(false);
        onRefreshOptions?.();
      } else {
        alert(res.error || "Failed to create site");
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setCreating(false);
    }
  };

  const createDeviceType = async () => {
    if (!newTypeName.trim()) return;
    setCreating(true);
    try {
      const res = await fetchApi("/integrations/v1/import/create-device-type", {
        method: "POST",
        body: JSON.stringify({ model: newTypeName.trim() })
      });
      if (res.success) {
        setMapping({ ...mapping, device_type_id: res.device_type.id.toString() });
        setNewTypeName("");
        setShowCreateType(false);
        onRefreshOptions?.();
      } else {
        alert(res.error || "Failed to create device type");
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setCreating(false);
    }
  };

  const createDeviceRole = async () => {
    if (!newRoleName.trim()) return;
    setCreating(true);
    try {
      const res = await fetchApi("/integrations/v1/import/create-device-role", {
        method: "POST",
        body: JSON.stringify({ name: newRoleName.trim() })
      });
      if (res.success) {
        setMapping({ ...mapping, role_id: res.device_role.id.toString() });
        setNewRoleName("");
        setShowCreateRole(false);
        onRefreshOptions?.();
      } else {
        alert(res.error || "Failed to create device role");
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setCreating(false);
    }
  };

  const mappedFields = device ? [
    { 
      prtgField: "host", 
      prtgValue: device.ip_address,
      netboxField: "primary_ip4",
      netboxValue: device.ip_address + "/32",
      description: "Primary IPv4 (identifier)"
    },
    { 
      prtgField: "device", 
      prtgValue: device.prtg_name,
      netboxField: "name",
      netboxValue: device.netbox_name,
      description: "Device name"
    },
    { 
      prtgField: "group", 
      prtgValue: device.prtg_group,
      netboxField: "comments",
      netboxValue: `PRTG Group: ${device.prtg_group}`,
      description: "Comments field"
    },
    { 
      prtgField: "tags", 
      prtgValue: device.prtg_tags || "(none)",
      netboxField: "tags",
      netboxValue: device.prtg_tags ? device.prtg_tags.split(',').map(t => t.trim()).join(', ') + ', prtg-import' : 'prtg-import',
      description: "Device tags"
    },
    { 
      prtgField: "status", 
      prtgValue: device.prtg_status,
      netboxField: "status",
      netboxValue: device.netbox_status,
      description: "Operational status",
      isStatus: true
    },
  ] : [];

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-3 border-b border-gray-200 bg-green-50">
        <h2 className="text-sm font-semibold text-green-800 uppercase tracking-wide flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
          NetBox Mapping
        </h2>
        <p className="text-xs text-green-600 mt-1">Target fields in NetBox</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {/* Required Assignments */}
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Required Assignments
          </h3>
          <div className="space-y-3">
            {/* Site */}
            <div className="bg-green-50 rounded-lg p-3 border border-green-200">
              <label className="text-xs text-green-700 font-semibold block mb-1.5">
                Site <span className="text-red-500">*</span>
              </label>
              {!showCreateSite ? (
                <div className="flex gap-2">
                  <select
                    value={mapping.site_id}
                    onChange={(e) => setMapping({ ...mapping, site_id: e.target.value })}
                    className="flex-1 px-2 py-1.5 text-sm border border-green-300 rounded bg-white focus:ring-2 focus:ring-green-500"
                  >
                    <option value="">Select Site...</option>
                    {netboxOptions.sites?.map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => setShowCreateSite(true)}
                    className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 hover:bg-green-200 rounded border border-green-300"
                    title="Create new site"
                  >
                    + New
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newSiteName}
                    onChange={(e) => setNewSiteName(e.target.value)}
                    placeholder="New site name..."
                    className="flex-1 px-2 py-1.5 text-sm border border-green-300 rounded focus:ring-2 focus:ring-green-500"
                    autoFocus
                  />
                  <button
                    onClick={createSite}
                    disabled={creating || !newSiteName.trim()}
                    className="px-2 py-1 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded disabled:opacity-50"
                  >
                    {creating ? "..." : "Create"}
                  </button>
                  <button
                    onClick={() => { setShowCreateSite(false); setNewSiteName(""); }}
                    className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded"
                  >
                    Cancel
                  </button>
                </div>
              )}
              {netboxOptions.sites?.length === 0 && !showCreateSite && (
                <p className="text-xs text-orange-600 mt-1">No sites found. Create one to continue.</p>
              )}
            </div>

            {/* Device Type */}
            <div className="bg-green-50 rounded-lg p-3 border border-green-200">
              <label className="text-xs text-green-700 font-semibold block mb-1.5">
                Device Type <span className="text-red-500">*</span>
              </label>
              {!showCreateType ? (
                <div className="flex gap-2">
                  <select
                    value={mapping.device_type_id}
                    onChange={(e) => setMapping({ ...mapping, device_type_id: e.target.value })}
                    className="flex-1 px-2 py-1.5 text-sm border border-green-300 rounded bg-white focus:ring-2 focus:ring-green-500"
                  >
                    <option value="">Select Device Type...</option>
                    {netboxOptions.device_types?.map(t => (
                      <option key={t.id} value={t.id}>{t.display || t.model}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => setShowCreateType(true)}
                    className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 hover:bg-green-200 rounded border border-green-300"
                    title="Create new device type"
                  >
                    + New
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newTypeName}
                    onChange={(e) => setNewTypeName(e.target.value)}
                    placeholder="New device type (model)..."
                    className="flex-1 px-2 py-1.5 text-sm border border-green-300 rounded focus:ring-2 focus:ring-green-500"
                    autoFocus
                  />
                  <button
                    onClick={createDeviceType}
                    disabled={creating || !newTypeName.trim()}
                    className="px-2 py-1 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded disabled:opacity-50"
                  >
                    {creating ? "..." : "Create"}
                  </button>
                  <button
                    onClick={() => { setShowCreateType(false); setNewTypeName(""); }}
                    className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded"
                  >
                    Cancel
                  </button>
                </div>
              )}
              {netboxOptions.device_types?.length === 0 && !showCreateType && (
                <p className="text-xs text-orange-600 mt-1">No device types found. Create one to continue.</p>
              )}
            </div>

            {/* Device Role */}
            <div className="bg-green-50 rounded-lg p-3 border border-green-200">
              <label className="text-xs text-green-700 font-semibold block mb-1.5">
                Device Role <span className="text-red-500">*</span>
              </label>
              {!showCreateRole ? (
                <div className="flex gap-2">
                  <select
                    value={mapping.role_id}
                    onChange={(e) => setMapping({ ...mapping, role_id: e.target.value })}
                    className="flex-1 px-2 py-1.5 text-sm border border-green-300 rounded bg-white focus:ring-2 focus:ring-green-500"
                  >
                    <option value="">Select Role...</option>
                    {netboxOptions.device_roles?.map(r => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => setShowCreateRole(true)}
                    className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 hover:bg-green-200 rounded border border-green-300"
                    title="Create new device role"
                  >
                    + New
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newRoleName}
                    onChange={(e) => setNewRoleName(e.target.value)}
                    placeholder="New role name..."
                    className="flex-1 px-2 py-1.5 text-sm border border-green-300 rounded focus:ring-2 focus:ring-green-500"
                    autoFocus
                  />
                  <button
                    onClick={createDeviceRole}
                    disabled={creating || !newRoleName.trim()}
                    className="px-2 py-1 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded disabled:opacity-50"
                  >
                    {creating ? "..." : "Create"}
                  </button>
                  <button
                    onClick={() => { setShowCreateRole(false); setNewRoleName(""); }}
                    className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded"
                  >
                    Cancel
                  </button>
                </div>
              )}
              {netboxOptions.device_roles?.length === 0 && !showCreateRole && (
                <p className="text-xs text-orange-600 mt-1">No device roles found. Create one to continue.</p>
              )}
            </div>
          </div>
        </div>

        {/* Field Mappings */}
        {device && (
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
              <ArrowRight className="w-3 h-3" />
              Field Mappings
            </h3>
            <div className="space-y-2">
              {mappedFields.map(field => (
                <div key={field.netboxField} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs text-orange-600 font-mono bg-orange-100 px-1.5 py-0.5 rounded">
                      {field.prtgField}
                    </span>
                    <ArrowRight className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-green-600 font-mono bg-green-100 px-1.5 py-0.5 rounded">
                      {field.netboxField}
                    </span>
                  </div>
                  <div className="text-sm text-gray-900 font-medium break-all">
                    {field.isStatus ? (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
                        field.netboxValue === 'active' ? 'bg-green-100 text-green-700' :
                        field.netboxValue === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {field.netboxValue}
                      </span>
                    ) : (
                      field.netboxValue
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{field.description}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!device && (
          <div className="text-center py-8">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm text-gray-400">Select a device to see</p>
            <p className="text-xs text-gray-400 mt-1">how fields will be mapped</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// BOTTOM ACTION BAR
// ============================================================================
function ActionBar({ 
  selectedCount, 
  canImport, 
  importing, 
  dryRun, 
  setDryRun, 
  updateExisting, 
  setUpdateExisting, 
  onImport,
  importResults 
}) {
  return (
    <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-t-2 border-gray-300 px-6 py-4 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="bg-blue-100 px-4 py-2 rounded-lg">
            <span className="text-blue-800 font-medium">Selected:</span>
            <span className="font-bold text-blue-600 ml-2 text-lg">{selectedCount}</span>
            <span className="text-blue-600 ml-1">devices</span>
          </div>
          
          <label className="flex items-center gap-2 cursor-pointer bg-white px-3 py-2 rounded-lg border border-gray-200">
            <input
              type="checkbox"
              checked={updateExisting}
              onChange={(e) => setUpdateExisting(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Update existing</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer bg-white px-3 py-2 rounded-lg border border-gray-200">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Dry run (preview)</span>
          </label>
        </div>

        <div className="flex items-center gap-4">
          {importResults && (
            <div className="flex items-center gap-3 text-sm bg-white px-4 py-2 rounded-lg border border-gray-200">
              <span className="text-green-600 font-medium">
                <CheckCircle className="w-4 h-4 inline mr-1" />
                {importResults.created || 0} created
              </span>
              <span className="text-blue-600 font-medium">
                {importResults.updated || 0} updated
              </span>
              <span className="text-gray-500">
                {importResults.skipped || 0} skipped
              </span>
              {importResults.errors?.length > 0 && (
                <span 
                  className="text-red-600 font-medium cursor-pointer hover:underline"
                  title={importResults.errors.map(e => `${e.name || e.ip}: ${e.error}`).join('\n')}
                  onClick={() => alert(`Import Errors:\n\n${importResults.errors.map(e => `• ${e.name || e.ip}: ${e.error}`).join('\n')}`)}
                >
                  <XCircle className="w-4 h-4 inline mr-1" />
                  {importResults.errors.length} errors (click for details)
                </span>
              )}
            </div>
          )}

          <button
            onClick={onImport}
            disabled={importing || !canImport}
            className={`flex items-center gap-2 px-6 py-3 text-base font-bold rounded-lg disabled:opacity-50 transition-all shadow-md hover:shadow-lg ${
              dryRun
                ? "text-gray-700 bg-white border-2 border-gray-300 hover:bg-gray-50"
                : "text-white bg-green-600 hover:bg-green-700 border-2 border-green-700"
            }`}
          >
            {importing ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : dryRun ? (
              <Eye className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            {dryRun ? "Preview Import" : "Import to NetBox"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN PAGE COMPONENT
// ============================================================================
export default function PRTGNetBoxImportPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [netboxOptions, setNetboxOptions] = useState({ sites: [], device_types: [], device_roles: [] });
  const [prtgGroups, setPrtgGroups] = useState([]);
  const [prtgDevices, setPrtgDevices] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [importResults, setImportResults] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");


  const [mapping, setMapping] = useState({
    site_id: "",
    device_type_id: "",
    role_id: "",
  });

  const [updateExisting, setUpdateExisting] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [importing, setImporting] = useState(false);

  // Filter devices by search term
  const filteredDevices = useMemo(() => {
    if (!searchTerm) return prtgDevices;
    const term = searchTerm.toLowerCase();
    return prtgDevices.filter(d => 
      d.ip_address?.includes(term) ||
      d.prtg_name?.toLowerCase().includes(term)
    );
  }, [prtgDevices, searchTerm]);

  // Get unique groups from filtered devices
  const activeGroups = useMemo(() => {
    const groups = new Set(filteredDevices.map(d => d.prtg_group));
    return Array.from(groups).sort();
  }, [filteredDevices]);

  // Load NetBox options and all PRTG devices on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [netboxRes, groupsRes, devicesRes] = await Promise.all([
          fetchApi("/integrations/v1/import/netbox-options"),
          fetchApi("/integrations/v1/import/prtg-groups"),
          fetchApi("/integrations/v1/import/prtg-devices"),
        ]);
        
        if (netboxRes.success) {
          setNetboxOptions(netboxRes.data || {});
        }
        if (groupsRes.success) {
          setPrtgGroups(groupsRes.groups || []);
        }
        if (devicesRes.success) {
          setPrtgDevices(devicesRes.devices || []);
          // Don't auto-select all - let user choose
        }
      } catch (err) {
        console.error("Error loading data:", err);
        setError("Failed to load PRTG devices");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const refreshDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchApi("/integrations/v1/import/prtg-devices");
      if (response.success) {
        setPrtgDevices(response.devices || []);
      } else {
        setError(response.error || "Failed to load devices");
      }
    } catch (err) {
      setError(err.message || "Failed to load devices");
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshNetboxOptions = useCallback(async () => {
    try {
      const response = await fetchApi("/integrations/v1/import/netbox-options");
      if (response.success) {
        setNetboxOptions(response.data || {});
      }
    } catch (err) {
      console.error("Error refreshing NetBox options:", err);
    }
  }, []);

  const runImport = useCallback(async () => {
    if (!mapping.site_id || !mapping.device_type_id || !mapping.role_id) {
      setError("Please select Site, Device Type, and Role before importing");
      return;
    }

    if (selectedIds.size === 0) {
      setError("Please select at least one device to import");
      return;
    }

    setImporting(true);
    setError(null);
    setImportResults(null);

    try {
      const selectedDevices = prtgDevices.filter((d) => selectedIds.has(d.ip_address));

      const response = await fetchApi("/integrations/v1/import/execute", {
        method: "POST",
        body: JSON.stringify({
          devices: selectedDevices,
          site_id: parseInt(mapping.site_id),
          device_type_id: parseInt(mapping.device_type_id),
          role_id: parseInt(mapping.role_id),
          update_existing: updateExisting,
          dry_run: dryRun,
        }),
      });

      setImportResults(response);

      if (!dryRun && response.success) {
        setSelectedIds(new Set());
      }
    } catch (err) {
      setError(err.message || "Import failed");
    } finally {
      setImporting(false);
    }
  }, [prtgDevices, selectedIds, mapping, updateExisting, dryRun]);

  const canImport = mapping.site_id && mapping.device_type_id && mapping.role_id && selectedIds.size > 0;

  return (
    <PageLayout module="inventory">
      <PageHeader
        title="PRTG → NetBox Import"
        description="Import devices from PRTG to NetBox"
      />

      <div className="flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>
        {/* Error Display */}
        {error && (
          <div className="mx-4 mt-2 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-3 flex-shrink-0">
            <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-700 flex-1">{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 text-lg font-bold">×</button>
          </div>
        )}

        {/* 2-Column Layout */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Left: PRTG Device List */}
          <div className="w-96 flex-shrink-0 overflow-hidden">
            <PRTGDeviceList
              devices={filteredDevices}
              groups={activeGroups}
              selectedIds={selectedIds}
              onSelectChange={setSelectedIds}
              selectedDevice={selectedDevice}
              onDeviceClick={setSelectedDevice}
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              loading={loading}
              onRefresh={refreshDevices}
            />
          </div>

          {/* Right: NetBox Mapping */}
          <div className="flex-1 overflow-hidden">
            <NetBoxMappingPanel
              device={selectedDevice}
              netboxOptions={netboxOptions}
              mapping={mapping}
              setMapping={setMapping}
              onRefreshOptions={refreshNetboxOptions}
            />
          </div>
        </div>

        {/* Bottom Action Bar - Always visible */}
        <div className="flex-shrink-0">
          <ActionBar
            selectedCount={selectedIds.size}
            canImport={canImport}
            importing={importing}
            dryRun={dryRun}
            setDryRun={setDryRun}
            updateExisting={updateExisting}
            setUpdateExisting={setUpdateExisting}
            onImport={runImport}
            importResults={importResults}
          />
        </div>
      </div>
    </PageLayout>
  );
}
