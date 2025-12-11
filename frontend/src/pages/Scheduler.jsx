import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { fetchApi, formatLocalTime, formatShortTime } from "../lib/utils";
import { PageHeader } from "../components/layout";
import { 
  CalendarClock, 
  RefreshCw, 
  Play, 
  Trash2, 
  Clock, 
  CheckCircle, 
  XCircle,
  Search,
  Filter,
  ChevronDown,
  X,
  Tag,
  ExternalLink,
  History,
  Settings,
  AlertCircle,
  Loader2
} from "lucide-react";
import { cn } from "../lib/utils";

export function Scheduler() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [loadingExecutions, setLoadingExecutions] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [showRawPayload, setShowRawPayload] = useState(false);
  const runOnceRefreshRef = useRef(null);

  // Filter state
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // all, enabled, disabled
  const [tagFilter, setTagFilter] = useState(null);
  const [filterDropdownOpen, setFilterDropdownOpen] = useState(false);
  const [sortConfig, setSortConfig] = useState({ key: "name", direction: "asc" });

  // Helper functions
  const formatSchedule = (job) => {
    if (job.schedule_type === "cron") {
      return job.cron_expression || "cron";
    }
    if (job.interval_seconds) {
      const secs = job.interval_seconds;
      if (secs < 60) return `Every ${secs}s`;
      if (secs < 3600) return `Every ${Math.round(secs / 60)}m`;
      if (secs < 86400) return `Every ${Math.round(secs / 3600)}h`;
      return `Every ${Math.round(secs / 86400)}d`;
    }
    return "—";
  };

  const getJobStatus = (job) => {
    if (!job.enabled) return "disabled";
    // Check if running based on recent execution
    const recentExec = executions.find(e => e.status === "running");
    if (recentExec && selectedJob === job.name) return "running";
    return "idle";
  };

  // Extract all unique tags from jobs
  const allTags = useMemo(() => {
    const tags = new Set();
    jobs.forEach(job => {
      (job.tags || []).forEach(tag => tags.add(tag));
    });
    return Array.from(tags).sort();
  }, [jobs]);

  // Filter and sort jobs
  const filteredJobs = useMemo(() => {
    let filtered = jobs;

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(job => 
        job.name?.toLowerCase().includes(searchLower) ||
        (job.tags || []).some(t => t.toLowerCase().includes(searchLower))
      );
    }

    // Status filter
    if (statusFilter === "enabled") {
      filtered = filtered.filter(job => job.enabled);
    } else if (statusFilter === "disabled") {
      filtered = filtered.filter(job => !job.enabled);
    }

    // Tag filter
    if (tagFilter) {
      filtered = filtered.filter(job => (job.tags || []).includes(tagFilter));
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
      let aVal, bVal;
      switch (sortConfig.key) {
        case "tags":
          aVal = (a.tags || []).join(",").toLowerCase();
          bVal = (b.tags || []).join(",").toLowerCase();
          break;
        case "name":
          aVal = a.name?.toLowerCase() || "";
          bVal = b.name?.toLowerCase() || "";
          break;
        case "schedule":
          aVal = a.interval_seconds || 0;
          bVal = b.interval_seconds || 0;
          break;
        case "next_run":
          aVal = a.next_run_at || "";
          bVal = b.next_run_at || "";
          break;
        case "last_run":
          aVal = a.last_run_at || "";
          bVal = b.last_run_at || "";
          break;
        case "enabled":
          aVal = a.enabled ? 1 : 0;
          bVal = b.enabled ? 1 : 0;
          break;
        default:
          aVal = a.name?.toLowerCase() || "";
          bVal = b.name?.toLowerCase() || "";
      }
      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [jobs, search, statusFilter, tagFilter, sortConfig]);

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === "asc" ? "desc" : "asc"
    }));
  };

  const SortHeader = ({ label, sortKey, className = "" }) => (
    <th
      className={cn(
        "px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer hover:bg-gray-100 select-none",
        className
      )}
      onClick={() => handleSort(sortKey)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortConfig.key === sortKey && (
          <span className="text-blue-600">{sortConfig.direction === "asc" ? "↑" : "↓"}</span>
        )}
      </div>
    </th>
  );

  // Count running jobs
  const runningCount = useMemo(() => {
    return jobs.filter(j => j.enabled).length;
  }, [jobs]);

  // API functions
  const loadJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi("/api/scheduler/jobs");
      setJobs(data.jobs || []);
    } catch (err) {
      console.error("Failed to load scheduler jobs", err);
      setError(err.message || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async (jobName) => {
    if (!jobName) {
      setExecutions([]);
      setSelectedExecution(null);
      setShowRawPayload(false);
      return;
    }
    try {
      setLoadingExecutions(true);
      setError(null);
      const data = await fetchApi(
        `/api/scheduler/jobs/${encodeURIComponent(jobName)}/executions?limit=50`
      );
      setExecutions(data.executions || []);
    } catch (err) {
      console.error("Failed to load executions", err);
      setError(err.message || "Failed to load executions");
    } finally {
      setLoadingExecutions(false);
    }
  };

  const handleSelectJob = (job) => {
    if (!job) return;
    setSelectedJob(job);
    setSelectedExecution(null);
    setShowRawPayload(false);
    loadExecutions(job.name);
  };

  const handleCloseDetail = () => {
    setSelectedJob(null);
    setExecutions([]);
    setSelectedExecution(null);
    setShowRawPayload(false);
  };

  const clearExecutions = async () => {
    if (!selectedJob) return;
    try {
      setError(null);
      await fetchApi(
        `/api/scheduler/jobs/${encodeURIComponent(selectedJob.name)}/executions/clear`,
        { method: "POST", body: JSON.stringify({}) }
      );
      await loadExecutions(selectedJob.name);
    } catch (err) {
      console.error("Failed to clear executions", err);
      setError(err.message || "Failed to clear executions");
    }
  };

  useEffect(() => {
    loadJobs();
    return () => {
      if (runOnceRefreshRef.current) {
        clearTimeout(runOnceRefreshRef.current);
      }
    };
  }, []);

  const handleDeleteJob = async (name) => {
    if (!name) return;
    if (!window.confirm(`Delete scheduler job "${name}"? This cannot be undone.`)) {
      return;
    }
    try {
      setError(null);
      await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      if (selectedJob?.name === name) {
        handleCloseDetail();
      }
      await loadJobs();
    } catch (err) {
      console.error("Failed to delete scheduler job", err);
      setError(err.message || "Failed to delete job");
    }
  };

  const handleToggleEnabled = async (job, e) => {
    e?.stopPropagation();
    try {
      setError(null);
      await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(job.name)}/toggle`, {
        method: "POST",
        body: JSON.stringify({ enabled: !job.enabled }),
      });
      await loadJobs();
    } catch (err) {
      console.error("Failed to toggle job", err);
      setError(err.message || "Failed to toggle job");
    }
  };

  const handleRunOnce = async (name) => {
    try {
      setError(null);
      await fetchApi(
        `/api/scheduler/jobs/${encodeURIComponent(name)}/run-once`,
        { method: "POST" }
      );
      await loadJobs();
      await loadExecutions(name);

      if (runOnceRefreshRef.current) {
        clearTimeout(runOnceRefreshRef.current);
      }
      runOnceRefreshRef.current = setTimeout(() => {
        if (selectedJob?.name === name) {
          loadExecutions(name);
        }
      }, 6000);
    } catch (err) {
      console.error("Failed to run job once", err);
      setError(err.message || "Failed to run job");
    }
  };

  const handleRefresh = async () => {
    await loadJobs();
    if (selectedJob) {
      await loadExecutions(selectedJob.name);
    }
  };

  const openJobDefinition = (job) => {
    if (!job || job.task_name !== "opsconductor.job.run") return;
    const jobDefId = job?.config?.job_definition_id;
    if (!jobDefId) return;
    navigate(`/jobs/definitions?id=${encodeURIComponent(jobDefId)}`);
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Job Scheduler"
        description={`${jobs.length} jobs • ${runningCount} enabled`}
        icon={CalendarClock}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/jobs/definitions')}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Settings className="w-4 h-4" />
              Job Definitions
            </button>
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-hidden p-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm h-full flex flex-col overflow-hidden">
          {/* Table Header with Search and Filters */}
          <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search jobs..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
                />
              </div>

              {/* Status Filter */}
              <div className="relative">
                <button
                  onClick={() => setFilterDropdownOpen(!filterDropdownOpen)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border transition-colors",
                    statusFilter !== "all" || tagFilter
                      ? "bg-blue-50 border-blue-200 text-blue-700"
                      : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
                  )}
                >
                  <Filter className="w-4 h-4" />
                  <span>
                    {statusFilter === "all" && !tagFilter ? "All Jobs" : 
                     statusFilter !== "all" ? statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1) :
                     tagFilter ? `Tag: ${tagFilter}` : "Filter"}
                  </span>
                  <ChevronDown className="w-3 h-3" />
                </button>

                {filterDropdownOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setFilterDropdownOpen(false)} />
                    <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-20 py-1">
                      <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase">Status</div>
                      {["all", "enabled", "disabled"].map((status) => (
                        <button
                          key={status}
                          onClick={() => { setStatusFilter(status); setFilterDropdownOpen(false); }}
                          className={cn(
                            "w-full text-left px-3 py-2 text-sm hover:bg-gray-50",
                            statusFilter === status && "bg-blue-50 text-blue-700"
                          )}
                        >
                          {status.charAt(0).toUpperCase() + status.slice(1)}
                        </button>
                      ))}
                      
                      {allTags.length > 0 && (
                        <>
                          <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase border-t border-gray-100 mt-1">Tags</div>
                          {allTags.map((tag) => (
                            <button
                              key={tag}
                              onClick={() => { setTagFilter(tagFilter === tag ? null : tag); setFilterDropdownOpen(false); }}
                              className={cn(
                                "w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center gap-2",
                                tagFilter === tag && "bg-blue-50 text-blue-700"
                              )}
                            >
                              <Tag className="w-3 h-3" />
                              {tag}
                            </button>
                          ))}
                        </>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Clear Filters */}
              {(statusFilter !== "all" || tagFilter) && (
                <button
                  onClick={() => { setStatusFilter("all"); setTagFilter(null); }}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                >
                  <X className="w-3 h-3" />
                  Clear
                </button>
              )}
            </div>

            {/* Right side - Count */}
            <div className="text-sm text-gray-500">
              {filteredJobs.length} jobs
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border-b border-red-200 text-red-800 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          {/* Job Table */}
          <div className="flex-1 overflow-auto">
            <table className="min-w-full text-sm table-fixed">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <SortHeader label="Tags" sortKey="tags" className="w-40" />
                  <SortHeader label="Job Name" sortKey="name" className="w-48" />
                  <SortHeader label="Schedule" sortKey="schedule" className="w-28" />
                  <SortHeader label="Next Run" sortKey="next_run" className="w-36" />
                  <SortHeader label="Last Run" sortKey="last_run" className="w-36" />
                  <SortHeader label="Enabled" sortKey="enabled" className="w-24 text-center" />
                </tr>
              </thead>
              <tbody>
                {loading && filteredJobs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading jobs...
                    </td>
                  </tr>
                )}
                {!loading && filteredJobs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                      {jobs.length === 0 ? "No scheduled jobs yet." : "No jobs match your filters."}
                    </td>
                  </tr>
                )}
                {filteredJobs.map((job) => (
                  <tr
                    key={job.name}
                    className={cn(
                      "border-t border-gray-100 hover:bg-blue-50 cursor-pointer transition-colors",
                      selectedJob?.name === job.name && "bg-blue-50"
                    )}
                    onClick={() => handleSelectJob(job)}
                  >
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {(job.tags || []).length > 0 ? (
                          (job.tags || []).map((tag) => (
                            <span
                              key={tag}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700"
                            >
                              {tag}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div 
                        className="font-medium text-gray-900 truncate max-w-[180px]" 
                        title={job.name}
                      >
                        {job.name}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-gray-600 text-xs">
                      {formatSchedule(job)}
                    </td>
                    <td className="px-3 py-2 text-gray-600 text-xs whitespace-nowrap">
                      {formatShortTime(job.next_run_at)}
                    </td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        {job.last_run_status === "success" && <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />}
                        {job.last_run_status === "failed" && <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />}
                        <span className="text-gray-600">{formatShortTime(job.last_run_at)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={(e) => handleToggleEnabled(job, e)}
                        className={cn(
                          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1",
                          job.enabled ? "bg-green-500" : "bg-gray-300"
                        )}
                      >
                        <span
                          className={cn(
                            "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
                            job.enabled ? "translate-x-6" : "translate-x-1"
                          )}
                        />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Job Detail Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" onClick={handleCloseDetail}>
          <div 
            className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-[calc(100vh-2rem)] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h2 className="text-xl font-semibold text-gray-900 truncate">{selectedJob.name}</h2>
                <div className="flex items-center gap-3 mt-1">
                  <span className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                    selectedJob.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                  )}>
                    {selectedJob.enabled ? "Enabled" : "Disabled"}
                  </span>
                  <span className="text-sm text-gray-500">{formatSchedule(selectedJob)}</span>
                  {(selectedJob.tags || []).map((tag) => (
                    <span key={tag} className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={handleCloseDetail}
                className="p-2 hover:bg-gray-100 rounded-lg ml-4"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column - Actions & Info */}
                <div className="space-y-4">
                  {/* Quick Actions */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Actions</h3>
                    <div className="space-y-2">
                      <button
                        onClick={() => handleRunOnce(selectedJob.name)}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                      >
                        <Play className="w-4 h-4" />
                        Run Now
                      </button>
                      <button
                        onClick={(e) => handleToggleEnabled(selectedJob, e)}
                        className={cn(
                          "w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border",
                          selectedJob.enabled
                            ? "text-orange-700 bg-orange-50 border-orange-200 hover:bg-orange-100"
                            : "text-green-700 bg-green-50 border-green-200 hover:bg-green-100"
                        )}
                      >
                        {selectedJob.enabled ? "Disable Job" : "Enable Job"}
                      </button>
                      {selectedJob.task_name === "opsconductor.job.run" && selectedJob.config?.job_definition_id && (
                        <button
                          onClick={() => openJobDefinition(selectedJob)}
                          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100"
                        >
                          <ExternalLink className="w-4 h-4" />
                          Edit Job Definition
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteJob(selectedJob.name)}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-200 rounded-lg hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete Job
                      </button>
                    </div>
                  </div>

                  {/* Schedule Info */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Schedule Details</h3>
                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Schedule Type</div>
                        <div className="text-gray-900 font-medium mt-0.5">
                          {selectedJob.schedule_type === "cron" ? "Cron Expression" : "Interval"}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">
                          {selectedJob.schedule_type === "cron" ? "Expression" : "Interval"}
                        </div>
                        <div className="text-gray-900 font-mono mt-0.5">
                          {selectedJob.schedule_type === "cron" 
                            ? selectedJob.cron_expression 
                            : formatSchedule(selectedJob)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Next Run</div>
                        <div className="text-gray-900 mt-0.5">{formatLocalTime(selectedJob.next_run_at)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Last Run</div>
                        <div className="text-gray-900 mt-0.5">{formatLocalTime(selectedJob.last_run_at)}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column - Execution History */}
                <div className="lg:col-span-2">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                      <History className="w-4 h-4" />
                      Execution History
                    </h3>
                    {executions.length > 0 && (
                      <button
                        onClick={clearExecutions}
                        className="text-xs text-red-600 hover:text-red-700 hover:underline"
                      >
                        Clear History
                      </button>
                    )}
                  </div>

                  {loadingExecutions ? (
                    <div className="text-center py-8 text-gray-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading executions...
                    </div>
                  ) : executions.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 bg-gray-50 rounded-lg">
                      No executions recorded yet
                    </div>
                  ) : (
                    <div className="border border-gray-200 rounded-lg overflow-hidden">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Started</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Duration</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Details</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {executions.slice(0, 15).map((exec) => {
                            const duration = exec.started_at && exec.finished_at
                              ? ((new Date(exec.finished_at) - new Date(exec.started_at)) / 1000).toFixed(1) + "s"
                              : "—";
                            return (
                              <tr
                                key={exec.id}
                                onClick={() => setSelectedExecution(exec)}
                                className="hover:bg-gray-50 cursor-pointer"
                              >
                                <td className="px-3 py-2">
                                  <span className={cn(
                                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                                    exec.status === "success" && "bg-green-100 text-green-700",
                                    exec.status === "failed" && "bg-red-100 text-red-700",
                                    exec.status === "running" && "bg-blue-100 text-blue-700",
                                    !["success", "failed", "running"].includes(exec.status) && "bg-gray-100 text-gray-600"
                                  )}>
                                    {exec.status === "success" && <CheckCircle className="w-3 h-3" />}
                                    {exec.status === "failed" && <XCircle className="w-3 h-3" />}
                                    {exec.status === "running" && <Loader2 className="w-3 h-3 animate-spin" />}
                                    {exec.status}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-gray-600 text-xs whitespace-nowrap">
                                  {formatShortTime(exec.started_at)}
                                </td>
                                <td className="px-3 py-2 text-gray-600 text-xs font-mono">
                                  {duration}
                                </td>
                                <td className="px-3 py-2 text-xs text-blue-600 hover:underline">
                                  View
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      {executions.length > 15 && (
                        <div className="px-3 py-2 text-xs text-gray-500 bg-gray-50 border-t border-gray-200">
                          Showing 15 of {executions.length} executions
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Execution Detail Modal */}
      {selectedExecution && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => { setSelectedExecution(null); setShowRawPayload(false); }}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {selectedExecution.status === "success" && <CheckCircle className="w-5 h-5 text-green-500" />}
                {selectedExecution.status === "failed" && <XCircle className="w-5 h-5 text-red-500" />}
                <span className="font-semibold text-gray-800">Execution #{selectedExecution.id}</span>
              </div>
              <button
                onClick={() => { setSelectedExecution(null); setShowRawPayload(false); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4 space-y-4 overflow-y-auto text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500">Started</div>
                  <div className="font-mono">{formatLocalTime(selectedExecution.started_at)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Finished</div>
                  <div className="font-mono">{formatLocalTime(selectedExecution.finished_at)}</div>
                </div>
              </div>

              {selectedExecution.error_message && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="text-xs text-red-600 font-semibold mb-1">Error</div>
                  <pre className="text-xs text-red-800 whitespace-pre-wrap">{selectedExecution.error_message}</pre>
                </div>
              )}

              {selectedExecution.result && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-500 font-semibold">Result</span>
                    <button
                      onClick={() => setShowRawPayload(!showRawPayload)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      {showRawPayload ? "Hide Raw" : "Show Raw"}
                    </button>
                  </div>
                  {showRawPayload ? (
                    <pre className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs overflow-x-auto max-h-64">
                      {JSON.stringify(selectedExecution.result, null, 2)}
                    </pre>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-3 text-xs space-y-2">
                      {selectedExecution.result.job_name && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Job</span>
                          <span>{selectedExecution.result.job_name}</span>
                        </div>
                      )}
                      {selectedExecution.result.duration_seconds && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Duration</span>
                          <span>{selectedExecution.result.duration_seconds.toFixed(2)}s</span>
                        </div>
                      )}
                      {selectedExecution.result.actions_completed !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Actions</span>
                          <span>{selectedExecution.result.actions_completed}/{selectedExecution.result.total_actions}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Scheduler;