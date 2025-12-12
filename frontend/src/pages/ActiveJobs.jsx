import React, { useState, useEffect, useRef } from "react";
import { 
  Activity, 
  RefreshCw, 
  Pause, 
  XCircle, 
  Play,
  Clock,
  Loader2,
  AlertCircle,
  CheckCircle,
  Timer,
  Server
} from "lucide-react";
import { cn, fetchApi, formatTimeOnly, formatElapsedDuration, formatRelativeTime } from "../lib/utils";
import { PageHeader } from "../components/layout";

export function ActiveJobs() {
  const [activeJobs, setActiveJobs] = useState([]);
  const [queuedJobs, setQueuedJobs] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const refreshInterval = useRef(null);

  const loadData = async () => {
    try {
      setError(null);
      
      // Fetch queue status which includes active/reserved/scheduled counts
      const status = await fetchApi("/api/scheduler/queues");
      setQueueStatus(status);
      
      // Fetch scheduled jobs for upcoming list
      const scheduledJobs = await fetchApi("/api/scheduler/jobs?enabled=true&limit=50");
      const now = new Date();
      const upcoming = (scheduledJobs.data || scheduledJobs.jobs || [])
        .filter(j => j.next_run_at && new Date(j.next_run_at) > now)
        .sort((a, b) => new Date(a.next_run_at) - new Date(b.next_run_at))
        .slice(0, 20);
      setQueuedJobs(upcoming);
      
      // For active jobs, we'd need an executions endpoint with status=running
      // For now, show empty if not available
      setActiveJobs([]);
      
    } catch (err) {
      setError(err.message || "Failed to load job status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh every 5 seconds
    refreshInterval.current = setInterval(loadData, 5000);
    return () => {
      if (refreshInterval.current) clearInterval(refreshInterval.current);
    };
  }, []);

  const handleCancelJob = async (executionId) => {
    if (!window.confirm("Cancel this running job?")) return;
    try {
      await fetchApi(`/api/scheduler/executions/${executionId}/cancel`, { method: "POST" });
      loadData();
    } catch (err) {
      alert(`Failed to cancel job: ${err.message}`);
    }
  };

  const handlePauseQueued = async (jobName) => {
    if (!window.confirm("Pause this scheduled job?")) return;
    try {
      await fetchApi(`/api/scheduler/jobs/${jobName}/toggle`, {
        method: "POST",
        body: JSON.stringify({ enabled: false })
      });
      loadData();
    } catch (err) {
      alert(`Failed to pause job: ${err.message}`);
    }
  };

  // Strip UUID suffix from job names like "System: Interface Scan_33333333-3333-..."
  const cleanJobName = (name) => {
    if (!name) return "—";
    // Remove UUID pattern at the end (underscore followed by UUID-like string)
    return name.replace(/_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, '')
               .replace(/_[0-9a-f-]{20,}$/i, ''); // Also catch partial UUIDs
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Active Jobs"
        description="Real-time view of running and queued jobs"
        icon={Activity}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Queue Status Summary */}
        {queueStatus && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-blue-600 mb-1">
                <Play className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wide">Running</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{queueStatus.active_total || queueStatus.active || 0}</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-orange-600 mb-1">
                <Clock className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wide">Reserved</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{queueStatus.reserved_total || queueStatus.reserved || 0}</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-purple-600 mb-1">
                <Timer className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wide">Scheduled</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{queueStatus.scheduled_total || queueStatus.scheduled || 0}</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-green-600 mb-1">
                <Server className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wide">Workers</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{queueStatus.active_by_worker ? Object.keys(queueStatus.active_by_worker).length : 0}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Running Jobs */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                {activeJobs.length > 0 ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 text-blue-500" />
                )}
                Running Jobs
              </h2>
              <span className="text-xs text-gray-500">{activeJobs.length} active</span>
            </div>
            <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
              {loading && activeJobs.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                  Loading...
                </div>
              ) : activeJobs.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-400" />
                  No jobs currently running
                </div>
              ) : (
                activeJobs.map((job) => (
                  <div key={job.id} className="px-3 py-2 hover:bg-gray-50">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-gray-900 truncate" title={job.job_name || job.task_id}>{cleanJobName(job.job_name || job.task_id)}</div>
                        <div className="text-[10px] text-gray-500">
                          {formatTimeOnly(job.started_at)} • {formatElapsedDuration(job.started_at)}
                        </div>
                      </div>
                      <button
                        onClick={() => handleCancelJob(job.id)}
                        className="ml-2 p-1.5 text-red-600 hover:bg-red-50 rounded"
                        title="Cancel job"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Queued Jobs */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                <Clock className="w-4 h-4 text-orange-500" />
                Upcoming Jobs
              </h2>
              <span className="text-xs text-gray-500">{queuedJobs.length} scheduled</span>
            </div>
            <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
              {loading && queuedJobs.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                  Loading...
                </div>
              ) : queuedJobs.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <Clock className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  No upcoming jobs scheduled
                </div>
              ) : (
                queuedJobs.map((job) => (
                  <div key={job.name} className="px-3 py-2 hover:bg-gray-50">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs font-medium text-gray-900 truncate flex-1" title={job.name}>{cleanJobName(job.name)}</div>
                      <div className="text-[10px] text-gray-500 whitespace-nowrap">
                        {formatTimeOnly(job.next_run_at)}
                      </div>
                      <button
                        onClick={() => handlePauseQueued(job.name)}
                        className="p-1.5 text-orange-600 hover:bg-orange-50 rounded"
                        title="Pause job"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ActiveJobs;
