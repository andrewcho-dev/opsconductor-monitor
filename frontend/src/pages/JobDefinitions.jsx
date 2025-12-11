import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Plus, RefreshCw, Trash2, FileText, Clock, Calendar, Zap, Play, Settings } from 'lucide-react';
import CompleteJobBuilder from '../components/jobBuilder/CompleteJobBuilder';
import { fetchApi, formatLocalTime } from '../lib/utils';
import { PageHeader } from '../components/layout';

const emptyScheduleForm = {
  scheduler_name: '',
  schedule_type: 'interval',
  interval_seconds: 3600,
  cron_expression: '',
  enabled: true,
  start_at: '',
  end_at: '',
  next_run_at: '',
  max_runs: '',
  overridesText: '{\n  \n}',
};

const JobDefinitions = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [selectedJobId, setSelectedJobId] = useState(null);

  const [builderOpen, setBuilderOpen] = useState(false);
  const [builderInitialJob, setBuilderInitialJob] = useState(null);
  const [builderEditingJobId, setBuilderEditingJobId] = useState(null);
  const [builderSaving, setBuilderSaving] = useState(false);
  const [builderError, setBuilderError] = useState(null);

  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleJobId, setScheduleJobId] = useState(null);
  const [scheduleForm, setScheduleForm] = useState(emptyScheduleForm);
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleError, setScheduleError] = useState(null);
  const [scheduleSuccess, setScheduleSuccess] = useState(null);

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi('/api/job-definitions');
      setJobs(data.jobs || []);
      const urlId = searchParams.get('id');
      const list = data.jobs || [];
      if (urlId && list.some((j) => j.id === urlId)) {
        setSelectedJobId(urlId);
      } else if (!selectedJobId && list.length > 0) {
        setSelectedJobId(list[0].id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load job definitions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const selectedJob = useMemo(
    () => jobs.find((j) => j.id === selectedJobId) || null,
    [jobs, selectedJobId]
  );

  const openCreateJob = () => {
    setBuilderEditingJobId(null);
    setBuilderInitialJob(null); // CompleteJobBuilder will use its DEFAULT_JOB
    setBuilderError(null);
    setBuilderOpen(true);
  };

  const openEditJob = (job) => {
    if (!job) return;
    const def = job.definition || {};
    const builderJob = {
      ...(typeof def === 'object' && def !== null ? def : {}),
      job_id: def.job_id || job.id,
      name: def.name || job.name || '',
      description: def.description || job.description || '',
    };
    setBuilderEditingJobId(job.id);
    setBuilderInitialJob(builderJob);
    setBuilderError(null);
    setBuilderOpen(true);
  };

  const handleBuilderSave = async (jobSpec) => {
    setBuilderSaving(true);
    setBuilderError(null);
    try {
      const payload = {
        name: (jobSpec.name || jobSpec.job_id || '').trim() || 'Untitled Job',
        description: jobSpec.description || '',
        enabled: true,
        definition: jobSpec,
      };

      let result;
      if (builderEditingJobId) {
        result = await fetchApi(`/api/job-definitions/${builderEditingJobId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
      } else {
        result = await fetchApi('/api/job-definitions', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }

      const savedJob = result.job;
      setBuilderOpen(false);
      setBuilderEditingJobId(null);
      setBuilderInitialJob(null);

      await loadJobs();
      if (savedJob && savedJob.id) {
        setSelectedJobId(savedJob.id);
      }
    } catch (err) {
      setBuilderError(err.message || 'Failed to save job definition');
    } finally {
      setBuilderSaving(false);
    }
  };

  const handleBuilderTest = async (jobSpec) => {
    // Ad-hoc test run via existing generic job execution endpoint.
    // This does NOT go through scheduler; it just runs the job spec once.
    try {
      setBuilderError(null);
      const response = await fetch(`/api/jobs/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jobSpec),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Job test failed');
      }
      console.log('Job definition test run result:', data);
    } catch (err) {
      setBuilderError(err.message || 'Failed to run job test');
    }
  };

  const handleDeleteJob = async (job) => {
    if (!job || !job.id) return;
    if (!window.confirm(`Delete job definition \"${job.name}\"?`)) return;
    try {
      await fetchApi(`/api/job-definitions/${job.id}`, { method: 'DELETE' });
      await loadJobs();
      if (selectedJobId === job.id) {
        setSelectedJobId(null);
      }
    } catch (err) {
      alert(`Failed to delete job definition: ${err.message}`);
    }
  };

  const toInputDateTime = (iso) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      const pad = (n) => String(n).padStart(2, '0');
      const yyyy = d.getFullYear();
      const mm = pad(d.getMonth() + 1);
      const dd = pad(d.getDate());
      const hh = pad(d.getHours());
      const mi = pad(d.getMinutes());
      return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
    } catch {
      return '';
    }
  };

  const fromInputDateTime = (value) => {
    if (!value) return null;
    try {
      return new Date(value).toISOString();
    } catch {
      return null;
    }
  };

  const openSchedule = (job) => {
    if (!job) return;
    setScheduleJobId(job.id);
    setScheduleError(null);
    setScheduleSuccess(null);
    setScheduleForm({
      ...emptyScheduleForm,
      scheduler_name: job.name || 'job',
    });
    setScheduleOpen(true);
  };

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!scheduleJobId) return;

    setScheduleSaving(true);
    setScheduleError(null);
    setScheduleSuccess(null);

    try {
      let overrides = {};
      const text = (scheduleForm.overridesText || '').trim();
      if (text && text !== '{\n  \n}') {
        try {
          overrides = JSON.parse(text);
        } catch (err) {
          setScheduleError('Overrides must be valid JSON');
          setScheduleSaving(false);
          return;
        }
      }

      const body = {
        scheduler_name: scheduleForm.scheduler_name.trim(),
        schedule_type: scheduleForm.schedule_type,
        enabled: Boolean(scheduleForm.enabled),
        overrides,
      };

      if (!body.scheduler_name) {
        setScheduleError('Scheduler name is required');
        setScheduleSaving(false);
        return;
      }

      if (scheduleForm.schedule_type === 'interval') {
        const value = Number(scheduleForm.interval_seconds);
        if (!Number.isFinite(value) || value <= 0) {
          setScheduleError('Interval seconds must be a positive number');
          setScheduleSaving(false);
          return;
        }
        body.interval_seconds = value;
      } else {
        const expr = (scheduleForm.cron_expression || '').trim();
        if (!expr) {
          setScheduleError('Cron expression is required for cron schedules');
          setScheduleSaving(false);
          return;
        }
        body.cron_expression = expr;
      }

      if (scheduleForm.start_at) {
        const iso = fromInputDateTime(scheduleForm.start_at);
        if (!iso) {
          setScheduleError('Invalid start_at value');
          setScheduleSaving(false);
          return;
        }
        body.start_at = iso;
      }

      if (scheduleForm.end_at) {
        const iso = fromInputDateTime(scheduleForm.end_at);
        if (!iso) {
          setScheduleError('Invalid end_at value');
          setScheduleSaving(false);
          return;
        }
        body.end_at = iso;
      }

      if (scheduleForm.next_run_at) {
        const iso = fromInputDateTime(scheduleForm.next_run_at);
        if (!iso) {
          setScheduleError('Invalid next_run_at value');
          setScheduleSaving(false);
          return;
        }
        body.next_run_at = iso;
      }

      if (scheduleForm.max_runs) {
        const value = Number(scheduleForm.max_runs);
        if (!Number.isInteger(value) || value <= 0) {
          setScheduleError('max_runs must be a positive integer when specified');
          setScheduleSaving(false);
          return;
        }
        body.max_runs = value;
      }

      const result = await fetchApi(`/api/job-definitions/${scheduleJobId}/schedule`, {
        method: 'POST',
        body: JSON.stringify(body),
      });

      setScheduleSuccess('Scheduler job saved successfully');
      console.log('Scheduler job for definition saved:', result);
    } catch (err) {
      setScheduleError(err.message || 'Failed to save scheduler job');
    } finally {
      setScheduleSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Job Definitions"
        description={`${jobs.length} definitions • Reusable automation templates`}
        icon={FileText}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={loadJobs}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={openCreateJob}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              New Definition
            </button>
          </div>
        }
      />

      {/* Main content */}
      <div className="flex-1 p-4 overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
          {/* Job list */}
          <div className="bg-white border border-gray-200 rounded-lg p-3 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Definitions</h2>
              <span className="text-xs text-gray-500">{jobs.length} total</span>
            </div>

            {error && (
              <div className="mb-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
                {error}
              </div>
            )}

            <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
              {loading ? (
                <div className="py-8 text-center text-sm text-gray-500">Loading job definitions...</div>
              ) : jobs.length === 0 ? (
                <div className="py-8 text-center text-sm text-gray-500">
                  No job definitions yet.
                  <br />
                  Click <span className="font-semibold">New Job Definition</span> to create your first one.
                </div>
              ) : (
                jobs.map((job) => (
                  <button
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className={`w-full text-left px-2 py-2 text-sm flex flex-col rounded-md hover:bg-gray-50 ${
                      selectedJobId === job.id ? 'bg-purple-50 border border-purple-200' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-gray-900 truncate">{job.name}</span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full border ${
                          job.enabled
                            ? 'bg-green-50 text-green-700 border-green-200'
                            : 'bg-gray-50 text-gray-500 border-gray-200'
                        }`}
                      >
                        {job.enabled ? 'ENABLED' : 'DISABLED'}
                      </span>
                    </div>
                    {job.description && (
                      <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">{job.description}</p>
                    )}
                    <div className="mt-1 flex items-center justify-between text-[10px] text-gray-400">
                      <span>
                        Created {job.created_at ? formatLocalTime(job.created_at) : 'n/a'}
                      </span>
                      <span>
                        Updated {job.updated_at ? formatLocalTime(job.updated_at) : 'n/a'}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Selected job details & actions */}
          <div className="bg-white border border-gray-200 rounded-lg p-3 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Details & Actions</h2>
              {selectedJob && (
                <div className="flex gap-2">
                  <button
                    onClick={() => openEditJob(selectedJob)}
                    className="px-2 py-1 text-xs border border-gray-200 rounded text-gray-700 hover:bg-gray-50 flex items-center gap-1"
                  >
                    <Settings className="w-3 h-3" />
                    Edit Definition
                  </button>
                  <button
                    onClick={() => openSchedule(selectedJob)}
                    className="px-2 py-1 text-xs border border-blue-200 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 flex items-center gap-1"
                  >
                    <Clock className="w-3 h-3" />
                    Schedule
                  </button>
                  <button
                    onClick={() => handleDeleteJob(selectedJob)}
                    className="px-2 py-1 text-xs border border-red-200 bg-red-50 text-red-700 rounded hover:bg-red-100 flex items-center gap-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                </div>
              )}
            </div>

            {!selectedJob ? (
              <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
                Select a job definition on the left to view details and actions.
              </div>
            ) : (
              <div className="flex-1 flex flex-col gap-3 overflow-y-auto">
                <div className="border border-gray-100 rounded-md p-2 bg-gray-50">
                  <h3 className="text-xs font-semibold text-gray-700 mb-1">Summary</h3>
                  <div className="text-xs text-gray-700">
                    <div className="font-medium text-gray-900">{selectedJob.name}</div>
                    {selectedJob.description && (
                      <p className="mt-1 text-gray-600 whitespace-pre-line">{selectedJob.description}</p>
                    )}
                  </div>
                </div>

                <div className="border border-gray-100 rounded-md p-2">
                  <h3 className="text-xs font-semibold text-gray-700 mb-1">Core Settings</h3>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-gray-600">
                    <div>
                      <dt className="font-medium text-gray-700">Enabled</dt>
                      <dd>{selectedJob.enabled ? 'Yes' : 'No'}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-gray-700">ID</dt>
                      <dd className="break-all text-gray-500">{selectedJob.id}</dd>
                    </div>
                  </dl>
                </div>

                <div className="border border-gray-100 rounded-md p-2">
                  <h3 className="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
                    <Zap className="w-3 h-3 text-green-600" />
                    Quick Actions
                  </h3>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <button
                      onClick={() => openEditJob(selectedJob)}
                      className="px-2 py-1 rounded bg-purple-600 text-white hover:bg-purple-700 flex items-center gap-1"
                    >
                      <Settings className="w-3 h-3" /> Edit Definition
                    </button>
                    <button
                      onClick={() => openSchedule(selectedJob)}
                      className="px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-1"
                    >
                      <Clock className="w-3 h-3" /> Configure Schedule
                    </button>
                    <button
                      onClick={() => {
                        const def = selectedJob.definition || {};
                        const jobSpec = {
                          ...(typeof def === 'object' && def !== null ? def : {}),
                          job_id: def.job_id || selectedJob.id,
                          name: def.name || selectedJob.name,
                          description: def.description || selectedJob.description,
                        };
                        handleBuilderTest(jobSpec);
                      }}
                      className="px-2 py-1 rounded bg-gray-800 text-white hover:bg-black flex items-center gap-1"
                    >
                      <Play className="w-3 h-3" /> Test Run (No Schedule)
                    </button>
                  </div>
                  {builderError && (
                    <div className="mt-2 text-[11px] text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
                      {builderError}
                    </div>
                  )}
                </div>

                <div className="border border-gray-100 rounded-md p-2 bg-gray-50">
                  <h3 className="text-xs font-semibold text-gray-700 mb-1">Raw Definition (read-only)</h3>
                  <pre className="text-[10px] text-gray-600 whitespace-pre overflow-x-auto max-h-64">
                    {JSON.stringify(selectedJob.definition || {}, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Scheduling panel */}
          <div className="bg-white border border-gray-200 rounded-lg p-3 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Scheduling</h2>
              {selectedJob && (
                <button
                  onClick={() => openSchedule(selectedJob)}
                  className="px-2 py-1 text-xs border border-blue-200 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 flex items-center gap-1"
                >
                  <Calendar className="w-3 h-3" />
                  New / Update Schedule
                </button>
              )}
            </div>

            {!selectedJob ? (
              <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
                Select a job definition to configure its scheduler job.
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto text-xs">
                <p className="mb-2 text-gray-600">
                  Scheduler jobs created here will appear on the <span className="font-medium">Scheduler</span> page
                  and run via the generic <code className="bg-gray-100 px-1 rounded">opsconductor.job.run</code> Celery task.
                </p>
                <p className="mb-3 text-gray-500">
                  Use the form below to create or update a scheduler job for this definition. You can choose between
                  simple interval scheduling or full cron expressions, set start/end windows, max runs, and runtime overrides.
                </p>

                <button
                  onClick={() => openSchedule(selectedJob)}
                  className="w-full px-3 py-2 border border-dashed border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2"
                >
                  <Clock className="w-4 h-4" />
                  Configure Schedule for <span className="font-semibold">{selectedJob.name}</span>
                </button>

                <p className="mt-3 text-[11px] text-gray-500">
                  Detailed execution history, worker metadata, and timeout status will always be visible from the
                  Scheduler page for any runs triggered by this definition.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Builder full-screen overlay */}
      {builderOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 overflow-hidden">
          <div className="h-full w-full overflow-auto bg-gray-100">
            <CompleteJobBuilder
              job={builderInitialJob}
              onBack={() => {
                if (!builderSaving) {
                  setBuilderOpen(false);
                  setBuilderInitialJob(null);
                  setBuilderEditingJobId(null);
                  setBuilderError(null);
                }
              }}
              onSave={handleBuilderSave}
              onTest={handleBuilderTest}
            />
            {builderSaving && (
              <div className="fixed bottom-4 right-4 px-3 py-2 bg-purple-600 text-white text-xs rounded shadow-lg">
                Saving job definition...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Schedule modal */}
      {scheduleOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-xl max-w-xl w-full mx-4 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-600" />
                Configure Schedule
              </h3>
              <button
                onClick={() => {
                  if (!scheduleSaving) {
                    setScheduleOpen(false);
                    setScheduleJobId(null);
                    setScheduleForm(emptyScheduleForm);
                    setScheduleError(null);
                    setScheduleSuccess(null);
                  }
                }}
                className="text-xs text-gray-500 hover:text-gray-800"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleScheduleSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">Scheduler Name</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    value={scheduleForm.scheduler_name}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, scheduler_name: e.target.value }))
                    }
                    placeholder="e.g. discovery-every-5min"
                  />
                </div>
                <div className="flex items-center gap-2 mt-4">
                  <label className="text-[11px] font-medium text-gray-700">Enabled</label>
                  <input
                    type="checkbox"
                    checked={scheduleForm.enabled}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, enabled: e.target.checked }))
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">Schedule Type</label>
                  <select
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    value={scheduleForm.schedule_type}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, schedule_type: e.target.value }))
                    }
                  >
                    <option value="interval">Interval (seconds)</option>
                    <option value="cron">Cron Expression</option>
                  </select>
                </div>

                {scheduleForm.schedule_type === 'interval' ? (
                  <div>
                    <label className="block text-[11px] font-medium text-gray-700 mb-1">Interval (seconds)</label>
                    <input
                      type="number"
                      min="1"
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                      value={scheduleForm.interval_seconds}
                      onChange={(e) =>
                        setScheduleForm((f) => ({ ...f, interval_seconds: e.target.value }))
                      }
                    />
                    <div className="mt-1 flex flex-wrap gap-1 text-[10px] text-gray-500">
                      <span className="mr-1">Presets:</span>
                      {[300, 900, 1800, 3600, 86400].map((v) => (
                        <button
                          key={v}
                          type="button"
                          className="px-1.5 py-0.5 border border-gray-200 rounded hover:bg-gray-50"
                          onClick={() =>
                            setScheduleForm((f) => ({ ...f, interval_seconds: v }))
                          }
                        >
                          {v < 3600
                            ? `${v / 60}m`
                            : v < 86400
                            ? `${v / 3600}h`
                            : `${v / 86400}d`}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="block text-[11px] font-medium text-gray-700 mb-1">
                      Cron Expression
                    </label>
                    <input
                      type="text"
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs font-mono"
                      value={scheduleForm.cron_expression}
                      onChange={(e) =>
                        setScheduleForm((f) => ({ ...f, cron_expression: e.target.value }))
                      }
                      placeholder="*/5 * * * *"
                    />
                    <p className="mt-1 text-[10px] text-gray-500">
                      Standard cron: minute hour day month weekday. Example: <code>0 */1 * * *</code> = hourly.
                    </p>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">Start At</label>
                  <input
                    type="datetime-local"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    value={scheduleForm.start_at}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, start_at: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">End At</label>
                  <input
                    type="datetime-local"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    value={scheduleForm.end_at}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, end_at: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">
                    Next Run At (override)
                  </label>
                  <input
                    type="datetime-local"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    value={scheduleForm.next_run_at}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, next_run_at: e.target.value }))
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 items-center">
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">Max Runs</label>
                  <input
                    type="number"
                    min="1"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    value={scheduleForm.max_runs}
                    onChange={(e) =>
                      setScheduleForm((f) => ({ ...f, max_runs: e.target.value }))
                    }
                    placeholder="blank = unlimited"
                  />
                </div>
                <div className="col-span-2 text-[10px] text-gray-500">
                  Leave blank for unlimited executions. When set, the job will automatically disable after that many
                  successful or failed runs.
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-gray-700 mb-1">
                  Runtime Overrides (JSON)
                </label>
                <textarea
                  rows={5}
                  className="w-full border border-gray-300 rounded px-2 py-1 text-[11px] font-mono"
                  value={scheduleForm.overridesText}
                  onChange={(e) =>
                    setScheduleForm((f) => ({ ...f, overridesText: e.target.value }))
                  }
                />
                <p className="mt-1 text-[10px] text-gray-500">
                  These keys will be merged into <code>definition.config</code> at runtime, without mutating the stored
                  definition. Use this for environment-specific settings, thresholds, or temporary experiments.
                </p>
              </div>

              {scheduleError && (
                <div className="text-[11px] text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
                  {scheduleError}
                </div>
              )}
              {scheduleSuccess && (
                <div className="text-[11px] text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">
                  {scheduleSuccess}
                </div>
              )}

              <div className="flex items-center justify-between mt-2">
                <p className="text-[10px] text-gray-500">
                  All scheduler jobs created here will be visible and manageable from the Scheduler page, including full
                  execution history and worker metadata.
                </p>
                <button
                  type="submit"
                  disabled={scheduleSaving}
                  className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  {scheduleSaving ? 'Saving...' : 'Save Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobDefinitions;
