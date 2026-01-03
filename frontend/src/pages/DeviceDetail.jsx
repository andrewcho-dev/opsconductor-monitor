import { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  X,
  RefreshCw,
  Server,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  ArrowLeft,
  Database,
  Network,
  Cpu,
  HardDrive,
  Package,
} from "lucide-react";
import { PageHeader } from "../components/layout";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from "chart.js";
import "chartjs-adapter-date-fns";
import { cn, fetchApi, formatDetailedTime } from "../lib/utils";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

export function DeviceDetail() {
  const { ip } = useParams();
  const navigate = useNavigate();
  const [device, setDevice] = useState(null);
  const [interfaces, setInterfaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [opticalModalOpen, setOpticalModalOpen] = useState(false);
  const [currentOpticalInterface, setCurrentOpticalInterface] = useState(null);
  const [opticalHistory, setOpticalHistory] = useState([]);
  const [opticalLoading, setOpticalLoading] = useState(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState(720); // Time range in hours (default 30 days)
  const [selectedTimescale, setSelectedTimescale] = useState('hour'); // Aggregation: 'minute', 'hour', 'day'
  const chartRef = useRef(null);
  
  // MCP Data
  const [mcpData, setMcpData] = useState(null);
  const [mcpLoading, setMcpLoading] = useState(false);

  useEffect(() => {
    if (ip) {
      loadDeviceData();
      loadStoredInterfaceData();
      loadMcpData();
    }
  }, [ip]);

  // Load optical history when currentOpticalInterface changes
  useEffect(() => {
    if (currentOpticalInterface && opticalModalOpen) {
      loadOpticalHistory(selectedTimeRange);
    }
  }, [currentOpticalInterface, opticalModalOpen]);

  const loadDeviceData = async () => {
    try {
      setLoading(true);
      let deviceData = null;
      
      // NetBox is the source of truth for device inventory
      try {
        const netboxResponse = await fetchApi("/api/netbox/devices");
        // API returns {success: true, data: [...]} or {success: true, data: {results: [...]}}
        const deviceList = Array.isArray(netboxResponse.data) 
          ? netboxResponse.data 
          : netboxResponse.data?.results || [];
        
        if (netboxResponse.success && deviceList.length > 0) {
          const netboxDevice = deviceList.find((d) => {
            const primaryIp = d.primary_ip4?.address?.split('/')[0] || d.primary_ip?.address?.split('/')[0];
            return primaryIp === ip;
          });
          
          if (netboxDevice) {
            // Transform NetBox device to standard format
            deviceData = {
              ip_address: netboxDevice.primary_ip4?.address?.split('/')[0] || netboxDevice.primary_ip?.address?.split('/')[0] || ip,
              hostname: netboxDevice.name,
              device_type: netboxDevice.device_type?.model || 'Unknown',
              manufacturer: netboxDevice.device_type?.manufacturer?.name || '',
              status: netboxDevice.status?.value || 'unknown',
              site: netboxDevice.site?.name || '',
              role: netboxDevice.role?.name || netboxDevice.device_role?.name || '',
              platform: netboxDevice.platform?.name || '',
              serial: netboxDevice.serial || '',
              asset_tag: netboxDevice.asset_tag || '',
              comments: netboxDevice.comments || '',
              netbox_id: netboxDevice.id,
              netbox_url: netboxDevice.url,
              source: 'netbox',
            };
          }
        }
      } catch (netboxErr) {
        console.warn("Could not fetch from NetBox:", netboxErr);
      }
      
      if (deviceData) {
        setDevice(deviceData);
      } else {
        setError("Device not found in NetBox");
      }
    } catch (err) {
      setError("Error loading device data");
    } finally {
      setLoading(false);
    }
  };

  const loadStoredInterfaceData = async () => {
    if (!ip) return;
    
    try {
      const data = await fetchApi("/get_combined_interfaces", {
        method: "POST",
        body: JSON.stringify({ ip, limit: 50 }),
      });
      
      // Backend returns array directly or {interfaces: [...]}
      const interfaceList = Array.isArray(data) ? data : (data.interfaces || []);
      
      if (interfaceList.length > 0) {
        setInterfaces(interfaceList.sort((a, b) => a.interface_index - b.interface_index));
      } else {
        // Try SSH/CLI data
        loadSshCliDataOnly();
      }
    } catch (err) {
      console.error("Error loading interface data:", err);
    }
  };

  const loadSshCliDataOnly = async () => {
    try {
      const data = await fetchApi("/get_ssh_cli_interfaces", {
        method: "POST",
        body: JSON.stringify({ ip, limit: 50 }),
      });
      
      // Backend returns array directly or {interfaces: [...]}
      const interfaceList = Array.isArray(data) ? data : (data.interfaces || []);
      
      if (interfaceList.length > 0) {
        setInterfaces(interfaceList.sort((a, b) => a.interface_index - b.interface_index));
      }
    } catch (err) {
      console.error("Error loading SSH/CLI data:", err);
    }
  };

  const loadMcpData = async () => {
    if (!ip) return;
    
    setMcpLoading(true);
    try {
      const data = await fetchApi(`/api/mcp/device/${ip}`);
      if (data.success && data.data?.found) {
        setMcpData(data.data);
      } else {
        setMcpData(null);
      }
    } catch (err) {
      console.log("MCP data not available for this device");
      setMcpData(null);
    } finally {
      setMcpLoading(false);
    }
  };

  const loadInterfaceData = async () => {
    // Implementation for real-time interface data loading
  };

  const storeInterfaceData = async () => {
    // Implementation for storing interface data
  };

  const showOpticalHistory = async (interfaceIndex, interfaceName) => {
    setCurrentOpticalInterface({ ip, interfaceIndex, interfaceName });
    setOpticalModalOpen(true);
    setSelectedTimeRange(720); // Default to 30 days
    setSelectedTimescale('hour'); // Default to hourly aggregation
    // Don't load data here - wait for the useEffect to trigger
  };

  const closeOpticalModal = () => {
    setOpticalModalOpen(false);
    setSelectedTimeRange(720);
    setSelectedTimescale('hour');
    setOpticalHistory([]);
  };

  const loadOpticalHistory = async (hours) => {
    if (!currentOpticalInterface) return;
    
    setSelectedTimeRange(hours); // Update selected time range
    
    try {
      setOpticalLoading(true);
      const data = await fetchApi("/power_history", {
        method: "POST",
        body: JSON.stringify({
          ip_addresses: [currentOpticalInterface.ip],
          interface_index: currentOpticalInterface.interfaceIndex,
          hours,
        }),
      });
      setOpticalHistory(data.history || []);
    } catch (err) {
      console.error("Error loading optical history:", err);
    } finally {
      setOpticalLoading(false);
    }
  };

  const formatSpeed = (speed) => {
    // Handle text-based speeds like "10GBASE-LR", "1GBASE-T", etc.
    if (typeof speed === 'string' && speed.trim()) {
      const upperSpeed = speed.toUpperCase().trim();
      
      // Map common text speeds to readable format
      if (upperSpeed.includes('10GBASE') || upperSpeed === '10G') return "10 Gbps";
      if (upperSpeed.includes('1GBASE') || upperSpeed === '1G') return "1 Gbps";
      if (upperSpeed.includes('100BASE') || upperSpeed === '100M') return "100 Mbps";
      if (upperSpeed.includes('1000BASE') || upperSpeed === '1000M') return "1 Gbps";
      if (upperSpeed.includes('2.5GBASE') || upperSpeed === '2.5G') return "2.5 Gbps";
      if (upperSpeed.includes('5GBASE') || upperSpeed === '5G') return "5 Gbps";
      if (upperSpeed.includes('40GBASE') || upperSpeed === '40G') return "40 Gbps";
      if (upperSpeed.includes('100GBASE') || upperSpeed === '100G') return "100 Gbps";
      
      // Return the original text if we can't parse it
      return speed;
    }
    
    // Handle numeric speeds
    if (speed === 4294967295) return "10 Gbps";
    if (speed === 1000000000) return "1 Gbps";
    if (speed === 100000000) return "100 Mbps";
    if (speed === 2500000000) return "2.5 Gbps";
    if (speed === 5000000000) return "5 Gbps";
    if (speed === 0) return "No link";
    if (!speed || speed === null || speed === undefined || speed === '') return "Unknown";
    
    // Convert numeric bps to readable format
    const numericSpeed = parseInt(speed);
    if (numericSpeed >= 1000000000) {
      return `${(numericSpeed / 1000000000).toFixed(0)} Gbps`;
    } else if (numericSpeed >= 1000000) {
      return `${(numericSpeed / 1000000).toFixed(0)} Mbps`;
    } else if (numericSpeed >= 1000) {
      return `${(numericSpeed / 1000).toFixed(0)} Kbps`;
    }
    
    return `${numericSpeed} bps`;
  };

  const formatBytes = (bytes) => {
    return (bytes / 1000000000).toFixed(2) + " GB";
  };

  const getStatusClass = (status) => {
    const statusLower = status?.toLowerCase();
    if (statusLower === "up" || statusLower?.includes("online")) {
      return "text-green-600 font-semibold";
    }
    if (statusLower === "down" || statusLower?.includes("offline")) {
      return "text-red-600 font-semibold";
    }
    return "text-gray-500";
  };

  // Aggregate data into Hi/Lo/Close buckets based on timescale
  const aggregatedData = useMemo(() => {
    if (opticalHistory.length === 0) return [];

    const sorted = [...opticalHistory].sort(
      (a, b) => new Date(a.measurement_timestamp) - new Date(b.measurement_timestamp)
    );

    // Determine bucket size in milliseconds
    const bucketMs = {
      'minute': 60 * 1000,
      'hour': 60 * 60 * 1000,
      'day': 24 * 60 * 60 * 1000,
    }[selectedTimescale] || 60 * 60 * 1000;

    const buckets = new Map();

    for (const reading of sorted) {
      const ts = new Date(reading.measurement_timestamp).getTime();
      const bucketKey = Math.floor(ts / bucketMs) * bucketMs;

      if (!buckets.has(bucketKey)) {
        buckets.set(bucketKey, {
          timestamp: new Date(bucketKey),
          tx: { values: [], high: null, low: null, close: null },
          rx: { values: [], high: null, low: null, close: null },
          temp: { values: [], high: null, low: null, close: null },
        });
      }

      const bucket = buckets.get(bucketKey);
      if (reading.tx_power != null) bucket.tx.values.push(reading.tx_power);
      if (reading.rx_power != null) bucket.rx.values.push(reading.rx_power);
      if (reading.temperature != null) bucket.temp.values.push(reading.temperature);
    }

    // Calculate hi/lo/close for each bucket
    const result = [];
    for (const [, bucket] of buckets) {
      const calcHLC = (values) => {
        if (values.length === 0) return { high: null, low: null, close: null };
        return {
          high: Math.max(...values),
          low: Math.min(...values),
          close: values[values.length - 1],
        };
      };

      result.push({
        timestamp: bucket.timestamp,
        tx: calcHLC(bucket.tx.values),
        rx: calcHLC(bucket.rx.values),
        temp: calcHLC(bucket.temp.values),
      });
    }

    return result.sort((a, b) => a.timestamp - b.timestamp);
  }, [opticalHistory, selectedTimescale]);

  const chartData = useMemo(() => {
    if (aggregatedData.length === 0) {
      return { labels: [], datasets: [] };
    }

    const pointRadius = aggregatedData.length > 200 ? 0 : aggregatedData.length > 50 ? 1 : 2;

    const datasets = [
      // TX Power - Close line with Hi/Lo range
      {
        label: "TX Close",
        data: aggregatedData.map((d) => d.tx.close),
        borderColor: "#007bff",
        backgroundColor: "#007bff20",
        borderWidth: 2,
        pointRadius: pointRadius,
        tension: 0.1,
        yAxisID: "y",
      },
      {
        label: "TX High",
        data: aggregatedData.map((d) => d.tx.high),
        borderColor: "#007bff80",
        backgroundColor: "transparent",
        borderWidth: 1,
        borderDash: [2, 2],
        pointRadius: 0,
        tension: 0.1,
        yAxisID: "y",
        fill: false,
      },
      {
        label: "TX Low",
        data: aggregatedData.map((d) => d.tx.low),
        borderColor: "#007bff80",
        backgroundColor: "#007bff15",
        borderWidth: 1,
        borderDash: [2, 2],
        pointRadius: 0,
        tension: 0.1,
        yAxisID: "y",
        fill: '-1', // Fill to previous dataset (TX High)
      },
      // RX Power - Close line with Hi/Lo range
      {
        label: "RX Close",
        data: aggregatedData.map((d) => d.rx.close),
        borderColor: "#28a745",
        backgroundColor: "#28a74520",
        borderWidth: 2,
        pointRadius: pointRadius,
        tension: 0.1,
        yAxisID: "y",
      },
      {
        label: "RX High",
        data: aggregatedData.map((d) => d.rx.high),
        borderColor: "#28a74580",
        backgroundColor: "transparent",
        borderWidth: 1,
        borderDash: [2, 2],
        pointRadius: 0,
        tension: 0.1,
        yAxisID: "y",
        fill: false,
      },
      {
        label: "RX Low",
        data: aggregatedData.map((d) => d.rx.low),
        borderColor: "#28a74580",
        backgroundColor: "#28a74515",
        borderWidth: 1,
        borderDash: [2, 2],
        pointRadius: 0,
        tension: 0.1,
        yAxisID: "y",
        fill: '-1', // Fill to previous dataset (RX High)
      },
    ];

    // Add temperature if available
    const hasTempData = aggregatedData.some((d) => d.temp.close !== null);
    if (hasTempData) {
      datasets.push({
        label: "Temp Close",
        data: aggregatedData.map((d) => d.temp.close),
        borderColor: "#dc3545",
        backgroundColor: "#dc354520",
        borderWidth: 2,
        pointRadius: pointRadius,
        tension: 0.1,
        yAxisID: "y1",
      });
    }

    return {
      labels: aggregatedData.map((d) => d.timestamp),
      datasets,
    };
  }, [aggregatedData]);

  const hasTempData = aggregatedData.some((d) => d.temp?.close !== null);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: hasTempData ? "Optical Power Levels & Temperature" : "Optical Power Levels",
      },
      legend: {
        display: true,
        position: "top",
        onClick: (e, legendItem, legend) => {
          const index = legendItem.datasetIndex;
          const ci = legend.chart;
          if (ci.isDatasetVisible(index)) {
            ci.hide(index);
            legendItem.hidden = true;
          } else {
            ci.show(index);
            legendItem.hidden = false;
          }
        },
        labels: {
          usePointStyle: true,
          padding: 15,
          font: {
            size: 12,
          },
        },
      },
    },
    scales: {
      x: {
        type: "time",
        time: {
          displayFormats: {
            minute: "MMM dd HH:mm",
            hour: "MMM dd HH:mm",
            day: "MMM dd HH:mm",
          },
          tooltipFormat: "MMM dd, yyyy HH:mm",
        },
        title: {
          display: true,
          text: "Time (24-hour format)",
        },
      },
      y: {
        type: "linear",
        display: true,
        position: "left",
        title: {
          display: true,
          text: "Power (dBm)",
        },
        ticks: {
          callback: function (value) {
            return value.toFixed(1) + " dBm";
          },
        },
      },
      ...(hasTempData && {
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Temperature (°C)",
          },
          ticks: {
            callback: function (value) {
              return value.toFixed(1) + " °C";
            },
          },
          grid: {
            drawOnChartArea: false,
          },
        },
      }),
    },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-600 font-semibold">{error}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title={device?.snmp_hostname || ip}
        description={`${ip} • ${device?.ping_status === 'online' ? 'Online' : 'Offline'}`}
        icon={Server}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/inventory/devices')}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <button
              onClick={loadDeviceData}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        }
      />
      
      <div className="flex-1 overflow-auto p-4 bg-gray-50">

      {/* Device Information - Integrated MCP + SNMP */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Device Info */}
        <div className={cn(
          "bg-white p-4 rounded-lg shadow",
          mcpData && "border-l-4 border-indigo-500"
        )}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {mcpData ? <Network className="w-5 h-5 text-indigo-600" /> : <Server className="w-5 h-5 text-gray-600" />}
              <h2 className="text-lg font-semibold text-gray-800">Device Information</h2>
            </div>
            {mcpData && (
              <span className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded-full font-medium">
                MCP Managed
              </span>
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">IP Address:</span>
              <span className="text-gray-800 font-mono">{ip}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Hostname:</span>
              <span className="text-gray-800">{mcpData?.device?.name || device?.hostname || device?.snmp_hostname || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Device Type:</span>
              <span className="text-gray-800">{mcpData?.device?.device_type || device?.device_type || device?.snmp_model || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Vendor:</span>
              <span className="text-gray-800">{mcpData?.device?.vendor || device?.manufacturer || device?.snmp_vendor_name || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Site:</span>
              <span className="text-gray-800">{device?.site || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Role:</span>
              <span className="text-gray-800">{device?.role || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Serial Number:</span>
              <span className="text-gray-800 font-mono">{mcpData?.device?.serial_number || device?.serial || device?.snmp_serial || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Status:</span>
              <span className={cn(
                "font-medium flex items-center gap-1",
                (device?.status === 'active' || mcpData?.device?.association_state?.toLowerCase().includes('connect') || device?.ping_status?.includes('online')) 
                  ? "text-green-600" : "text-red-600"
              )}>
                {(device?.status === 'active' || mcpData?.device?.association_state?.toLowerCase().includes('connect') || device?.ping_status?.includes('online')) 
                  ? <><CheckCircle className="w-4 h-4" /> {device?.status === 'active' ? 'Active' : 'Online'}</> 
                  : <><XCircle className="w-4 h-4" /> {device?.status || 'Offline'}</>}
              </span>
            </div>
          </div>
        </div>

        {/* System Details */}
        <div className={cn(
          "bg-white p-4 rounded-lg shadow",
          mcpData && "border-l-4 border-indigo-500"
        )}>
          <h3 className="text-lg font-semibold text-gray-800 mb-3">System Details</h3>
          <div className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Software Version:</span>
              <span className="text-gray-800 font-mono">{mcpData?.device?.software_version || device?.snmp_description || "Unknown"}</span>
            </div>
            {mcpData && (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium text-gray-600">Sync State:</span>
                  <span className={cn(
                    "font-medium",
                    mcpData.device?.sync_state?.toLowerCase().includes('synch') ? "text-green-600" : "text-yellow-600"
                  )}>
                    {mcpData.device?.sync_state || "Unknown"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium text-gray-600">Association:</span>
                  <span className={cn(
                    "font-medium",
                    mcpData.device?.association_state?.toLowerCase().includes('connect') ? "text-green-600" : "text-yellow-600"
                  )}>
                    {mcpData.device?.association_state || "Unknown"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium text-gray-600">Equipment Count:</span>
                  <span className="text-gray-800">{mcpData.equipment_count || 0} items</span>
                </div>
              </>
            )}
            {!mcpData && (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium text-gray-600">Location:</span>
                  <span className="text-gray-800">{device?.snmp_location || "Unknown"}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium text-gray-600">Contact:</span>
                  <span className="text-gray-800">{device?.snmp_contact || "Unknown"}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium text-gray-600">Uptime:</span>
                  <span className="text-gray-800">{device?.snmp_uptime || "Unknown"}</span>
                </div>
              </>
            )}
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Last Scan:</span>
              <span className="text-gray-800">{device?.scan_timestamp || "Never scanned"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Interface Information */}
      <div className="bg-white p-4 rounded-lg shadow mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-800">Interface Information</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={loadInterfaceData}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
            >
              Load Interfaces
            </button>
            <button
              onClick={storeInterfaceData}
              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
            >
              Store Current Data
            </button>
          </div>
        </div>

        {(() => {
          // Build MCP SFP lookup by slot number
          const mcpSfpBySlot = {};
          if (mcpData?.equipment) {
            mcpData.equipment.forEach(eq => {
              if (eq.type === 'SFP' && eq.slot) {
                mcpSfpBySlot[eq.slot] = eq;
              }
            });
          }
          
          return interfaces.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">Port</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">Name</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">Type</th>
                    <th className="px-3 py-2 text-right font-semibold text-gray-700">Speed</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">Status</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">Medium</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">SFP</th>
                    <th className="px-3 py-2 text-right font-semibold text-gray-700">TX Power</th>
                    <th className="px-3 py-2 text-right font-semibold text-gray-700">RX Power</th>
                    <th className="px-3 py-2 text-right font-semibold text-gray-700">Temp</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-700">Neighbor</th>
                    <th className="px-3 py-2 text-center font-semibold text-gray-700"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {interfaces.map((iface, index) => {
                    // Match MCP SFP by interface index
                    const mcpSfp = mcpSfpBySlot[String(iface.interface_index)];
                    
                    // Build neighbor string
                    const neighbor = iface.lldp_remote_system_name || iface.lldp_remote_mgmt_addr || '';
                    const remotePort = iface.lldp_remote_port || '';
                    const neighborInfo = neighbor ? (remotePort ? `${neighbor}:${remotePort}` : neighbor) : '—';
                    
                    // Build SFP info - combine manufacturer and part number from MCP
                    const sfpInfo = mcpSfp 
                      ? `${mcpSfp.manufacturer || ''} ${mcpSfp.part_number?.trim() || ''}`.trim()
                      : (iface.connector || '—');
                    
                    return (
                      <tr
                        key={index}
                        className={cn(
                          "hover:bg-gray-50",
                          iface.is_optical && "bg-blue-50/50"
                        )}
                      >
                        <td className="px-3 py-2 font-medium text-gray-900">{iface.interface_index}</td>
                        <td className="px-3 py-2 text-gray-700">{iface.interface_name}</td>
                        <td className="px-3 py-2 text-gray-700">{iface.interface_type_name || '—'}</td>
                        <td className="px-3 py-2 text-right font-mono text-gray-700">
                          {formatSpeed(iface.interface_speed)}
                        </td>
                        <td className="px-3 py-2">
                          <span className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                            iface.status?.toLowerCase() === 'up'
                              ? "bg-green-100 text-green-700" 
                              : "bg-red-100 text-red-700"
                          )}>
                            {iface.status || "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className={cn(
                            "font-medium",
                            iface.is_optical ? "text-blue-600" : "text-gray-600"
                          )}>
                            {iface.is_optical ? "Optical" : "Electrical"}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-mono text-gray-700 max-w-[200px] truncate" title={sfpInfo}>
                          {sfpInfo}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-green-600">
                          {iface.is_optical ? (iface.tx_power || '—') : '—'}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-green-600">
                          {iface.is_optical ? (iface.rx_power || '—') : '—'}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-orange-600">
                          {iface.is_optical && iface.temperature ? `${iface.temperature}°C` : '—'}
                        </td>
                        <td className="px-3 py-2 text-gray-700 max-w-[180px] truncate" title={neighborInfo}>
                          {neighborInfo}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {iface.is_optical ? (
                            <button
                              onClick={() => showOpticalHistory(iface.interface_index, iface.interface_name)}
                              className="text-blue-600 hover:text-blue-800"
                              title="View optical power history"
                            >
                              <TrendingUp className="w-4 h-4" />
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 text-sm">
              No interface data available. Please run an interface scan.
            </div>
          );
        })()}
      </div>

      {/* Optical Power History Modal */}
      {opticalModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-6xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-800">
                Optical Power History - {currentOpticalInterface?.interfaceName} ({currentOpticalInterface?.ip})
              </h2>
              <button
                onClick={closeOpticalModal}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Timescale and Time Range Selectors */}
            <div className="p-4 border-b border-gray-200 space-y-3">
              {/* Timescale (aggregation granularity) */}
              <div className="flex items-center justify-center gap-2">
                <span className="font-medium text-gray-700 w-24">Timescale:</span>
                {[
                  { value: 'minute', label: 'Minutes' },
                  { value: 'hour', label: 'Hours' },
                  { value: 'day', label: 'Days' },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setSelectedTimescale(value)}
                    className={cn(
                      "px-4 py-1 text-sm border rounded transition-colors",
                      selectedTimescale === value
                        ? "bg-purple-600 text-white border-purple-600"
                        : "border-gray-300 hover:bg-gray-50"
                    )}
                  >
                    {label}
                  </button>
                ))}
                <span className="text-xs text-gray-500 ml-2">
                  ({aggregatedData.length} data points)
                </span>
              </div>
              
              {/* Time Range */}
              <div className="flex items-center justify-center gap-2">
                <span className="font-medium text-gray-700 w-24">Range:</span>
                {[
                  { hours: 1, label: '1hr' },
                  { hours: 6, label: '6hr' },
                  { hours: 24, label: '1d' },
                  { hours: 168, label: '7d' },
                  { hours: 720, label: '30d' },
                  { hours: 2160, label: '90d' },
                  { hours: 4320, label: '180d' },
                  { hours: 8640, label: '1yr' },
                  { hours: 17280, label: '2yr' },
                ].map(({ hours, label }) => (
                  <button
                    key={hours}
                    onClick={() => loadOpticalHistory(hours)}
                    className={cn(
                      "px-3 py-1 text-sm border rounded transition-colors",
                      selectedTimeRange === hours
                        ? "bg-blue-600 text-white border-blue-600"
                        : "border-gray-300 hover:bg-gray-50"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Chart */}
            <div className="p-4">
              <div className="h-96">
                {opticalLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                ) : opticalHistory.length > 0 ? (
                  <>
                    <Line ref={chartRef} data={chartData} options={chartOptions} />
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <Database className="w-12 h-12 mb-4 text-gray-400" />
                    <div className="text-center">
                      <p className="font-medium mb-2">No power history data available</p>
                      <p className="text-sm">Try selecting a longer time range or run an optical scan to collect current data.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Data Table */}
            <div className="p-4 border-t border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Power Readings</h3>
              {opticalHistory.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Timestamp</th>
                        <th className="px-4 py-2 text-right font-medium text-gray-700">TX Power (dBm)</th>
                        <th className="px-4 py-2 text-right font-medium text-gray-700">RX Power (dBm)</th>
                        <th className="px-4 py-2 text-right font-medium text-gray-700">Temperature (°C)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {opticalHistory
                        .sort((a, b) => new Date(b.measurement_timestamp) - new Date(a.measurement_timestamp))
                        .map((reading, index) => (
                          <tr key={index}>
                            <td className="px-4 py-2 font-mono">
                              {formatDetailedTime(reading.measurement_timestamp)}
                            </td>
                            <td className="px-4 py-2 text-right font-mono">
                              {reading.tx_power ? reading.tx_power.toFixed(2) : "N/A"}
                            </td>
                            <td className="px-4 py-2 text-right font-mono">
                              {reading.rx_power ? reading.rx_power.toFixed(2) : "N/A"}
                            </td>
                            <td className="px-4 py-2 text-right font-mono">
                              {reading.temperature ? reading.temperature.toFixed(1) : "N/A"}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-4 text-gray-500">
                  No power history data available
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
