import { useState, useMemo, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle,
  XCircle,
  Search,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Eye,
  Trash2,
  Plus,
  Filter,
  FolderOpen,
  FolderClosed,
} from "lucide-react";
import { cn } from "../lib/utils";

export function DeviceTable({
  devices,
  selectedDevices,
  onSelectDevice,
  onSelectAll,
  highlightedIps,
  loading,
  onShowDetail,
  onDeleteDevice,
  onDeleteSelected,
  onAddSelectedToGroup,
  selectedGroup,
  groupDevices,
}) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: "ip_address", direction: "asc" });
  const [visibleCount, setVisibleCount] = useState(100);
  
  // Load service filters from localStorage on mount
  const [serviceFilters, setServiceFilters] = useState(() => {
    try {
      // Try new key first, then fall back to old key for migration
      let saved = localStorage.getItem('deviceTableServiceFilters');
      if (!saved) {
        saved = localStorage.getItem('deviceTableFooterFilters');
        if (saved) {
          // Migrate to new key
          localStorage.setItem('deviceTableServiceFilters', saved);
          localStorage.removeItem('deviceTableFooterFilters');
        }
      }
      
      if (saved) {
        const parsed = JSON.parse(saved);
        // Check if all filters are false (safe state) or if any are true (potentially problematic)
        const hasActiveFilters = Object.values(parsed).some(active => active === true);
        
        // If all filters are active (which would hide everything), reset to safe defaults
        if (hasActiveFilters && Object.values(parsed).every(active => active === true)) {
          return {
            group: false,
            ping: false,
            snmp: false,
            ssh: false,
            rdp: false,
            any: false,
          };
        }
        
        return parsed;
      }
      
      return {
        group: false,
        ping: false,
        snmp: false,
        ssh: false,
        rdp: false,
        any: false,
      };
    } catch {
      return {
        group: false,
        ping: false,
        snmp: false,
        ssh: false,
        rdp: false,
        any: false,
      };
    }
  });
  
  // Save service filters to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('deviceTableServiceFilters', JSON.stringify(serviceFilters));
    } catch {
      // Ignore localStorage errors
    }
  }, [serviceFilters]);
  
  // Load expanded networks from localStorage on mount
  const [expandedNetworks, setExpandedNetworks] = useState(() => {
    try {
      const saved = localStorage.getItem('deviceTableExpandedNetworks');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });
  
  // Save expanded networks to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('deviceTableExpandedNetworks', JSON.stringify(Array.from(expandedNetworks)));
    } catch {
      // Ignore localStorage errors
    }
  }, [expandedNetworks]);
  
  const tableRef = useRef(null);

  const filteredDevices = useMemo(() => {
    let filtered = devices;

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(
        (device) =>
          device.ip_address?.toLowerCase().includes(searchLower) ||
          device.snmp_hostname?.toLowerCase().includes(searchLower) ||
          device.snmp_description?.toLowerCase().includes(searchLower) ||
          device.network_range?.toLowerCase().includes(searchLower)
      );
    }

    // Apply service filters
    const activeFilters = Object.entries(serviceFilters).filter(([_, active]) => active);
    
    // Debug logging for group filter
    if (activeFilters.some(([service, _]) => service === 'group')) {
      console.log('Group filter active:', { selectedGroup, groupDevicesLength: groupDevices?.length || 0 });
    }
    
    if (activeFilters.length > 0) {
      filtered = filtered.filter((device) => {
        return activeFilters.some(([service, _]) => {
          if (service === 'any') {
            // ANY filter: show devices that are not completely offline
            const pingOffline = !device.ping_status || device.ping_status.toLowerCase() !== 'online';
            const snmpOffline = !device.snmp_status || device.snmp_status.toUpperCase() !== 'YES';
            const sshOffline = !device.ssh_status || device.ssh_status.toUpperCase() !== 'YES';
            const rdpOffline = !device.rdp_status || device.rdp_status.toUpperCase() !== 'YES';
            return !(pingOffline && snmpOffline && sshOffline && rdpOffline);
          } else if (service === 'ping') {
            return device.ping_status && (
              device.ping_status.toLowerCase() === 'online' ||
              device.ping_status.toUpperCase() === 'YES'
            );
          } else if (service === 'group') {
            // GROUP filter: show only devices in the selected group
            if (selectedGroup.type === "custom") {
              // For custom groups, check if device IP is in the group devices list
              if (groupDevices && groupDevices.length > 0) {
                const groupIpSet = new Set(groupDevices.map(d => d.ip_address || d));
                return groupIpSet.has(device.ip_address);
              } else {
                // If no group devices loaded, don't filter (show all)
                console.log('No group devices loaded for custom group, showing all devices');
                return true;
              }
            }
            if (selectedGroup.type === "network") {
              return device.network_range === selectedGroup.name;
            }
            // If "All Devices" selected or no valid group, show all devices
            return selectedGroup.name === "All Devices";
          } else {
            // For SNMP, SSH, RDP - filter for "YES" (positive status)
            const status = device[`${service}_status`];
            return status && status.toUpperCase() === "YES";
          }
        });
      });
    }

    return filtered;
  }, [devices, search, serviceFilters, selectedGroup, groupDevices]);

  // Group devices by network and create hierarchical structure
  const groupedDevices = useMemo(() => {
    const networks = {};
    
    // Group devices by network_range
    filteredDevices.forEach(device => {
      const network = device.network_range || 'Unknown';
      if (!networks[network]) {
        networks[network] = [];
      }
      networks[network].push(device);
    });

    // Sort devices within each network
    Object.keys(networks).forEach(network => {
      networks[network].sort((a, b) => {
        const aNum = a.ip_address.split(".").reduce((acc, octet) => acc * 256 + parseInt(octet, 10), 0);
        const bNum = b.ip_address.split(".").reduce((acc, octet) => acc * 256 + parseInt(octet, 10), 0);
        return aNum - bNum;
      });
    });

    // Create hierarchical structure
    const hierarchical = [];
    Object.keys(networks).sort().forEach(network => {
      const networkDevices = networks[network];
      const isExpanded = expandedNetworks.has(network);
      
      // Add network row
      hierarchical.push({
        type: 'network',
        network,
        devices: networkDevices,
        count: networkDevices.length,
        isExpanded
      });
      
      // Add device rows if expanded
      if (isExpanded) {
        networkDevices.forEach(device => {
          hierarchical.push({
            type: 'device',
            ...device
          });
        });
      }
    });

    return hierarchical;
  }, [filteredDevices, expandedNetworks]);

  const visibleDevices = useMemo(() => {
    return groupedDevices.slice(0, visibleCount);
  }, [groupedDevices, visibleCount]);

  // Reset visible count when filters change
  useEffect(() => {
    setVisibleCount(100);
  }, [groupedDevices.length]);

  // Toggle network expansion
  const toggleNetwork = (network) => {
    setExpandedNetworks(prev => {
      const next = new Set(prev);
      if (next.has(network)) {
        next.delete(network);
      } else {
        next.add(network);
      }
      return next;
    });
  };

  // Select/deselect all devices in a network
  const handleNetworkSelect = (network, checked) => {
    const networkDevices = groupedDevices
      .filter(item => item.type === 'network' && item.network === network)
      .flatMap(item => item.devices);
    
    networkDevices.forEach(device => {
      onSelectDevice(device.ip_address, checked);
    });
  };

  // Infinite scroll handler
  useEffect(() => {
    const handleScroll = () => {
      if (tableRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = tableRef.current;
        if (scrollHeight - scrollTop <= clientHeight * 1.5) {
          setVisibleCount(prev => Math.min(prev + 50, groupedDevices.length));
        }
      }
    };

    const tableElement = tableRef.current;
    if (tableElement) {
      tableElement.addEventListener('scroll', handleScroll);
      return () => tableElement.removeEventListener('scroll', handleScroll);
    }
  }, [groupedDevices.length]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === "asc" ? "desc" : "asc",
    }));
  };

  const toggleServiceFilter = (filter) => {
    setServiceFilters((prev) => ({
      ...prev,
      [filter]: !prev[filter],
    }));
  };

  const clearAllFilters = () => {
    setServiceFilters({
      group: false,
      ping: false,
      snmp: false,
      ssh: false,
      rdp: false,
      any: false,
    });
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown className="w-4 h-4 text-gray-400" />;
    }
    return sortConfig.direction === "asc" ? (
      <ChevronUp className="w-4 h-4 text-blue-600" />
    ) : (
      <ChevronDown className="w-4 h-4 text-blue-600" />
    );
  };

  const StatusIcon = ({ status }) => {
    if (status?.toLowerCase().includes("online") || status?.toLowerCase().includes("success")) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
    if (status?.toLowerCase().includes("offline") || status?.toLowerCase().includes("fail")) {
      return <XCircle className="w-4 h-4 text-red-500" />;
    }
    return <XCircle className="w-4 h-4 text-gray-400" />;
  };

  const NetworkStatus = ({ devices, service = 'ping' }) => {
    const statusKey = service === 'ping' ? 'ping_status' : `${service}_status`;
    const onlineDevices = devices.filter(d => {
      const status = d[statusKey];
      if (service === 'ping') {
        return status && (
          status.includes('RESPONDS') || 
          status.toUpperCase() === 'YES' ||
          status.toLowerCase() === 'online'
        );
      } else {
        return status && status.toUpperCase() === 'YES';
      }
    }).length;
    
    const totalDevices = devices.length;
    const percentage = totalDevices > 0 ? Math.round((onlineDevices / totalDevices) * 100) : 0;
    
    return (
      <span className="text-sm text-gray-600">
        {onlineDevices}/{totalDevices}
      </span>
    );
  };

  // Check if device is completely offline (all services down)
  const isCompletelyOffline = (device) => {
    const pingOffline = !device.ping_status || (
      !device.ping_status.includes('RESPONDS') && 
      device.ping_status.toUpperCase() !== 'YES' &&
      device.ping_status.toLowerCase() !== 'online'
    );
    const snmpOffline = !device.snmp_status || device.snmp_status.toUpperCase() !== 'YES';
    const sshOffline = !device.ssh_status || device.ssh_status.toUpperCase() !== 'YES';
    const rdpOffline = !device.rdp_status || device.rdp_status.toUpperCase() !== 'YES';
    
    return pingOffline && snmpOffline && sshOffline && rdpOffline;
  };

  // Custom status component that handles offline devices
  const DeviceStatus = ({ device, service }) => {
    const statusKey = service === 'ping' ? 'ping_status' : `${service}_status`;
    const status = device[statusKey];
    const offline = isCompletelyOffline(device);
    
    if (offline) {
      return (
        <div className="flex items-center gap-2">
          <XCircle className="w-4 h-4 text-gray-400" />
          <span className="text-gray-400">---</span>
        </div>
      );
    }
    
    if (service === 'ping') {
      const isOnline = status && status.toLowerCase() === 'online';
      return (
        <div className="flex items-center gap-2">
          <StatusIcon status={status} />
          <span className={isOnline ? "text-green-600" : "text-red-600"}>
            {status || "-"}
          </span>
        </div>
      );
    } else {
      const isOnline = status && status.toUpperCase() === 'YES';
      return (
        <div className="flex items-center gap-2">
          {isOnline ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500" />
          )}
          <span className={isOnline ? "text-green-600" : "text-red-600"}>
            {status || "-"}
          </span>
        </div>
      );
    }
  };

  const StatusBadge = ({ status, type }) => {
    const isOnline = status?.toLowerCase().includes("online") || 
                     status?.toLowerCase().includes("success") ||
                     status?.toLowerCase().includes("open");
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
          isOnline
            ? "bg-green-100 text-green-700"
            : "bg-red-100 text-red-700"
        )}
      >
        {isOnline ? (
          <CheckCircle className="w-3 h-3" />
        ) : (
          <XCircle className="w-3 h-3" />
        )}
        {status || "N/A"}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search and action bar */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search devices..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
              }}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onAddSelectedToGroup}
              disabled={selectedDevices.size === 0}
              className={cn(
                "px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1",
                selectedDevices.size > 0
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-gray-100 text-gray-400 cursor-not-allowed"
              )}
            >
              <Plus className="w-4 h-4" />
              Add to Group
            </button>
            <button
              onClick={onDeleteSelected}
              disabled={selectedDevices.size === 0}
              className={cn(
                "px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1",
                selectedDevices.size > 0
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "bg-gray-100 text-gray-400 cursor-not-allowed"
              )}
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>
        
        {/* Right side - Filters and count */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 mr-2">Filters:</span>
            <button
              onClick={() => clearAllFilters()}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              ALL
            </button>
            {Object.entries(serviceFilters).map(([service, active]) => (
              <button
                key={service}
                onClick={() => toggleServiceFilter(service)}
                className={cn(
                  "px-3 py-1 text-sm border rounded-md transition-colors",
                  active
                    ? "bg-blue-100 border-blue-300 text-blue-700"
                    : "border-gray-300 hover:bg-gray-50"
                )}
              >
                {service.toUpperCase()}
              </button>
            ))}
          </div>
          <div className="text-sm text-gray-500">
            {filteredDevices.length} devices
            {selectedDevices.size > 0 && ` • ${selectedDevices.size} selected`}
            {devices.length > 0 && filteredDevices.length === 0 && (
              <span className="ml-2 text-yellow-600">
                (All devices hidden by filters - click ALL to clear)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-x-auto overflow-y-auto" ref={tableRef}>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={
                    visibleDevices.length > 0 &&
                    visibleDevices.every((d) => selectedDevices.has(d.ip_address))
                  }
                  onChange={(e) => onSelectAll(visibleDevices, e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("ip_address")}
              >
                <div className="flex items-center gap-1">
                  IP Address
                  <SortIcon columnKey="ip_address" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("snmp_hostname")}
              >
                <div className="flex items-center gap-1">
                  Hostname
                  <SortIcon columnKey="snmp_hostname" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("network_range")}
              >
                <div className="flex items-center gap-1">
                  Network
                  <SortIcon columnKey="network_range" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Ping
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                SNMP
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                SSH
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                RDP
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {visibleDevices.map((item) => {
              if (item.type === 'network') {
                // Network row
                const allSelected = item.devices.every(d => selectedDevices.has(d.ip_address));
                const someSelected = item.devices.some(d => selectedDevices.has(d.ip_address));
                
                return (
                  <tr
                    key={`network-${item.network}`}
                    className={cn(
                      "bg-gray-100 hover:bg-gray-200 transition-colors cursor-pointer",
                      "border-l-4 border-l-gray-400"
                    )}
                    onClick={() => toggleNetwork(item.network)}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        ref={someSelected && !allSelected ? (input) => {
                          if (input) input.indeterminate = true;
                        } : null}
                        onChange={(e) => {
                          e.stopPropagation();
                          handleNetworkSelect(item.network, e.target.checked);
                        }}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-4 py-3 font-mono text-sm font-semibold">
                      <div className="flex items-center gap-2">
                        {item.isExpanded ? (
                          <FolderOpen className="w-4 h-4 text-gray-600" />
                        ) : (
                          <FolderClosed className="w-4 h-4 text-gray-600" />
                        )}
                        {item.network}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      ({item.count} devices)
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      Network
                    </td>
                    <td className="px-4 py-3">
                      <NetworkStatus devices={item.devices} />
                    </td>
                    <td className="px-4 py-3">
                      <NetworkStatus devices={item.devices} service="snmp" />
                    </td>
                    <td className="px-4 py-3">
                      <NetworkStatus devices={item.devices} service="ssh" />
                    </td>
                    <td className="px-4 py-3">
                      <NetworkStatus devices={item.devices} service="rdp" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleNetwork(item.network);
                          }}
                          className="p-1 rounded hover:bg-gray-300 text-gray-500 hover:text-gray-700"
                          title="Toggle network"
                        >
                          {item.isExpanded ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              } else {
                // Device row
                const isHighlighted = highlightedIps.has(item.ip_address);
                const isSelected = selectedDevices.has(item.ip_address);
                const completelyOffline = isCompletelyOffline(item);
                
                return (
                  <tr
                    key={item.ip_address}
                    className={cn(
                      "hover:bg-gray-50 transition-colors",
                      isHighlighted && "bg-blue-50 border-l-4 border-l-blue-500"
                    )}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => onSelectDevice(item.ip_address, e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className={cn(
                      "px-4 py-3 font-mono text-sm pl-8",
                      completelyOffline && "text-gray-400"
                    )}>
                      {item.ip_address}
                    </td>
                    <td className={cn(
                      "px-4 py-3 text-sm",
                      completelyOffline ? "text-gray-400" : "text-gray-700"
                    )}>
                      {(item.snmp_hostname || "-").toLowerCase()}
                    </td>
                    <td className={cn(
                      "px-4 py-3 font-mono text-sm",
                      completelyOffline ? "text-gray-400" : "text-gray-500"
                    )}>
                      {(item.network_range || "-").toLowerCase()}
                    </td>
                    <td className={cn(
                      "px-4 py-3 text-sm",
                      completelyOffline ? "text-gray-400" : "text-gray-700"
                    )}>
                      {completelyOffline ? "---" : (
                        item.ping_status && (
                          item.ping_status.includes('RESPONDS') || 
                          item.ping_status.toUpperCase() === 'YES' ||
                          item.ping_status.toLowerCase() === 'online'
                        ) ? 'yes' : 'no'
                      )}
                    </td>
                    <td className={cn(
                      "px-4 py-3 text-sm",
                      completelyOffline ? "text-gray-400" : "text-gray-700"
                    )}>
                      {completelyOffline ? "---" : (item.snmp_status || "no").toLowerCase()}
                    </td>
                    <td className={cn(
                      "px-4 py-3 text-sm",
                      completelyOffline ? "text-gray-400" : "text-gray-700"
                    )}>
                      {completelyOffline ? "---" : (item.ssh_status || "no").toLowerCase()}
                    </td>
                    <td className={cn(
                      "px-4 py-3 text-sm",
                      completelyOffline ? "text-gray-400" : "text-gray-700"
                    )}>
                      {completelyOffline ? "---" : (item.rdp_status || "no").toLowerCase()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => onShowDetail(item.ip_address)}
                          className={cn(
                            "p-1 rounded hover:bg-gray-100",
                            completelyOffline ? "text-gray-400 hover:text-gray-500" : "text-gray-500 hover:text-gray-700"
                          )}
                          title="View details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onDeleteDevice(item.ip_address)}
                          className={cn(
                            "p-1 rounded hover:bg-red-100",
                            completelyOffline ? "text-gray-400 hover:text-red-400" : "text-red-500 hover:text-red-700"
                          )}
                          title="Delete device"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              }
            })}
          </tbody>
        </table>
      </div>

              {/* Scroll indicator */}
      {visibleDevices.length < groupedDevices.length && (
        <div className="text-center py-4 text-sm text-gray-500">
          Showing {visibleDevices.length} of {groupedDevices.length} entries (scroll to load more)
        </div>
      )}
    </div>
  );
}
