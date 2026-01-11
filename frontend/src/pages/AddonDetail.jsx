import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2, Upload, Download, Server, Eye, EyeOff, Save, AlertTriangle, Info, AlertCircle, XCircle, CheckCircle, ArrowUpDown, Search, X } from 'lucide-react'
import clsx from 'clsx'

const SEVERITIES = [
  { value: 'critical', label: 'Critical', color: 'bg-red-600', icon: XCircle },
  { value: 'major', label: 'Major', color: 'bg-orange-600', icon: AlertCircle },
  { value: 'minor', label: 'Minor', color: 'bg-yellow-600', icon: AlertTriangle },
  { value: 'warning', label: 'Warning', color: 'bg-amber-500', icon: AlertTriangle },
  { value: 'info', label: 'Info', color: 'bg-blue-500', icon: Info },
  { value: 'clear', label: 'Clear', color: 'bg-green-600', icon: CheckCircle },
]

const CATEGORIES = [
  { value: 'network', label: 'Network' },
  { value: 'power', label: 'Power' },
  { value: 'video', label: 'Video' },
  { value: 'wireless', label: 'Wireless' },
  { value: 'security', label: 'Security' },
  { value: 'environment', label: 'Environment' },
  { value: 'compute', label: 'Compute' },
  { value: 'storage', label: 'Storage' },
  { value: 'application', label: 'Application' },
  { value: 'system', label: 'System' },
  { value: 'unknown', label: 'Unknown' },
]

const methodLabels = {
  snmp_trap: 'SNMP Trap Receiver',
  webhook: 'Webhook Receiver',
  api_poll: 'API Polling',
  snmp_poll: 'SNMP Polling',
  ssh: 'SSH Connection',
}

