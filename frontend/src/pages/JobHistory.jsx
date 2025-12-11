import React, { useState, useEffect, useMemo } from "react";
import { 
  History, 
  RefreshCw, 
  Search,
  Filter,
  ChevronDown,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  X
} from "lucide-react";
import { cn, fetchApi, formatLocalTime, formatShortTime, formatDuration } from "../lib/utils";
import { PageHeader } from "../components/layout";

export function JobHistory() {
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [showRawPayload, setShowRawPayload] = useState(false);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [filterDropdownOpen, setFilterDropdownOpen] = useState(false);

  const loadExecutions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // First get all jobs, then fetch executions for each
      const jobsData = await fetchApi("/api/scheduler/jobs");
      const jobs = jobsData.jobs || [];
      
      // Fetch executions for each job (limit to first 20 jobs to avoid too many requests)
      const allExecutions = [];
      for (const job of jobs.slice(0, 20)) {
        try {
          const execData = await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(job.name)}/executions?limit=20`);
          const jobExecs = (execData.executions || []).map(e => ({
            ...e,
            job_name: job.name
          }));
          allExecutions.push(...jobExecs);
        } catch {
          // Skip jobs that fail to load executions
        }
      }
      
      // Sort by started_at descending
      allExecutions.sort((a, b) => {
        const aTime = a.started_at ? new Date(a.started_at) : new Date(0);
        const bTime = b.started_at ? new Date(b.started_at) : new Date(0);
        return bTime - aTime;
      });
      
      setExecutions(allExecutions.slice(0, 200));
    } catch (err) {
      setError(err.message || "Failed to load execution history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecutions();
  }, []);

  const filteredExecutions = useMemo(() => {
    let filtered = executions;

    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(exec => 
        exec.job_name?.toLowerCase().includes(searchLower) ||
        exec.task_id?.toLowerCase().includes(searchLower)
      );
    }

    if (statusFilter !== "all") {
      filtered = filtered.filter(exec => exec.status === statusFilter);
    }

    return filtered;
  }, [executions, search, statusFilter]);

  // Strip UUID suffix from job names
  const cleanJobName = (name) => {
    if (!name) return "—";
    return name.replace(/_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, '')
               .replace(/_[0-9a-f-]{20,}$/i, '');
  };

  // Stats
  const stats = useMemo(() => {
    const total = executions.length;
    const success = executions.filter(e => e.status === "success").length;
    const failed = executions.filter(e => e.status === "failed").length;
    const running = executions.filter(e => e.status === "running").length;
    return { total, success, failed, running };
  }, [executions]);

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Job History"
        description="Execution history and error logs"
        icon={History}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={loadExecutions}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-hidden p-4">
        {/* Stats Bar */}
        <div className="flex items-center gap-4 mb-4 text-sm">
          <span className="text-gray-600">
            <strong>{stats.total}</strong> total executions
          </span>
          <span className="text-green-600">
            <CheckCircle className="w-4 h-4 inline mr-1" />
            {stats.success} success
          </span>
          <span className="text-red-600">
            <XCircle className="w-4 h-4 inline mr-1" />
            {stats.failed} failed
          </span>
          {stats.running > 0 && (
            <span className="text-blue-600">
              <Loader2 className="w-4 h-4 inline mr-1 animate-spin" />
              {stats.running} running
            </span>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm h-full flex flex-col overflow-hidden">
          {/* Filters */}
          <div className="flex items-center gap-3 p-3 border-b border-gray-200 bg-gray-50">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by job name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="relative">
              <button
                onClick={() => setFilterDropdownOpen(!filterDropdownOpen)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-white"
              >
                <Filter className="w-4 h-4 text-gray-500" />
                {statusFilter === "all" ? "All Status" : statusFilter}
                <ChevronDown className="w-4 h-4 text-gray-400" />
              </button>
              {filterDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
                  {["all", "success", "failed", "running"].map((status) => (
                    <button
                      key={status}
                      onClick={() => {
                        setStatusFilter(status);
                        setFilterDropdownOpen(false);
                      }}
                      className={cn(
                        "w-full text-left px-3 py-2 text-sm hover:bg-gray-50",
                        statusFilter === status && "bg-blue-50 text-blue-700"
                      )}
                    >
                      {status === "all" ? "All Status" : status}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border-b border-red-200 text-red-800 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          {/* Table */}
          <div className="flex-1 overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-24">Status</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Job Name</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-40">Started</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-24">Duration</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-20">Details</th>
                </tr>
              </thead>
              <tbody>
                {loading && filteredExecutions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading execution history...
                    </td>
                  </tr>
                )}
                {!loading && filteredExecutions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      {executions.length === 0 ? "No execution history yet." : "No executions match your filters."}
                    </td>
                  </tr>
                )}
                {filteredExecutions.map((exec) => (
                  <tr
                    key={exec.id}
                    className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedExecution(exec)}
                  >
                    <td className="px-4 py-2">
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
                    <td className="px-4 py-2">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-xs" title={exec.job_name}>{cleanJobName(exec.job_name)}</div>
                    </td>
                    <td className="px-4 py-2 text-gray-600 text-xs whitespace-nowrap">
                      {formatShortTime(exec.started_at)}
                    </td>
                    <td className="px-4 py-2 text-gray-600 text-xs font-mono">
                      {formatDuration(exec.started_at, exec.finished_at)}
                    </td>
                    <td className="px-4 py-2 text-xs text-blue-600 hover:underline">
                      View
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Execution Detail Modal */}
      {selectedExecution && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => { setSelectedExecution(null); setShowRawPayload(false); }}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {selectedExecution.status === "success" && <CheckCircle className="w-5 h-5 text-green-500" />}
                {selectedExecution.status === "failed" && <XCircle className="w-5 h-5 text-red-500" />}
                <span className="font-semibold text-gray-800">
                  {selectedExecution.job_name || `Execution #${selectedExecution.id}`}
                </span>
              </div>
              <button
                onClick={() => { setSelectedExecution(null); setShowRawPayload(false); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4 space-y-4 overflow-y-auto text-sm">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-xs text-gray-500">Status</div>
                  <div className={cn(
                    "font-medium",
                    selectedExecution.status === "success" && "text-green-600",
                    selectedExecution.status === "failed" && "text-red-600"
                  )}>
                    {selectedExecution.status}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Started</div>
                  <div className="font-mono text-xs">{formatLocalTime(selectedExecution.started_at)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Finished</div>
                  <div className="font-mono text-xs">{formatLocalTime(selectedExecution.finished_at)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Duration</div>
                  <div className="font-mono">{formatDuration(selectedExecution.started_at, selectedExecution.finished_at)}</div>
                </div>
              </div>

              {selectedExecution.error_message && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="text-xs text-red-600 font-semibold mb-1">Error Message</div>
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
                      {showRawPayload ? "Show Summary" : "Show Raw JSON"}
                    </button>
                  </div>
                  {showRawPayload ? (
                    <pre className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs overflow-x-auto max-h-96 font-mono">
                      {JSON.stringify(selectedExecution.result, null, 2)}
                    </pre>
                  ) : (
                    <div className="space-y-3">
                      {/* Summary stats */}
                      <div className="bg-gray-50 rounded-lg p-3 text-xs grid grid-cols-2 md:grid-cols-4 gap-3">
                        {selectedExecution.result.job_name && (
                          <div>
                            <div className="text-gray-500">Job</div>
                            <div className="font-medium">{selectedExecution.result.job_name}</div>
                          </div>
                        )}
                        {selectedExecution.result.duration_seconds !== undefined && (
                          <div>
                            <div className="text-gray-500">Duration</div>
                            <div className="font-medium">{selectedExecution.result.duration_seconds.toFixed(3)}s</div>
                          </div>
                        )}
                        {selectedExecution.result.actions_completed !== undefined && (
                          <div>
                            <div className="text-gray-500">Actions</div>
                            <div className="font-medium">{selectedExecution.result.actions_completed}/{selectedExecution.result.total_actions}</div>
                          </div>
                        )}
                        {selectedExecution.result.execution_meta?.worker_hostname && (
                          <div>
                            <div className="text-gray-500">Worker</div>
                            <div className="font-medium truncate">{selectedExecution.result.execution_meta.worker_hostname}</div>
                          </div>
                        )}
                      </div>

                      {/* Action results - dynamically find action_* keys */}
                      {Object.entries(selectedExecution.result)
                        .filter(([key]) => key.startsWith('action_'))
                        .map(([actionKey, actionData]) => (
                          <div key={actionKey} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                            <div className="text-xs font-semibold text-blue-800 mb-2 flex items-center justify-between">
                              <span>{actionData.action_type || actionKey.replace('action_', '')}</span>
                              <span className="text-blue-600">
                                {actionData.successful_results !== undefined && `${actionData.successful_results}/${actionData.targets_processed} targets`}
                              </span>
                            </div>
                            {actionData.results && actionData.results.length > 0 && (
                              <div className="space-y-1 max-h-48 overflow-y-auto">
                                {actionData.results.slice(0, 20).map((r, idx) => (
                                  <div key={idx} className="text-xs bg-white rounded px-2 py-1 flex items-center justify-between">
                                    <span className="font-mono">{r.ip_address || r.hostname || r.target || JSON.stringify(r).slice(0, 50)}</span>
                                    <span className={cn(
                                      "px-1.5 py-0.5 rounded text-[10px] font-medium",
                                      r.ping_status === 'online' && "bg-green-100 text-green-700",
                                      r.ping_status === 'offline' && "bg-red-100 text-red-700",
                                      r.status === 'success' && "bg-green-100 text-green-700",
                                      r.status === 'error' && "bg-red-100 text-red-700",
                                      !r.ping_status && !r.status && "bg-gray-100 text-gray-600"
                                    )}>
                                      {r.ping_status || r.status || 'done'}
                                    </span>
                                  </div>
                                ))}
                                {actionData.results.length > 20 && (
                                  <div className="text-[10px] text-gray-500 text-center">
                                    ... and {actionData.results.length - 20} more
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}

                      {/* Errors */}
                      {selectedExecution.result.errors?.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                          <div className="text-xs text-red-600 font-semibold mb-1">Errors ({selectedExecution.result.errors.length})</div>
                          {selectedExecution.result.errors.slice(0, 10).map((err, i) => (
                            <div key={i} className="text-xs text-red-700">{typeof err === 'string' ? err : JSON.stringify(err)}</div>
                          ))}
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

export default JobHistory;
