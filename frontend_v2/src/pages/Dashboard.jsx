import { useState, useEffect } from 'react'
import { AlertTriangle, AlertCircle, Info, CheckCircle, Activity } from 'lucide-react'
import useSocketIO from '../hooks/useWebSocket'

const severityConfig = {
  critical: { color: 'bg-red-600', icon: AlertTriangle },
  major: { color: 'bg-orange-500', icon: AlertTriangle },
  minor: { color: 'bg-yellow-500', icon: AlertCircle },
  warning: { color: 'bg-yellow-400', icon: AlertCircle },
  info: { color: 'bg-blue-500', icon: Info },
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recentAlerts, setRecentAlerts] = useState([])
  const [systemHealth, setSystemHealth] = useState(null)

  const fetchData = async () => {
    const token = localStorage.getItem('access_token')
    const headers = { Authorization: `Bearer ${token}` }

    const [statsRes, alertsRes, healthRes] = await Promise.all([
      fetch('/api/v1/alerts/stats', { headers }),
      fetch('/api/v1/alerts?limit=10', { headers }),
      fetch('/api/v1/health'),
    ])

    if (statsRes.ok) setStats(await statsRes.json())
    if (alertsRes.ok) {
      const data = await alertsRes.json()
      setRecentAlerts(data.items || [])
    }
    if (healthRes.ok) setSystemHealth(await healthRes.json())
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  useSocketIO((event) => {
    if (event.type.startsWith('alert_')) {
      fetchData()
    }
  })

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        {['critical', 'major', 'minor', 'warning', 'info'].map(severity => {
          const config = severityConfig[severity]
          const Icon = config.icon
          const count = stats?.by_severity?.[severity] || 0

          return (
            <div key={severity} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-400 text-sm capitalize">{severity}</div>
                  <div className="text-3xl font-bold">{count}</div>
                </div>
                <div className={`p-3 rounded-full ${config.color}`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Alerts */}
        <div className="lg:col-span-2 bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="font-semibold">Recent Alerts</h2>
          </div>
          <div className="divide-y divide-gray-700">
            {recentAlerts.length === 0 ? (
              <div className="p-4 text-gray-400 text-center">No active alerts</div>
            ) : (
              recentAlerts.map(alert => (
                <div key={alert.id} className="p-4 hover:bg-gray-700/50">
                  <div className="flex items-start gap-3">
                    <span className={`mt-1 w-2 h-2 rounded-full ${severityConfig[alert.severity]?.color || 'bg-gray-500'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{alert.title}</div>
                      <div className="text-sm text-gray-400">{alert.device_ip}</div>
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(alert.occurred_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* System Status */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="font-semibold">System Status</h2>
          </div>
          <div className="p-4 space-y-4">
            {systemHealth?.components && Object.entries(systemHealth.components).map(([name, status]) => (
              <div key={name} className="flex items-center justify-between">
                <span className="text-gray-300 capitalize">{name.replace('_', ' ')}</span>
                <span className={`px-2 py-1 rounded text-xs ${
                  status.includes('healthy') || status.includes('running') 
                    ? 'bg-green-900 text-green-300' 
                    : 'bg-yellow-900 text-yellow-300'
                }`}>
                  {status}
                </span>
              </div>
            ))}

            <div className="pt-4 border-t border-gray-700">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Activity className="w-4 h-4" />
                <span>Version {systemHealth?.version || '2.0.0'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