function ConfigTab({ addon, addonId, headers, onSave }) {
  const [pollInterval, setPollInterval] = useState(addon?.manifest?.default_poll_interval || 300)
  const [defaultUsername, setDefaultUsername] = useState(addon?.manifest?.default_credentials?.username || '')
  const [defaultPassword, setDefaultPassword] = useState(addon?.manifest?.default_credentials?.password || '')
  const [defaultCommunity, setDefaultCommunity] = useState(addon?.manifest?.default_credentials?.community || 'public')
  const [showPassword, setShowPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [changed, setChanged] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const updatedManifest = {
        ...addon.manifest,
        default_poll_interval: parseInt(pollInterval),
        default_credentials: {
          username: defaultUsername,
          password: defaultPassword,
          community: defaultCommunity
        }
      }
      
      const res = await fetch(`/api/v1/addons/${addonId}/manifest`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest: updatedManifest })
      })
      
      if (res.ok) {
        setChanged(false)
        onSave()
      } else {
        alert('Failed to save configuration')
      }
    } catch (e) {
      alert('Failed to save configuration')
    }
    setSaving(false)
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Global Addon Configuration</h3>
        <button
          onClick={handleSave}
          disabled={saving || !changed}
          className={clsx(
            "px-3 py-1.5 rounded flex items-center gap-2 text-sm",
            changed ? "bg-green-600 hover:bg-green-700" : "bg-gray-600 cursor-not-allowed opacity-50"
          )}
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Config'}
        </button>
      </div>
      <div className="space-y-6">
        {(addon.method === 'api_poll' || addon.method === 'snmp_poll' || addon.method === 'ssh') && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">Default Poll Interval (seconds)</label>
            <input
              type="number"
              value={pollInterval}
              onChange={e => { setPollInterval(e.target.value); setChanged(true) }}
              className="w-64 px-3 py-2 bg-gray-700 border border-gray-600 rounded"
              min={10}
              max={86400}
            />
            <p className="text-xs text-gray-500 mt-1">How often to poll each device (10-86400 seconds)</p>
          </div>
        )}
        
        {/* Default Credentials Section */}
        {(addon.method === 'api_poll' || addon.method === 'ssh') && (
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-md font-medium mb-3">Default Credentials</h4>
            <p className="text-xs text-gray-500 mb-3">Used for all devices unless overridden per-device</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Username</label>
                <input
                  type="text"
                  value={defaultUsername}
                  onChange={e => { setDefaultUsername(e.target.value); setChanged(true) }}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                  placeholder="admin"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={defaultPassword}
                    onChange={e => { setDefaultPassword(e.target.value); setChanged(true) }}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded pr-10"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {addon.method === 'snmp_poll' && (
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-md font-medium mb-3">Default SNMP Settings</h4>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Community String</label>
              <input
                type="text"
                value={defaultCommunity}
                onChange={e => { setDefaultCommunity(e.target.value); setChanged(true) }}
                className="w-64 px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                placeholder="public"
              />
            </div>
          </div>
        )}
        
        {addon.method === 'snmp_trap' && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">Listen Port</label>
            <input
              type="number"
              defaultValue={162}
              className="w-64 px-3 py-2 bg-gray-700 border border-gray-600 rounded"
              disabled
            />
            <p className="text-xs text-gray-500 mt-1">SNMP traps are received on UDP port 162</p>
          </div>
        )}
        {addon.method === 'webhook' && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">Webhook Endpoint</label>
            <input
              type="text"
              value={`/webhooks/${addonId}`}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded font-mono text-sm"
              disabled
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default function AddonDetail() {
  const { addonId } = useParams()
  const navigate = useNavigate()
  const [addon, setAddon] = useState(null)
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('mappings')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [showPassword, setShowPassword] = useState({})
  const [mappings, setMappings] = useState([])
  const [mappingsChanged, setMappingsChanged] = useState(false)
  const [savingMappings, setSavingMappings] = useState(false)
  const mappingsChangedRef = useRef(false)
  const [selectedSources, setSelectedSources] = useState(new Set())
  
  // Sort and filter state for sources
  const [sortField, setSortField] = useState('ip_address')
  const [sortDirection, setSortDirection] = useState('asc')
  const [ipFilter, setIpFilter] = useState('')
  const [nameFilter, setNameFilter] = useState('')
  
  const [newSource, setNewSource] = useState({
    name: '',
    ip_address: '',
    port: '',
    username: '',
    password: '',
    community: '',
    api_key: '',
    poll_interval: 300,
    enabled: true
  })
  
  const [bulkText, setBulkText] = useState('')

  const token = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetchData()
  }, [addonId])

  const fetchData = async (resetMappings = false) => {
    try {
      const [addonRes, sourcesRes] = await Promise.all([
        fetch(`/api/v1/addons/${addonId}`, { headers }),
        fetch(`/api/v1/targets?addon_id=${addonId}`, { headers })
      ])
      
      if (addonRes.ok) {
        const addonData = await addonRes.json()
        setAddon(addonData)
        
        // Only reset mappings if explicitly requested OR if no unsaved changes
        if (resetMappings || !mappingsChangedRef.current) {
          // Check for new grouped alert_mappings format
          if (addonData.manifest?.alert_mappings) {
            // New format: grouped alerts with enable/disable
            setMappings(addonData.manifest.alert_mappings)
          } else {
            // Legacy format: flat severity/category mappings
            const severityMap = addonData.manifest?.severity_mappings || {}
            const categoryMap = addonData.manifest?.category_mappings || {}
            const titleMap = addonData.manifest?.title_templates || {}
            const descMap = addonData.manifest?.description_templates || {}
            
            const alertTypes = new Set([
              ...Object.keys(severityMap),
              ...Object.keys(categoryMap)
            ])
            
            const mappingsList = Array.from(alertTypes).map(alertType => ({
              alert_type: alertType,
              enabled: true,
              severity: severityMap[alertType] || 'info',
              category: categoryMap[alertType] || 'unknown',
              title: titleMap[alertType] || '',
              description: descMap[alertType] || ''
            }))
            
            // Convert to grouped format with single "Uncategorized" group
            setMappings([{ group: 'Alert Types', alerts: mappingsList }])
          }
          setMappingsChanged(false)
          mappingsChangedRef.current = false
        }
      }
      if (sourcesRes.ok) {
        const data = await sourcesRes.json()
        setSources(data.items || [])
      }
    } catch (e) {
      console.error('Failed to fetch data')
    }
    setLoading(false)
  }

  const handleAddSource = async (e) => {
    e.preventDefault()
    
    const config = {}
    if (newSource.port) config.port = parseInt(newSource.port)
    if (newSource.username) config.username = newSource.username
    if (newSource.password) config.password = newSource.password
    if (newSource.community) config.community = newSource.community
    if (newSource.api_key) config.api_key = newSource.api_key

    const payload = {
      name: newSource.name || newSource.ip_address,
      ip_address: newSource.ip_address,
      addon_id: addonId,
      poll_interval: parseInt(newSource.poll_interval),
      enabled: newSource.enabled,
      config
    }

    const res = await fetch('/api/v1/targets', {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      setShowAddModal(false)
      setNewSource({
        name: '', ip_address: '', port: '', username: '', password: '',
        community: '', api_key: '', poll_interval: 300, enabled: true
      })
      fetchData()
    } else {
      const err = await res.json()
      alert(err.detail || 'Failed to add source')
    }
  }

  const expandIPRange = (rangeStr) => {
    const ipPattern = /^(\d+\.\d+\.\d+)\.(\d+)-\1\.(\d+)$/
    const fullRangePattern = /^(\d+\.\d+\.\d+\.\d+)-(\d+\.\d+\.\d+\.\d+)$/
    
    let match = rangeStr.match(ipPattern)
    if (match) {
      const prefix = match[1]
      const start = parseInt(match[2])
      const end = parseInt(match[3])
      const ips = []
      for (let i = start; i <= end && i <= 255; i++) {
        ips.push(`${prefix}.${i}`)
      }
      return ips
    }
    
    match = rangeStr.match(fullRangePattern)
    if (match) {
      const startParts = match[1].split('.').map(Number)
      const endParts = match[2].split('.').map(Number)
      if (startParts[0] === endParts[0] && startParts[1] === endParts[1] && startParts[2] === endParts[2]) {
        const prefix = `${startParts[0]}.${startParts[1]}.${startParts[2]}`
        const ips = []
        for (let i = startParts[3]; i <= endParts[3] && i <= 255; i++) {
          ips.push(`${prefix}.${i}`)
        }
        return ips
      }
    }
    
    if (rangeStr.match(/^\d+\.\d+\.\d+\.\d+$/)) {
      return [rangeStr]
    }
    
    return []
  }

  const handleBulkAdd = async () => {
    const lines = bulkText.split('\n').filter(l => l.trim())
    let added = 0
    let failed = 0
    let skipped = 0

    for (const line of lines) {
      const parts = line.split(',').map(p => p.trim())
      const ipOrRange = parts[0]
      const namePrefix = parts[1] || ''
      
      const ips = expandIPRange(ipOrRange)
      
      if (ips.length === 0) {
        failed++
        continue
      }

      for (const ip of ips) {
        const name = namePrefix ? (ips.length > 1 ? `${namePrefix}-${ip.split('.').pop()}` : namePrefix) : ip
        
        const payload = {
          name,
          ip_address: ip,
          addon_id: addonId,
          poll_interval: 300,
          enabled: true,
          config: {}
        }

        const res = await fetch('/api/v1/targets', {
          method: 'POST',
          headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })

        if (res.ok) added++
        else if (res.status === 409) skipped++
        else failed++
      }
    }

    const msg = skipped > 0 
      ? `Added: ${added}, Skipped (duplicates): ${skipped}, Failed: ${failed}`
      : `Added: ${added}, Failed: ${failed}`
    alert(msg)
    setShowBulkModal(false)
    setBulkText('')
    fetchData()
  }

  const handleDelete = async (id) => {
    if (!confirm('Remove this source?')) return
    await fetch(`/api/v1/targets/${id}`, { method: 'DELETE', headers })
    fetchData()
  }

  const handleToggle = async (source) => {
    await fetch(`/api/v1/targets/${source.id}`, {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...source, enabled: !source.enabled })
    })
    fetchData()
  }

  const exportCSV = () => {
    const csv = sources.map(s => `${s.ip_address},${s.name}`).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${addonId}-sources.csv`
    a.click()
  }

  const updateMapping = (groupIndex, alertIndex, field, value) => {
    const newMappings = [...mappings]
    newMappings[groupIndex] = {
      ...newMappings[groupIndex],
      alerts: newMappings[groupIndex].alerts.map((alert, i) =>
        i === alertIndex ? { ...alert, [field]: value } : alert
      )
    }
    setMappings(newMappings)
    setMappingsChanged(true)
    mappingsChangedRef.current = true
  }

  const toggleAlert = (groupIndex, alertIndex) => {
    const newMappings = [...mappings]
    const alert = newMappings[groupIndex].alerts[alertIndex]
    newMappings[groupIndex] = {
      ...newMappings[groupIndex],
      alerts: newMappings[groupIndex].alerts.map((a, i) =>
        i === alertIndex ? { ...a, enabled: !a.enabled } : a
      )
    }
    setMappings(newMappings)
    setMappingsChanged(true)
    mappingsChangedRef.current = true
  }

  const addMapping = (groupIndex) => {
    const newMappings = [...mappings]
    newMappings[groupIndex] = {
      ...newMappings[groupIndex],
      alerts: [...newMappings[groupIndex].alerts, {
        alert_type: 'new_alert_type',
        enabled: true,
        severity: 'info',
        category: 'unknown',
        title: '',
        description: ''
      }]
    }
    setMappings(newMappings)
    setMappingsChanged(true)
    mappingsChangedRef.current = true
  }

  const addGroup = () => {
    setMappings([...mappings, { group: 'New Group', alerts: [] }])
    setMappingsChanged(true)
    mappingsChangedRef.current = true
  }

  const removeMapping = (groupIndex, alertIndex) => {
    const newMappings = [...mappings]
    newMappings[groupIndex] = {
      ...newMappings[groupIndex],
      alerts: newMappings[groupIndex].alerts.filter((_, i) => i !== alertIndex)
    }
    setMappings(newMappings)
    setMappingsChanged(true)
    mappingsChangedRef.current = true
  }

  const saveMappings = async () => {
    setSavingMappings(true)
    
    const updatedManifest = {
      ...addon.manifest,
      alert_mappings: mappings
    }
    
    // Remove legacy flat mappings if present
    delete updatedManifest.severity_mappings
    delete updatedManifest.category_mappings
    delete updatedManifest.title_templates
    delete updatedManifest.description_templates
    
    try {
      const res = await fetch(`/api/v1/addons/${addonId}/manifest`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest: updatedManifest })
      })
      
      if (res.ok) {
        setMappingsChanged(false)
        mappingsChangedRef.current = false
        fetchData(true)
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to save mappings')
      }
    } catch (e) {
      alert('Failed to save mappings')
    }
    
    setSavingMappings(false)
  }

  // Count total alerts
  const totalAlerts = mappings.reduce((sum, g) => sum + (g.alerts?.length || 0), 0)
  const enabledAlerts = mappings.reduce((sum, g) => 
    sum + (g.alerts?.filter(a => a.enabled)?.length || 0), 0)

  const needsCredentials = addon?.method && ['api_poll', 'snmp_poll', 'ssh'].includes(addon.method)

  // Helper to parse IP for proper numeric sorting
  const parseIP = (ip) => {
    const parts = ip.split('.').map(Number)
    return parts[0] * 16777216 + parts[1] * 65536 + parts[2] * 256 + parts[3]
  }

  // Filter and sort sources
  const filteredSources = sources
    .filter(s => {
      if (ipFilter && !s.ip_address.includes(ipFilter)) return false
      if (nameFilter && !s.name.toLowerCase().includes(nameFilter.toLowerCase())) return false
      return true
    })
    .sort((a, b) => {
      let cmp = 0
      if (sortField === 'ip_address') {
        cmp = parseIP(a.ip_address) - parseIP(b.ip_address)
      } else if (sortField === 'name') {
        cmp = a.name.localeCompare(b.name)
      } else if (sortField === 'last_poll_at') {
        const aTime = a.last_poll_at ? new Date(a.last_poll_at).getTime() : 0
        const bTime = b.last_poll_at ? new Date(b.last_poll_at).getTime() : 0
        cmp = aTime - bTime
      }
      return sortDirection === 'asc' ? cmp : -cmp
    })

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }
  const needsSNMP = addon?.method === 'snmp_poll'
  const needsAPI = addon?.method === 'api_poll'
  const needsSSH = addon?.method === 'ssh'

  if (loading) {
    return <div className="p-6 text-gray-400">Loading...</div>
  }

  if (!addon) {
    return <div className="p-6 text-red-400">Addon not found</div>
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/addons')}
          className="p-2 hover:bg-gray-700 rounded"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">{addon.name}</h1>
          <p className="text-gray-400">{methodLabels[addon.method] || addon.method}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('mappings')}
          className={clsx(
            'px-4 py-2 -mb-px border-b-2 transition-colors',
            activeTab === 'mappings'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-white'
          )}
        >
          Alert Mappings ({mappings.length})
        </button>
        <button
          onClick={() => setActiveTab('sources')}
          className={clsx(
            'px-4 py-2 -mb-px border-b-2 transition-colors',
            activeTab === 'sources'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-white'
          )}
        >
          Sources ({sources.length})
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={clsx(
            'px-4 py-2 -mb-px border-b-2 transition-colors',
            activeTab === 'config'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-white'
          )}
        >
          Configuration
        </button>
      </div>

      {/* Mappings Tab */}
      {activeTab === 'mappings' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <div>
              <p className="text-gray-400">
                Define how raw alert types are normalized to severity, category, title, and description.
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {enabledAlerts} of {totalAlerts} alert types enabled
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={addGroup}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Group
              </button>
              <button
                onClick={saveMappings}
                disabled={savingMappings || !mappingsChanged}
                className={clsx(
                  "px-3 py-1.5 rounded flex items-center gap-2 text-sm",
                  mappingsChanged 
                    ? "bg-green-600 hover:bg-green-700" 
                    : "bg-gray-600 cursor-not-allowed opacity-50"
                )}
              >
                <Save className="w-4 h-4" />
                {savingMappings ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>

          <div className="space-y-6">
            {mappings.length === 0 ? (
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center text-gray-400">
                No alert mappings defined. Click "Add Group" to create one.
              </div>
            ) : (
              mappings.map((group, groupIndex) => (
                <div key={groupIndex} className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                  {/* Group Header */}
                  <div className="bg-gray-900 px-4 py-3 flex justify-between items-center border-b border-gray-700">
                    <h3 className="font-semibold text-lg">{group.group}</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-400">
                        {group.alerts?.filter(a => a.enabled).length || 0}/{group.alerts?.length || 0} enabled
                      </span>
                      <button
                        onClick={() => addMapping(groupIndex)}
                        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" />
                        Add
                      </button>
                    </div>
                  </div>
                  
                  {/* Alerts in Group */}
                  <div className="divide-y divide-gray-700">
                    {group.alerts?.length === 0 ? (
                      <div className="px-4 py-6 text-center text-gray-500 text-sm">
                        No alerts in this group. Click "Add" to create one.
                      </div>
                    ) : (
                      group.alerts?.map((alert, alertIndex) => {
                        const severityDef = SEVERITIES.find(s => s.value === alert.severity) || SEVERITIES[4]
                        
                        return (
                          <div 
                            key={alertIndex} 
                            className={clsx(
                              'px-3 py-1.5 transition-opacity flex items-center gap-2',
                              !alert.enabled && 'opacity-50 bg-gray-900/50'
                            )}
                          >
                            {/* Enable Toggle */}
                            <button
                              onClick={() => toggleAlert(groupIndex, alertIndex)}
                              className={clsx(
                                'w-8 h-4 rounded-full relative transition-colors flex-shrink-0',
                                alert.enabled ? 'bg-green-600' : 'bg-gray-600'
                              )}
                            >
                              <div className={clsx(
                                'w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform',
                                alert.enabled ? 'translate-x-4' : 'translate-x-0.5'
                              )} />
                            </button>
                            
                            {/* Alert Type */}
                            <input
                              type="text"
                              value={alert.alert_type}
                              onChange={e => updateMapping(groupIndex, alertIndex, 'alert_type', e.target.value)}
                              className="w-40 px-2 py-1 bg-gray-700 border border-gray-600 rounded font-mono text-xs"
                              disabled={!alert.enabled}
                            />
                            
                            {/* Title */}
                            <input
                              type="text"
                              value={alert.title || ''}
                              onChange={e => updateMapping(groupIndex, alertIndex, 'title', e.target.value)}
                              className="w-36 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs"
                              placeholder="Title"
                              disabled={!alert.enabled}
                            />
                            
                            {/* Severity */}
                            <select
                              value={alert.severity}
                              onChange={e => updateMapping(groupIndex, alertIndex, 'severity', e.target.value)}
                              className={clsx(
                                'w-24 px-1 py-1 border border-gray-600 rounded text-xs',
                                severityDef.color, 'text-white'
                              )}
                              disabled={!alert.enabled}
                            >
                              {SEVERITIES.map(s => (
                                <option key={s.value} value={s.value}>{s.label}</option>
                              ))}
                            </select>
                            
                            {/* Category */}
                            <select
                              value={alert.category}
                              onChange={e => updateMapping(groupIndex, alertIndex, 'category', e.target.value)}
                              className="w-28 px-1 py-1 bg-gray-700 border border-gray-600 rounded text-xs"
                              disabled={!alert.enabled}
                            >
                              {CATEGORIES.map(c => (
                                <option key={c.value} value={c.value}>{c.label}</option>
                              ))}
                            </select>
                            
                            {/* Description - truncated with tooltip */}
                            <input
                              type="text"
                              value={alert.description || ''}
                              onChange={e => updateMapping(groupIndex, alertIndex, 'description', e.target.value)}
                              className="flex-1 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs min-w-0"
                              placeholder="Description..."
                              title={alert.description || ''}
                              disabled={!alert.enabled}
                            />
                            
                            {/* Delete */}
                            <button
                              onClick={() => removeMapping(groupIndex, alertIndex)}
                              className="p-1 hover:bg-gray-700 rounded text-red-400 flex-shrink-0"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        )
                      })
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          
          {totalAlerts > 0 && (
            <div className="mt-4 p-4 bg-gray-900 rounded-lg border border-gray-700">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Template Variables</h4>
              <p className="text-xs text-gray-500">
                Use <code className="bg-gray-800 px-1 rounded">{'{{device_ip}}'}</code>, 
                <code className="bg-gray-800 px-1 rounded ml-1">{'{{device_name}}'}</code>, 
                <code className="bg-gray-800 px-1 rounded ml-1">{'{{value}}'}</code>, 
                <code className="bg-gray-800 px-1 rounded ml-1">{'{{timestamp}}'}</code> in title/description templates.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Sources Tab */}
      {activeTab === 'sources' && (
        <div>
          <div className="flex justify-between mb-4">
            <div className="flex items-center gap-4">
              <p className="text-gray-400">
                {addon.method === 'webhook' || addon.method === 'snmp_trap'
                  ? 'Devices that will send data to this addon (for reference/filtering)'
                  : 'Devices this addon will poll or connect to'}
              </p>
              {selectedSources.size > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-blue-400">{selectedSources.size} selected</span>
                  <button
                    onClick={async () => {
                      if (!confirm(`Delete ${selectedSources.size} selected sources?`)) return
                      for (const id of selectedSources) {
                        await fetch(`/api/v1/targets/${id}`, { method: 'DELETE', headers })
                      }
                      setSelectedSources(new Set())
                      fetchData()
                    }}
                    className="px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-xs"
                  >
                    Delete Selected
                  </button>
                  <button
                    onClick={() => setSelectedSources(new Set())}
                    className="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs"
                  >
                    Clear Selection
                  </button>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={exportCSV}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2 text-sm"
              >
                <Download className="w-4 h-4" />
                Export
              </button>
              <button
                onClick={() => setShowBulkModal(true)}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2 text-sm"
              >
                <Upload className="w-4 h-4" />
                Bulk Import
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded flex items-center gap-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Source
              </button>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            {/* Filter bar */}
            <div className="bg-gray-900 px-4 py-2 border-b border-gray-700 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Filter by IP..."
                  value={ipFilter}
                  onChange={e => setIpFilter(e.target.value)}
                  className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm w-40"
                />
                {ipFilter && (
                  <button onClick={() => setIpFilter('')} className="text-gray-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Filter by name..."
                  value={nameFilter}
                  onChange={e => setNameFilter(e.target.value)}
                  className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm w-40"
                />
                {nameFilter && (
                  <button onClick={() => setNameFilter('')} className="text-gray-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
              <span className="text-sm text-gray-500 ml-auto">
                {filteredSources.length} of {sources.length} sources
              </span>
            </div>
            <table className="w-full">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-2 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={filteredSources.length > 0 && selectedSources.size === filteredSources.length}
                      onChange={e => {
                        if (e.target.checked) {
                          setSelectedSources(new Set(filteredSources.map(s => s.id)))
                        } else {
                          setSelectedSources(new Set())
                        }
                      }}
                      className="rounded bg-gray-700 border-gray-600"
                    />
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => toggleSort('name')}
                  >
                    <div className="flex items-center gap-1">
                      Name
                      {sortField === 'name' 
                        ? <span className="text-blue-400 text-xs font-bold">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                        : <ArrowUpDown className="w-3 h-3 text-gray-600" />
                      }
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => toggleSort('ip_address')}
                  >
                    <div className="flex items-center gap-1">
                      IP Address
                      {sortField === 'ip_address' 
                        ? <span className="text-blue-400 text-xs font-bold">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                        : <ArrowUpDown className="w-3 h-3 text-gray-600" />
                      }
                    </div>
                  </th>
                  {needsCredentials && (
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Credentials</th>
                  )}
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Status</th>
                  <th 
                    className="px-4 py-3 text-left text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                    onClick={() => toggleSort('last_poll_at')}
                  >
                    <div className="flex items-center gap-1">
                      Last Poll
                      {sortField === 'last_poll_at' 
                        ? <span className="text-blue-400 text-xs font-bold">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                        : <ArrowUpDown className="w-3 h-3 text-gray-600" />
                      }
                    </div>
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {filteredSources.length === 0 ? (
                  <tr>
                    <td colSpan={needsCredentials ? 7 : 6} className="px-4 py-8 text-center text-gray-400">
                      {sources.length === 0 ? 'No sources configured. Add devices to monitor.' : 'No sources match the filter.'}
                    </td>
                  </tr>
                ) : (
                  filteredSources.map(source => (
                    <tr key={source.id} className={clsx(
                      !source.enabled && 'opacity-50',
                      selectedSources.has(source.id) && 'bg-blue-900/20'
                    )}>
                      <td className="px-2 py-3">
                        <input
                          type="checkbox"
                          checked={selectedSources.has(source.id)}
                          onChange={e => {
                            const newSelected = new Set(selectedSources)
                            if (e.target.checked) {
                              newSelected.add(source.id)
                            } else {
                              newSelected.delete(source.id)
                            }
                            setSelectedSources(newSelected)
                          }}
                          className="rounded bg-gray-700 border-gray-600"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Server className="w-4 h-4 text-gray-400" />
                          {source.name}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-sm">{source.ip_address}</td>
                      {needsCredentials && (
                        <td className="px-4 py-3 text-sm text-gray-400">
                          {source.config?.username ? `${source.config.username}:***` : 
                           source.config?.community ? `community: ${source.config.community}` :
                           source.config?.api_key ? 'API Key: ***' : 
                           addon?.manifest?.default_credentials?.username ? '(default)' : 'None'}
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'px-2 py-0.5 rounded text-xs',
                          source.enabled ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'
                        )}>
                          {source.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {source.last_poll_at ? new Date(source.last_poll_at).toLocaleString() : 'Never'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleToggle(source)}
                            className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                          >
                            {source.enabled ? 'Disable' : 'Enable'}
                          </button>
                          <button
                            onClick={() => handleDelete(source.id)}
                            className="p-1.5 hover:bg-gray-700 rounded text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Config Tab */}
      {activeTab === 'config' && (
        <ConfigTab 
          addon={addon} 
          addonId={addonId} 
          headers={headers}
          onSave={() => fetchData(true)}
        />
      )}


      {/* Add Source Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Add Source</h2>
            <form onSubmit={handleAddSource} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">IP Address *</label>
                <input
                  type="text"
                  value={newSource.ip_address}
                  onChange={e => setNewSource({ ...newSource, ip_address: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                  placeholder="192.168.1.100"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Name (optional)</label>
                <input
                  type="text"
                  value={newSource.name}
                  onChange={e => setNewSource({ ...newSource, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                  placeholder="UPS-Building-A"
                />
              </div>
              
              {needsSNMP && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">SNMP Community</label>
                  <input
                    type="text"
                    value={newSource.community}
                    onChange={e => setNewSource({ ...newSource, community: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    placeholder="public"
                  />
                </div>
              )}
              
              {needsAPI && (
                <>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Port</label>
                    <input
                      type="number"
                      value={newSource.port}
                      onChange={e => setNewSource({ ...newSource, port: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                      placeholder="443"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">API Key</label>
                    <input
                      type="password"
                      value={newSource.api_key}
                      onChange={e => setNewSource({ ...newSource, api_key: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                </>
              )}
              
              {needsSSH && (
                <>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Username</label>
                    <input
                      type="text"
                      value={newSource.username}
                      onChange={e => setNewSource({ ...newSource, username: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Password</label>
                    <input
                      type="password"
                      value={newSource.password}
                      onChange={e => setNewSource({ ...newSource, password: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                </>
              )}

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
                >
                  Add
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Import Modal */}
      {showBulkModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">Bulk Import Sources</h2>
            <div className="text-gray-400 mb-4 text-sm space-y-1">
              <p>Enter one IP or range per line. Optional name after comma.</p>
              <p className="text-gray-500">Formats:</p>
              <ul className="text-gray-500 ml-4 list-disc">
                <li><code className="bg-gray-700 px-1 rounded">10.1.1.100</code> - single IP</li>
                <li><code className="bg-gray-700 px-1 rounded">10.1.1.100-10.1.1.110</code> - IP range</li>
                <li><code className="bg-gray-700 px-1 rounded">10.1.1.100-10.1.1.110,Camera</code> - range with name prefix</li>
              </ul>
            </div>
            <textarea
              value={bulkText}
              onChange={e => setBulkText(e.target.value)}
              className="w-full h-48 px-4 py-2 bg-gray-900 border border-gray-700 rounded font-mono text-sm"
              placeholder="10.120.38.101-10.120.38.117,Axis-Cam
10.120.39.1,PTZ-Lobby
10.120.39.10-10.120.39.20"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setShowBulkModal(false); setBulkText('') }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkAdd}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
              >
                Import
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
