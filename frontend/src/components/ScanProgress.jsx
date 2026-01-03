import { Play, RefreshCw, Settings, Network, Server, Terminal, Globe, Trash2, X, Filter } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { cn, fetchApi } from "../lib/utils";

export function ScanProgress({ progress, onStartScan, onRefresh, onOpenSettings, onSNMPScan, onSSHScan, onDeleteSelected }) {
  const navigate = useNavigate();
  const [showScanModal, setShowScanModal] = useState(false);
  const [networkRange, setNetworkRange] = useState("10.127.0.0/24");
  const isScanning = progress.status === "scanning";
  const percentage = progress.total > 0 
    ? Math.round((progress.scanned / progress.total) * 100) 
    : 0;

  const handleSNMPScan = async () => {
    try {
      const result = await fetchApi("/snmp_scan", { 
        method: "POST", 
        body: JSON.stringify({}) 
      });
      alert(`SNMP scan started: ${result.message || 'Started'}`);
    } catch (err) {
      console.error("SNMP scan failed:", err);
      if (err.message?.includes('409')) {
        alert("Scan already in progress. Please wait for the current scan to complete.");
      } else {
        alert("SNMP scan failed: " + err.message);
      }
    }
  };

  const handleSSHScan = async () => {
    try {
      const result = await fetchApi("/ssh_scan", { 
        method: "POST", 
        body: JSON.stringify({}) 
      });
      alert(`SSH scan started: ${result.message || 'Started'}`);
    } catch (err) {
      console.error("SSH scan failed:", err);
      if (err.message?.includes('409')) {
        alert("Scan already in progress. Please wait for the current scan to complete.");
      } else {
        alert("SSH scan failed: " + err.message);
      }
    }
  };

  const handleStartScan = () => {
    setShowScanModal(true);
  };

  const executeScan = async () => {
    if (!networkRange.trim()) {
      alert("Please enter a network range");
      return;
    }
    
    try {
      const result = await fetchApi("/scan", { 
        method: "POST", 
        body: JSON.stringify({ network_range: networkRange.trim() })
      });
      setShowScanModal(false);
      if (onStartScan) onStartScan();
      alert(`Network scan started: ${result.message || 'Started'}`);
    } catch (err) {
      console.error("Scan failed:", err);
      if (err.message?.includes('409')) {
        alert("Scan already in progress. Please wait for the current scan to complete.");
      } else {
        alert("Scan failed: " + err.message);
      }
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex flex-col gap-3">
        {/* Title */}
        <h1 className="text-xl font-bold text-gray-800">Network Scan Results</h1>
        
        {/* Main button row */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleStartScan}
            disabled={isScanning}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
              isScanning
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            )}
          >
            <Play className="w-4 h-4" />
            {isScanning ? "Scanning..." : "SCAN"}
          </button>

          <button
            onClick={handleSNMPScan}
            disabled={isScanning}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
              isScanning
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-green-600 text-white hover:bg-green-700"
            )}
          >
            <Server className="w-4 h-4" />
            SNMP
          </button>

          <button
            onClick={handleSSHScan}
            disabled={isScanning}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
              isScanning
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-purple-600 text-white hover:bg-purple-700"
            )}
          >
            <Terminal className="w-4 h-4" />
            SSH
          </button>

          <button
            onClick={() => navigate("/topology")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-orange-600 text-white hover:bg-orange-700 transition-colors"
          >
            <Globe className="w-4 h-4" />
            LLDP
          </button>

          <button
            onClick={() => navigate("/settings")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            <Settings className="w-4 h-4" />
            SETTINGS
          </button>

          <button
            onClick={() => navigate("/scheduler")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
          >
            <Network className="w-4 h-4" />
            SCHEDULER
          </button>

          <button
            onClick={() => navigate("/power-trends")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-yellow-600 text-white hover:bg-yellow-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            POWER TRENDS
          </button>

          <button
            onClick={onDeleteSelected}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            DELETE SELECTED
          </button>
        </div>

        {/* Progress bar section */}
        {isScanning && (
          <div className="flex items-center gap-4 mt-2">
            <div className="flex-1 max-w-md">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${percentage}%` }}
                ></div>
              </div>
              <div className="text-sm text-gray-600 mt-1">
                {progress.scanned} / {progress.total} scanned ({progress.online} online)
              </div>
            </div>
            <button
              onClick={onRefresh}
              className="flex items-center gap-2 px-3 py-1 rounded-lg text-sm border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
        )}

        {/* Scan Modal */}
        {showScanModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Fast Network Scan (Ports + Hostnames)</h2>
                <button
                  onClick={() => setShowScanModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Network Range:
                </label>
                <input
                  type="text"
                  value={networkRange}
                  onChange={(e) => setNetworkRange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., 10.127.0.0/24"
                />
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={executeScan}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Start Scan
                </button>
                <button
                  onClick={() => setShowScanModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
