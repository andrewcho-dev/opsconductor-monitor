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
  const [auditTrail, setAuditTrail] = useState([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

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
      const jobs = jobsData.data || jobsData.jobs || [];
      
      // Fetch executions for each job (limit to first 20 jobs to avoid too many requests)
      const allExecutions = [];
      for (const job of jobs.slice(0, 20)) {
        try {
          const execData = await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(job.name)}/executions?limit=20`);
          const jobExecs = (execData.data || execData.executions || []).map(e => ({
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

  // Load audit trail when execution is selected
  const loadAuditTrail = async (executionId) => {
    if (!executionId) return;
    
    try {
      setLoadingAudit(true);
      const data = await fetchApi(`/api/scheduler/executions/${executionId}/audit`);
      setAuditTrail(data.data || []);
    } catch (err) {
      console.error('Failed to load audit trail:', err);
      setAuditTrail([]);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    if (selectedExecution?.id) {
      loadAuditTrail(selectedExecution.id);
    } else {
      setAuditTrail([]);
    }
  }, [selectedExecution]);

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
            <table className="min-w-full text-sm font-mono">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-40">Timestamp</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-56">Job Name</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-24">Duration</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-24">Status</th>
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
                    className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer text-xs"
                    onClick={() => setSelectedExecution(exec)}
                  >
                    <td className="px-4 py-2 text-gray-600 whitespace-nowrap">
                      {formatShortTime(exec.started_at)}
                    </td>
                    <td className="px-4 py-2 w-56">
                      <div className="text-gray-900 truncate" title={exec.job_name}>{cleanJobName(exec.job_name)}</div>
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {formatDuration(exec.started_at, exec.finished_at)}
                    </td>
                    <td className={cn(
                      "px-4 py-2",
                      exec.status === "success" && "text-green-600",
                      exec.status === "failed" && "text-red-600",
                      exec.status === "running" && "text-blue-600",
                      !["success", "failed", "running"].includes(exec.status) && "text-gray-600"
                    )}>
                      {exec.status}
                    </td>
                    <td className="px-4 py-2 text-blue-600 hover:underline">
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
                              <div className="space-y-1 max-h-64 overflow-y-auto">
                                {actionData.results.map((r, idx) => {
                                  const deviceIp = r.ip_address || r.target;
                                  const hasOptical = r.optical_interfaces > 0;
                                  return (
                                  <div key={idx} className="text-xs bg-white rounded px-2 py-1 flex items-center justify-between">
                                    <span className="font-mono">{deviceIp || r.hostname || JSON.stringify(r).slice(0, 50)}</span>
                                    <div className="flex items-center gap-2">
                                      {/* Show optical interfaces count with link if present */}
                                      {r.optical_interfaces !== undefined && (
                                        hasOptical && deviceIp ? (
                                          <a 
                                            href={`/inventory/devices/${deviceIp}?tab=optical`}
                                            onClick={(e) => e.stopPropagation()}
                                            className="text-[10px] text-purple-600 font-medium hover:underline"
                                          >
                                            {r.optical_interfaces} optical →
                                          </a>
                                        ) : (
                                          <span className="text-[10px] text-gray-400">
                                            {r.optical_interfaces} optical
                                          </span>
                                        )
                                      )}
                                      {/* Show interface count if present */}
                                      {r.interfaces !== undefined && (
                                        <span className="text-[10px] text-gray-500">
                                          {r.interfaces} intf
                                        </span>
                                      )}
                                      {/* Status badge */}
                                      <span className={cn(
                                        "px-1.5 py-0.5 rounded text-[10px] font-medium",
                                        (r.ping_status === 'online' || r.success === true) && "bg-green-100 text-green-700",
                                        (r.ping_status === 'offline' || r.success === false) && "bg-red-100 text-red-700",
                                        r.status === 'success' && "bg-green-100 text-green-700",
                                        r.status === 'error' && "bg-red-100 text-red-700",
                                        r.snmp_status === 'YES' && "bg-green-100 text-green-700",
                                        r.snmp_status === 'NO' && "bg-red-100 text-red-700",
                                        r.ssh_status === 'YES' && "bg-green-100 text-green-700",
                                        r.ssh_status === 'NO' && "bg-red-100 text-red-700",
                                        !r.ping_status && r.success === undefined && !r.status && !r.snmp_status && !r.ssh_status && "bg-gray-100 text-gray-600"
                                      )}>
                                        {r.ping_status || (r.success === true ? 'success' : r.success === false ? 'failed' : null) || r.status || r.snmp_status || r.ssh_status || 'done'}
                                      </span>
                                    </div>
                                  </div>
                                  );
                                })}
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

              {/* Audit Trail - shows ALL events for this execution */}
              <div className="border-t border-gray-200 pt-4 mt-4">
                <div className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Audit Trail (All Events)
                  {loadingAudit && <Loader2 className="w-3 h-3 animate-spin" />}
                </div>
                {auditTrail.length > 0 ? (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {auditTrail.map((event, idx) => (
                      <div 
                        key={idx} 
                        className={cn(
                          "text-xs rounded px-2 py-1 flex items-start justify-between gap-2",
                          event.event_type === 'job_started' && "bg-blue-50 border-l-2 border-blue-500",
                          event.event_type === 'job_completed' && (event.success ? "bg-green-50 border-l-2 border-green-500" : "bg-red-50 border-l-2 border-red-500"),
                          event.event_type === 'action_started' && "bg-indigo-50 border-l-2 border-indigo-400",
                          event.event_type === 'action_completed' && (event.success ? "bg-indigo-50 border-l-2 border-indigo-500" : "bg-red-50 border-l-2 border-red-400"),
                          event.event_type?.startsWith('db_') && "bg-purple-50 border-l-2 border-purple-500",
                          event.event_type === 'error' && "bg-red-50 border-l-2 border-red-500",
                          event.event_type === 'target_processed' && "bg-yellow-50 border-l-2 border-yellow-500"
                        )}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-[10px] text-gray-500">
                              {formatShortTime(event.event_timestamp)}
                            </span>
                            <span className={cn(
                              "font-medium",
                              event.event_type === 'job_started' && "text-blue-700",
                              event.event_type === 'job_completed' && (event.success ? "text-green-700" : "text-red-700"),
                              event.event_type === 'action_started' && "text-indigo-700",
                              event.event_type === 'action_completed' && "text-indigo-700",
                              event.event_type?.startsWith('db_') && "text-purple-700",
                              event.event_type === 'error' && "text-red-700"
                            )}>
                              {event.event_type?.replace(/_/g, ' ')}
                            </span>
                            {event.action_name && (
                              <span className="text-gray-600">→ {event.action_name}</span>
                            )}
                          </div>
                          {/* Show event details from details JSON */}
                          {event.details && (
                            <div className="text-[10px] text-gray-600 mt-0.5">
                              {typeof event.details === 'string' ? event.details : 
                                Object.entries(typeof event.details === 'object' ? event.details : {})
                                  .filter(([k, v]) => v !== null && v !== undefined)
                                  .slice(0, 4)
                                  .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v).slice(0, 30) : v}`)
                                  .join(' | ')
                              }
                            </div>
                          )}
                          {/* Database operation details */}
                          {event.table_name && (
                            <div className="text-[10px] text-purple-600 mt-0.5">
                              {event.operation_type} on <span className="font-mono">{event.table_name}</span>
                              {event.record_id && <span> → Record ID: <strong>{event.record_id}</strong></span>}
                              {event.record_ids?.length > 0 && <span> → {event.record_ids.length} records: [{event.record_ids.slice(0, 5).join(', ')}{event.record_ids.length > 5 ? '...' : ''}]</span>}
                            </div>
                          )}
                          {event.target_ip && (
                            <div className="text-[10px] text-gray-500 font-mono">Target: {event.target_ip}</div>
                          )}
                          {event.error_message && (
                            <div className="text-[10px] text-red-600 mt-0.5">Error: {event.error_message}</div>
                          )}
                        </div>
                        {event.success === false && (
                          <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                        )}
                        {event.success === true && event.event_type?.includes('completed') && (
                          <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                        )}
                      </div>
                    ))}
                  </div>
                ) : !loadingAudit ? (
                  <div className="text-xs text-gray-400 italic">No audit events recorded yet. Events will appear for new job executions.</div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default JobHistory;
