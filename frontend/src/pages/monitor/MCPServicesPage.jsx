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
  const [rings, setRings] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [sortField, setSortField] = useState('name');
  const [sortDir, setSortDir] = useState('asc');
  const [expandedRings, setExpandedRings] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setError(null);
      const [summaryRes, servicesRes, ringsRes] = await Promise.all([
        fetchApi('/api/mcp/services/summary', { headers: getAuthHeader() }),
        fetchApi('/api/mcp/services?limit=500', { headers: getAuthHeader() }),
        fetchApi('/api/mcp/services/rings', { headers: getAuthHeader() }),
      ]);

      if (summaryRes.success) setSummary(summaryRes.data);
      if (servicesRes.success) setServices(servicesRes.data.services || []);
      if (ringsRes.success) setRings(ringsRes.data.rings || []);
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
          services={filteredServices}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          classFilter={classFilter}
          setClassFilter={setClassFilter}
          stateFilter={stateFilter}
          setStateFilter={setStateFilter}
          serviceClasses={serviceClasses}
          sortField={sortField}
          sortDir={sortDir}
          handleSort={handleSort}
        />
      )}

      {activeTab === 'rings' && (
        <RingsTab
          rings={rings}
          expandedRings={expandedRings}
          toggleRingExpanded={toggleRingExpanded}
        />
      )}
    </PageLayout>
  );
}

function SummaryCard({ title, value, icon: Icon, color, subtitle, alert }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    yellow: 'bg-yellow-50 text-yellow-600',
  };

  return (
    <div className={cn(
      "bg-white rounded-xl border p-5 shadow-sm",
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
  services,
  searchTerm,
  setSearchTerm,
  classFilter,
  setClassFilter,
  stateFilter,
  setStateFilter,
  serviceClasses,
  sortField,
  sortDir,
  handleSort
}) {
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
          <option value="unknown">Unknown</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <SortableHeader field="name" label="Name" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
              <SortableHeader field="service_class" label="Class" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
              <SortableHeader field="operation_state" label="State" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
              <SortableHeader field="admin_state" label="Admin" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Layer Rate</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-700">Capacity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {services.slice(0, 100).map((svc, idx) => (
              <tr key={svc.id || idx} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <ServiceClassIcon serviceClass={svc.service_class} />
                    <span className="font-medium text-gray-900 truncate max-w-[250px]" title={svc.name}>
                      {svc.name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">{svc.service_class || '—'}</td>
                <td className="px-4 py-3">
                  <StateIndicator state={svc.operation_state} />
                </td>
                <td className="px-4 py-3">
                  <span className={cn(
                    "text-xs",
                    svc.admin_state?.toLowerCase() === 'up' ? "text-green-600" : "text-gray-500"
                  )}>
                    {svc.admin_state || '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{svc.layer_rate || '—'}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-600">
                  {svc.total_capacity ? `${svc.total_capacity} ${svc.capacity_units || ''}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {services.length > 100 && (
          <div className="p-4 text-center text-sm text-gray-500 border-t">
            Showing 100 of {services.length} services
          </div>
        )}
      </div>
    </div>
  );
}

function RingsTab({ rings, expandedRings, toggleRingExpanded }) {
  return (
    <div className="space-y-4">
      {rings.length === 0 ? (
        <div className="bg-white rounded-xl border p-8 text-center">
          <Circle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No G.8032 rings configured</p>
        </div>
      ) : (
        rings.map(ring => (
          <div key={ring.id} className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <button
              onClick={() => toggleRingExpanded(ring.id)}
              className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className={cn(
                  "w-4 h-4 rounded-full",
                  ring.ring_state === 'OK' && ring.ring_status === 'OK'
                    ? "bg-green-500"
                    : "bg-red-500"
                )} />
                <div className="text-left">
                  <p className="font-semibold text-gray-900">{ring.name}</p>
                  <p className="text-sm text-gray-500">
                    Ring ID: {ring.ring_id} • {ring.ring_type} • {ring.logical_ring}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex gap-2">
                  <span className={cn(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                    ring.ring_state === 'OK'
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  )}>
                    State: {ring.ring_state || 'Unknown'}
                  </span>
                  <span className={cn(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                    ring.ring_status === 'OK'
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  )}>
                    Status: {ring.ring_status || 'Unknown'}
                  </span>
                </div>
                {expandedRings[ring.id] ? (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </button>

            {expandedRings[ring.id] && (
              <div className="px-5 pb-5 border-t bg-gray-50">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
                  <RingDetail label="Ring ID" value={ring.ring_id} />
                  <RingDetail label="Ring Type" value={ring.ring_type} />
                  <RingDetail label="Logical Ring" value={ring.logical_ring} />
                  <RingDetail label="Virtual Ring" value={ring.virtual_ring} />
                  <RingDetail label="RAPS VID" value={ring.raps_vid} />
                  <RingDetail label="Revertive" value={ring.revertive} />
                  <RingDetail label="Wait to Restore" value={ring.wait_to_restore ? `${ring.wait_to_restore} min` : null} />
                  <RingDetail label="Guard Time" value={ring.guard_time ? `${ring.guard_time} ms` : null} />
                  <RingDetail label="Hold-off Time" value={ring.hold_off_time ? `${ring.hold_off_time} ms` : null} />
                  <RingDetail label="Members" value={ring.ring_members} className="col-span-2 md:col-span-3" />
                </div>
              </div>
            )}
          </div>
        ))
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
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      {state || 'Unknown'}
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
