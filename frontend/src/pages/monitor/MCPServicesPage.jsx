import { useState, useEffect } from 'react';
import { 
  Network, 
  RefreshCw, 
  Circle,
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  ArrowUpDown,
  Zap,
  Cable,
  Radio
} from 'lucide-react';
import { PageLayout, PageHeader } from '../../components/layout';
import { cn, fetchApi } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';

export function MCPServicesPage() {
  const { getAuthHeader } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [services, setServices] = useState([]);
  const [serviceFolders, setServiceFolders] = useState([]);
  const [rings, setRings] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [sortField, setSortField] = useState('name');
  const [sortDir, setSortDir] = useState('asc');
  const [expandedRings, setExpandedRings] = useState({});
  const [expandedServices, setExpandedServices] = useState({});
  const [selectedSegment, setSelectedSegment] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setError(null);
      const [summaryRes, servicesRes, ringsRes] = await Promise.all([
        fetchApi('/integrations/v1/mcp/services/summary', { headers: getAuthHeader() }),
        fetchApi('/integrations/v1/mcp/services?limit=500', { headers: getAuthHeader() }),
        fetchApi('/integrations/v1/mcp/services/rings', { headers: getAuthHeader() }),
      ]);

      // Handle both {success, data} and direct response formats
      const summaryData = summaryRes?.data || summaryRes;
      const servicesData = servicesRes?.data || servicesRes;
      const ringsData = ringsRes?.data || ringsRes;
      
      setSummary(summaryData);
      setServices(servicesData?.services || (Array.isArray(servicesData) ? servicesData : []));
      setServiceFolders(servicesData?.service_folders || []);
      setRings(ringsData?.rings || (Array.isArray(ringsData) ? ringsData : []));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const toggleRingExpanded = (ringId) => {
    setExpandedRings(prev => ({ ...prev, [ringId]: !prev[ringId] }));
  };

  // Filter and sort services
  const filteredServices = services
    .filter(svc => {
      if (searchTerm && !svc.name?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      if (classFilter && svc.service_class !== classFilter) return false;
      if (stateFilter) {
        const state = (svc.operation_state || '').toLowerCase();
        if (stateFilter === 'up' && state !== 'up') return false;
        if (stateFilter === 'down' && state !== 'down') return false;
        if (stateFilter === 'unknown' && state !== '' && state !== 'unknown') return false;
      }
      return true;
    })
    .sort((a, b) => {
      let aVal = a[sortField] || '';
      let bVal = b[sortField] || '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  // Get unique service classes for filter
  const serviceClasses = [...new Set(services.map(s => s.service_class).filter(Boolean))].sort();

  if (loading) {
    return (
      <PageLayout module="monitor">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout module="monitor">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <XCircle className="h-5 w-5 text-red-500" />
          <div>
            <p className="font-medium text-red-800">Failed to load MCP services</p>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="MCP Services"
        description="Monitor Ciena MCP services, circuits, and G.8032 rings"
        icon={Circle}
        actions={
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
            Refresh
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Total Services"
          value={summary?.total || 0}
          icon={Network}
          color="blue"
        />
        <SummaryCard
          title="Services Up"
          value={summary?.by_state?.up || 0}
          icon={CheckCircle}
          color="green"
        />
        <SummaryCard
          title="Services Down"
          value={summary?.by_state?.down || 0}
          icon={XCircle}
          color="red"
          alert={summary?.by_state?.down > 0}
        />
        <SummaryCard
          title="G.8032 Rings"
          value={rings.length}
          icon={Circle}
          color="purple"
          subtitle={`${rings.filter(r => r.ring_state === 'OK').length} OK`}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {[
            { id: 'overview', label: 'Overview', icon: Activity },
            { id: 'services', label: 'All Services', icon: Network },
            { id: 'rings', label: 'G.8032 Rings', icon: Circle },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors",
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <OverviewTab summary={summary} rings={rings} services={services} />
      )}

      {activeTab === 'services' && (
        <ServicesTab
          serviceFolders={serviceFolders}
          expandedServices={expandedServices}
          setExpandedServices={setExpandedServices}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          classFilter={classFilter}
          setClassFilter={setClassFilter}
          stateFilter={stateFilter}
          setStateFilter={setStateFilter}
          serviceClasses={serviceClasses}
        />
      )}

      {activeTab === 'rings' && (
        <RingsTab
          rings={rings}
          expandedRings={expandedRings}
          toggleRingExpanded={toggleRingExpanded}
          selectedSegment={selectedSegment}
          setSelectedSegment={setSelectedSegment}
        />
      )}
      </div>
    </PageLayout>
  );
}

function SummaryCard({ title, value, icon: Icon, color, subtitle, alert }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    purple: 'bg-purple-100 text-purple-600',
    yellow: 'bg-yellow-100 text-yellow-600',
  };

  return (
    <div className={cn(
      "bg-white rounded-xl border border-gray-200 shadow-sm p-4",
      alert && "border-red-300 bg-red-50/30"
    )}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className={cn("text-3xl font-bold mt-1", alert && "text-red-600")}>
            {value}
          </p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={cn("p-3 rounded-lg", colors[color])}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ summary, rings, services }) {
  const byClass = summary?.by_class || {};
  const downServices = summary?.down_services || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Services by Class */}
      <div className="bg-white rounded-xl border p-5 shadow-sm">
        <h3 className="font-semibold text-gray-900 mb-4">Services by Class</h3>
        <div className="space-y-3">
          {Object.entries(byClass)
            .sort((a, b) => b[1] - a[1])
            .map(([cls, count]) => (
              <div key={cls} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ServiceClassIcon serviceClass={cls} />
                  <span className="text-sm text-gray-700">{cls}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${(count / (summary?.total || 1)) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-900 w-10 text-right">
                    {count}
                  </span>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* G.8032 Rings Status */}
      <div className="bg-white rounded-xl border p-5 shadow-sm">
        <h3 className="font-semibold text-gray-900 mb-4">G.8032 Ring Status</h3>
        {rings.length === 0 ? (
          <p className="text-gray-500 text-sm">No rings configured</p>
        ) : (
          <div className="space-y-3">
            {rings.map(ring => (
              <div key={ring.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-3 h-3 rounded-full",
                    ring.ring_state === 'OK' ? "bg-green-500" : "bg-red-500"
                  )} />
                  <div>
                    <p className="font-medium text-gray-900">{ring.name}</p>
                    <p className="text-xs text-gray-500">
                      Ring ID: {ring.ring_id} • {ring.ring_type}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                    ring.ring_state === 'OK'
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  )}>
                    {ring.ring_state || 'Unknown'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Down Services Alert */}
      {downServices.length > 0 && (
        <div className="lg:col-span-2 bg-red-50 border border-red-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <h3 className="font-semibold text-red-800">Down Services ({downServices.length})</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {downServices.map(svc => (
              <div key={svc.id} className="bg-white rounded-lg p-3 border border-red-200">
                <p className="font-medium text-gray-900 truncate">{svc.name}</p>
                <p className="text-xs text-gray-500">{svc.class}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ServicesTab({
  serviceFolders,
  expandedServices,
  setExpandedServices,
  searchTerm,
  setSearchTerm,
  classFilter,
  setClassFilter,
  stateFilter,
  setStateFilter,
  serviceClasses,
}) {
  // Filter folders
  const filteredFolders = serviceFolders.filter(folder => {
    if (searchTerm && !folder.name?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    if (classFilter && folder.service_class !== classFilter) return false;
    if (stateFilter) {
      if (stateFilter === 'up' && folder.state !== 'up') return false;
      if (stateFilter === 'down' && folder.state !== 'down') return false;
    }
    return true;
  });

  const toggleService = (name) => {
    setExpandedServices(prev => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <div className="bg-white rounded-xl border shadow-sm">
      {/* Filters */}
      <div className="p-4 border-b flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search services..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Classes</option>
          {serviceClasses.map(cls => (
            <option key={cls} value={cls}>{cls}</option>
          ))}
        </select>
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All States</option>
          <option value="up">Up</option>
          <option value="down">Down</option>
        </select>
      </div>

      {/* Service Folders */}
      <div className="overflow-auto max-h-[calc(100vh-400px)]">
        <div className="divide-y divide-gray-200">
          {filteredFolders.map((folder) => (
            <div key={folder.name}>
              {/* Folder Header */}
              <button
                onClick={() => toggleService(folder.name)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {expandedServices[folder.name] ? (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                  <ServiceClassIcon serviceClass={folder.service_class} />
                  <span className="font-medium text-gray-900">{folder.name}</span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                    {folder.link_count} {folder.link_count === 1 ? 'link' : 'links'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-500">{folder.service_class || '—'}</span>
                  <FolderStateIndicator state={folder.state} />
                </div>
              </button>

              {/* Expanded Links */}
              {expandedServices[folder.name] && (
                <div className="bg-gray-50 border-t">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 pl-12 text-left text-xs font-medium text-gray-500">A-End (Device:Port)</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Z-End (Device:Port)</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">State</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Capacity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {folder.links.map((link, idx) => (
                        <tr key={link.id || idx} className="hover:bg-gray-100">
                          <td className="px-4 py-2 pl-12 text-gray-600 font-mono text-xs">
                            {link.a_end ? `${link.a_end}${link.a_end_port ? ':' + link.a_end_port : ''}` : '—'}
                          </td>
                          <td className="px-4 py-2 text-gray-600 font-mono text-xs">
                            {link.z_end ? `${link.z_end}${link.z_end_port ? ':' + link.z_end_port : ''}` : '—'}
                          </td>
                          <td className="px-4 py-2">
                            <StateIndicator state={link.operation_state} />
                          </td>
                          <td className="px-4 py-2 text-right font-mono text-gray-600 text-xs">
                            {link.total_capacity ? `${link.total_capacity} ${link.capacity_units || ''}` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="p-3 text-center text-sm text-gray-500 border-t bg-gray-50">
        {filteredFolders.length} services ({filteredFolders.reduce((sum, f) => sum + f.link_count, 0)} links)
      </div>
    </div>
  );
}

function FolderStateIndicator({ state }) {
  if (state === 'up') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
        <CheckCircle className="h-3 w-3" /> All Up
      </span>
    );
  }
  if (state === 'down') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <XCircle className="h-3 w-3" /> Down
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
      <AlertTriangle className="h-3 w-3" /> Partial
    </span>
  );
}

function RingsTab({ rings, expandedRings, toggleRingExpanded, selectedSegment, setSelectedSegment }) {
  return (
    <div className="bg-white rounded-xl border shadow-sm">
      {rings.length === 0 ? (
        <div className="p-8 text-center">
          <Circle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No G.8032 rings configured</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-200">
          {rings.map(ring => (
            <div key={ring.id}>
              {/* Ring Header */}
              <button
                onClick={() => toggleRingExpanded(ring.id)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {expandedRings[ring.id] ? (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                  <div className={cn(
                    "w-3 h-3 rounded-full",
                    ring.ring_state === 'OK' && ring.ring_status === 'OK'
                      ? "bg-green-500"
                      : "bg-red-500"
                  )} />
                  <div className="text-left">
                    <span className="font-semibold text-gray-900">{ring.name}</span>
                    <span className="text-xs text-gray-500 ml-2">
                      ID: {ring.ring_id} • {ring.ring_type}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                    {ring.segment_count || 0} {ring.segment_count === 1 ? 'segment' : 'segments'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {ring.protection_active && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700">
                      <AlertTriangle className="h-3 w-3" /> Protection Active
                    </span>
                  )}
                  <span className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                    ring.ring_state === 'OK'
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  )}>
                    {ring.ring_state || 'Unknown'}
                  </span>
                  <FolderStateIndicator state={ring.members_state} />
                </div>
              </button>

              {/* Expanded Content */}
              {expandedRings[ring.id] && (
                <div className="bg-gray-50 border-t">
                  {/* Ring Details */}
                  <div className="px-4 py-3 border-b bg-gray-100">
                    <div className="flex flex-wrap gap-4 text-xs">
                      <span><strong>Logical Ring:</strong> {ring.logical_ring || '—'}</span>
                      <span><strong>RAPS VID:</strong> {ring.raps_vid || '—'}</span>
                      <span><strong>Revertive:</strong> {ring.revertive ? 'Yes' : 'No'}</span>
                      <span><strong>Node IDs:</strong> {ring.ring_members || '—'}</span>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs mt-2 pt-2 border-t border-gray-200">
                      <span className={cn(
                        "font-medium",
                        ring.protection_active ? "text-orange-700" : "text-green-700"
                      )}>
                        <strong>RPL Block:</strong> {ring.rpl_owner_device ? `${ring.rpl_owner_device}:${ring.rpl_owner_port}` : '—'}
                        {ring.protection_active && ' (SWITCHED!)'}
                      </span>
                      <span><strong>Ring State:</strong> {ring.ring_state || '—'}</span>
                      <span><strong>Ring Status:</strong> {ring.ring_status || '—'}</span>
                    </div>
                  </div>
                  
                  {/* Ring Segments Table - actual inter-switch links */}
                  {ring.ring_segments && ring.ring_segments.length > 0 ? (
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-2 pl-12 text-left text-xs font-medium text-gray-500">#</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">A-End (Device:Port)</th>
                          <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Link</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Z-End (Device:Port)</th>
                          <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {ring.ring_segments.map((seg, idx) => (
                          <tr 
                            key={idx} 
                            className={cn(
                              "hover:bg-blue-50 cursor-pointer transition-colors",
                              seg.is_rpl_block && "bg-yellow-50"
                            )}
                            onClick={() => setSelectedSegment({ ...seg, ring_name: ring.name, segment_number: idx + 1 })}
                          >
                            <td className="px-4 py-2 pl-12 text-gray-500 text-xs">
                              {idx + 1}
                            </td>
                            <td className="px-4 py-2 font-mono text-xs font-medium">
                              <span className={cn(
                                seg.is_rpl_block && seg.rpl_blocked_port === 'a_end' 
                                  ? "text-red-600 bg-red-100 px-1 rounded" 
                                  : "text-gray-900"
                              )}>
                                {seg.a_end ? `${seg.a_end}:${seg.a_end_port || '?'}` : '—'}
                              </span>
                              {seg.is_rpl_block && seg.rpl_blocked_port === 'a_end' && (
                                <span className="ml-2 text-red-600 text-xs font-bold">🔒 BLOCKED</span>
                              )}
                            </td>
                            <td className="px-4 py-2 text-center">
                              {seg.is_rpl_block ? (
                                <span className="text-red-500 font-bold">✕</span>
                              ) : (
                                <span className="text-green-500">↔</span>
                              )}
                            </td>
                            <td className="px-4 py-2 text-gray-900 font-mono text-xs font-medium">
                              {seg.z_end ? `${seg.z_end}:${seg.z_end_port || '?'}` : '—'}
                            </td>
                            <td className="px-4 py-2 text-center">
                              {seg.is_rpl_block ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                                  Blocked
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                                  Active
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="px-4 py-4 text-center text-sm text-gray-500">
                      No ring segments found
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="p-3 text-center text-sm text-gray-500 border-t bg-gray-50">
        {rings.length} rings ({rings.reduce((sum, r) => sum + (r.segment_count || 0), 0)} total segments)
      </div>
      
      {/* Segment Detail Modal */}
      {selectedSegment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setSelectedSegment(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Ring Segment Details
              </h3>
              <button 
                onClick={() => setSelectedSegment(null)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Ring</div>
                <div className="font-semibold text-gray-900">{selectedSegment.ring_name}</div>
              </div>
              
              <div className="text-center text-sm text-gray-500">Segment #{selectedSegment.segment_number}</div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className={cn(
                  "rounded-lg p-4",
                  selectedSegment.is_rpl_block ? "bg-red-50 border-2 border-red-300" : "bg-green-50"
                )}>
                  <div className="text-xs text-gray-500 mb-1">A-End Device</div>
                  <div className="font-semibold text-gray-900">{selectedSegment.a_end}</div>
                  <div className="text-sm text-gray-600 mt-1">Port: {selectedSegment.a_end_port}</div>
                  {selectedSegment.is_rpl_block && (
                    <div className="mt-2 text-red-600 text-xs font-bold flex items-center gap-1">
                      🔒 RPL BLOCKED
                    </div>
                  )}
                </div>
                
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-xs text-gray-500 mb-1">Z-End Device</div>
                  <div className="font-semibold text-gray-900">{selectedSegment.z_end}</div>
                  <div className="text-sm text-gray-600 mt-1">Port: {selectedSegment.z_end_port}</div>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Link Status</div>
                <div className="flex items-center gap-2">
                  {selectedSegment.is_rpl_block ? (
                    <>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-700">
                        Blocked
                      </span>
                      <span className="text-sm text-gray-600">
                        Traffic is blocked on this segment (RPL protection)
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-700">
                        Active
                      </span>
                      <span className="text-sm text-gray-600">
                        Traffic is flowing through this segment
                      </span>
                    </>
                  )}
                </div>
              </div>
              
              {selectedSegment.is_rpl_block && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-yellow-800">RPL Block Location</div>
                      <div className="text-sm text-yellow-700 mt-1">
                        This is the Ring Protection Link (RPL) block point. Under normal operation, 
                        traffic is blocked here to prevent loops. If a failure occurs elsewhere in the ring, 
                        this block will be removed to restore connectivity.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t bg-gray-50 rounded-b-xl">
              <button
                onClick={() => setSelectedSegment(null)}
                className="w-full px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RingDetail({ label, value, className }) {
  return (
    <div className={className}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium text-gray-900">{value || '—'}</p>
    </div>
  );
}

function SortableHeader({ field, label, sortField, sortDir, onSort }) {
  return (
    <th
      className="px-4 py-3 text-left font-semibold text-gray-700 cursor-pointer hover:bg-gray-100"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown className={cn(
          "h-3 w-3",
          sortField === field ? "text-blue-500" : "text-gray-300"
        )} />
      </div>
    </th>
  );
}

function StateIndicator({ state }) {
  const s = (state || '').toLowerCase();
  if (s === 'up') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
        <CheckCircle className="h-3 w-3" /> Up
      </span>
    );
  }
  if (s === 'down') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <XCircle className="h-3 w-3" /> Down
      </span>
    );
  }
  // For ring FTP links and other services without state, show N/A instead of Unknown
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
      —
    </span>
  );
}

function ServiceClassIcon({ serviceClass }) {
  const cls = (serviceClass || '').toLowerCase();
  if (cls === 'ring') return <Circle className="h-4 w-4 text-purple-500" />;
  if (cls === 'evc') return <Cable className="h-4 w-4 text-blue-500" />;
  if (cls === 'ethernet') return <Network className="h-4 w-4 text-green-500" />;
  if (cls === 'vlan') return <Radio className="h-4 w-4 text-orange-500" />;
  if (cls.includes('access') || cls.includes('transit')) return <Zap className="h-4 w-4 text-yellow-500" />;
  return <Activity className="h-4 w-4 text-gray-400" />;
}

export default MCPServicesPage;
