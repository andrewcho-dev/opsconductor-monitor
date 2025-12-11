import React, { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../../components/layout';
import { 
  Users, 
  RefreshCw,
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
  Clock,
  AlertTriangle,
  Activity
} from 'lucide-react';
import { fetchApi } from '../../lib/utils';

export function WorkersPage() {
  const [loading, setLoading] = useState(true);
  const [queueStatus, setQueueStatus] = useState(null);
  const [error, setError] = useState(null);

  const loadQueues = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi('/api/scheduler/queues');
      setQueueStatus(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueues();
    const interval = setInterval(loadQueues, 10000);
    return () => clearInterval(interval);
  }, []);

  const workers = queueStatus?.workers || [];
  const workerDetails = queueStatus?.worker_details || {};

  return (
    <PageLayout module="system">
      <PageHeader
        title="Workers & Queues"
        description="Monitor Celery workers and task queues"
        icon={Users}
        actions={
          <button
            onClick={loadQueues}
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

        {/* Queue Summary */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Queue Summary
            </h2>
            <span className="text-xs text-gray-400">Auto-refreshes every 10s</span>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-gray-900">
                  {queueStatus?.active_total || 0}
                </div>
                <div className="text-sm text-gray-500 mt-1">Active Tasks</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-gray-900">
                  {queueStatus?.reserved_total || 0}
                </div>
                <div className="text-sm text-gray-500 mt-1">Reserved</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-gray-900">
                  {queueStatus?.scheduled_total || 0}
                </div>
                <div className="text-sm text-gray-500 mt-1">Scheduled</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-gray-900">
                  {workers.length}
                </div>
                <div className="text-sm text-gray-500 mt-1">Workers Online</div>
              </div>
            </div>
          </div>
        </div>

        {/* Workers List */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Workers ({workers.length})
            </h2>
          </div>
          
          {workers.length === 0 ? (
            <div className="p-8 text-center">
              <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 mb-1">No Workers Online</h3>
              <p className="text-sm text-gray-500">
                Make sure the Celery worker service is running.
              </p>
              <code className="mt-3 inline-block px-3 py-2 bg-gray-100 rounded text-xs font-mono">
                sudo systemctl start opsconductor-worker
              </code>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {workers.map((worker) => {
                const details = workerDetails[worker] || {};
                const concurrency = details.concurrency || 0;
                const active = details.active || 0;
                const reserved = details.reserved || 0;
                const scheduled = details.scheduled || 0;
                
                return (
                  <div key={worker} className="p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        </div>
                        <div>
                          <div className="font-mono text-sm font-medium text-gray-900">
                            {worker}
                          </div>
                          <div className="text-xs text-gray-500">
                            Concurrency: {concurrency} processes
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                          Online
                        </span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div className="bg-blue-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-blue-700 mb-1">
                          <Activity className="w-4 h-4" />
                          <span className="font-medium">Active</span>
                        </div>
                        <div className="text-2xl font-bold text-blue-900">{active}</div>
                      </div>
                      <div className="bg-yellow-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-yellow-700 mb-1">
                          <Clock className="w-4 h-4" />
                          <span className="font-medium">Reserved</span>
                        </div>
                        <div className="text-2xl font-bold text-yellow-900">{reserved}</div>
                      </div>
                      <div className="bg-purple-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-purple-700 mb-1">
                          <Clock className="w-4 h-4" />
                          <span className="font-medium">Scheduled</span>
                        </div>
                        <div className="text-2xl font-bold text-purple-900">{scheduled}</div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-gray-700 mb-1">
                          <Users className="w-4 h-4" />
                          <span className="font-medium">Processes</span>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">{concurrency}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Beat Scheduler Status */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Beat Scheduler
            </h2>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Clock className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <div className="font-medium text-gray-900">Scheduler Active</div>
                <div className="text-sm text-gray-500">
                  Tick interval: 5 seconds
                </div>
              </div>
              <div className="ml-auto">
                <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full">
                  Running
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default WorkersPage;
