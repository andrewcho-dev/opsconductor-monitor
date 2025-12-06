import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Square, RefreshCw, Plus, Trash2, Save, TestTube, Settings } from 'lucide-react';
import { cn } from '../lib/utils';
import CompleteJobBuilder from '../components/jobBuilder/CompleteJobBuilder';

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Poller Modal Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4">
            <h3 className="text-lg font-bold text-red-800 mb-2">⚠️ Job Builder Error</h3>
            <p className="text-gray-600 mb-4">Something went wrong loading the job builder.</p>
            <button 
              onClick={() => {
                this.setState({ hasError: false, error: null });
                if (this.props.onClose) this.props.onClose();
              }}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Close Job Builder
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const Poller = ({ openJobBuilder = false }) => {
  const [status, setStatus] = useState({
    discovery: { active: false, next_run: null },
    interface: { active: false, next_run: null },
    optical: { active: false, next_run: null },
    scheduler_running: false,
    execution_log: []
  });
  const [logs, setLogs] = useState([]);
  const [showJobBuilder, setShowJobBuilder] = useState(false);
  const [editingJob, setEditingJob] = useState(null);
  
  // Handle openJobBuilder prop safely
  useEffect(() => {
    if (openJobBuilder) {
      setShowJobBuilder(true);
    }
  }, [openJobBuilder]);
  const [jobs, setJobs] = useState([
    {
      id: 'discovery',
      name: 'Network Discovery',
      type: 'discovery',
      enabled: false,
      interval: 3600,
      config: {
        network: '10.127.0.0/24',
        ping: true,
        snmp: true,
        ssh: true,
        rdp: false,
        retention: 30
      }
    },
    {
      id: 'interface',
      name: 'Interface Scan',
      type: 'interface',
      enabled: false,
      interval: 1800,
      config: {
        targets: 'all',
        custom: '',
        retention: 7
      }
    },
    {
      id: 'optical',
      name: 'Optical Power',
      type: 'optical',
      enabled: false,
      interval: 600,
      config: {
        targets: 'all',
        custom: '',
        retention: 90,
        temperature_threshold: 70
      }
    }
  ]);

  const navigate = useNavigate();

  const refreshStatus = async () => {
    try {
      const response = await fetch('/poller/status');
      const statusData = await response.json();
      setStatus(statusData);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  const refreshLogs = async () => {
    try {
      const response = await fetch('/poller/logs');
      const logsData = await response.json();
      setLogs(logsData);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  const addLog = (level, message) => {
    const timestamp = new Date().toLocaleString();
    setLogs(prev => [...prev, { timestamp, level, message }]);
  };

  const startJob = async (jobId) => {
    try {
      const response = await fetch(`/poller/${jobId}/start`, { method: 'POST' });
      const result = await response.json();
      if (response.ok) {
        addLog('info', `Started ${jobId} poller`);
        refreshStatus();
      } else {
        addLog('error', `Failed to start ${jobId}: ${result.error}`);
      }
    } catch (error) {
      addLog('error', `Error starting ${jobId}: ${error.message}`);
    }
  };

  const stopJob = async (jobId) => {
    try {
      const response = await fetch(`/poller/${jobId}/stop`, { method: 'POST' });
      const result = await response.json();
      if (response.ok) {
        addLog('info', `Stopped ${jobId} poller`);
        refreshStatus();
      } else {
        addLog('error', `Failed to stop ${jobId}: ${result.error}`);
      }
    } catch (error) {
      addLog('error', `Error stopping ${jobId}: ${error.message}`);
    }
  };

  const testJob = async (jobId) => {
    try {
      const response = await fetch(`/poller/${jobId}/test`, { method: 'POST' });
      const result = await response.json();
      if (response.ok) {
        addLog('success', `${jobId} test completed successfully`);
        refreshStatus();
      } else {
        addLog('error', `${jobId} test failed: ${result.error}`);
      }
    } catch (error) {
      addLog('error', `Error testing ${jobId}: ${error.message}`);
    }
  };

  const saveJob = async (job) => {
    try {
      const response = await fetch(`/poller/${job.type}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(job.config)
      });
      const result = await response.json();
      if (response.ok) {
        addLog('success', `Saved ${job.name} configuration`);
        refreshStatus();
      } else {
        addLog('error', `Failed to save ${job.name}: ${result.error}`);
      }
    } catch (error) {
      addLog('error', `Error saving ${job.name}: ${error.message}`);
    }
  };

  const getStatusIndicator = (active) => {
    return active ? (
      <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
    ) : (
      <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
    );
  };

  const updateJob = (jobId, field, value) => {
    setJobs(prev => prev.map(job => 
      job.id === jobId ? { ...job, [field]: value } : job
    ));
  };

  const updateJobConfig = (jobId, configField, value) => {
    setJobs(prev => prev.map(job => 
      job.id === jobId 
        ? { ...job, config: { ...job.config, [configField]: value } }
        : job
    ));
  };

  const addNewJob = () => {
    const newJob = {
      id: `custom_${Date.now()}`,
      name: 'Custom Job',
      type: 'discovery',
      enabled: false,
      interval: 3600,
      config: {
        network: '10.127.0.0/24',
        ping: true,
        snmp: true,
        ssh: true,
        rdp: false,
        retention: 30
      }
    };
    setJobs(prev => [...prev, newJob]);
    setEditingJob(newJob.id);
    setShowJobBuilder(true);
  };

  const deleteJob = (jobId) => {
    setJobs(prev => prev.filter(job => job.id !== jobId));
    if (editingJob === jobId) {
      setEditingJob(null);
      setShowJobBuilder(false);
    }
  };

  const duplicateJob = (job) => {
    const newJob = {
      ...job,
      id: `custom_${Date.now()}`,
      name: `${job.name} (Copy)`,
      enabled: false
    };
    setJobs(prev => [...prev, newJob]);
  };

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const currentJob = jobs.find(job => job.id === editingJob);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Main
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">Poller Jobs</h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowJobBuilder(true)}
              className="flex items-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <Settings className="w-4 h-4" />
              Job Builder
            </button>
            <button
              onClick={refreshStatus}
              className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              onClick={addNewJob}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Job
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Job List */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Poller Jobs</h2>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">
                {jobs.filter(j => j.enabled).length} / {jobs.length} enabled
              </span>
              <button
                onClick={refreshStatus}
                className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                title="Refresh Status"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
              <button
                onClick={addNewJob}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <Plus className="w-3 h-3" />
                Add Job
              </button>
            </div>
          </div>

          {/* Job Table with Fixed Columns */}
          <div className="bg-gray-50 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-2 bg-gray-100 px-3 py-2 border-b border-gray-200 text-xs font-medium text-gray-700">
              <span className="w-6"></span>
              <span className="w-32">JOB NAME</span>
              <span className="w-24">TYPE</span>
              <span className="w-16 text-center">ENABLED</span>
              <span className="w-20">INTERVAL</span>
              <span className="w-32">NEXT RUN</span>
              <span className="w-24 text-center">STATUS</span>
              <span className="flex-1">ACTIONS</span>
            </div>

            {/* Job Rows */}
            {jobs.map((job) => (
              <div key={job.id} className="flex items-center gap-2 px-3 py-2 border-b border-gray-200 hover:bg-gray-50 text-xs">
                <span className="w-6">
                  {getStatusIndicator(job.enabled && status[job.type]?.active)}
                </span>
                <span className="w-32 font-medium text-gray-900 truncate">{job.name}</span>
                <span className="w-24 text-gray-600 capitalize">{job.type}</span>
                <span className="w-16 text-center">
                  <input
                    type="checkbox"
                    checked={job.enabled}
                    onChange={(e) => updateJob(job.id, 'enabled', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                </span>
                <span className="w-20 text-gray-600">
                  {job.interval < 3600 ? `${job.interval/60}m` : 
                   job.interval < 86400 ? `${job.interval/3600}h` : `${job.interval/86400}d`}
                </span>
                <span className="w-32 text-gray-500 truncate">
                  {status[job.type]?.next_run || 'Not scheduled'}
                </span>
                <span className="w-24 text-center">
                  {job.enabled && status[job.type]?.active ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      RUNNING
                    </span>
                  ) : job.enabled ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                      SCHEDULED
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                      STOPPED
                    </span>
                  )}
                </span>
                <span className="flex-1 flex items-center gap-1">
                  <button
                    onClick={() => testJob(job.type)}
                    className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                    title="Test Job"
                  >
                    <TestTube className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => duplicateJob(job)}
                    className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                    title="Duplicate Job"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => {
                      // Load the actual discovery job definition
                      const discoveryJob = {
                        job_id: 'discovery',
                        name: 'Network Discovery',
                        description: 'Discover devices on network using ping, SNMP, SSH, and RDP',
                        actions: [
                          {
                            type: 'ping_scan',
                            enabled: true,
                            login_method: {
                              type: 'ping',
                              command: 'ping -c {count} -W {timeout} -i {interval} {target}',
                              parameters: {
                                count: 1,
                                timeout: 1,
                                interval: 0.2,
                                timeout_unit: 'seconds'
                              },
                              success_criteria: {
                                return_code: 0,
                                output_contains: ['bytes from'],
                                output_regex: 'bytes from .*: icmp_seq=\\d+ ttl=\\d+ time=([0-9.]+)'
                              }
                            },
                            targeting: {
                              source: 'network_range',
                              network_range: '10.127.0.0/24',
                              target_list: '',
                              exclude_list: '',
                              custom_groups: [],
                              network_groups: [],
                              group_filter: {
                                include_empty: true,
                                status_filter: 'all',
                                tag_filter: []
                              },
                              max_concurrent: 50,
                              retry_count: 3,
                              retry_delay: 1
                            },
                            execution: {
                              timeout: 5,
                              kill_signal: 'SIGTERM',
                              working_directory: '/tmp',
                              environment: {},
                              pre_command: '',
                              post_command: ''
                            },
                            result_parsing: {
                              parser_type: 'regex',
                              patterns: [
                                {
                                  name: 'ping_success',
                                  regex: 'bytes from .*: icmp_seq=\\d+ ttl=\\d+ time=([0-9.]+)',
                                  field_mapping: {
                                    'ping_time': '$1',
                                    'ping_status': 'online'
                                  }
                                },
                                {
                                  name: 'ping_failure',
                                  regex: 'no answer|100% packet loss|Destination host unreachable',
                                  field_mapping: {
                                    'ping_status': 'offline',
                                    'ping_time': '0'
                                  }
                                }
                              ],
                              default_values: {
                                'ping_status': 'offline',
                                'ping_time': '0',
                                'last_seen': 'NOW()'
                              }
                            },
                            database: {
                              table: 'devices',
                              operation: 'upsert',
                              key_fields: ['ip_address'],
                              field_types: {
                                'ip_address': 'INET',
                                'ping_status': 'VARCHAR(20)',
                                'ping_time': 'FLOAT',
                                'last_seen': 'TIMESTAMP'
                              },
                              indexes: ['ip_address', 'last_seen']
                            }
                          },
                          {
                            type: 'snmp_scan',
                            enabled: true,
                            login_method: {
                              type: 'snmp',
                              command: 'snmpget -v{version} -c {community} {target} {oids}',
                              parameters: {
                                version: '2c',
                                community: 'public',
                                oids: 'sysDescr.0 sysUpTime.0'
                              },
                              success_criteria: {
                                return_code: 0,
                                output_contains: ['STRING:'],
                                output_regex: '.* = STRING: (.*)'
                              }
                            },
                            targeting: {
                              source: 'network_range',
                              network_range: '10.127.0.0/24',
                              target_list: '',
                              exclude_list: '',
                              custom_groups: [],
                              network_groups: [],
                              group_filter: {
                                include_empty: true,
                                status_filter: 'all',
                                tag_filter: []
                              },
                              max_concurrent: 20,
                              retry_count: 2,
                              retry_delay: 2
                            },
                            execution: {
                              timeout: 10,
                              kill_signal: 'SIGTERM',
                              working_directory: '/tmp',
                              environment: {},
                              pre_command: '',
                              post_command: ''
                            },
                            result_parsing: {
                              parser_type: 'regex',
                              patterns: [
                                {
                                  name: 'snmp_success',
                                  regex: '.* = STRING: (.*)',
                                  field_mapping: {
                                    'sys_description': '$1',
                                    'snmp_status': 'online'
                                  }
                                }
                              ],
                              default_values: {
                                'snmp_status': 'offline',
                                'sys_description': '',
                                'last_seen': 'NOW()'
                              }
                            },
                            database: {
                              table: 'devices',
                              operation: 'upsert',
                              key_fields: ['ip_address'],
                              field_types: {
                                'ip_address': 'INET',
                                'snmp_status': 'VARCHAR(20)',
                                'sys_description': 'TEXT',
                                'last_seen': 'TIMESTAMP'
                              },
                              indexes: ['ip_address', 'last_seen']
                            }
                          }
                        ],
                        config: {
                          network: '10.127.0.0/24',
                          parallel_threads: 20,
                          batch_size: 50,
                          global_timeout: 300,
                          error_handling: 'continue',
                          logging: {
                            level: 'INFO',
                            file: '/var/log/poller.log',
                            format: 'json'
                          },
                          scheduling: {
                            enabled: true,
                            interval: 3600,
                            timezone: 'UTC',
                            retry_on_failure: true,
                            max_retries: 3
                          }
                        }
                      };
                      setEditingJob(discoveryJob);
                      setShowJobBuilder(true);
                    }}
                    className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                    title="Configure Job"
                  >
                    <Save className="w-3 h-3" />
                  </button>
                  {!job.id.startsWith('discovery') && !job.id.startsWith('interface') && !job.id.startsWith('optical') && (
                    <button
                      onClick={() => deleteJob(job.id)}
                      className="p-1 text-red-600 hover:bg-red-50 rounded"
                      title="Delete Job"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                  <button
                    onClick={() => startJob(job.type)}
                    disabled={job.enabled}
                    className="p-1 text-green-600 hover:bg-green-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Start Job"
                  >
                    <Play className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => stopJob(job.type)}
                    disabled={!job.enabled}
                    className="p-1 text-red-600 hover:bg-red-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Stop Job"
                  >
                    <Square className="w-3 h-3" />
                  </button>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Execution Log */}
        <div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">Execution Log</h2>
              <button
                onClick={refreshStatus}
                className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                title="Refresh Log"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
            
            <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-xs overflow-y-auto" style={{maxHeight: '500px'}}>
              {/* Header with fixed columns */}
              <div className="flex items-center gap-2 border-b border-gray-700 pb-2 mb-2 text-gray-400">
                <span className="w-32">TIMESTAMP</span>
                <span className="w-36">JOB TYPE</span>
                <span className="w-16 text-center">STATUS</span>
                <span className="w-16 text-right">DURATION</span>
                <span className="flex-1">RESULT</span>
              </div>
              
              {/* Log entries with fixed columns */}
              {status.execution_log && status.execution_log.length > 0 ? (
                status.execution_log.map((log, index) => (
                  <div key={index} className="flex items-center gap-2 border-b border-gray-800">
                    <span className="w-32 text-gray-500 truncate">{log.timestamp}</span>
                    <span className={cn(
                      "w-36 font-medium truncate",
                      log.status === 'Success' ? "text-green-400" :
                      log.status === 'Error' ? "text-red-400" :
                      "text-yellow-400"
                    )}>
                      {log.job_name}
                    </span>
                    <span className={cn(
                      "w-16 text-center text-xs px-2 py-0.5 rounded",
                      log.status === 'Success' ? "bg-green-900 text-green-300" :
                      log.status === 'Error' ? "bg-red-900 text-red-300" :
                      "bg-yellow-900 text-yellow-300"
                    )}>
                      {log.status === 'Success' ? 'SUCCESS' : 
                       log.status === 'Error' ? 'FAILED' : 'UNKNOWN'}
                    </span>
                    <span className="w-16 text-right text-gray-500">
                      {log.duration || '-'}
                    </span>
                    <span className="flex-1 text-cyan-300">
                      {log.brief_status || 'Completed'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-gray-500">No job executions recorded</div>
              )}
            </div>
          </div>
        </div>
      </div>
      </div>

      {/* Generic Job Builder Modal */}
      {showJobBuilder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 overflow-hidden">
          <div className="h-full w-full overflow-auto">
            <ErrorBoundary onClose={() => {
              setShowJobBuilder(false);
              setEditingJob(null);
            }}>
              <CompleteJobBuilder
                job={editingJob || {
                job_id: 'discovery',
                name: 'Network Discovery',
                description: 'Complete network discovery with all parameters exposed',
                actions: [
                  {
                    type: 'ping_scan',
                    enabled: true,
                    login_method: {
                      type: 'ping',
                      command: 'ping -c {count} -W {timeout} -i {interval} {target}',
                      parameters: {
                        count: 1,
                        timeout: 1,
                        interval: 0.2,
                        timeout_unit: 'seconds'
                      },
                      success_criteria: {
                        return_code: 0,
                        output_contains: ['bytes from'],
                        output_regex: 'bytes from .*: icmp_seq=\\d+ ttl=\\d+ time=([0-9.]+)'
                      }
                    },
                    targeting: {
                      source: 'network_range',
                      network_range: '10.127.0.0/24',
                      target_list: '',
                      exclude_list: '',
                      max_concurrent: 50,
                      retry_count: 3,
                      retry_delay: 1
                    },
                    execution: {
                      timeout: 5,
                      kill_signal: 'SIGTERM',
                      working_directory: '/tmp',
                      environment: {},
                      pre_command: '',
                      post_command: ''
                    },
                    result_parsing: {
                      parser_type: 'regex',
                      patterns: [
                        {
                          name: 'ping_success',
                          regex: 'bytes from .*: icmp_seq=\\d+ ttl=\\d+ time=([0-9.]+)',
                          field_mapping: {
                            'ping_time': '$1',
                            'ping_status': 'online'
                          }
                        },
                        {
                          name: 'ping_failure',
                          regex: 'no answer|100% packet loss|Destination host unreachable',
                          field_mapping: {
                            'ping_status': 'offline',
                            'ping_time': '0'
                          }
                        }
                      ],
                      default_values: {
                        'ping_status': 'offline',
                        'ping_time': '0',
                        'last_seen': 'NOW()'
                      }
                    },
                    database: {
                      table: 'devices',
                      operation: 'upsert',
                      key_fields: ['ip_address'],
                      field_types: {
                        'ip_address': 'INET',
                        'ping_status': 'VARCHAR(20)',
                        'ping_time': 'FLOAT',
                        'last_seen': 'TIMESTAMP'
                      },
                      indexes: ['ip_address', 'last_seen']
                    }
                  }
                ],
                config: {
                  network: '10.127.0.0/24',
                  parallel_threads: 20,
                  batch_size: 50,
                  global_timeout: 300,
                  error_handling: 'continue',
                  logging: {
                    level: 'INFO',
                    file: '/var/log/poller.log',
                    format: 'json'
                  },
                  scheduling: {
                    enabled: true,
                    interval: 3600,
                    timezone: 'UTC',
                    retry_on_failure: true,
                    max_retries: 3
                  }
                }
              }}
              onSave={(job) => {
                console.log('Saving COMPLETE job:', job);
                setShowJobBuilder(false);
                setEditingJob(null);
              }}
              onTest={(job) => {
                console.log('Testing COMPLETE job:', job);
              }}
              onBack={() => {
                setShowJobBuilder(false);
                setEditingJob(null);
              }}
            />
            </ErrorBoundary>
          </div>
        </div>
      )}
    </div>
  );
};

export default Poller;
