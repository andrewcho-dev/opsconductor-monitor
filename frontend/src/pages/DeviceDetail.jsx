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
import { cn } from "../lib/utils";
import { fetchApi } from "../lib/utils";

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
  const [selectedTimeRange, setSelectedTimeRange] = useState(8640); // Track selected time range in hours
  const chartRef = useRef(null);

  useEffect(() => {
    if (ip) {
      loadDeviceData();
      loadStoredInterfaceData();
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
      const allDevices = await fetchApi("/data");
      const deviceData = allDevices.find((d) => d.ip_address === ip);
      
      if (deviceData) {
        setDevice(deviceData);
      } else {
        setError("Device not found");
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
      const response = await fetch("/get_combined_interfaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip, limit: 50 }),
      });
      
      const data = await response.json();
      
      if (data.interfaces && data.interfaces.length > 0) {
        setInterfaces(data.interfaces.sort((a, b) => a.interface_index - b.interface_index));
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
      const response = await fetch("/get_ssh_cli_interfaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip, limit: 50 }),
      });
      
      const data = await response.json();
      
      if (data.interfaces && data.interfaces.length > 0) {
        setInterfaces(data.interfaces.sort((a, b) => a.interface_index - b.interface_index));
      }
    } catch (err) {
      console.error("Error loading SSH/CLI data:", err);
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
    setSelectedTimeRange(8640); // Set default to 360 days
    // Don't load data here - wait for the useEffect to trigger
  };

  const closeOpticalModal = () => {
    setOpticalModalOpen(false);
    setSelectedTimeRange(8640); // Reset to default when closing
    setOpticalHistory([]);
  };

  const loadOpticalHistory = async (hours) => {
    if (!currentOpticalInterface) return;
    
    setSelectedTimeRange(hours); // Update selected time range
    
    try {
      setOpticalLoading(true);
      const response = await fetch("/power_history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ip_addresses: [currentOpticalInterface.ip],
          interface_index: currentOpticalInterface.interfaceIndex,
          hours,
        }),
      });
      
      const data = await response.json();
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

  const chartData = useMemo(() => {
    if (opticalHistory.length === 0) {
      return {
        labels: [],
        datasets: [],
      };
    }

    const data = {
      labels: opticalHistory.map((h) => new Date(h.measurement_timestamp)),
      datasets: [
        {
          label: "TX Power",
          data: opticalHistory.map((h) => h.tx_power),
          borderColor: "#007bff",
          backgroundColor: "#007bff20",
          borderWidth: 2,
          pointRadius: 4,
          tension: 0.1,
          yAxisID: "y",
        },
        {
          label: "RX Power",
          data: opticalHistory.map((h) => h.rx_power),
          borderColor: "#28a745",
          backgroundColor: "#28a74520",
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 4,
          tension: 0.1,
          yAxisID: "y",
        },
      ],
    };

    const hasTempData = opticalHistory.some((h) => h.temperature !== null && h.temperature !== undefined);
    
    if (hasTempData) {
      data.datasets.push({
        label: "Temperature",
        data: opticalHistory.map((h) => h.temperature),
        borderColor: "#dc3545",
        backgroundColor: "#dc354520",
        borderWidth: 2,
        borderDash: [2, 2],
        pointRadius: 3,
        tension: 0.1,
        yAxisID: "y1",
      });
    }

    return data;
  }, [opticalHistory]);

  const hasTempData = opticalHistory.some((h) => h.temperature !== null && h.temperature !== undefined);

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

      {/* Device Info and SNMP Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Device Info */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Device Information</h2>
          <div className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">IP Address:</span>
              <span className="text-gray-800">{ip}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Hostname:</span>
              <span className="text-gray-800">{device?.snmp_hostname || "No hostname available"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Ping Status:</span>
              <span className={getStatusClass(device?.ping_status)}>
                {device?.ping_status?.includes("online") ? (
                  <span className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    Online
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <XCircle className="w-4 h-4" />
                    Offline
                  </span>
                )}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">SNMP Status:</span>
              <span className={getStatusClass(device?.snmp_status)}>
                {device?.snmp_status?.includes("YES") ? (
                  <span className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    SNMP Available
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <XCircle className="w-4 h-4" />
                    SNMP Not Available
                  </span>
                )}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Last Scan:</span>
              <span className="text-gray-800">{device?.scan_timestamp || "Never scanned"}</span>
            </div>
          </div>
        </div>

        {/* SNMP System Information */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">SNMP System Information</h3>
          <div className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Vendor:</span>
              <span className="text-gray-800">{device?.snmp_vendor_name || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Model:</span>
              <span className="text-gray-800">{device?.snmp_model || "Unknown"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Description:</span>
              <span className="text-gray-800">{device?.snmp_description || "No description available"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Contact:</span>
              <span className="text-gray-800">{device?.snmp_contact || "No contact information"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Location:</span>
              <span className="text-gray-800">{device?.snmp_location || "No location information"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Uptime:</span>
              <span className="text-gray-800">{device?.snmp_uptime || "No uptime information"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Chassis MAC:</span>
              <span className="text-gray-800">{device?.snmp_chassis_mac || "No MAC address available"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Vendor OID:</span>
              <span className="text-gray-800">{device?.snmp_vendor_oid || "No vendor OID available"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="font-medium text-gray-600">Serial Number:</span>
              <span className="text-gray-800">{device?.snmp_serial || "No serial number available"}</span>
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

        {interfaces.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">Port</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">Name</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">Type</th>
                  <th className="px-2 py-2 text-right font-medium text-gray-700">Speed</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">Status</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">MAC Address</th>
                  <th className="px-2 py-2 text-right font-medium text-gray-700">RX Bytes</th>
                  <th className="px-2 py-2 text-right font-medium text-gray-700">TX Bytes</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">Medium</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">Connector</th>
                  <th className="px-2 py-2 text-right font-medium text-gray-700">TX Power</th>
                  <th className="px-2 py-2 text-right font-medium text-gray-700">RX Power</th>
                  <th className="px-2 py-2 text-right font-medium text-gray-700">Temperature</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">LLDP Neighbor</th>
                  <th className="px-2 py-2 text-left font-medium text-gray-700">LLDP Remote Port</th>
                  <th className="px-2 py-2 text-center font-medium text-gray-700">Optical History</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {interfaces.map((iface, index) => (
                  <tr
                    key={index}
                    className={cn(
                      "hover:bg-gray-50",
                      iface.is_optical && "bg-blue-50"
                    )}
                  >
                    <td className="px-2 py-2">{iface.interface_index}</td>
                    <td className="px-2 py-2">{iface.interface_name}</td>
                    <td className="px-2 py-2">{iface.interface_type_name || "SSH/CLI"}</td>
                    <td className="px-2 py-2 text-right font-mono">
                      {formatSpeed(iface.interface_speed)}
                    </td>
                    <td className="px-2 py-2">
                      <span className={getStatusClass(iface.status)}>
                        {iface.status || "Unknown"}
                      </span>
                    </td>
                    <td className="px-2 py-2 font-mono">{iface.physical_address || "N/A"}</td>
                    <td className="px-2 py-2 text-right font-mono">
                      {formatBytes(iface.rx_bytes)}
                    </td>
                    <td className="px-2 py-2 text-right font-mono">
                      {formatBytes(iface.tx_bytes)}
                    </td>
                    <td className="px-2 py-2">
                      <span className={cn(
                        iface.is_optical ? "text-green-600" : "text-gray-600"
                      )}>
                        {iface.is_optical ? "Optical" : "Electrical"}
                      </span>
                    </td>
                    <td className="px-2 py-2">{iface.connector || "-"}</td>
                    <td className="px-2 py-2 text-right font-mono text-green-600">
                      {iface.is_optical ? (iface.tx_power || "N/A") : "-"}
                    </td>
                    <td className="px-2 py-2 text-right font-mono text-green-600">
                      {iface.is_optical ? (iface.rx_power || "N/A") : "-"}
                    </td>
                    <td className="px-2 py-2 text-right font-mono text-orange-600">
                      {iface.is_optical ? (iface.temperature || "N/A") : "-"}
                    </td>
                    <td className="px-2 py-2">
                      {iface.lldp_remote_system_name || 
                       iface.lldp_remote_mgmt_addr || 
                       iface.lldp_remote_chassis_id || "-"}
                    </td>
                    <td className="px-2 py-2">{iface.lldp_remote_port || "-"}</td>
                    <td className="px-2 py-2 text-center">
                      {iface.is_optical ? (
                        <button
                          onClick={() => showOpticalHistory(iface.interface_index, iface.interface_name)}
                          className="text-blue-600 hover:text-blue-800 cursor-pointer"
                          title="View optical power history"
                        >
                          <TrendingUp className="w-4 h-4 mx-auto" />
                        </button>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No interface data available. Please run an interface scan.
          </div>
        )}
      </div>

      {/* Optical Power History Modal */}
      {opticalModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-6xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-800">
                Optical Power History - {currentOpticalInterface?.interface_name} ({currentOpticalInterface?.ip})
              </h2>
              <button
                onClick={closeOpticalModal}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Time Range Selector */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-center gap-2">
                <span className="font-medium text-gray-700">Time Range:</span>
                {[1, 12, 24, 168, 720, 2160, 4320, 8640, 17280, 34560].map((hours) => (
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
                    {hours === 1 ? "1hr" : 
                     hours === 12 ? "12hr" : 
                     hours === 24 ? "1day" : 
                     hours === 168 ? "7day" : 
                     hours === 720 ? "30day" : 
                     hours === 2160 ? "90day" : 
                     hours === 4320 ? "180day" : 
                     hours === 8640 ? "360day" : 
                     hours === 17280 ? "720day" : 
                     hours === 34560 ? "1440day" : `${hours}hr`}
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
                              {new Date(reading.measurement_timestamp).toLocaleString("en-US", {
                                year: "numeric",
                                month: "2-digit",
                                day: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                                hour12: false,
                              })}
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
