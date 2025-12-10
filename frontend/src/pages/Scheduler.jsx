import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchApi } from "../lib/utils";
import JobNavHeader from "../components/JobNavHeader";

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
  const [queueStatus, setQueueStatus] = useState(null);
  const [loadingQueues, setLoadingQueues] = useState(false);
  const runOnceRefreshRef = useRef(null);
  // Scheduler is read-only for job structure; creation/editing happens via Job Builder.

  const formatLocalTime = (value) => {
    if (!value) return "—";
    try {
      let iso = value;
      // If the backend sends a naive ISO string (no timezone), assume UTC.
      const isoLike = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?$/;
      const hasZone = /[Zz]|[+-]\d{2}:?\d{2}$/.test(iso);
      if (isoLike.test(iso) && !hasZone) {
        iso = iso + "Z";
      }
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return value;
      return d.toLocaleString();
    } catch {
      return value;
    }
  };

  const openJobDefinitionFromConfig = (job) => {
    if (!job || job.task_name !== "opsconductor.job.run") return;
    const jobDefId = job?.config?.job_definition_id;
    if (!jobDefId) return;
    navigate(`/job-definitions?id=${encodeURIComponent(jobDefId)}`);
  };

  const workers = queueStatus?.workers || [];
  let totalProcs = 0;
  if (queueStatus?.worker_details) {
    for (const w of workers) {
      const conc = queueStatus.worker_details[w]?.concurrency;
      if (typeof conc === "number") {
        totalProcs += conc;
      }
    }
  }

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

  const loadQueues = async () => {
    try {
      setLoadingQueues(true);
      const data = await fetchApi("/api/scheduler/queues");
      setQueueStatus(data);
    } catch (err) {
      console.error("Failed to load queue status", err);
      // Don't overwrite main error unless nothing there
      setError((prev) => prev || err.message || "Failed to load queue status");
    } finally {
      setLoadingQueues(false);
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
    setSelectedJob(job.name);
    setSelectedExecution(null);
    setShowRawPayload(false);
    loadExecutions(job.name);
  };

  const clearExecutions = async () => {
    if (!selectedJob) return;
    try {
      setError(null);
      await fetchApi(
        `/api/scheduler/jobs/${encodeURIComponent(selectedJob)}/executions/clear`,
        {
          method: "POST",
          body: JSON.stringify({}),
        }
      );
      await loadExecutions(selectedJob);
    } catch (err) {
      console.error("Failed to clear executions", err);
      setError(err.message || "Failed to clear executions");
    }
  };

  useEffect(() => {
    loadJobs();
    loadQueues();
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

      if (selectedJob === name) {
        setSelectedJob(null);
        setExecutions([]);
        setSelectedExecution(null);
        setShowRawPayload(false);
      }

      await loadJobs();
    } catch (err) {
      console.error("Failed to delete scheduler job", err);
      setError(err.message || "Failed to delete job");
    }
  };

  const handleRunOnce = async (name) => {
    try {
      setError(null);
      await fetchApi(
        `/api/scheduler/jobs/${encodeURIComponent(name)}/run-once`,
        {
          method: "POST",
        }
      );
      // We don't know when the job will finish, but we can refresh metadata
      await loadJobs();
      await loadExecutions(name);

      // Lightweight auto-refresh: one more execution refresh after a short delay
      // so the user sees queued -> success/failed without manual clicking.
      if (runOnceRefreshRef.current) {
        clearTimeout(runOnceRefreshRef.current);
      }
      runOnceRefreshRef.current = setTimeout(() => {
        // Only refresh if this job is still selected so we don't surprise the user
        if (selectedJob === name) {
          loadExecutions(name);
        }
      }, 6000);
    } catch (err) {
      console.error("Failed to run job once", err);
      setError(err.message || "Failed to run job");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <JobNavHeader active="scheduler" />
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-800">Scheduler</h1>
          <button
            onClick={async () => {
              await loadJobs();
              await loadQueues();
              if (selectedJob) {
                await loadExecutions(selectedJob);
              }
            }}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <div className="mt-4 bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-3 text-xs text-gray-700">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-gray-800">Queue Status</span>
            <span className="text-[11px] text-gray-400">
              Updated when you click Refresh above
            </span>
          </div>
          {queueStatus ? (
            <>
              <div className="flex flex-wrap gap-3 mb-2">
                <span>
                  Active:{" "}
                  <span className="font-semibold">
                    {queueStatus.active_total}
                  </span>
                </span>
                <span>
                  Reserved:{" "}
                  <span className="font-semibold">
                    {queueStatus.reserved_total}
                  </span>
                </span>
                <span>
                  Scheduled:{" "}
                  <span className="font-semibold">
                    {queueStatus.scheduled_total}
                  </span>
                </span>
                <span>
                  Workers:{" "}
                  <span className="font-semibold">{workers.length}</span>
                </span>
                {totalProcs > 0 && (
                  <span>
                    Procs:{" "}
                    <span className="font-semibold">{totalProcs}</span>
                  </span>
                )}
              </div>
              <div className="mt-1">
                {workers.length === 0 && (
                  <div className="text-[11px] text-gray-400">
                    No workers reported. Is the Celery worker running?
                  </div>
                )}
                {workers.length > 0 && (
                  <div className="mt-1 flex gap-3 overflow-x-auto pb-1">
                    {workers.map((w) => {
                      const details = queueStatus.worker_details?.[w] || {};
                      const conc = details.concurrency;
                      const active =
                        details.active ??
                        (queueStatus.active_by_worker &&
                        queueStatus.active_by_worker[w] != null
                          ? queueStatus.active_by_worker[w]
                          : 0);
                      const reserved =
                        details.reserved ??
                        (queueStatus.reserved_by_worker &&
                        queueStatus.reserved_by_worker[w] != null
                          ? queueStatus.reserved_by_worker[w]
                          : 0);
                      const scheduled =
                        details.scheduled ??
                        (queueStatus.scheduled_by_worker &&
                        queueStatus.scheduled_by_worker[w] != null
                          ? queueStatus.scheduled_by_worker[w]
                          : 0);

                      return (
                        <div
                          key={w}
                          className="min-w-[180px] border border-gray-200 rounded-lg px-3 py-2 bg-white shadow-xs text-[11px] flex flex-col gap-1"
                        >
                          <div
                            className="font-mono text-gray-800 truncate"
                            title={w}
                          >
                            {w}
                          </div>
                          <div className="text-gray-500">
                            {typeof conc === "number" && (
                              <span className="mr-2">procs:{conc}</span>
                            )}
                          </div>
                          <div className="text-gray-500 flex flex-wrap gap-2">
                            <span>Active:{active}</span>
                            <span>Reserved:{reserved}</span>
                            <span>Scheduled:{scheduled}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-[11px] text-gray-400">
              Queue status not available.
            </div>
          )}
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Scheduled Jobs
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Name
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Task
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Schedule
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Enabled
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Last Run
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Next Run
                      </th>
                      <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.length === 0 && (
                      <tr>
                        <td
                          colSpan={7}
                          className="px-4 py-4 text-center text-gray-400 text-sm"
                        >
                          No scheduler jobs defined yet.
                        </td>
                      </tr>
                    )}
                    {jobs.map((job) => (
                      <tr
                        key={job.name}
                        className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                        onClick={() => handleSelectJob(job)}
                      >
                        <td className="px-4 py-2 font-medium text-gray-800 whitespace-nowrap">
                          {job.name}
                        </td>
                        <td className="px-4 py-2 text-gray-700 whitespace-nowrap">
                          {job.task_name}
                        </td>
                        <td className="px-4 py-2 text-gray-700 whitespace-nowrap text-xs">
                          {job.schedule_type === "cron"
                            ? `cron: ${job.cron_expression || ""}`
                            : job.interval_seconds
                            ? `every ${job.interval_seconds}s`
                            : "(interval not set)"}
                          {job.task_name === "opsconductor.job.run" &&
                            job.config?.job_definition_id && (
                              <div className="mt-0.5 text-[10px] text-purple-700 flex items-center gap-1">
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full bg-purple-50 border border-purple-200 font-medium">
                                  Job Definition
                                </span>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openJobDefinitionFromConfig(job);
                                  }}
                                  className="underline hover:no-underline"
                                >
                                  open
                                </button>
                              </div>
                            )}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              job.enabled
                                ? "bg-green-50 text-green-700 border border-green-200"
                                : "bg-gray-50 text-gray-600 border border-gray-200"
                            }`}
                          >
                            {job.enabled ? "Enabled" : "Disabled"}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-gray-600 whitespace-nowrap text-xs">
                          {formatLocalTime(job.last_run_at)}
                        </td>
                        <td className="px-4 py-2 text-gray-600 whitespace-nowrap text-xs">
                          {formatLocalTime(job.next_run_at)}
                        </td>
                        <td className="px-4 py-2 text-right space-x-2 whitespace-nowrap">
                          <button
                            className="px-2 py-1 text-xs rounded border border-blue-500 text-blue-600 hover:bg-blue-50"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRunOnce(job.name);
                            }}
                          >
                            Run Once
                          </button>
                          {job.task_name === "opsconductor.job.run" &&
                            job.config?.job_definition_id && (
                              <button
                                className="px-2 py-1 text-xs rounded border border-purple-500 text-purple-700 hover:bg-purple-50"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openJobDefinitionFromConfig(job);
                                }}
                              >
                                Job Def
                              </button>
                            )}
                          <button
                            className="px-2 py-1 text-xs rounded border border-red-500 text-red-700 hover:bg-red-50"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteJob(job.name);
                            }}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    Execution History{selectedJob ? ` – ${selectedJob}` : ""}
                  </h2>
                  {selectedJob && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={clearExecutions}
                        className="px-3 py-1 text-xs font-medium rounded border border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
                      >
                        Clear History
                      </button>
                    </div>
                  )}
                </div>
                <div className="overflow-x-auto max-h-80">
                  <table className="min-w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">
                          Status
                        </th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">
                          Started
                        </th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">
                          Finished
                        </th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">
                          Task ID
                        </th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">
                          Error
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {(!selectedJob || executions.length === 0) && (
                        <tr>
                          <td
                            colSpan={5}
                            className="px-3 py-3 text-center text-gray-400"
                          >
                            {selectedJob
                              ? "No executions yet for this job."
                              : "Select a job to view its execution history."}
                          </td>
                        </tr>
                      )}
                      {executions.map((exec) => (
                        <tr
                          key={exec.id}
                          className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                          onClick={() => {
                            setSelectedExecution(exec);
                            setShowRawPayload(false);
                          }}
                        >
                          <td className="px-3 py-2 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full font-medium ${
                                exec.status === "success"
                                  ? "bg-green-50 text-green-700 border border-green-200"
                                  : exec.status === "failed"
                                  ? "bg-red-50 text-red-700 border border-red-200"
                                  : exec.status === "running"
                                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                                  : "bg-gray-50 text-gray-600 border border-gray-200"
                              }`}
                            >
                              {exec.status}
                            </span>
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap text-gray-700">
                            {formatLocalTime(exec.started_at)}
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap text-gray-700">
                            {formatLocalTime(exec.finished_at)}
                          </td>
                          <td
                            className="px-3 py-2 whitespace-nowrap text-gray-500 font-mono truncate max-w-xs"
                            title={exec.task_id}
                          >
                            {exec.task_id}
                          </td>
                          <td
                            className="px-3 py-2 whitespace-nowrap text-gray-700 max-w-xs truncate"
                            title={exec.error_message || ""}
                          >
                            {exec.error_message || ""}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        {selectedExecution && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
            onClick={() => {
              setSelectedExecution(null);
              setShowRawPayload(false);
            }}
          >
            <div
              className="bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <div className="font-semibold text-gray-800 text-sm">
                  Execution Details – ID {selectedExecution.id} (
                  {selectedExecution.status})
                </div>
                <div className="flex items-center gap-2">
                  {selectedExecution.result &&
                    selectedExecution.result.job_definition_id && (
                      <button
                        className="px-3 py-1 text-[11px] rounded border border-purple-500 text-purple-700 hover:bg-purple-50"
                        onClick={() => {
                          navigate(
                            `/job-definitions?id=${encodeURIComponent(
                              String(
                                selectedExecution.result.job_definition_id
                              )
                            )}`
                          );
                        }}
                      >
                        Open Job Definition
                      </button>
                    )}
                  <button
                    className="px-3 py-1 text-[11px] rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
                    onClick={() => {
                      setSelectedExecution(null);
                      setShowRawPayload(false);
                    }}
                  >
                    Close
                  </button>
                </div>
              </div>
              <div className="px-4 py-3 space-y-3 text-xs overflow-y-auto">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <div className="text-[11px] text-gray-500">Started</div>
                    <div className="font-mono">
                      {formatLocalTime(selectedExecution.started_at)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-gray-500">Finished</div>
                    <div className="font-mono">
                      {formatLocalTime(selectedExecution.finished_at)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-gray-500">Task ID</div>
                    <div className="font-mono break-all">
                      {selectedExecution.task_id}
                    </div>
                  </div>
                </div>
                {selectedExecution.result &&
                  selectedExecution.result.execution_meta && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <div className="text-[11px] text-gray-500">
                          Worker
                        </div>
                        <div className="font-mono break-all">
                          {selectedExecution.result.execution_meta
                            .worker_hostname || "unknown"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] text-gray-500">
                          Worker PID
                        </div>
                        <div className="font-mono break-all">
                          {typeof selectedExecution.result.execution_meta
                            .worker_pid !== "undefined"
                            ? selectedExecution.result.execution_meta.worker_pid
                            : ""}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] text-gray-500">Queue</div>
                        <div className="font-mono break-all">
                          {selectedExecution.result.execution_meta.queue || ""}
                        </div>
                      </div>
                    </div>
                  )}
                {selectedExecution.error_message && (
                  <div>
                    <div className="text-[11px] text-red-600 font-semibold">
                      Error
                    </div>
                    <pre className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-[11px] whitespace-pre-wrap break-all">
                      {selectedExecution.error_message}
                    </pre>
                  </div>
                )}
                <div>
                  <div className="text-[11px] text-gray-500 font-semibold">
                    Result
                  </div>
                  {selectedExecution.result ? (
                    <div className="mt-1 space-y-3">
                      {/* Job Builder style results */}
                      {selectedExecution.result.job_name && (
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-[11px]">
                          <div>
                            <div className="text-gray-500">Job Name</div>
                            <div className="font-mono break-all">
                              {selectedExecution.result.job_name}
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-500">Actions</div>
                            <div className="font-mono">
                              {selectedExecution.result.actions_completed || 0} / {selectedExecution.result.total_actions || 0}
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-500">Duration</div>
                            <div className="font-mono">
                              {selectedExecution.result.duration_seconds?.toFixed(3) || selectedExecution.result.metrics?.duration_seconds?.toFixed(3) || "—"}s
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-500">Errors</div>
                            <div className="font-mono">
                              {selectedExecution.result.errors?.length || 0}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Action results summary */}
                      {Object.keys(selectedExecution.result)
                        .filter((k) => k.startsWith("action_"))
                        .map((actionKey) => {
                          const action = selectedExecution.result[actionKey];
                          return (
                            <div key={actionKey} className="border border-gray-200 rounded p-2 text-[11px]">
                              <div className="font-semibold text-gray-700 mb-1">
                                {actionKey.replace("action_", "").toUpperCase()} Action
                              </div>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                <div>
                                  <div className="text-gray-500">Type</div>
                                  <div className="font-mono">{action.action_type || "—"}</div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Targets</div>
                                  <div className="font-mono">{action.targets_processed || 0}</div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Successful</div>
                                  <div className="font-mono text-green-600">{action.successful_results || 0}</div>
                                </div>
                                {action.failed_results > 0 && (
                                  <div>
                                    <div className="text-gray-500">Failed</div>
                                    <div className="font-mono text-red-600">{action.failed_results}</div>
                                  </div>
                                )}
                              </div>
                              {action.results && action.results.length > 0 && (
                                <div className="mt-2">
                                  <div className="text-gray-500 mb-1">Results ({action.results.length})</div>
                                  <div className="max-h-32 overflow-y-auto bg-gray-50 rounded p-1">
                                    {action.results.slice(0, 10).map((r, i) => (
                                      <div key={i} className="font-mono text-[10px] py-0.5 border-b border-gray-100 last:border-0">
                                        {r.ip_address || r.host || "—"}: {r.ping_status || r.status || "—"}
                                      </div>
                                    ))}
                                    {action.results.length > 10 && (
                                      <div className="text-gray-400 text-[10px] py-0.5">
                                        ... and {action.results.length - 10} more
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}

                      {/* Legacy ping_host style results */}
                      {selectedExecution.result.host && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
                          <div>
                            <div className="text-gray-500">Host</div>
                            <div className="font-mono break-all">
                              {selectedExecution.result.host}
                            </div>
                          </div>
                          {typeof selectedExecution.result.count !== "undefined" && (
                            <div>
                              <div className="text-gray-500">Count</div>
                              <div className="font-mono">
                                {selectedExecution.result.count}
                              </div>
                            </div>
                          )}
                          {typeof selectedExecution.result.returncode !== "undefined" && (
                            <div>
                              <div className="text-gray-500">Return Code</div>
                              <div className="font-mono">
                                {selectedExecution.result.returncode}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {(selectedExecution.result.stdout ||
                        selectedExecution.result.stderr) && (
                        <div className="space-y-3 text-[11px]">
                          {selectedExecution.result.stdout && (
                            <div>
                              <div className="text-gray-500 font-semibold mb-1">
                                Stdout
                              </div>
                              <pre className="p-2 bg-gray-50 border border-gray-200 rounded whitespace-pre overflow-x-auto">
                                {selectedExecution.result.stdout}
                              </pre>
                            </div>
                          )}
                          {selectedExecution.result.stderr && (
                            <div>
                              <div className="text-gray-500 font-semibold mb-1">
                                Stderr
                              </div>
                              <pre className="p-2 bg-gray-50 border border-gray-200 rounded whitespace-pre overflow-x-auto">
                                {selectedExecution.result.stderr}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <div className="text-[11px] text-gray-500 font-semibold">
                            Raw Payload
                          </div>
                          <button
                            type="button"
                            className="text-[11px] text-blue-600 hover:underline"
                            onClick={() =>
                              setShowRawPayload((prev) => !prev)
                            }
                          >
                            {showRawPayload ? "Hide" : "Show"}
                          </button>
                        </div>
                        {showRawPayload && (
                          <pre className="p-2 bg-white border border-gray-200 rounded text-[11px] whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(selectedExecution.result, null, 2)}
                          </pre>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mt-1 text-[11px] text-gray-400">
                      No result payload recorded for this execution.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}