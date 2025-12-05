import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  TrendingUp,
  Activity,
  Zap,
  Thermometer,
  RefreshCw,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
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

export function PowerTrends() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState(null);
  const [interfaces, setInterfaces] = useState([]);
  const [selectedInterfaces, setSelectedInterfaces] = useState(new Set());
  const [powerHistory, setPowerHistory] = useState([]);
  const [timeRange, setTimeRange] = useState(24);
  const [showCharts, setShowCharts] = useState(false);
  const [stats, setStats] = useState([]);
  
  const powerChartRef = useRef(null);
  const temperatureChartRef = useRef(null);

  useEffect(() => {
    loadInterfaces();
  }, []);

  const loadInterfaces = async () => {
    try {
      setLoading(true);
      const ipsParam = searchParams.get('ips');
      let ipList = [];
      
      try {
        ipList = JSON.parse(decodeURIComponent(ipsParam || '[]'));
      } catch (e) {
        ipList = [];
      }

      if (ipList.length === 0) {
        setError('No devices selected');
        return;
      }

      const response = await fetch('/power_history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ip_list: ipList,
          hours: 1  // Just to get interfaces
        }),
      });
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Get unique interfaces from history
      const interfaceMap = new Map();
      data.history.forEach(reading => {
        const key = `${reading.ip_address}:${reading.interface_index}`;
        if (!interfaceMap.has(key)) {
          interfaceMap.set(key, {
            ip_address: reading.ip_address,
            interface_index: reading.interface_index,
            interface_name: reading.interface_name,
            cli_port: reading.cli_port,
            has_data: true,
            key,
          });
        }
      });
      
      const allInterfaces = Array.from(interfaceMap.values());
      setInterfaces(allInterfaces);
      
      if (allInterfaces.length === 0) {
        setError('No optical interfaces found or no power data available. Make sure to run an SSH scan on devices with optical transceivers first.');
      }
      
    } catch (err) {
      setError('Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleInterface = (interfaceKey) => {
    const newSelected = new Set(selectedInterfaces);
    if (newSelected.has(interfaceKey)) {
      newSelected.delete(interfaceKey);
    } else {
      newSelected.add(interfaceKey);
    }
    setSelectedInterfaces(newSelected);
  };

  const loadPowerHistory = async () => {
    if (selectedInterfaces.size === 0) {
      alert('Please select at least one interface first');
      return;
    }
    
    try {
      setLoadingData(true);
      const ipsParam = searchParams.get('ips');
      let ipList = [];
      
      try {
        ipList = JSON.parse(decodeURIComponent(ipsParam || '[]'));
      } catch (e) {
        ipList = [];
      }
      
      const response = await fetch('/power_history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ip_list: ipList,
          hours: timeRange
        }),
      });
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Filter data for selected interfaces
      const filteredData = data.history.filter(reading => {
        const key = `${reading.ip_address}:${reading.interface_index}`;
        return selectedInterfaces.has(key);
      });
      
      if (filteredData.length === 0) {
        alert('No power data found for selected interfaces in the specified time range');
        return;
      }
      
      setPowerHistory(filteredData);
      processChartData(filteredData);
      setShowCharts(true);
      
    } catch (err) {
      alert('Error loading power data: ' + err.message);
    } finally {
      setLoadingData(false);
    }
  };

  const processChartData = (data) => {
    // Group data by interface
    const interfaceData = {};
    const interfaceStats = {};
    
    data.forEach(reading => {
      const key = `${reading.interface_name} (${reading.ip_address})`;
      if (!interfaceData[key]) {
        interfaceData[key] = {
          labels: [],
          txPower: [],
          rxPower: [],
          temperature: []
        };
        interfaceStats[key] = {
          txValues: [],
          rxValues: [],
          tempValues: []
        };
      }
      
      const timestamp = new Date(reading.measurement_timestamp);
      interfaceData[key].labels.push(timestamp);
      interfaceData[key].txPower.push(reading.tx_power);
      interfaceData[key].rxPower.push(reading.rx_power);
      interfaceData[key].temperature.push(reading.temperature);
      
      if (reading.tx_power !== null) interfaceStats[key].txValues.push(reading.tx_power);
      if (reading.rx_power !== null) interfaceStats[key].rxValues.push(reading.rx_power);
      if (reading.temperature !== null) interfaceStats[key].tempValues.push(reading.temperature);
    });
    
    // Create stats
    const statsArray = [];
    Object.keys(interfaceStats).forEach(iface => {
      const stats = interfaceStats[iface];
      
      if (stats.txValues.length > 0) {
        const txAvg = (stats.txValues.reduce((a, b) => a + b, 0) / stats.txValues.length).toFixed(2);
        const txMin = Math.min(...stats.txValues).toFixed(2);
        const txMax = Math.max(...stats.txValues).toFixed(2);
        
        statsArray.push({
          label: `${iface} - TX Power`,
          value: `${txAvg} dBm`,
          details: `Min: ${txMin} dBm | Max: ${txMax} dBm`,
        });
      }
      
      if (stats.rxValues.length > 0) {
        const rxAvg = (stats.rxValues.reduce((a, b) => a + b, 0) / stats.rxValues.length).toFixed(2);
        const rxMin = Math.min(...stats.rxValues).toFixed(2);
        const rxMax = Math.max(...stats.rxValues).toFixed(2);
        
        statsArray.push({
          label: `${iface} - RX Power`,
          value: `${rxAvg} dBm`,
          details: `Min: ${rxMin} dBm | Max: ${rxMax} dBm`,
        });
      }
    });
    
    setStats(statsArray);
  };

  const getPowerChartData = () => {
    if (powerHistory.length === 0) return null;
    
    // Group data by interface
    const interfaceData = {};
    powerHistory.forEach(reading => {
      const key = `${reading.interface_name} (${reading.ip_address})`;
      if (!interfaceData[key]) {
        interfaceData[key] = {
          labels: [],
          txPower: [],
          rxPower: [],
        };
      }
      
      const timestamp = new Date(reading.measurement_timestamp);
      interfaceData[key].labels.push(timestamp);
      interfaceData[key].txPower.push(reading.tx_power);
      interfaceData[key].rxPower.push(reading.rx_power);
    });
    
    const datasets = [];
    const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#fd7e14'];
    
    Object.keys(interfaceData).forEach((iface, index) => {
      const color = colors[index % colors.length];
      
      // TX Power dataset
      datasets.push({
        label: `${iface} - TX Power`,
        data: interfaceData[iface].txPower,
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.1,
        yAxisID: 'y',
      });
      
      // RX Power dataset
      datasets.push({
        label: `${iface} - RX Power`,
        data: interfaceData[iface].rxPower,
        borderColor: color,
        backgroundColor: color + '40',
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.1,
        yAxisID: 'y',
      });
    });
    
    const firstInterface = Object.keys(interfaceData)[0];
    
    return {
      labels: interfaceData[firstInterface]?.labels || [],
      datasets,
    };
  };

  const getTemperatureChartData = () => {
    if (powerHistory.length === 0) return null;
    
    // Group data by interface
    const interfaceData = {};
    powerHistory.forEach(reading => {
      const key = `${reading.interface_name} (${reading.ip_address})`;
      if (!interfaceData[key]) {
        interfaceData[key] = {
          labels: [],
          temperature: [],
        };
      }
      
      const timestamp = new Date(reading.measurement_timestamp);
      interfaceData[key].labels.push(timestamp);
      interfaceData[key].temperature.push(reading.temperature);
    });
    
    const datasets = [];
    const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#fd7e14'];
    
    Object.keys(interfaceData).forEach((iface, index) => {
      const color = colors[index % colors.length];
      
      datasets.push({
        label: `${iface} - Temperature`,
        data: interfaceData[iface].temperature,
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.1,
        yAxisID: 'y',
      });
    });
    
    const firstInterface = Object.keys(interfaceData)[0];
    
    return {
      labels: interfaceData[firstInterface]?.labels || [],
      datasets,
    };
  };

  const powerChartData = getPowerChartData();
  const temperatureChartData = getTemperatureChartData();
  const hasTempData = temperatureChartData?.datasets.some(d => d.data.some(v => v !== null));

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      title: {
        display: true,
        text: 'Optical Transceiver Power Levels',
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
      tooltip: {
        callbacks: {
          title: (context) => new Date(context[0].parsed.x).toLocaleString(),
          label: (context) => {
            let label = context.dataset.label || '';
            if (label) label += ': ';
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(2) + ' dBm';
            }
            return label;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time',
        time: {
          displayFormats: {
            hour: 'MMM dd HH:mm',
            minute: 'HH:mm',
          },
          tooltipFormat: 'MMM dd, yyyy HH:mm:ss',
        },
        title: {
          display: true,
          text: 'Measurement Time',
          font: {
            size: 14,
            weight: 'bold',
          },
        },
      },
      y: {
        title: {
          display: true,
          text: 'Optical Power (dBm)',
          font: {
            size: 14,
            weight: 'bold',
          },
        },
        ticks: {
          callback: (value) => value.toFixed(1) + ' dBm',
        },
      },
    },
  };

  const temperatureChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Temperature (°C)',
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
    },
    scales: {
      x: {
        type: 'time',
        time: {
          displayFormats: {
            hour: 'MMM dd HH:mm',
          },
        },
        title: {
          display: true,
          text: 'Time',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Temperature (°C)',
        },
        ticks: {
          callback: (value) => value.toFixed(1) + ' °C',
        },
      },
    },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-gray-600">Loading optical interfaces...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle className="w-6 h-6" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/")}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Main
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                Optical Power Trends
              </h1>
              <p className="text-sm text-gray-600">
                Analyze optical transceiver power levels and temperature trends over time
              </p>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4 mt-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Time Range:</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(parseInt(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>Last 1 Hour</option>
              <option value={6}>Last 6 Hours</option>
              <option value={24}>Last 24 Hours</option>
              <option value={168}>Last 7 Days</option>
              <option value={720}>Last 30 Days</option>
            </select>
          </div>
          <button
            onClick={loadInterfaces}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh Interfaces
          </button>
          <button
            onClick={loadPowerHistory}
            disabled={selectedInterfaces.size === 0 || loadingData}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loadingData ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Loading...
              </>
            ) : (
              <>
                <Activity className="w-4 h-4" />
                Load Power Data
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-4">
        {/* Interface Selection */}
        {interfaces.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-600" />
              Select Optical Interfaces ({selectedInterfaces.size} selected)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {interfaces.map((iface) => (
                <div
                  key={iface.key}
                  onClick={() => toggleInterface(iface.key)}
                  className={cn(
                    "p-3 border rounded-lg cursor-pointer transition-all hover:shadow-md",
                    selectedInterfaces.has(iface.key)
                      ? "border-blue-500 bg-blue-50 shadow-sm"
                      : "border-gray-200 hover:border-gray-300"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-semibold text-gray-800 text-sm">
                        {iface.interface_name}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">
                        <div>IP: {iface.ip_address}</div>
                        <div>Port: {iface.cli_port}</div>
                      </div>
                    </div>
                    <div className="ml-2">
                      {iface.has_data ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    {iface.has_data ? 'Has power data' : 'No data'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Charts Section */}
        {showCharts && powerChartData && (
          <div className="space-y-4">
            {/* Statistics */}
            {stats.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" />
                  Statistics Summary
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {stats.map((stat, index) => (
                    <div key={index} className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                      <div className="text-xs text-gray-600 mb-1">{stat.label}</div>
                      <div className="text-lg font-bold text-gray-800">{stat.value}</div>
                      <div className="text-xs text-gray-500">{stat.details}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Power Chart */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-600" />
                Optical Power Levels
              </h3>
              <div className="h-96">
                <Line ref={powerChartRef} data={powerChartData} options={chartOptions} />
              </div>
            </div>

            {/* Temperature Chart */}
            {hasTempData && temperatureChartData && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Thermometer className="w-5 h-5 text-red-600" />
                  Temperature Trends
                </h3>
                <div className="h-96">
                  <Line ref={temperatureChartRef} data={temperatureChartData} options={temperatureChartOptions} />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
