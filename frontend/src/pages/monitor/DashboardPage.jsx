import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageLayout, PageHeader } from "../../components/layout";
import { fetchApi } from "../../lib/utils";
import { 
  LayoutDashboard, 
  Server, 
  Wifi, 
  WifiOff, 
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  RefreshCw
} from "lucide-react";

function StatCard({ title, value, icon: Icon, color, subtitle }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    totalDevices: 0,
    onlineDevices: 0,
    offlineDevices: 0,
    sshEnabled: 0,
    opticalInterfaces: 0,
    recentAlerts: 0,
  });
  const [loading, setLoading] = useState(true);

  const loadStats = async () => {
    try {
      setLoading(true);
      const response = await fetchApi('/api/devices');
      const deviceList = response.data || response || [];
      
      const online = deviceList.filter(d => d.ping_status === 'online').length;
      const sshEnabled = deviceList.filter(d => d.ssh_status === 'YES').length;
      
      setStats({
        totalDevices: deviceList.length,
        onlineDevices: online,
        offlineDevices: deviceList.length - online,
        sshEnabled,
        opticalInterfaces: 0, // Would need separate API call
        recentAlerts: 0,
      });
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="Dashboard"
        description="Network monitoring overview"
        icon={LayoutDashboard}
        actions={
          <button
            onClick={loadStats}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Devices"
            value={stats.totalDevices}
            icon={Server}
            color="blue"
          />
          <StatCard
            title="Online"
            value={stats.onlineDevices}
            icon={Wifi}
            color="green"
            subtitle={`${((stats.onlineDevices / stats.totalDevices) * 100 || 0).toFixed(1)}% uptime`}
          />
          <StatCard
            title="Offline"
            value={stats.offlineDevices}
            icon={WifiOff}
            color="red"
          />
          <StatCard
            title="SSH Enabled"
            value={stats.sshEnabled}
            icon={Activity}
            color="purple"
          />
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Quick Actions
              </h2>
            </div>
            <div className="p-4 grid grid-cols-2 gap-3">
              <button
                onClick={() => navigate('/inventory/discovery')}
                className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Server className="w-5 h-5 text-blue-600" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-gray-900">Run Discovery</div>
                  <div className="text-xs text-gray-500">Scan for new devices</div>
                </div>
              </button>
              <button
                onClick={() => navigate('/jobs/scheduler')}
                className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Clock className="w-5 h-5 text-purple-600" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-gray-900">View Jobs</div>
                  <div className="text-xs text-gray-500">Scheduled tasks</div>
                </div>
              </button>
              <button
                onClick={() => navigate('/monitor/power')}
                className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-yellow-600" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-gray-900">Power Trends</div>
                  <div className="text-xs text-gray-500">Optical monitoring</div>
                </div>
              </button>
              <button
                onClick={() => navigate('/monitor/topology')}
                className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <Activity className="w-5 h-5 text-green-600" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-gray-900">Topology</div>
                  <div className="text-xs text-gray-500">Network map</div>
                </div>
              </button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Recent Alerts
              </h2>
            </div>
            <div className="p-4">
              {stats.recentAlerts === 0 ? (
                <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                  <div>
                    <div className="font-medium text-green-900">All Systems Normal</div>
                    <div className="text-sm text-green-700">No active alerts</div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Alert items would go here */}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default DashboardPage;
