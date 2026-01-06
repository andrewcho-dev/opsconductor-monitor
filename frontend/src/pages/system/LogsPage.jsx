import React, { useState, useEffect, useCallback } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { ScrollText, RefreshCw, Download, Search, Filter, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchApi, formatDetailedTime } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';

export function LogsPage() {
  const { getAuthHeader } = useAuth();
  const [logs, setLogs] = useState([]);
  const [sources, setSources] = useState([]);
  const [levels, setLevels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  
  // Pagination
  const [total, setTotal] = useState(0);
  const [limit] = useState(100);
  const [offset, setOffset] = useState(0);
  
  // Filters
  const [filters, setFilters] = useState({
    source: 'all',
    level: 'all',
    search: '',
  });
  
  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Fetch logs from API
  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (filters.source !== 'all') params.append('source', filters.source);
      if (filters.level !== 'all') params.append('level', filters.level);
      if (filters.search) params.append('search', filters.search);
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());
      
      const queryString = params.toString();
      const url = queryString ? `/system/v1/logs?${queryString}` : '/system/v1/logs';
      
      const response = await fetchApi(url, { headers: getAuthHeader() });
      
      // Handle both wrapped and direct array format
      const logsData = response?.data || response;
      const logsList = logsData?.logs || (Array.isArray(logsData) ? logsData : []);
      setLogs(logsList);
      setTotal(logsData?.total || logsList.length);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      setError(err.message || 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  }, [filters, limit, offset]);

  // Fetch metadata (sources, levels)
  const fetchMetadata = async () => {
    try {
      const [sourcesRes, levelsRes, statsRes] = await Promise.all([
        fetchApi('/system/v1/logs/sources', { headers: getAuthHeader() }),
        fetchApi('/system/v1/logs/levels', { headers: getAuthHeader() }),
        fetchApi('/system/v1/logs/stats?hours=24', { headers: getAuthHeader() }),
      ]);
      
      // Handle both wrapped and direct formats
      const srcData = sourcesRes?.data || sourcesRes;
      const lvlData = levelsRes?.data || levelsRes;
      const statsData = statsRes?.data || statsRes;
      setSources(srcData?.sources || (Array.isArray(srcData) ? srcData : []));
      setLevels(lvlData?.levels || (Array.isArray(lvlData) ? lvlData : []));
      setStats(statsData);
    } catch (err) {
      console.error('Failed to fetch log metadata:', err);
    }
  };

  // Initial load
  useEffect(() => {
    fetchMetadata();
  }, []);

  // Fetch logs when filters or pagination change
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchLogs]);

  // Handle filter changes - reset pagination
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setOffset(0);
  };

  // Export logs
  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.source !== 'all') params.append('source', filters.source);
      if (filters.level !== 'all') params.append('level', filters.level);
      if (filters.search) params.append('search', filters.search);
      
      const queryString = params.toString();
      const url = queryString ? `/system/v1/logs/export?${queryString}` : '/system/v1/logs/export';
      
      window.open(url, '_blank');
    } catch (err) {
      console.error('Failed to export logs:', err);
    }
  };

  const levelColors = {
    DEBUG: 'bg-gray-100 text-gray-600',
    INFO: 'bg-blue-100 text-blue-700',
    WARNING: 'bg-yellow-100 text-yellow-700',
    ERROR: 'bg-red-100 text-red-700',
    CRITICAL: 'bg-purple-100 text-purple-700',
  };

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  return (
    <PageLayout module="system">
      <PageHeader
        title="System Logs"
        description={`${total.toLocaleString()} log entries`}
        icon={ScrollText}
        actions={
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Auto-refresh
            </label>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-4">
        {/* Stats Summary */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-lg border border-gray-200 p-3">
              <div className="text-2xl font-bold text-gray-900">{stats.total || 0}</div>
              <div className="text-xs text-gray-500">Total (24h)</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-3">
              <div className="text-2xl font-bold text-blue-600">{stats.by_level?.INFO || 0}</div>
              <div className="text-xs text-gray-500">Info</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-3">
              <div className="text-2xl font-bold text-yellow-600">{stats.by_level?.WARNING || 0}</div>
              <div className="text-xs text-gray-500">Warnings</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-3">
              <div className="text-2xl font-bold text-red-600">{stats.by_level?.ERROR || 0}</div>
              <div className="text-xs text-gray-500">Errors</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-3">
              <div className="text-2xl font-bold text-purple-600">{stats.by_level?.CRITICAL || 0}</div>
              <div className="text-xs text-gray-500">Critical</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
            </div>
            <select
              value={filters.source}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Sources</option>
              {sources.map(source => (
                <option key={source.id} value={source.id}>{source.name}</option>
              ))}
            </select>
            <select
              value={filters.level}
              onChange={(e) => handleFilterChange('level', e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Levels</option>
              {levels.map(level => (
                <option key={level.id} value={level.id}>{level.name}</option>
              ))}
            </select>
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                placeholder="Search logs..."
                className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <div>
              <div className="font-medium text-red-800">Failed to load logs</div>
              <div className="text-sm text-red-600">{error}</div>
            </div>
          </div>
        )}

        {/* Logs Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Timestamp</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Level</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Source</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Category</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">User</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-mono text-xs">
                {loading && logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading logs...
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No logs found matching your filters
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-gray-600 whitespace-nowrap">
                        {formatDetailedTime(log.timestamp)}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[log.level] || 'bg-gray-100 text-gray-600'}`}>
                          {log.level}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{log.source}</td>
                      <td className="px-4 py-2 text-gray-500">{log.category || '-'}</td>
                      <td className="px-4 py-2 text-gray-600">
                        {log.details?.user?.username || log.details?.user?.display_name || '-'}
                      </td>
                      <td className="px-4 py-2 text-gray-800 max-w-xl truncate" title={log.message}>
                        {log.message}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-sm text-gray-500">
            <span>
              Showing {offset + 1}-{Math.min(offset + limit, total)} of {total.toLocaleString()} entries
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="flex items-center gap-1 px-3 py-1 border border-gray-300 rounded hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <span className="px-2">
                Page {currentPage} of {totalPages || 1}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="flex items-center gap-1 px-3 py-1 border border-gray-300 rounded hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default LogsPage;
