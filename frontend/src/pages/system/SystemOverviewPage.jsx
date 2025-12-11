import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { 
  Activity, 
  Server, 
  Database, 
  Cpu, 
  HardDrive,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw
} from 'lucide-react';
import { fetchApi, formatTimeOnly, formatShortTime, formatDuration } from '../../lib/utils';

function StatusCard({ title, icon: Icon, status, details, color }) {
  const statusColors = {
    online: 'bg-green-100 text-green-700 border-green-200',
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    offline: 'bg-red-100 text-red-700 border-red-200',
    unknown: 'bg-gray-100 text-gray-700 border-gray-200',
  };

  const statusIcons = {
    online: CheckCircle,
    warning: AlertTriangle,
    offline: XCircle,
    unknown: Clock,
  };

  const StatusIcon = statusIcons[status] || Clock;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <Icon className="w-4 h-4 text-blue-600" />
          </div>
          <span className="font-semibold text-gray-900">{title}</span>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${statusColors[status]}`}>
          <StatusIcon className="w-3 h-3" />
          <span className="capitalize">{status}</span>
        </div>
      </div>
      <div className="space-y-1 text-sm text-gray-600">
        {details.map((detail, i) => (
          <div key={i} className="flex justify-between">
            <span>{detail.label}</span>
            <span className="font-medium text-gray-900">{detail.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SystemOverviewPage() {
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState(null);
  const [queueStatus, setQueueStatus] = useState(null);
  const [recentExecutions, setRecentExecutions] = useState([]);
  const [error, setError] = useState(null);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load queue status from existing endpoint
      const queues = await fetchApi('/api/scheduler/queues');
      setQueueStatus(queues);
      
      // Build system status from available data
      setSystemStatus({
        backend: { status: 'online' },
        database: { status: 'online' },
        redis: { status: queues.workers?.length > 0 ? 'online' : 'warning' },
        workers: {
          count: queues.workers?.length || 0,
          active: queues.active_total || 0,
          scheduled: queues.scheduled_total || 0,
        }
      });
      
      // Load recent executions
      try {
        const execData = await fetchApi('/api/scheduler/executions/recent?limit=15');
        setRecentExecutions(execData.executions || []);
      } catch {
        // Non-critical, just show empty
        setRecentExecutions([]);
      }
    } catch (err) {
      setError(err.message);
      setSystemStatus({
        backend: { status: 'online' },
        database: { status: 'unknown' },
        redis: { status: 'unknown' },
        workers: { count: 0, active: 0, scheduled: 0 }
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <PageLayout module="system">
      <PageHeader
        title="System Overview"
        description="Monitor system health and infrastructure status"
        icon={Activity}
        actions={
          <button
            onClick={loadStatus}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
            {error}
          </div>
        )}

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard
            title="Backend API"
            icon={Server}
            status={systemStatus?.backend?.status || 'unknown'}
            details={[
              { label: 'Port', value: '5000' },
              { label: 'Workers', value: '4' },
            ]}
          />
          <StatusCard
            title="Celery Workers"
            icon={Cpu}
            status={systemStatus?.workers?.count > 0 ? 'online' : 'warning'}
            details={[
              { label: 'Workers', value: systemStatus?.workers?.count || 0 },
              { label: 'Active Tasks', value: systemStatus?.workers?.active || 0 },
              { label: 'Scheduled', value: systemStatus?.workers?.scheduled || 0 },
            ]}
          />
          <StatusCard
            title="Database"
            icon={Database}
            status={systemStatus?.database?.status || 'unknown'}
            details={[
              { label: 'Type', value: 'PostgreSQL' },
              { label: 'Status', value: 'Connected' },
            ]}
          />
          <StatusCard
            title="Redis"
            icon={HardDrive}
            status={systemStatus?.redis?.status || 'unknown'}
            details={[
              { label: 'Port', value: '6379' },
              { label: 'Role', value: 'Message Broker' },
            ]}
          />
        </div>

        {/* Worker Details */}
        {queueStatus?.workers?.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Active Workers
              </h2>
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {queueStatus.workers.map((worker) => {
                const details = queueStatus.worker_details?.[worker] || {};
                const activeTasks = details.active_tasks || [];
                return (
                  <div key={worker} className="border border-gray-200 rounded-lg p-3">
                    <div className="font-mono text-sm text-gray-800 truncate mb-2" title={worker}>
                      {worker}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                      <div>
                        <div className="text-gray-500">Concurrency</div>
                        <div className="font-semibold">{details.concurrency || '—'}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Active</div>
                        <div className="font-semibold">{details.active || 0}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Reserved</div>
                        <div className="font-semibold">{details.reserved || 0}</div>
                      </div>
                    </div>
                    {/* Active Tasks */}
                    {activeTasks.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Running Tasks</div>
                        <div className="space-y-1">
                          {activeTasks.map((task, idx) => {
                            const taskName = task.job_name || task.name?.split('.').pop() || 'unknown';
                            const startTime = task.time_start ? formatTimeOnly(new Date(task.time_start * 1000)) : null;
                            return (
                              <div key={task.id || idx} className="bg-blue-50 rounded px-2 py-1 text-xs">
                                <div className="font-medium text-blue-800 truncate" title={task.name}>
                                  {taskName}
                                </div>
                                {startTime && (
                                  <div className="text-[10px] text-blue-600">Started: {startTime}</div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                    {details.active > 0 && activeTasks.length === 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <div className="text-[10px] text-gray-400 italic">Task details loading...</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Recent Activity
              </h2>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {recentExecutions.length === 0 ? (
                <div className="p-4 text-sm text-gray-500">No recent activity</div>
              ) : (
                <table className="min-w-full text-xs">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Time</th>
                      <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Job</th>
                      <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Duration</th>
                      <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Worker</th>
                      <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {recentExecutions.map((exec) => (
                      <tr key={exec.id} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                          {formatShortTime(exec.started_at)}
                        </td>
                        <td className="px-3 py-2 text-gray-900 font-medium truncate max-w-[150px]" title={exec.job_name}>
                          {exec.job_display_name || exec.job_name}
                        </td>
                        <td className="px-3 py-2 text-gray-600 font-mono">
                          {formatDuration(exec.started_at, exec.finished_at)}
                        </td>
                        <td className="px-3 py-2 text-gray-500 truncate max-w-[100px]" title={exec.worker}>
                          {exec.worker ? exec.worker.split('@')[0] : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            exec.status === 'success' ? 'bg-green-100 text-green-700' :
                            exec.status === 'failed' ? 'bg-red-100 text-red-700' :
                            exec.status === 'running' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {exec.status === 'success' && <CheckCircle className="w-3 h-3" />}
                            {exec.status === 'failed' && <XCircle className="w-3 h-3" />}
                            {exec.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                System Alerts
              </h2>
            </div>
            <div className="p-4 text-sm text-gray-500">
              <p>No active alerts</p>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default SystemOverviewPage;
