import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { ScrollText, RefreshCw, Download, Trash2, Search, Filter } from 'lucide-react';

export function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    source: 'all',
    level: 'all',
    search: '',
  });

  // Generate sample logs
  useEffect(() => {
    const sampleLogs = [
      { id: 1, timestamp: '2025-12-10 11:30:45', level: 'INFO', source: 'worker', message: 'Task completed: interface_discovery for 58 targets' },
      { id: 2, timestamp: '2025-12-10 11:30:44', level: 'DEBUG', source: 'scheduler', message: 'Tick: 0 jobs enqueued' },
      { id: 3, timestamp: '2025-12-10 11:30:40', level: 'WARN', source: 'ssh', message: 'Connection timeout: 10.127.0.105 after 30s' },
      { id: 4, timestamp: '2025-12-10 11:30:35', level: 'INFO', source: 'api', message: 'POST /api/scheduler/jobs/system.interface.discovery/run-once 200' },
      { id: 5, timestamp: '2025-12-10 11:30:30', level: 'ERROR', source: 'worker', message: 'Task failed: optical_power_monitoring - timeout exceeded' },
      { id: 6, timestamp: '2025-12-10 11:30:25', level: 'INFO', source: 'database', message: 'Inserted 24 interface records for 10.127.0.156' },
      { id: 7, timestamp: '2025-12-10 11:30:20', level: 'DEBUG', source: 'ssh', message: 'SSH connection established to 10.127.0.156' },
      { id: 8, timestamp: '2025-12-10 11:30:15', level: 'INFO', source: 'worker', message: 'Starting task: interface_discovery' },
    ];
    setLogs(sampleLogs);
  }, []);

  const levelColors = {
    DEBUG: 'bg-gray-100 text-gray-600',
    INFO: 'bg-blue-100 text-blue-700',
    WARN: 'bg-yellow-100 text-yellow-700',
    ERROR: 'bg-red-100 text-red-700',
  };

  const filteredLogs = logs.filter(log => {
    if (filters.source !== 'all' && log.source !== filters.source) return false;
    if (filters.level !== 'all' && log.level !== filters.level) return false;
    if (filters.search && !log.message.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });

  return (
    <PageLayout module="system">
      <PageHeader
        title="System Logs"
        description="View and search system log entries"
        icon={ScrollText}
        actions={
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
              <Download className="w-4 h-4" />
              Export
            </button>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-4">
        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
            </div>
            <select
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value })}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Sources</option>
              <option value="worker">Worker</option>
              <option value="scheduler">Scheduler</option>
              <option value="api">API</option>
              <option value="ssh">SSH</option>
              <option value="database">Database</option>
            </select>
            <select
              value={filters.level}
              onChange={(e) => setFilters({ ...filters, level: e.target.value })}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Levels</option>
              <option value="DEBUG">Debug</option>
              <option value="INFO">Info</option>
              <option value="WARN">Warning</option>
              <option value="ERROR">Error</option>
            </select>
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="Search logs..."
                className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Logs Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Timestamp</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Level</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Source</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-mono text-xs">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-600 whitespace-nowrap">{log.timestamp}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[log.level]}`}>
                        {log.level}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-600">{log.source}</td>
                    <td className="px-4 py-2 text-gray-800">{log.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-sm text-gray-500">
            <span>Showing {filteredLogs.length} of {logs.length} entries</span>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1 border border-gray-300 rounded hover:bg-white">Previous</button>
              <button className="px-3 py-1 border border-gray-300 rounded hover:bg-white">Next</button>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default LogsPage;
