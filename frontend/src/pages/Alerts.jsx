import { useState, useEffect } from 'react'
import { Search, Filter, CheckCircle, Eye, Trash2, X, Clock, Server, AlertTriangle, Info } from 'lucide-react'
import clsx from 'clsx'
import useSocketIO from '../hooks/useWebSocket'

// Helper to format dates safely
const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'N/A'
  return date.toLocaleString()
}

// Extract threshold/sensor values from raw_data
const getThresholdInfo = (rawData) => {
  if (!rawData?.fields) return null
  const fields = rawData.fields
  const info = []
  
  if (fields.value) info.push({ label: 'Value', value: fields.value })
  if (fields.threshold) info.push({ label: 'Threshold', value: fields.threshold })
  if (fields.temperature) info.push({ label: 'Temperature', value: `${fields.temperature}°C` })
  if (fields.current_temp) info.push({ label: 'Current Temp', value: `${fields.current_temp}°C` })
  if (fields.max_temp) info.push({ label: 'Max Temp', value: `${fields.max_temp}°C` })
  if (fields.min_temp) info.push({ label: 'Min Temp', value: `${fields.min_temp}°C` })
  if (fields.storage_used) info.push({ label: 'Storage Used', value: fields.storage_used })
  if (fields.storage_total) info.push({ label: 'Storage Total', value: fields.storage_total })
  if (fields.camera_event) info.push({ label: 'Camera Event', value: fields.camera_event })
  if (fields.source) info.push({ label: 'Source', value: fields.source })
  
  return info.length > 0 ? info : null
}

// Alert Detail Modal Component
function AlertDetailModal({ alert, onClose, onAcknowledge, onResolve }) {
  if (!alert) return null

  const severityConfig = {
    critical: { bg: 'bg-red-600', text: 'text-red-400', icon: AlertTriangle },
    major: { bg: 'bg-orange-500', text: 'text-orange-400', icon: AlertTriangle },
    minor: { bg: 'bg-yellow-500', text: 'text-yellow-400', icon: Info },
    warning: { bg: 'bg-yellow-400', text: 'text-yellow-400', icon: Info },
    info: { bg: 'bg-blue-500', text: 'text-blue-400', icon: Info },
  }

  const config = severityConfig[alert.severity] || severityConfig.info
  const SeverityIcon = config.icon
  const thresholdInfo = getThresholdInfo(alert.raw_data)

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-gray-800 rounded-lg border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-hidden shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className={clsx('px-6 py-4 flex items-center justify-between', config.bg)}>
          <div className="flex items-center gap-3">
            <SeverityIcon className="w-6 h-6 text-white" />
            <div>
              <h2 className="text-lg font-semibold text-white">{alert.title}</h2>
              <span className="text-sm text-white/80 capitalize">{alert.severity} Alert</span>
            </div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/20 rounded">
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Description (from manifest) */}
          {alert.description && (
            <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
              <div className="text-xs text-blue-400 uppercase mb-1">Description</div>
              <div className="text-gray-200">{alert.description}</div>
            </div>
          )}

          {/* Status & Time */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-400 uppercase mb-1">Status</div>
              <div className={clsx('text-lg font-medium capitalize', statusColors[alert.status])}>
                {alert.status}
              </div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-400 uppercase mb-1">Occurred At</div>
              <div className="text-lg font-medium text-gray-200">
                {formatDate(alert.occurred_at)}
              </div>
            </div>
          </div>

          {/* Device Info */}
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase mb-2">Device Information</div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-400">IP Address</div>
                <div className="text-gray-200 font-mono">{alert.device_ip || 'N/A'}</div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Device Name</div>
                <div className="text-gray-200">{alert.device_name || 'N/A'}</div>
              </div>
            </div>
          </div>

          {/* Threshold/Sensor Values */}
          {thresholdInfo && (
            <div className="bg-orange-900/20 border border-orange-700 rounded-lg p-4">
              <div className="text-xs text-orange-400 uppercase mb-2">Sensor / Threshold Values</div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {thresholdInfo.map((item, idx) => (
                  <div key={idx}>
                    <div className="text-gray-400">{item.label}</div>
                    <div className="text-gray-200 font-mono">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Message */}
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase mb-2">Message</div>
            <div className="text-gray-200">{alert.message || 'No message provided'}</div>
          </div>

          {/* Alert Details */}
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase mb-2">Alert Details</div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-400">Alert Type</div>
                <div className="text-gray-200 font-mono">{alert.alert_type}</div>
              </div>
              <div>
                <div className="text-gray-400">Category</div>
                <div className="text-gray-200 capitalize">{alert.category || 'unknown'}</div>
              </div>
              <div>
                <div className="text-gray-400">Addon</div>
                <div className="text-gray-200">{alert.addon_id}</div>
              </div>
              <div>
                <div className="text-gray-400">Fingerprint</div>
                <div className="text-gray-200 font-mono text-xs truncate" title={alert.fingerprint}>
                  {alert.fingerprint || 'N/A'}
                </div>
              </div>
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="text-xs text-gray-400 uppercase mb-2">Timeline</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Created</span>
                <span className="text-gray-200">{formatDate(alert.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Occurred</span>
                <span className="text-gray-200">{formatDate(alert.occurred_at)}</span>
              </div>
              {alert.acknowledged_at && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Acknowledged</span>
                  <span className="text-gray-200">{formatDate(alert.acknowledged_at)}</span>
                </div>
              )}
              {alert.resolved_at && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Resolved</span>
                  <span className="text-gray-200">{formatDate(alert.resolved_at)}</span>
                </div>
              )}
              {alert.occurrence_count > 1 && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Occurrence Count</span>
                  <span className="text-gray-200">{alert.occurrence_count}</span>
                </div>
              )}
            </div>
          </div>

          {/* Raw Data (collapsible for debugging) */}
          {alert.raw_data && Object.keys(alert.raw_data).length > 0 && (
            <details className="bg-gray-900 rounded-lg p-4">
              <summary className="text-xs text-gray-400 uppercase cursor-pointer hover:text-gray-300">
                Raw Data (click to expand)
              </summary>
              <pre className="text-xs text-gray-300 bg-gray-950 p-3 rounded overflow-x-auto mt-2">
                {JSON.stringify(alert.raw_data, null, 2)}
              </pre>
            </details>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-gray-900 border-t border-gray-700 flex justify-end gap-3">
          {alert.status === 'active' && (
            <button
              onClick={() => { onAcknowledge(alert.id); onClose(); }}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg flex items-center gap-2"
            >
              <Eye className="w-4 h-4" />
              Acknowledge
            </button>
          )}
          {alert.status !== 'resolved' && (
            <button
              onClick={() => { onResolve(alert.id); onClose(); }}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Resolve
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

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
  const [selectedAlert, setSelectedAlert] = useState(null)
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
                <tr 
                  key={alert.id} 
                  className="hover:bg-gray-700/50 cursor-pointer"
                  onClick={() => setSelectedAlert(alert)}
                >
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
                    {formatDate(alert.occurred_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {alert.status === 'active' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleAcknowledge(alert.id); }}
                          className="p-1 hover:bg-gray-600 rounded"
                          title="Acknowledge"
                        >
                          <Eye className="w-4 h-4 text-yellow-400" />
                        </button>
                      )}
                      {alert.status !== 'resolved' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleResolve(alert.id); }}
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

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <AlertDetailModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
        />
      )}
    </div>
  )
}
