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
  Server,
  Cpu,
  Zap,
  Info,
  ChevronRight,
  Circle
} from "lucide-react";
import { cn, fetchApi, formatTimeOnly, formatElapsedDuration, formatRelativeTime } from "../lib/utils";
import { PageHeader } from "../components/layout";
import { useAuth } from "../contexts/AuthContext";

export function ActiveJobs() {
  const { getAuthHeader } = useAuth();
  const [activeJobs, setActiveJobs] = useState([]);
  const [queuedJobs, setQueuedJobs] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobProgress, setJobProgress] = useState({});
  const refreshInterval = useRef(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const loadData = async () => {
    try {
      setError(null);
      
      // Fetch queue status which includes active/reserved/scheduled counts and worker details
      const status = await fetchApi("/api/scheduler/queues", { headers: getAuthHeader() });
      const statusData = status.data || status;
      setQueueStatus(statusData);
      
      // Fetch scheduled jobs for upcoming list
      const scheduledJobs = await fetchApi("/api/scheduler/jobs?enabled=true&limit=50", { headers: getAuthHeader() });
      const now = new Date();
      const upcoming = (scheduledJobs.data || scheduledJobs.jobs || [])
        .filter(j => j.next_run_at && new Date(j.next_run_at) > now)
        .sort((a, b) => new Date(a.next_run_at) - new Date(b.next_run_at))
        .slice(0, 20);
      setQueuedJobs(upcoming);
      
      // Fetch running executions from recent executions endpoint
      try {
        const execResponse = await fetchApi("/api/scheduler/executions/recent?limit=50&status=running", { headers: getAuthHeader() });
        const execData = execResponse.data || execResponse;
        const jobs = Array.isArray(execData) ? execData : [];
        setActiveJobs(jobs);
        
        // Fetch progress for each running job
        const progressPromises = jobs.map(async (job) => {
          try {
            const progressRes = await fetchApi(`/api/scheduler/executions/${job.id}/progress`, { headers: getAuthHeader() });
            return { id: job.id, progress: progressRes.data?.progress || progressRes.progress };
          } catch {
            return { id: job.id, progress: null };
          }
        });
        const progressResults = await Promise.all(progressPromises);
        const progressMap = {};
        progressResults.forEach(p => { if (p.progress) progressMap[p.id] = p.progress; });
        setJobProgress(progressMap);
      } catch {
        setActiveJobs([]);
      }
      
      setLastUpdate(new Date());
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

        {/* Queue Status Summary - Updated every refresh */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className={cn(
            "rounded-lg border p-4 transition-all",
            activeJobs.length > 0 ? "bg-blue-50 border-blue-200" : "bg-white border-gray-200"
          )}>
            <div className="flex items-center gap-2 text-blue-600 mb-1">
              <Loader2 className={cn("w-4 h-4", activeJobs.length > 0 && "animate-spin")} />
              <span className="text-xs font-medium uppercase tracking-wide">Running</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{activeJobs.length}</div>
            <div className="text-[10px] text-gray-500 mt-1">From DB executions</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-orange-600 mb-1">
              <Cpu className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Celery Active</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{queueStatus?.active_total || 0}</div>
            <div className="text-[10px] text-gray-500 mt-1">Tasks in workers</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-purple-600 mb-1">
              <Clock className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Reserved</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{queueStatus?.reserved_total || 0}</div>
            <div className="text-[10px] text-gray-500 mt-1">Queued for workers</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-indigo-600 mb-1">
              <Timer className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Scheduled</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{queuedJobs.length}</div>
            <div className="text-[10px] text-gray-500 mt-1">Upcoming jobs</div>
          </div>
          <div className={cn(
            "rounded-lg border p-4",
            (queueStatus?.workers?.length || 0) > 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
          )}>
            <div className={cn(
              "flex items-center gap-2 mb-1",
              (queueStatus?.workers?.length || 0) > 0 ? "text-green-600" : "text-red-600"
            )}>
              <Server className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Workers</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{queueStatus?.workers?.length || 0}</div>
            <div className="text-[10px] text-gray-500 mt-1">
              {(queueStatus?.workers?.length || 0) > 0 ? "Online" : "No workers!"}
            </div>
          </div>
        </div>
        
        {/* Last Update indicator */}
        <div className="text-[10px] text-gray-400 mb-4 flex items-center gap-2">
          <Zap className="w-3 h-3" />
          Last updated: {lastUpdate.toLocaleTimeString()} • Auto-refresh every 5s
        </div>

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
            <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
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
                  <div 
                    key={job.id} 
                    className={cn(
                      "px-4 py-3 hover:bg-blue-50 cursor-pointer transition-colors",
                      selectedJob?.id === job.id && "bg-blue-50 border-l-4 border-blue-500"
                    )}
                    onClick={() => setSelectedJob(selectedJob?.id === job.id ? null : job)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-3 h-3 text-blue-500 animate-spin flex-shrink-0" />
                          <span className="text-sm font-medium text-gray-900 truncate" title={job.job_name || job.task_id}>
                            {cleanJobName(job.job_name || job.task_id)}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-[11px] text-gray-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Started: {formatTimeOnly(job.started_at)}
                          </span>
                          <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded text-blue-600">
                            {formatElapsedDuration(job.started_at)}
                          </span>
                          {job.worker && (
                            <span className="flex items-center gap-1 text-gray-400">
                              <Server className="w-3 h-3" />
                              {job.worker.split('@')[0]}
                            </span>
                          )}
                        </div>
                        {/* Progress bar */}
                        {jobProgress[job.id] && (
                          <div className="mt-2">
                            <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                              <span>{jobProgress[job.id].current_step || jobProgress[job.id].message || 'Processing...'}</span>
                              <span>{jobProgress[job.id].percent || 0}%</span>
                            </div>
                            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-blue-500 transition-all duration-300"
                                style={{ width: `${jobProgress[job.id].percent || 0}%` }}
                              />
                            </div>
                          </div>
                        )}
                        {/* Expanded details */}
                        {selectedJob?.id === job.id && (
                          <div className="mt-3 pt-3 border-t border-gray-200 space-y-3 text-xs">
                            {/* Live Steps */}
                            {jobProgress[job.id]?.steps?.length > 0 && (
                              <div>
                                <span className="text-gray-500 font-medium">Execution Steps:</span>
                                <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                                  {jobProgress[job.id].steps.map((step, idx) => (
                                    <div key={idx} className="flex items-center gap-2 py-1 px-2 bg-gray-50 rounded">
                                      {step.status === 'running' ? (
                                        <Loader2 className="w-3 h-3 text-blue-500 animate-spin flex-shrink-0" />
                                      ) : step.status === 'completed' ? (
                                        <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                                      ) : step.status === 'failed' ? (
                                        <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                                      ) : (
                                        <Circle className="w-3 h-3 text-gray-300 flex-shrink-0" />
                                      )}
                                      <span className={cn(
                                        "flex-1 truncate",
                                        step.status === 'running' && "text-blue-700 font-medium",
                                        step.status === 'completed' && "text-gray-600",
                                        step.status === 'failed' && "text-red-600"
                                      )}>
                                        {step.name}
                                      </span>
                                      {step.data?.duration_ms && (
                                        <span className="text-[10px] text-gray-400">
                                          {step.data.duration_ms}ms
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <span className="text-gray-500">Task ID:</span>
                                <div className="font-mono text-[10px] text-gray-700 truncate" title={job.task_id}>{job.task_id}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Task Name:</span>
                                <div className="font-mono text-[10px] text-gray-700 truncate" title={job.task_name}>{job.task_name}</div>
                              </div>
                            </div>
                            {job.config && Object.keys(job.config).length > 0 && (
                              <div>
                                <span className="text-gray-500">Config:</span>
                                <pre className="mt-1 p-2 bg-gray-50 rounded text-[10px] overflow-x-auto max-h-32">
                                  {JSON.stringify(job.config, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); setSelectedJob(selectedJob?.id === job.id ? null : job); }}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                          title="View details"
                        >
                          <Info className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCancelJob(job.id); }}
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                          title="Cancel job"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </div>
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
