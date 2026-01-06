import React, { useState, useEffect, useCallback } from "react";
import { PageLayout, PageHeader } from "../../components/layout";
import { fetchApi } from "../../lib/utils";
import { 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle,
  XCircle,
  Clock,
  Server,
  Filter
} from "lucide-react";

function SeverityBadge({ severity }) {
  const colors = {
    critical: 'bg-red-100 text-red-800 border-red-200',
    major: 'bg-orange-100 text-orange-800 border-orange-200',
    minor: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    warning: 'bg-amber-100 text-amber-800 border-amber-200',
    cleared: 'bg-green-100 text-green-800 border-green-200',
    indeterminate: 'bg-gray-100 text-gray-800 border-gray-200',
    unknown: 'bg-gray-100 text-gray-800 border-gray-200',
  };
  
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${colors[severity] || colors.unknown}`}>
      {severity}
    </span>
  );
}

function SeverityIcon({ severity }) {
  const iconClass = {
    critical: 'text-red-500',
    major: 'text-orange-500',
    minor: 'text-yellow-500',
    warning: 'text-amber-500',
  };
  
  return <AlertTriangle className={`w-4 h-4 ${iconClass[severity] || 'text-gray-400'}`} />;
}

export function SNMPAlarmsPage() {
  const [devices, setDevices] = useState([]);
  const [allAlarms, setAllAlarms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [community, setCommunity] = useState('public');
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      const response = await fetchApi('/inventory/v1/devices?limit=100');
      const devData = response?.data || response;
      const deviceList = devData?.items || [];
      setDevices(deviceList);
    } catch (err) {
      console.error('Failed to load devices:', err);
    }
  };

  const pollAllDevices = useCallback(async () => {
    if (devices.length === 0) return;
    
    setLoading(true);
    setError(null);
    
    const alarms = [];
    let successCount = 0;
    let errorCount = 0;
    
    // Poll devices in batches of 5
    const batchSize = 5;
    for (let i = 0; i < devices.length; i += batchSize) {
      const batch = devices.slice(i, i + batchSize);
      
      const results = await Promise.allSettled(
        batch.map(device => 
          fetchApi(`/monitoring/v1/snmp/alarms/${device.ip_address}?community=${community}`)
            .then(res => ({ device, data: res.data }))
        )
      );
      
      results.forEach(result => {
        if (result.status === 'fulfilled') {
          successCount++;
          const { device, data } = result.value;
          if (data.alarms && data.alarms.length > 0) {
            data.alarms.forEach(alarm => {
              alarms.push({
                ...alarm,
                device_name: device.name,
                device_ip: device.ip_address,
              });
            });
          }
        } else {
          errorCount++;
        }
      });
    }
    
    // Sort by severity (critical first)
    const severityOrder = { critical: 0, major: 1, minor: 2, warning: 3, indeterminate: 4, cleared: 5, unknown: 6 };
    alarms.sort((a, b) => (severityOrder[a.severity] || 6) - (severityOrder[b.severity] || 6));
    
    setAllAlarms(alarms);
    setLastUpdate(new Date());
    setLoading(false);
    
    if (errorCount > 0) {
      setError(`Polled ${successCount} devices, ${errorCount} failed`);
    }
  }, [devices, community]);

  const filteredAlarms = filterSeverity === 'all' 
    ? allAlarms 
    : allAlarms.filter(a => a.severity === filterSeverity);

  const severityCounts = allAlarms.reduce((acc, alarm) => {
    acc[alarm.severity] = (acc[alarm.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="SNMP Active Alarms"
        description="Real-time alarms from all Ciena devices"
        icon={AlertTriangle}
        actions={
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={community}
              onChange={(e) => setCommunity(e.target.value)}
              className="w-32 px-3 py-2 text-sm border border-gray-300 rounded-lg"
              placeholder="Community"
            />
            <button
              onClick={pollAllDevices}
              disabled={loading || devices.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Poll All Devices ({devices.length})
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <button
            onClick={() => setFilterSeverity('all')}
            className={`p-4 rounded-lg border text-left transition-colors ${
              filterSeverity === 'all' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
            }`}
          >
            <div className="text-2xl font-bold text-gray-900">{allAlarms.length}</div>
            <div className="text-sm text-gray-500">Total Alarms</div>
          </button>
          
          {['critical', 'major', 'minor', 'warning'].map(sev => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`p-4 rounded-lg border text-left transition-colors ${
                filterSeverity === sev ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-2">
                <SeverityIcon severity={sev} />
                <span className="text-2xl font-bold text-gray-900">{severityCounts[sev] || 0}</span>
              </div>
              <div className="text-sm text-gray-500 capitalize">{sev}</div>
            </button>
          ))}
          
          <div className="p-4 rounded-lg border border-gray-200 bg-white">
            <div className="text-2xl font-bold text-green-600">{devices.length}</div>
            <div className="text-sm text-gray-500">Devices</div>
          </div>
        </div>

        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            <span className="text-yellow-700">{error}</span>
          </div>
        )}

        {/* Alarms Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              {filterSeverity === 'all' ? 'All Alarms' : `${filterSeverity} Alarms`}
              {filteredAlarms.length > 0 && ` (${filteredAlarms.length})`}
            </h2>
            {lastUpdate && (
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
            )}
          </div>

          {filteredAlarms.length === 0 ? (
            <div className="p-12 text-center">
              {allAlarms.length === 0 && !loading ? (
                <>
                  <Server className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Alarms Loaded</h3>
                  <p className="text-gray-500 mb-4">Click "Poll All Devices" to fetch active alarms from all switches.</p>
                </>
              ) : (
                <>
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No {filterSeverity} Alarms</h3>
                  <p className="text-gray-500">
                    {filterSeverity === 'all' 
                      ? 'All systems are operating normally.' 
                      : `No alarms with ${filterSeverity} severity.`}
                  </p>
                </>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Object</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredAlarms.map((alarm, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <SeverityBadge severity={alarm.severity} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{alarm.device_name}</div>
                        <div className="text-xs text-gray-500">{alarm.device_ip}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-gray-900">{alarm.description}</div>
                        {alarm.object_instance && (
                          <div className="text-xs text-blue-600 font-mono truncate max-w-xs">{alarm.object_instance}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{alarm.object_class}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{alarm.timestamp || '-'}</td>
                      <td className="px-4 py-3">
                        {alarm.acknowledged ? (
                          <span className="flex items-center gap-1 text-green-600 text-sm">
                            <CheckCircle className="w-3 h-3" />
                            Acknowledged
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-orange-600 text-sm">
                            <XCircle className="w-3 h-3" />
                            Active
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

export default SNMPAlarmsPage;
