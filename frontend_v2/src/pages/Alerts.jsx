import { useState, useEffect } from 'react'
import { Search, Filter, CheckCircle, Eye, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import useSocketIO from '../hooks/useWebSocket'

const severityColors = {
  critical: 'bg-red-600',
  major: 'bg-orange-500',
  minor: 'bg-yellow-500',
  warning: 'bg-yellow-400',
  info: 'bg-blue-500',
}

const statusColors = {
  active: 'text-red-400',
  acknowledged: 'text-yellow-400',
  suppressed: 'text-gray-400',
  resolved: 'text-green-400',
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    status: ['active', 'acknowledged'],
    severity: [],
    search: '',
  })

  const fetchAlerts = async () => {
    const token = localStorage.getItem('access_token')
    const params = new URLSearchParams()
    
    filters.status.forEach(s => params.append('status', s))
    filters.severity.forEach(s => params.append('severity', s))
    params.append('limit', '100')

    const res = await fetch(`/api/v1/alerts?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (res.ok) {
      const data = await res.json()
      setAlerts(data.items || [])
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchAlerts()
  }, [filters.status, filters.severity])

  useSocketIO((event) => {
    if (event.type.startsWith('alert_')) {
      fetchAlerts()
    }
  })

  const handleAcknowledge = async (alertId) => {
    const token = localStorage.getItem('access_token')
    await fetch(`/api/v1/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchAlerts()
  }

  const handleResolve = async (alertId) => {
    const token = localStorage.getItem('access_token')
    await fetch(`/api/v1/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchAlerts()
  }

  const filteredAlerts = alerts.filter(alert => {
    if (filters.search) {
      const search = filters.search.toLowerCase()
      return (
        alert.title.toLowerCase().includes(search) ||
        alert.device_ip?.toLowerCase().includes(search) ||
        alert.device_name?.toLowerCase().includes(search)
      )
    }
    return true
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Alerts</h1>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search alerts..."
              value={filters.search}
              onChange={e => setFilters({ ...filters, search: e.target.value })}
              className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Status:</span>
          {['active', 'acknowledged', 'resolved'].map(status => (
            <button
              key={status}
              onClick={() => {
                const newStatus = filters.status.includes(status)
                  ? filters.status.filter(s => s !== status)
                  : [...filters.status, status]
                setFilters({ ...filters, status: newStatus })
              }}
              className={clsx(
                'px-3 py-1 rounded text-sm capitalize',
                filters.status.includes(status)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300'
              )}
            >
              {status}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Severity:</span>
          {['critical', 'major', 'minor', 'warning'].map(severity => (
            <button
              key={severity}
              onClick={() => {
                const newSeverity = filters.severity.includes(severity)
                  ? filters.severity.filter(s => s !== severity)
                  : [...filters.severity, severity]
                setFilters({ ...filters, severity: newSeverity })
              }}
              className={clsx(
                'px-3 py-1 rounded text-sm capitalize',
                filters.severity.includes(severity)
                  ? severityColors[severity] + ' text-white'
                  : 'bg-gray-700 text-gray-300'
              )}
            >
              {severity}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Severity</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Title</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Device</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Time</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  Loading...
                </td>
              </tr>
            ) : filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No alerts found
                </td>
              </tr>
            ) : (
              filteredAlerts.map(alert => (
                <tr key={alert.id} className="hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'px-2 py-1 rounded text-xs font-medium text-white capitalize',
                      severityColors[alert.severity] || 'bg-gray-500'
                    )}>
                      {alert.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{alert.title}</div>
                    <div className="text-sm text-gray-400 truncate max-w-md">{alert.message}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{alert.device_ip}</td>
                  <td className="px-4 py-3">
                    <span className={clsx('capitalize', statusColors[alert.status])}>
                      {alert.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400">
                    {new Date(alert.occurred_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {alert.status === 'active' && (
                        <button
                          onClick={() => handleAcknowledge(alert.id)}
                          className="p-1 hover:bg-gray-600 rounded"
                          title="Acknowledge"
                        >
                          <Eye className="w-4 h-4 text-yellow-400" />
                        </button>
                      )}
                      {alert.status !== 'resolved' && (
                        <button
                          onClick={() => handleResolve(alert.id)}
                          className="p-1 hover:bg-gray-600 rounded"
                          title="Resolve"
                        >
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
