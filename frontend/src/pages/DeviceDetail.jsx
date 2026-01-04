import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  RefreshCw,
  Server,
  MapPin,
  Tag,
  Activity,
  Zap,
  Clock,
  AlertTriangle,
  AlertCircle,
  Bell,
  CheckCircle,
  XCircle,
  ChevronDown,
} from "lucide-react";
import { PageHeader } from "../components/layout";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import { cn, fetchApi } from "../lib/utils";

// Interface Metrics Panel Component
function InterfaceMetricsPanel({ deviceIp, interfaceName, timeRange, isOptical = false, onClose }) {
  const [trafficMetrics, setTrafficMetrics] = useState([]);
  const [latestTraffic, setLatestTraffic] = useState(null);
  const [opticalMetrics, setOpticalMetrics] = useState([]);
  const [opticalThresholds, setOpticalThresholds] = useState(null);
  const [loading, setLoading] = useState(true);
  const [trafficExpanded, setTrafficExpanded] = useState(false);

  // Extract port number from interface name (e.g., "21" from "21" or "Port 21" or "port21")
  const portNum = interfaceName.replace(/\D/g, '');

  useEffect(() => {
    const loadMetrics = async () => {
      setLoading(true);
      try {
        // Load traffic metrics from SNMP polling
        try {
          const trafficRes = await fetchApi(
            `/api/metrics/interface?device_ip=${encodeURIComponent(deviceIp)}&hours=${timeRange}&limit=500`
          );
          const trafficData = (trafficRes.metrics || []).filter(m => {
            const mName = m.interface_name || '';
            return mName.endsWith(portNum) || mName === `port${portNum}` || mName === portNum;
          });
          if (trafficData.length > 0) {
            setLatestTraffic(trafficData[0]);
            setTrafficMetrics(trafficData.map(m => ({
              timestamp: new Date(m.recorded_at).getTime(),
              time: new Date(m.recorded_at).toLocaleString(),
              rxBytes: parseInt(m.rx_bytes) || 0,
              txBytes: parseInt(m.tx_bytes) || 0,
              rxBps: parseInt(m.rx_bps) || 0,
              txBps: parseInt(m.tx_bps) || 0,
              rxErrors: parseInt(m.rx_errors) || 0,
              txErrors: parseInt(m.tx_errors) || 0,
            })));
          }
        } catch (trafficErr) {
          console.log("Traffic metrics not available:", trafficErr);
        }

        // Load optical metrics from SNMP polling (only for optical interfaces)
        if (isOptical) {
          try {
            const opticalRes = await fetchApi(
              `/api/metrics/optical?device_ip=${encodeURIComponent(deviceIp)}&hours=${timeRange}`
            );
            const opticalData = (opticalRes.metrics || []).filter(m => {
              const mName = m.interface_name || '';
              return mName.endsWith(portNum) || mName === `port${portNum}`;
            });
            setOpticalMetrics(opticalData.map(m => ({
              timestamp: new Date(m.recorded_at).getTime(),
              time: new Date(m.recorded_at).toLocaleString(),
              txPower: parseFloat(m.tx_power) || null,
              rxPower: parseFloat(m.rx_power) || null,
            })));

            // Load optical thresholds from SNMP polling data
            const thresholdRes = await fetchApi(
              `/api/metrics/optical/thresholds?device_ip=${encodeURIComponent(deviceIp)}&interface_index=${portNum}`
            );
            if (thresholdRes.thresholds && Object.keys(thresholdRes.thresholds).length > 0) {
              const portThresholds = thresholdRes.thresholds[portNum] || 
                                     thresholdRes.thresholds[Object.keys(thresholdRes.thresholds)[0]];
              setOpticalThresholds(portThresholds);
            }
          } catch (opticalErr) {
            console.log("Optical metrics not available:", opticalErr);
          }
        }
      } catch (err) {
        console.error("Failed to load interface metrics:", err);
      } finally {
        setLoading(false);
      }
    };
    loadMetrics();
  }, [deviceIp, portNum, timeRange, isOptical]);

  // Format bytes to human readable
  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Format bps to Mbps
  const formatMbps = (bps) => {
    if (!bps || bps === 0) return '0 Mbps';
    const mbps = bps / 1_000_000;
    if (mbps >= 1000) {
      return (mbps / 1000).toFixed(2) + ' Gbps';
    } else if (mbps >= 1) {
      return mbps.toFixed(2) + ' Mbps';
    } else {
      return (mbps * 1000).toFixed(2) + ' Kbps';
    }
  };

  const hasTraffic = latestTraffic !== null;
  const hasOptical = isOptical && opticalMetrics.length > 0;

  // Calculate shared X-axis bounds for all charts
  const allTimestamps = [
    ...opticalMetrics.map(m => m.timestamp),
    ...trafficMetrics.map(m => m.timestamp)
  ].filter(t => t > 0);
  
  const xMin = allTimestamps.length > 0 ? Math.min(...allTimestamps) : 0;
  const xMax = allTimestamps.length > 0 ? Math.max(...allTimestamps) : 1;
  
  // Generate nice 15-minute tick values (shared across all charts)
  const FIFTEEN_MIN = 15 * 60 * 1000;
  const tickStart = Math.ceil(xMin / FIFTEEN_MIN) * FIFTEEN_MIN;
  const sharedTicks = [];
  for (let t = tickStart; t <= xMax; t += FIFTEEN_MIN) {
    sharedTicks.push(t);
  }

  return (
    <div className="bg-white rounded-xl border border-blue-200 p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-500" />
          Port {portNum} Metrics
        </h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <XCircle className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : !hasTraffic && !hasOptical ? (
        <p className="text-gray-500 text-center py-4">
          No metrics collected yet for port {portNum}. Data will appear after the next polling cycle.
        </p>
      ) : (
        <div className="space-y-6">
          {/* Optical Power Charts - Stacked RX and TX with threshold visualization */}
          {hasOptical && (
            <div className="space-y-4">
              {/* RX Power Chart */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-purple-500" />
                    RX Optical Power
                    {opticalThresholds?.rx_low_alarm && (
                      <span className="text-xs text-gray-400 ml-1">
                        (Safe: {opticalThresholds.rx_low_alarm?.toFixed(1)} to {opticalThresholds.rx_high_alarm?.toFixed(1)} dBm)
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-semibold text-purple-600">
                    {opticalMetrics[0]?.rxPower?.toFixed(2) || '—'} dBm
                  </span>
                </h3>
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    {(() => {
                      const yMin = opticalThresholds?.rx_low_alarm ? Math.min(opticalThresholds.rx_low_alarm - 3, -30) : -30;
                      const yMax = opticalThresholds?.rx_high_alarm ? Math.max(opticalThresholds.rx_high_alarm + 3, 0) : 0;
                      
                      return (
                        <LineChart 
                          data={opticalMetrics}
                          margin={{ top: 5, right: 60, left: 5, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="timestamp" 
                            type="number"
                            domain={[xMin, xMax]}
                            ticks={sharedTicks.length > 0 ? sharedTicks : undefined}
                            tickFormatter={(ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            stroke="#9ca3af"
                            fontSize={10}
                          />
                          <YAxis 
                            stroke="#9ca3af"
                            fontSize={10}
                            tickFormatter={(v) => `${v?.toFixed(1)}`}
                            domain={[yMin, yMax]}
                            label={{ value: 'dBm', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#9ca3af' }}
                          />
                          {opticalThresholds?.rx_high_alarm && (
                            <ReferenceArea x1={xMin} x2={xMax} y1={opticalThresholds.rx_high_alarm} y2={yMax} fill="#ef4444" fillOpacity={0.3} />
                          )}
                          {opticalThresholds?.rx_low_alarm && (
                            <ReferenceArea x1={xMin} x2={xMax} y1={yMin} y2={opticalThresholds.rx_low_alarm} fill="#ef4444" fillOpacity={0.3} />
                          )}
                          {opticalThresholds?.rx_low_alarm && (
                            <ReferenceLine y={opticalThresholds.rx_low_alarm} stroke="#dc2626" strokeWidth={2} label={{ value: `Low: ${opticalThresholds.rx_low_alarm?.toFixed(1)}`, position: 'right', fontSize: 9, fill: '#dc2626' }} />
                          )}
                          {opticalThresholds?.rx_high_alarm && (
                            <ReferenceLine y={opticalThresholds.rx_high_alarm} stroke="#dc2626" strokeWidth={2} label={{ value: `High: ${opticalThresholds.rx_high_alarm?.toFixed(1)}`, position: 'right', fontSize: 9, fill: '#dc2626' }} />
                          )}
                          <Tooltip 
                            labelFormatter={(ts) => new Date(ts).toLocaleString()}
                            formatter={(value) => [`${value?.toFixed(2)} dBm`, 'RX Power']}
                            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                          />
                          <Line type="monotone" dataKey="rxPower" name="RX Power" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3, fill: '#8b5cf6' }} />
                        </LineChart>
                      );
                    })()}
                  </ResponsiveContainer>
                </div>
              </div>

              {/* TX Power Chart */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-500" />
                    TX Optical Power
                    {opticalThresholds?.tx_low_alarm && (
                      <span className="text-xs text-gray-400 ml-1">
                        (Safe: {opticalThresholds.tx_low_alarm?.toFixed(1)} to {opticalThresholds.tx_high_alarm?.toFixed(1)} dBm)
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-semibold text-amber-600">
                    {opticalMetrics[0]?.txPower?.toFixed(2) || '—'} dBm
                  </span>
                </h3>
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    {(() => {
                      const yMin = opticalThresholds?.tx_low_alarm ? Math.min(opticalThresholds.tx_low_alarm - 3, -10) : -10;
                      const yMax = opticalThresholds?.tx_high_alarm ? Math.max(opticalThresholds.tx_high_alarm + 3, 10) : 10;
                      
                      return (
                        <LineChart 
                          data={opticalMetrics}
                          margin={{ top: 5, right: 60, left: 5, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="timestamp" 
                            type="number"
                            domain={[xMin, xMax]}
                            ticks={sharedTicks.length > 0 ? sharedTicks : undefined}
                            tickFormatter={(ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            stroke="#9ca3af"
                            fontSize={10}
                          />
                          <YAxis 
                            stroke="#9ca3af"
                            fontSize={10}
                            tickFormatter={(v) => `${v?.toFixed(1)}`}
                            domain={[yMin, yMax]}
                            label={{ value: 'dBm', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#9ca3af' }}
                          />
                          {opticalThresholds?.tx_high_alarm && (
                            <ReferenceArea x1={xMin} x2={xMax} y1={opticalThresholds.tx_high_alarm} y2={yMax} fill="#ef4444" fillOpacity={0.3} />
                          )}
                          {opticalThresholds?.tx_low_alarm && (
                            <ReferenceArea x1={xMin} x2={xMax} y1={yMin} y2={opticalThresholds.tx_low_alarm} fill="#ef4444" fillOpacity={0.3} />
                          )}
                          {opticalThresholds?.tx_low_alarm && (
                            <ReferenceLine y={opticalThresholds.tx_low_alarm} stroke="#dc2626" strokeWidth={2} label={{ value: `Low: ${opticalThresholds.tx_low_alarm?.toFixed(1)}`, position: 'right', fontSize: 9, fill: '#dc2626' }} />
                          )}
                          {opticalThresholds?.tx_high_alarm && (
                            <ReferenceLine y={opticalThresholds.tx_high_alarm} stroke="#dc2626" strokeWidth={2} label={{ value: `High: ${opticalThresholds.tx_high_alarm?.toFixed(1)}`, position: 'right', fontSize: 9, fill: '#dc2626' }} />
                          )}
                          <Tooltip 
                            labelFormatter={(ts) => new Date(ts).toLocaleString()}
                            formatter={(value) => [`${value?.toFixed(2)} dBm`, 'TX Power']}
                            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                          />
                          <Line type="monotone" dataKey="txPower" name="TX Power" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3, fill: '#f59e0b' }} />
                        </LineChart>
                      );
                    })()}
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* Traffic Statistics Charts - RX and TX separated (showing rate in Mbps) */}
          {hasTraffic && trafficMetrics.length > 0 && (
            <div className="space-y-4">
              {/* RX Traffic Rate Chart */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-green-500" />
                    RX Traffic Rate
                  </div>
                  <span className="text-sm font-semibold text-green-600">
                    {formatMbps(latestTraffic?.rx_bps)}
                  </span>
                </h3>
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart 
                      data={[...trafficMetrics].reverse().filter(m => m.rxBps > 0)}
                      margin={{ top: 5, right: 20, left: 5, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="timestamp" 
                        type="number"
                        domain={[xMin, xMax]}
                        ticks={sharedTicks.length > 0 ? sharedTicks : undefined}
                        tickFormatter={(ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        stroke="#9ca3af"
                        fontSize={10}
                      />
                      <YAxis 
                        stroke="#9ca3af"
                        fontSize={10}
                        tickFormatter={(v) => formatMbps(v)}
                      />
                      <Tooltip 
                        labelFormatter={(ts) => new Date(ts).toLocaleString()}
                        formatter={(value) => [formatMbps(value), 'RX Rate']}
                        contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      />
                      <Line type="monotone" dataKey="rxBps" name="RX Rate" stroke="#22c55e" strokeWidth={2} dot={{ r: 3, fill: '#22c55e' }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* TX Traffic Rate Chart */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-500" />
                    TX Traffic Rate
                  </div>
                  <span className="text-sm font-semibold text-blue-600">
                    {formatMbps(latestTraffic?.tx_bps)}
                  </span>
                </h3>
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart 
                      data={[...trafficMetrics].reverse().filter(m => m.txBps > 0)}
                      margin={{ top: 5, right: 20, left: 5, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="timestamp" 
                        type="number"
                        domain={[xMin, xMax]}
                        ticks={sharedTicks.length > 0 ? sharedTicks : undefined}
                        tickFormatter={(ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        stroke="#9ca3af"
                        fontSize={10}
                      />
                      <YAxis 
                        stroke="#9ca3af"
                        fontSize={10}
                        tickFormatter={(v) => formatMbps(v)}
                      />
                      <Tooltip 
                        labelFormatter={(ts) => new Date(ts).toLocaleString()}
                        formatter={(value) => [formatMbps(value), 'TX Rate']}
                        contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      />
                      <Line type="monotone" dataKey="txBps" name="TX Rate" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Traffic Counters & Errors - Always visible */}
              <div className="grid grid-cols-4 gap-3 text-sm">
                <div className="bg-green-50 rounded-lg p-3">
                  <p className="text-gray-500 text-xs">RX Packets</p>
                  <p className="font-semibold text-green-700">{latestTraffic?.rx_packets?.toLocaleString() || '—'}</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-gray-500 text-xs">TX Packets</p>
                  <p className="font-semibold text-blue-700">{latestTraffic?.tx_packets?.toLocaleString() || '—'}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500 text-xs">RX Errors</p>
                  <p className={cn("font-semibold", (latestTraffic?.rx_errors || 0) > 0 && "text-red-600")}>
                    {latestTraffic?.rx_errors?.toLocaleString() || 0}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500 text-xs">RX Discards</p>
                  <p className={cn("font-semibold", (latestTraffic?.rx_discards || 0) > 0 && "text-amber-600")}>
                    {latestTraffic?.rx_discards?.toLocaleString() || 0}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Time range options for charts
const TIME_RANGES = [
  { label: "1h", hours: 1 },
  { label: "6h", hours: 6 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
];

export function DeviceDetail() {
  const { ip } = useParams();
  const navigate = useNavigate();
  
  // Device info from NetBox cache
  const [device, setDevice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Interfaces from NetBox
  const [interfaces, setInterfaces] = useState([]);
  const [interfacesLoading, setInterfacesLoading] = useState(false);
  
  // Metrics data
  const [opticalMetrics, setOpticalMetrics] = useState([]);
  const [availabilityMetrics, setAvailabilityMetrics] = useState([]);
  const [metricsLoading, setMetricsLoading] = useState(false);
  
  // Alarms
  const [alarms, setAlarms] = useState([]);
  const [alarmsLoading, setAlarmsLoading] = useState(false);
  
  // UI state
  const [timeRange, setTimeRange] = useState(24);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedInterface, setSelectedInterface] = useState(null);

  // Load device from NetBox cache
  const loadDevice = useCallback(async () => {
    if (!ip) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetchApi(`/api/netbox/devices/cached?q=${encodeURIComponent(ip)}`);
      
      if (res.success && res.data?.length > 0) {
        // Find exact IP match
        const found = res.data.find(d => {
          const deviceIp = d.primary_ip4?.address?.split('/')[0];
          return deviceIp === ip;
        });
        
        if (found) {
          setDevice({
            id: found.id,
            name: found.name,
            ip: found.primary_ip4?.address?.split('/')[0],
            site: found.site?.name,
            role: found.role?.name,
            deviceType: found.device_type?.model,
            manufacturer: found.device_type?.manufacturer?.name,
            status: found.status?.value || 'active',
            statusLabel: found.status?.label || 'Active',
          });
        } else {
          setError("Device not found in NetBox");
        }
      } else {
        setError("Device not found");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [ip]);

  // Load optical metrics
  const loadOpticalMetrics = useCallback(async () => {
    if (!ip) return;
    
    setMetricsLoading(true);
    try {
      const res = await fetchApi(`/api/metrics/optical?device_ip=${encodeURIComponent(ip)}&hours=${timeRange}`);
      // API returns { metrics: [...], count: N } not { success, data }
      const metrics = res.metrics || res.data || [];
      if (metrics.length > 0) {
        const data = metrics.map(m => ({
          timestamp: new Date(m.recorded_at).getTime(),
          time: new Date(m.recorded_at).toLocaleString(),
          txPower: parseFloat(m.tx_power) || null,
          rxPower: parseFloat(m.rx_power) || null,
          interface: m.interface_name,
        }));
        setOpticalMetrics(data);
      }
    } catch (err) {
      console.error("Failed to load optical metrics:", err);
    } finally {
      setMetricsLoading(false);
    }
  }, [ip, timeRange]);

  // Check if device is Ciena (supports SNMP alarms)
  const isCienaDevice = device?.manufacturer?.toLowerCase().includes('ciena') || 
                        device?.deviceType?.toLowerCase().includes('3942') ||
                        device?.deviceType?.toLowerCase().includes('5160');

  // Load alarms via SNMP (only for Ciena devices)
  const loadAlarms = useCallback(async () => {
    if (!ip || !isCienaDevice) {
      setAlarms([]);
      setAlarmsLoading(false);
      return;
    }
    
    setAlarmsLoading(true);
    try {
      const res = await fetchApi(`/api/snmp/alarms/${encodeURIComponent(ip)}`);
      const alarmsData = res.data?.alarms || res.alarms || [];
      setAlarms(alarmsData);
    } catch (err) {
      console.error("Failed to load alarms:", err);
      setAlarms([]);
    } finally {
      setAlarmsLoading(false);
    }
  }, [ip, isCienaDevice]);

  // Load availability metrics
  const loadAvailabilityMetrics = useCallback(async () => {
    if (!ip) return;
    
    try {
      const res = await fetchApi(`/api/metrics/availability?device_ip=${encodeURIComponent(ip)}&hours=${timeRange}`);
      // API returns { metrics: [...], count: N } not { success, data }
      const metrics = res.metrics || res.data || [];
      if (metrics.length > 0) {
        const data = metrics.map(m => ({
          timestamp: new Date(m.recorded_at).getTime(),
          time: new Date(m.recorded_at).toLocaleString(),
          status: m.ping_status === 'up' ? 1 : 0,
          latency: parseFloat(m.ping_latency_ms) || 0,
        }));
        setAvailabilityMetrics(data);
      }
    } catch (err) {
      console.error("Failed to load availability metrics:", err);
    }
  }, [ip, timeRange]);

  // Load interfaces from NetBox
  const loadInterfaces = useCallback(async () => {
    if (!device?.id) return;
    
    setInterfacesLoading(true);
    try {
      const res = await fetchApi(`/api/netbox/devices/${device.id}/interfaces`);
      if (res.success && res.data) {
        // Sort interfaces by name naturally
        const sorted = res.data.sort((a, b) => {
          const aNum = parseInt(a.name) || 0;
          const bNum = parseInt(b.name) || 0;
          if (aNum && bNum) return aNum - bNum;
          return a.name.localeCompare(b.name);
        });
        setInterfaces(sorted);
      }
    } catch (err) {
      console.error("Failed to load interfaces:", err);
    } finally {
      setInterfacesLoading(false);
    }
  }, [device?.id]);

  useEffect(() => {
    loadDevice();
  }, [loadDevice]);

  useEffect(() => {
    if (device) {
      loadOpticalMetrics();
      loadAvailabilityMetrics();
      loadInterfaces();
      loadAlarms();
    }
  }, [device, timeRange, loadOpticalMetrics, loadAvailabilityMetrics, loadInterfaces, loadAlarms]);

  const handleRefresh = () => {
    loadDevice();
    loadOpticalMetrics();
    loadAvailabilityMetrics();
    loadInterfaces();
    loadAlarms();
  };

  const openInNetBox = () => {
    if (device?.id) {
      window.open(`http://192.168.10.51:8000/dcim/devices/${device.id}/`, '_blank');
    }
  };

  // Calculate availability percentage
  const availabilityPercent = availabilityMetrics.length > 0
    ? ((availabilityMetrics.filter(m => m.status === 1).length / availabilityMetrics.length) * 100).toFixed(1)
    : null;

  // Calculate average latency
  const avgLatency = availabilityMetrics.length > 0
    ? (availabilityMetrics.reduce((sum, m) => sum + (m.latency || 0), 0) / availabilityMetrics.filter(m => m.latency).length).toFixed(1)
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !device) {
    return (
      <div className="p-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error || "Device not found"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{device.name}</h1>
            <p className="text-gray-500">{device.ip}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <RefreshCw className={cn("w-4 h-4", metricsLoading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={openInNetBox}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <ExternalLink className="w-4 h-4" />
            View in NetBox
          </button>
        </div>
      </div>

      {/* Active Alarms Card - Compact single row per alarm (Ciena devices only) */}
      {isCienaDevice && alarms.length > 0 && (
        <div className={cn(
          "rounded-lg border px-4 py-2",
          alarms.some(a => a.severity === 'critical') ? "bg-red-50 border-red-300" :
          alarms.some(a => a.severity === 'major') ? "bg-orange-50 border-orange-300" :
          alarms.some(a => a.severity === 'minor') ? "bg-yellow-50 border-yellow-300" :
          "bg-amber-50 border-amber-300"
        )}>
          <div className="flex items-center gap-3 flex-wrap">
            <Bell className={cn(
              "w-5 h-5",
              alarms.some(a => a.severity === 'critical') ? "text-red-600" :
              alarms.some(a => a.severity === 'major') ? "text-orange-600" :
              alarms.some(a => a.severity === 'minor') ? "text-yellow-600" :
              "text-amber-600"
            )} />
            <span className="font-semibold text-gray-900">Active Alarms ({alarms.length}):</span>
            {alarms.map((alarm, idx) => (
              <span key={idx} className={cn(
                "inline-flex items-center gap-1 text-xs px-2 py-1 rounded",
                alarm.severity === 'critical' ? "bg-red-200 text-red-800" :
                alarm.severity === 'major' ? "bg-orange-200 text-orange-800" :
                alarm.severity === 'minor' ? "bg-yellow-200 text-yellow-800" :
                "bg-amber-200 text-amber-800"
              )}>
                <span className="font-semibold uppercase">{alarm.severity}</span>
                <span>—</span>
                <span>{alarm.description || 'Unknown'}</span>
                {alarm.object_instance && <span className="text-gray-500">(Port {alarm.object_instance})</span>}
              </span>
            ))}
            {alarmsLoading && <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />}
          </div>
        </div>
      )}

      {/* No Alarms - Show green status (Ciena devices only) */}
      {isCienaDevice && !alarmsLoading && alarms.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <span className="text-green-800 font-medium">No Active Alarms</span>
        </div>
      )}

      {/* Device Info - Compact single row */}
      <div className="bg-white rounded-lg border border-gray-200 px-4 py-2 flex items-center gap-6 text-sm flex-wrap">
        <span className="flex items-center gap-1">
          <MapPin className="w-4 h-4 text-gray-400" />
          <span className="text-gray-500">Site:</span>
          <span className="font-medium">{device.site || "—"}</span>
        </span>
        <span className="flex items-center gap-1">
          <Tag className="w-4 h-4 text-gray-400" />
          <span className="text-gray-500">Role:</span>
          <span className="font-medium">{device.role || "—"}</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="text-gray-500">Type:</span>
          <span className="font-medium">{device.manufacturer} {device.deviceType || "—"}</span>
        </span>
        <span className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
          device.status === 'active' ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700"
        )}>
          {device.status === 'active' ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
          {device.statusLabel}
        </span>
      </div>

      {/* Interfaces Section - Compact */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-2 border-b border-gray-100 flex items-center justify-between">
          <span className="font-medium text-sm">Interfaces ({interfaces.length})</span>
          {interfacesLoading && <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />}
        </div>
        {interfaces.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="border-b border-gray-200">
                  <th className="text-left py-1.5 px-3 font-medium text-gray-500">Port</th>
                  <th className="text-left py-1.5 px-3 font-medium text-gray-500">Type</th>
                  <th className="text-left py-1.5 px-3 font-medium text-gray-500">Speed</th>
                  <th className="text-left py-1.5 px-3 font-medium text-gray-500">Description</th>
                  <th className="text-left py-1.5 px-3 font-medium text-gray-500">Connected To</th>
                </tr>
              </thead>
              <tbody>
                {interfaces.map((iface, i) => (
                  <tr 
                    key={iface.id || i} 
                    className={cn(
                      "border-b border-gray-50 hover:bg-blue-50 cursor-pointer",
                      selectedInterface?.id === iface.id && "bg-blue-100"
                    )}
                    onClick={() => setSelectedInterface(iface)}
                  >
                    <td className="py-1 px-3 font-medium">{iface.name}</td>
                    <td className="py-1 px-3 text-gray-600">{iface.type?.label || iface.type?.value || '—'}</td>
                    <td className="py-1 px-3 text-gray-600">
                      {iface.speed ? `${(iface.speed / 1000).toFixed(0)}G` : '—'}
                    </td>
                    <td className="py-1 px-3 text-gray-500 max-w-xs truncate">
                      {iface.description || '—'}
                    </td>
                    <td className="py-1 px-3 text-gray-600">
                      {iface.connected_endpoints?.length > 0 
                        ? iface.connected_endpoints.map(e => e.device?.name || e.name).join(', ')
                        : iface.link_peers?.length > 0
                          ? iface.link_peers.map(p => p.device?.name || p.name).join(', ')
                          : '—'
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-2 text-sm">No interfaces found</p>
        )}
      </div>

      {/* Selected Interface Metrics */}
      {selectedInterface && (
        <InterfaceMetricsPanel 
          deviceIp={ip} 
          interfaceName={selectedInterface.name}
          timeRange={timeRange}
          isOptical={/sfp|xfp|qsfp|optical|fiber|1000base-x|10gbase/i.test(selectedInterface.type?.label || selectedInterface.type?.value || '')}
          onClose={() => setSelectedInterface(null)}
        />
      )}

      {/* Time Range Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Time Range:</span>
        {TIME_RANGES.map(range => (
          <button
            key={range.hours}
            onClick={() => setTimeRange(range.hours)}
            className={cn(
              "px-3 py-1 rounded-lg text-sm font-medium transition-colors",
              timeRange === range.hours
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {range.label}
          </button>
        ))}
      </div>

      {/* No Data Message */}
      {opticalMetrics.length === 0 && !metricsLoading && (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-700 mb-2">No Metrics Data</h3>
          <p className="text-gray-500">
            No optical or availability metrics found for this device in the selected time range.
          </p>
        </div>
      )}
    </div>
  );
}

export default DeviceDetail;
