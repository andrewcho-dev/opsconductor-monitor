import { useEffect, useState } from "react";
import { fetchApi } from "../lib/utils";

export function Scheduler() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [loadingExecutions, setLoadingExecutions] = useState(false);
  const [queueStatus, setQueueStatus] = useState(null);
  const [loadingQueues, setLoadingQueues] = useState(false);
  const [form, setForm] = useState({
    name: "",
    task_name: "",
    interval_seconds: 60,
    schedule_type: "interval",
    cron_expression: "",
    start_at: "",
    end_at: "",
    max_runs: "",
    enabled: true,
    config: "{}",
  });

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
      return;
    }
    try {
      setLoadingExecutions(true);
      setError(null);
      const data = await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(jobName)}/executions?limit=50`);
      setExecutions(data.executions || []);
    } catch (err) {
      console.error("Failed to load executions", err);
      setError(err.message || "Failed to load executions");
    } finally {
      setLoadingExecutions(false);
    }
  };

  const clearExecutions = async () => {
    if (!selectedJob) return;
    try {
      setError(null);
      await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(selectedJob)}/executions/clear`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await loadExecutions(selectedJob);
    } catch (err) {
      console.error("Failed to clear executions", err);
      setError(err.message || "Failed to clear executions");
    }
  };

  useEffect(() => {
    loadJobs();
    loadQueues();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleEditJob = (job) => {
    setSelectedJob(job.name);
    loadExecutions(job.name);
    setForm({
      name: job.name,
      task_name: job.task_name,
      interval_seconds: job.interval_seconds || 60,
      schedule_type: job.schedule_type || "interval",
      cron_expression: job.cron_expression || "",
      start_at: job.start_at || "",
      end_at: job.end_at || "",
      max_runs: job.max_runs != null ? String(job.max_runs) : "",
      enabled: job.enabled,
      config: JSON.stringify(job.config || {}, null, 2),
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);

      let parsedConfig = {};
      if (form.config && form.config.trim()) {
        try {
          parsedConfig = JSON.parse(form.config);
        } catch (err) {
          alert("Config must be valid JSON");
          return;
        }
      }

      const payload = {
        name: form.name.trim(),
        task_name: form.task_name.trim(),
        schedule_type: form.schedule_type,
        interval_seconds:
          form.schedule_type === "interval" ? Number(form.interval_seconds) || 0 : null,
        cron_expression:
          form.schedule_type === "cron" ? (form.cron_expression || "").trim() : null,
        start_at: form.start_at || null,
        end_at: form.end_at || null,
        max_runs: form.max_runs ? Number(form.max_runs) : null,
        enabled: !!form.enabled,
        config: parsedConfig,
      };

      if (!payload.name || !payload.task_name) {
        alert("name and task_name are required");
        return;
      }

      if (form.schedule_type === "interval" && !payload.interval_seconds) {
        alert("interval_seconds is required for interval schedules");
        return;
      }

      if (form.schedule_type === "cron" && !payload.cron_expression) {
        alert("cron_expression is required for cron schedules");
        return;
      }

      await fetchApi("/api/scheduler/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      await loadJobs();
    } catch (err) {
      console.error("Failed to save scheduler job", err);
      setError(err.message || "Failed to save job");
    } finally {
      setSaving(false);
    }
  };

  const handleRunOnce = async (name) => {
    try {
      setError(null);
      await fetchApi(`/api/scheduler/jobs/${encodeURIComponent(name)}/run-once`, {
        method: "POST",
      });
      // We don't know when the job will finish, but we can refresh metadata
      await loadJobs();
      await loadExecutions(name);
    } catch (err) {
      console.error("Failed to run job once", err);
      setError(err.message || "Failed to run job");
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Scheduler</h1>
        <button
          onClick={loadJobs}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-3 text-xs text-gray-700">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-gray-800">Queue Status</span>
            <button
              onClick={loadQueues}
              className="px-2 py-0.5 text-[11px] font-medium rounded border border-gray-300 bg-white hover:bg-gray-50"
              disabled={loadingQueues}
            >
              {loadingQueues ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          {queueStatus ? (
            <>
              <div className="flex gap-3 mb-2">
                <span>Active: <span className="font-semibold">{queueStatus.active_total}</span></span>
                <span>Reserved: <span className="font-semibold">{queueStatus.reserved_total}</span></span>
                <span>Scheduled: <span className="font-semibold">{queueStatus.scheduled_total}</span></span>
              </div>
              <div className="space-y-1">
                {(queueStatus.workers || []).length === 0 && (
                  <div className="text-[11px] text-gray-400">No workers reported. Is the Celery worker running?</div>
                )}
                {(queueStatus.workers || []).map((w) => (
                  <div key={w} className="flex justify-between text-[11px]">
                    <span className="truncate mr-2">{w}</span>
                    <span className="text-gray-500">
                      A:{queueStatus.active_by_worker?.[w] || 0} · R:{queueStatus.reserved_by_worker?.[w] || 0} · S:{queueStatus.scheduled_by_worker?.[w] || 0}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-[11px] text-gray-400">Queue status not available.</div>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
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
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Name</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Task</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Schedule</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Enabled</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Last Run</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Next Run</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-4 text-center text-gray-400 text-sm">
                        No scheduler jobs defined yet.
                      </td>
                    </tr>
                  )}
                  {jobs.map((job) => (
                    <tr key={job.name} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium text-gray-800 whitespace-nowrap">{job.name}</td>
                      <td className="px-4 py-2 text-gray-700 whitespace-nowrap">{job.task_name}</td>
                      <td className="px-4 py-2 text-gray-700 whitespace-nowrap text-xs">
                        {job.schedule_type === "cron"
                          ? `cron: ${job.cron_expression || ""}`
                          : job.interval_seconds
                          ? `every ${job.interval_seconds}s`
                          : "(interval not set)"}
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
                          className="px-2 py-1 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
                          onClick={() => handleEditJob(job)}
                        >
                          Edit
                        </button>
                        <button
                          className="px-2 py-1 text-xs rounded border border-blue-500 text-blue-600 hover:bg-blue-50"
                          onClick={() => handleRunOnce(job.name)}
                        >
                          Run Once
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Execution History{selectedJob ? ` – ${selectedJob}` : ""}
              </h2>
              {selectedJob && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => loadExecutions(selectedJob)}
                    className="px-3 py-1 text-xs font-medium rounded border border-gray-300 bg-white hover:bg-gray-50"
                    disabled={loadingExecutions}
                  >
                    {loadingExecutions ? "Refreshing..." : "Refresh"}
                  </button>
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
                    <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">Started</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">Finished</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">Task ID</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {(!selectedJob || executions.length === 0) && (
                    <tr>
                      <td colSpan={5} className="px-3 py-3 text-center text-gray-400">
                        {selectedJob ? "No executions yet for this job." : "Select a job to view its execution history."}
                      </td>
                    </tr>
                  )}
                  {executions.map((exec) => (
                    <tr key={exec.id} className="border-t border-gray-100 hover:bg-gray-50">
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
                      <td className="px-3 py-2 whitespace-nowrap text-gray-700">{formatLocalTime(exec.started_at)}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-gray-700">{formatLocalTime(exec.finished_at)}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-gray-500 font-mono truncate max-w-xs" title={exec.task_id}>
                        {exec.task_id}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-gray-700 max-w-xs truncate" title={exec.error_message || ""}>
                        {exec.error_message || ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Create / Edit Job
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-3 text-sm">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
                <input
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g. discovery-hourly"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Task Name</label>
                <input
                  type="text"
                  name="task_name"
                  value={form.task_name}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g. opsconductor.discovery.run"
                />
              </div>

              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Schedule Type</label>
                  <select
                    name="schedule_type"
                    value={form.schedule_type}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="interval">Interval</option>
                    <option value="cron">Cron</option>
                  </select>
                </div>
                <div className="pt-5 flex items-center gap-2">
                  <input
                    id="enabled"
                    type="checkbox"
                    name="enabled"
                    checked={form.enabled}
                    onChange={handleChange}
                    className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                  />
                  <label htmlFor="enabled" className="text-xs font-medium text-gray-700">
                    Enabled
                  </label>
                </div>
              </div>

              {form.schedule_type === "interval" && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Interval (seconds)</label>
                  <input
                    type="number"
                    name="interval_seconds"
                    min={1}
                    value={form.interval_seconds}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              )}

              {form.schedule_type === "cron" && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Cron Expression</label>
                  <input
                    type="text"
                    name="cron_expression"
                    value={form.cron_expression}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g. 0 2 * * * (daily at 02:00)"
                  />
                  <p className="mt-1 text-[11px] text-gray-500">
                    Supports standard 5-field cron. Examples: "0 2 * * *" (daily at 02:00), "0 0 1 * *" (first of month at midnight).
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Start At</label>
                  <input
                    type="datetime-local"
                    name="start_at"
                    value={form.start_at}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">End At</label>
                  <input
                    type="datetime-local"
                    name="end_at"
                    value={form.end_at}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Max Runs</label>
                  <input
                    type="number"
                    name="max_runs"
                    min={1}
                    value={form.max_runs}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="unlimited"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Config (JSON)</label>
                <textarea
                  name="config"
                  value={form.config}
                  onChange={handleChange}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="{}"
                />
              </div>

              <button
                type="submit"
                disabled={saving}
                className="w-full mt-2 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {saving ? "Saving..." : "Save Job"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
