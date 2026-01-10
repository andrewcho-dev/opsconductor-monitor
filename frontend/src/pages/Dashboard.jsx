import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, AlertCircle, Info, CheckCircle, Activity, Server, Wifi } from 'lucide-react'
import useSocketIO from '../hooks/useWebSocket'

const severityConfig = {
  critical: { color: 'bg-red-600', icon: AlertTriangle },
  major: { color: 'bg-orange-500', icon: AlertTriangle },
  minor: { color: 'bg-yellow-500', icon: AlertCircle },
  warning: { color: 'bg-yellow-400', icon: AlertCircle },
  info: { color: 'bg-blue-500', icon: Info },
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [addons, setAddons] = useState([])
  const [systemHealth, setSystemHealth] = useState(null)

  const fetchData = async () => {
    const token = localStorage.getItem('access_token')
    const headers = { Authorization: `Bearer ${token}` }

    const [statsRes, addonsRes, healthRes] = await Promise.all([
      fetch('/api/v1/alerts/stats', { headers }),
      fetch('/api/v1/addons', { headers }),
      fetch('/api/v1/health'),
    ])

    if (statsRes.ok) setStats(await statsRes.json())
    if (addonsRes.ok) {
      const data = await addonsRes.json()
      setAddons(data.items || [])
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

  const totalActive = stats?.total_active || 0

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Alert Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {/* Total Active */}
        <div 
          onClick={() => navigate('/alerts')}
          className="bg-gray-800 rounded-lg p-4 border border-gray-700 cursor-pointer hover:border-gray-500 transition-colors"
        >
          <div className="text-gray-400 text-xs uppercase tracking-wide">Active</div>
          <div className="text-2xl font-bold mt-1">{totalActive}</div>
        </div>
        
        {['critical', 'major', 'minor', 'warning', 'info'].map(severity => {
          const config = severityConfig[severity]
          const count = stats?.by_severity?.[severity] || 0

          return (
            <div 
              key={severity} 
              onClick={() => navigate(`/alerts?severity=${severity}`)}
              className="bg-gray-800 rounded-lg p-4 border border-gray-700 cursor-pointer hover:border-gray-500 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${config.color}`} />
                <span className="text-gray-400 text-xs uppercase tracking-wide">{severity}</span>
              </div>
              <div className="text-2xl font-bold mt-1">{count}</div>
            </div>
          )
        })}
      </div>

      {/* Addons Grid */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Addons</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {addons.filter(a => a.enabled).map(addon => (
            <div 
              key={addon.id}
              onClick={() => navigate(`/addons/${addon.id}`)}
              className="bg-gray-800 rounded-lg p-4 border border-gray-700 cursor-pointer hover:border-blue-500 transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                <Server className="w-4 h-4 text-gray-400" />
                <span className="font-medium text-sm truncate">{addon.name}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">{addon.method?.replace('_', ' ')}</span>
                <span className="text-green-400">Active</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Status - Compact */}
      <div className="flex items-center gap-4 text-sm text-gray-400">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4" />
          <span>v{systemHealth?.version || '2.0.0'}</span>
        </div>
        {systemHealth?.components && Object.entries(systemHealth.components).map(([name, status]) => (
          <div key={name} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${
              status.includes('healthy') || status.includes('running') ? 'bg-green-500' : 'bg-yellow-500'
            }`} />
            <span className="capitalize">{name.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
