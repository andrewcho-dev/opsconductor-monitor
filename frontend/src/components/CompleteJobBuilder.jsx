import React, { useState, useEffect } from 'react';
import IntelligentCommandBuilder from './IntelligentCommandBuilder';
import { getCommand } from '../data/commandLibraries';

const CompleteJobBuilder = ({ job, onSave, onTest, onBack }) => {
  const [currentJob, setCurrentJob] = useState(job || {
    job_id: 'discovery',
    name: 'Network Discovery',
    description: 'Complete network discovery with intelligent command configuration',
    actions: [
      {
        type: 'ping',
        enabled: true,
        login_method: {
          platform: 'ubuntu-20.04',
          command_id: 'ping',
          command_template: 'ping -c {count} -W {timeout} -i {interval} {target}',
          parameters: {
            count: 1,
            timeout: 1,
            interval: 0.2
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
          command: 'snmpget -v{version} -c {community} -t {timeout} {target} {oids}',
          parameters: {
            version: '2c',
            community: 'public',
            timeout: 3,
            retries: 2,
            oids: 'sysDescr.0 sysName.0 sysLocation.0'
          },
          success_criteria: {
            return_code: 0,
            output_contains: ['STRING:'],
            output_regex: 'STRING: "(.*)"'
          }
        },
        targeting: {
          source: 'network_range',
          network_range: '10.127.0.0/24',
          target_list: '',
          exclude_list: '',
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
              regex: 'sysDescr\\.0 = STRING: "(.*?)"',
              field_mapping: {
                'system_description': '$1',
                'snmp_status': 'YES'
              }
            },
            {
              name: 'snmp_name',
              regex: 'sysName\\.0 = STRING: "(.*?)"',
              field_mapping: {
                'hostname': '$1'
              }
            },
            {
              name: 'snmp_location',
              regex: 'sysLocation\\.0 = STRING: "(.*?)"',
              field_mapping: {
                'location': '$1'
              }
            },
            {
              name: 'snmp_failure',
              regex: 'Timeout|No Response',
              field_mapping: {
                'snmp_status': 'NO'
              }
            }
          ],
          default_values: {
            'snmp_status': 'NO',
            'last_seen': 'NOW()'
          }
        },
        database: {
          table: 'devices',
          operation: 'upsert',
          key_fields: ['ip_address'],
          field_types: {
            'ip_address': 'INET',
            'system_description': 'TEXT',
            'hostname': 'VARCHAR(255)',
            'location': 'VARCHAR(255)',
            'snmp_status': 'VARCHAR(10)',
            'last_seen': 'TIMESTAMP'
          },
          indexes: ['ip_address', 'hostname']
        }
      },
      {
        type: 'ssh_scan',
        enabled: true,
        login_method: {
          type: 'ssh_port',
          command: 'nc -z -v -w {timeout} {target} {port}',
          parameters: {
            port: 22,
            timeout: 5,
            source_port: 0
          },
          success_criteria: {
            return_code: 0,
            output_contains: ['succeeded', 'open'],
            output_regex: 'Connection to .* port .* \\[tcp/ssh\\] succeeded!'
          }
        },
        targeting: {
          source: 'network_range',
          network_range: '10.127.0.0/24',
          target_list: '',
          exclude_list: '',
          max_concurrent: 30,
          retry_count: 2,
          retry_delay: 1
        },
        execution: {
          timeout: 7,
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
              name: 'ssh_success',
              regex: 'succeeded|open',
              field_mapping: {
                'ssh_status': 'YES',
                'ssh_port': '22'
              }
            },
            {
              name: 'ssh_failure',
              regex: 'failed|refused|timeout',
              field_mapping: {
                'ssh_status': 'NO',
                'ssh_port': '22'
              }
            }
          ],
          default_values: {
            'ssh_status': 'NO',
            'ssh_port': '22',
            'last_seen': 'NOW()'
          }
        },
        database: {
          table: 'devices',
          operation: 'upsert',
          key_fields: ['ip_address'],
          field_types: {
            'ip_address': 'INET',
            'ssh_status': 'VARCHAR(10)',
            'ssh_port': 'INTEGER',
            'last_seen': 'TIMESTAMP'
          },
          indexes: ['ip_address', 'ssh_status']
        }
      },
      {
        type: 'rdp_scan',
        enabled: true,
        login_method: {
          type: 'rdp_port',
          command: 'nc -z -v -w {timeout} {target} {port}',
          parameters: {
            port: 3389,
            timeout: 3,
            source_port: 0
          },
          success_criteria: {
            return_code: 0,
            output_contains: ['succeeded', 'open'],
            output_regex: 'Connection to .* port .* \\[tcp/rdp\\] succeeded!'
          }
        },
        targeting: {
          source: 'network_range',
          network_range: '10.127.0.0/24',
          target_list: '',
          exclude_list: '',
          max_concurrent: 25,
          retry_count: 2,
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
              name: 'rdp_success',
              regex: 'succeeded|open',
              field_mapping: {
                'rdp_status': 'YES',
                'rdp_port': '3389'
              }
            },
            {
              name: 'rdp_failure',
              regex: 'failed|refused|timeout',
              field_mapping: {
                'rdp_status': 'NO',
                'rdp_port': '3389'
              }
            }
          ],
          default_values: {
            'rdp_status': 'NO',
            'rdp_port': '3389',
            'last_seen': 'NOW()'
          }
        },
        database: {
          table: 'devices',
          operation: 'upsert',
          key_fields: ['ip_address'],
          field_types: {
            'ip_address': 'INET',
            'rdp_status': 'VARCHAR(10)',
            'rdp_port': 'INTEGER',
            'last_seen': 'TIMESTAMP'
          },
          indexes: ['ip_address', 'rdp_status']
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
  });

  const [testMode, setTestMode] = useState(false);
  const [testActionIndex, setTestActionIndex] = useState(0);
  const [testInput, setTestInput] = useState('PING 192.168.1.1 (192.168.1.1): 56 data bytes\n64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.123 ms\n64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=0.456 ms');
  const [testResults, setTestResults] = useState([]);

  const testRegexPatterns = () => {
    const action = currentJob.actions[testActionIndex];
    if (!action || !action.result_parsing.patterns) {
      setTestResults([]);
      return;
    }

    const results = [];
    const input = testInput;

    // Test each pattern against the input
    action.result_parsing.patterns.forEach(pattern => {
      try {
        const regex = new RegExp(pattern.regex, 'g');
        const matches = [];
        let match;

        while ((match = regex.exec(input)) !== null) {
          const mappedFields = {};
          
          // Apply field mapping
          Object.entries(pattern.field_mapping).forEach(([field, mapping]) => {
            if (mapping.startsWith('$') && match.length > parseInt(mapping.substring(1))) {
              mappedFields[field] = match[parseInt(mapping.substring(1))];
            } else {
              mappedFields[field] = mapping;
            }
          });

          matches.push({
            patternName: pattern.name,
            match: match[0],
            groups: match.slice(1),
            mappedFields: mappedFields
          });
        }

        if (matches.length > 0) {
          results.push({
            patternName: pattern.name,
            regex: pattern.regex,
            matches: matches,
            success: true
          });
        } else {
          results.push({
            patternName: pattern.name,
            regex: pattern.regex,
            matches: [],
            success: false,
            error: 'No matches found'
          });
        }
      } catch (error) {
        results.push({
          patternName: pattern.name,
          regex: pattern.regex,
          matches: [],
          success: false,
          error: error.message
        });
      }
    });

    // Apply default values
    const finalResult = {
      parsedFields: {},
      patterns: results
    };

    // Merge all mapped fields
    results.forEach(result => {
      if (result.success) {
        result.matches.forEach(match => {
          Object.assign(finalResult.parsedFields, match.mappedFields);
        });
      }
    });

    // Add default values for missing fields
    Object.assign(finalResult.parsedFields, action.result_parsing.default_values || {});

    setTestResults([finalResult]);
  };

  // Auto-test when patterns or input changes
  React.useEffect(() => {
    if (testMode && currentJob.actions[testActionIndex]) {
      testRegexPatterns();
    }
  }, [testInput, testActionIndex, currentJob.actions[testActionIndex]?.result_parsing.patterns, testMode]);

  const updateAction = (actionIndex, field, value) => {
    const newActions = [...currentJob.actions];
    const keys = field.split('.');
    let current = newActions[actionIndex];
    
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    
    // Auto-update action type when command changes
    if (field === 'login_method.command_id') {
      newActions[actionIndex].type = value.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    }
    
    setCurrentJob(prev => ({ ...prev, actions: newActions }));
  };

  const addAction = () => {
    const newAction = {
      type: 'ping', // Default command, will be auto-updated based on selection
      enabled: true,
      login_method: {
        platform: 'ubuntu-20.04',
        command_id: 'ping',
        command_template: 'ping -c {count} -W {timeout} -i {interval} {target}',
        parameters: {
          count: 1,
          timeout: 1,
          interval: 0.2
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
        max_concurrent: 10,
        retry_count: 1,
        retry_delay: 1
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
        patterns: [],
        default_values: {
          'last_seen': 'NOW()'
        }
      },
      database: {
        table: 'devices',
        operation: 'upsert',
        key_fields: ['ip_address'],
        field_types: {},
        indexes: []
      }
    };
    setCurrentJob(prev => ({
      ...prev,
      actions: [...prev.actions, newAction]
    }));
  };

  const deleteAction = (index) => {
    setCurrentJob(prev => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== index)
    }));
  };

  const addParsingPattern = (actionIndex) => {
    const newPattern = {
      name: 'custom_pattern',
      regex: '(.*)',
      field_mapping: {
        'custom_field': '$1'
      }
    };
    updateAction(actionIndex, 'result_parsing.patterns', [
      ...(currentJob.actions[actionIndex].result_parsing.patterns || []),
      newPattern
    ]);
  };

  const getActionType = (action) => {
    // Automatically determine action type based on login method and configuration
    const method = action.login_method?.type;
    
    switch (method) {
      case 'ping':
        return 'ping_scan';
      case 'snmp':
        return 'snmp_scan';
      case 'ssh_port':
        return 'ssh_scan';
      case 'rdp_port':
        return 'rdp_scan';
      case 'ssh_command':
        return 'ssh_command';
      case 'http_request':
        return 'http_check';
      case 'custom':
        return 'custom_scan';
      default:
        return 'unknown_scan';
    }
  };

  const getActionDisplayName = (action) => {
    // Get the intelligent command name if available
    if (action.login_method?.command_id) {
      const command = getCommand(action.login_method.platform || 'ubuntu-20.04', action.login_method.command_id);
      return command?.name || action.login_method.command_id.toUpperCase();
    }
    // Fallback to automatic action type
    return getActionType(action).toUpperCase();
  };

  const moveAction = (index, direction) => {
    const newActions = [...currentJob.actions];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    
    if (targetIndex >= 0 && targetIndex < newActions.length) {
      // Swap actions
      [newActions[index], newActions[targetIndex]] = [newActions[targetIndex], newActions[index]];
      setCurrentJob(prev => ({ ...prev, actions: newActions }));
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-2">
      <div className="w-full">
        {/* Header - Spans full width */}
        <div className="bg-white rounded shadow p-3 mb-2">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-bold">COMPLETE JOB DEFINITION</h1>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={testMode}
                  onChange={(e) => setTestMode(e.target.checked)}
                  className="rounded"
                />
                Test Mode
              </label>
            </div>
            <div className="flex gap-2">
              <button onClick={onBack} className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600">Back</button>
              <button onClick={() => onTest(currentJob)} className="px-3 py-1 bg-green-500 text-white rounded text-sm">Test</button>
              <button onClick={() => onSave(currentJob)} className="px-3 py-1 bg-blue-500 text-white rounded text-sm">Save</button>
            </div>
          </div>
        </div>

        {/* Main Content - 2/3 left, 1/3 right */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
          {/* Left Column - 2/3 width */}
          <div className="lg:col-span-2">
        <div className="bg-white rounded shadow p-3 mb-2">
          <h2 className="text-lg font-bold mb-2">JOB INFORMATION</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Job ID</label>
              <input
                type="text"
                value={currentJob.job_id}
                onChange={(e) => setCurrentJob(prev => ({ ...prev, job_id: e.target.value }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Name</label>
              <input
                type="text"
                value={currentJob.name}
                onChange={(e) => setCurrentJob(prev => ({ ...prev, name: e.target.value }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Description</label>
              <input
                type="text"
                value={currentJob.description}
                onChange={(e) => setCurrentJob(prev => ({ ...prev, description: e.target.value }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                placeholder="Describe what this job does"
              />
            </div>
          </div>
        </div>

        {/* Execution Configuration */}
        <div className="bg-white rounded shadow p-3 mb-2">
          <h2 className="text-lg font-bold mb-2">
            EXECUTION CONFIGURATION
            <span className="text-xs font-normal text-gray-600 ml-2">
              (Global settings for how this job runs - threads, timeouts, error handling)
            </span>
          </h2>
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Parallel Threads</label>
              <input
                type="number"
                value={currentJob.config.parallel_threads}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, parallel_threads: parseInt(e.target.value) }
                }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Batch Size</label>
              <input
                type="number"
                value={currentJob.config.batch_size}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, batch_size: parseInt(e.target.value) }
                }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Global Timeout (sec)</label>
              <input
                type="number"
                value={currentJob.config.global_timeout}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, global_timeout: parseInt(e.target.value) }
                }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Error Handling</label>
              <select
                value={currentJob.config.error_handling}
                onChange={(e) => setCurrentJob(prev => ({ 
                  ...prev, 
                  config: { ...prev.config, error_handling: e.target.value }
                }))}
                className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
              >
                <option value="continue">Continue</option>
                <option value="stop">Stop</option>
                <option value="retry">Retry</option>
              </select>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white rounded shadow p-3 mb-2">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-bold">
              ACTIONS ({currentJob.actions.length})
              <span className="text-xs font-normal text-gray-600 ml-2">
                (What this job actually does - each action runs commands on targets)
              </span>
            </h2>
            <button onClick={addAction} className="px-3 py-1 bg-green-500 text-white rounded text-sm">Add Action</button>
          </div>

          {currentJob.actions.map((action, actionIndex) => (
            <details key={actionIndex} className="border rounded shadow">
              <summary className={`cursor-pointer p-2 flex justify-between items-center ${
                  action.enabled ? 'bg-gray-50 hover:bg-gray-100' : 'bg-red-50 hover:bg-red-100'
                }`}>
                <div>
                  <h3 className="text-sm font-bold">
                    ACTION {actionIndex + 1}: {getActionDisplayName(action)}
                  </h3>
                  <span className="text-xs text-gray-500">
                    {action.login_method?.platform || 'ubuntu-20.04'} • {action.login_method?.command_id || action.login_method?.type || 'unknown'} • {action.targeting?.source} • {action.database?.table}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      moveAction(actionIndex, 'up');
                    }}
                    disabled={actionIndex === 0}
                    className={`p-1 text-xs rounded ${actionIndex === 0 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-200'}`}
                    title="Move Up"
                  >
                    ↑
                  </button>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      moveAction(actionIndex, 'down');
                    }}
                    disabled={actionIndex === currentJob.actions.length - 1}
                    className={`p-1 text-xs rounded ${actionIndex === currentJob.actions.length - 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-200'}`}
                    title="Move Down"
                  >
                    ↓
                  </button>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      updateAction(actionIndex, 'enabled', !action.enabled);
                    }}
                    className={`px-2 py-1 text-xs rounded font-medium ${
                      action.enabled 
                        ? 'bg-green-500 text-white hover:bg-green-600' 
                        : 'bg-red-500 text-white hover:bg-red-600'
                    }`}
                    title={action.enabled ? 'Disable Action' : 'Enable Action'}
                  >
                    {action.enabled ? 'ON' : 'OFF'}
                  </button>
                  <button 
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      deleteAction(actionIndex);
                    }} 
                    className="px-2 py-1 bg-red-500 text-white rounded text-xs font-medium hover:bg-red-600"
                    title="Delete Action"
                  >
                    DELETE
                  </button>
                </div>
              </summary>

              <div className="p-2">
                {/* Compact Action Fields */}
                <div className="mb-2">
                  {/* Intelligent Command Configuration */}
                  <div className="mb-4">
                    <IntelligentCommandBuilder 
                      action={action}
                      actionIndex={actionIndex}
                      updateAction={updateAction}
                    />
                  </div>

                  {/* Target Configuration */}
                  <div className="mb-2">
                    <h4 className="text-xs font-bold mb-1">
                      TARGETS
                      <span className="text-xs font-normal text-gray-600 ml-1">
                        (What devices this action runs on)
                      </span>
                    </h4>
                    <div className="grid grid-cols-1 gap-2 mb-2">
                      <div>
                        <label className="block text-xs font-medium mb-1">Target Source</label>
                      <select
                        value={action.targeting.source}
                        onChange={(e) => updateAction(actionIndex, 'targeting.source', e.target.value)}
                        className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                      >
                        <option value="network_range">Network Range</option>
                        <option value="target_list">Target List</option>
                        <option value="custom_groups">Custom Groups</option>
                        <option value="network_groups">Network Groups</option>
                        <option value="database_query">Database Query</option>
                        <option value="file">File</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Target Configuration - Only show relevant fields */}
                <div className="mb-2">
                  <h4 className="text-xs font-bold mb-1">
                    TARGETS
                    <span className="text-xs font-normal text-gray-600 ml-1">
                      (What devices this action runs on)
                    </span>
                  </h4>
                  <div className="grid grid-cols-3 gap-2">
                    {action.targeting.source === 'network_range' && (
                      <div>
                        <label className="block text-xs font-medium mb-1">Network Range</label>
                        <input
                          type="text"
                          value={action.targeting.network_range}
                          onChange={(e) => updateAction(actionIndex, 'targeting.network_range', e.target.value)}
                          className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                        />
                      </div>
                    )}
                    {(action.targeting.source === 'target_list' || action.targeting.source === 'file') && (
                      <div className="col-span-2">
                        <label className="block text-xs font-medium mb-1">
                          {action.targeting.source === 'target_list' ? 'Target List' : 'File Path'} (one per line)
                        </label>
                        <textarea
                          value={action.targeting.source === 'target_list' ? action.targeting.target_list : action.targeting.file_path}
                          onChange={(e) => updateAction(actionIndex, action.targeting.source === 'target_list' ? 'targeting.target_list' : 'targeting.file_path', e.target.value)}
                          className="w-full p-1 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                          rows={2}
                        />
                      </div>
                    )}
                    {(action.targeting.source === 'custom_groups' || action.targeting.source === 'network_groups') && (
                      <div className="col-span-2">
                        <label className="block text-xs font-medium mb-1">
                          {action.targeting.source === 'custom_groups' ? 'Custom' : 'Network'} Groups (JSON array)
                        </label>
                        <textarea
                          value={JSON.stringify(action.targeting[action.targeting.source] || [], null, 2)}
                          onChange={(e) => {
                            try {
                              updateAction(actionIndex, `targeting.${action.targeting.source}`, JSON.parse(e.target.value));
                            } catch (err) {
                              // Invalid JSON, don't update
                            }
                          }}
                          className="w-full p-1 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                          rows={2}
                          placeholder='["group1", "group2"]'
                        />
                      </div>
                    )}
                    <div>
                      <label className="block text-xs font-medium mb-1">Max Concurrent</label>
                      <input
                        type="number"
                        value={action.targeting.max_concurrent}
                        onChange={(e) => updateAction(actionIndex, 'targeting.max_concurrent', parseInt(e.target.value))}
                        className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                      />
                    </div>
                  </div>
                </div>

                {/* Results Configuration */}
                <div className="mb-2">
                  <h4 className="text-xs font-bold mb-1">
                    RESULTS
                    <span className="text-xs font-normal text-gray-600 ml-1">
                      (How command output is parsed and stored)
                    </span>
                  </h4>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="block text-xs font-medium mb-1">Parser Type</label>
                      <select
                        value={action.result_parsing.parser_type}
                        onChange={(e) => updateAction(actionIndex, 'result_parsing.parser_type', e.target.value)}
                        className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                      >
                        <option value="regex">Regex</option>
                        <option value="json">JSON</option>
                        <option value="xml">XML</option>
                        <option value="csv">CSV</option>
                        <option value="custom">Custom</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Database Table</label>
                      <input
                        type="text"
                        value={action.database.table}
                        onChange={(e) => updateAction(actionIndex, 'database.table', e.target.value)}
                        className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Operation</label>
                      <select
                        value={action.database.operation}
                        onChange={(e) => updateAction(actionIndex, 'database.operation', e.target.value)}
                        className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                      >
                        <option value="insert">Insert</option>
                        <option value="update">Update</option>
                        <option value="upsert">Upsert</option>
                        <option value="replace">Replace</option>
                      </select>
                    </div>
                  </div>
                </div>
                </div>

                {/* Advanced Configuration - Collapsible */}
                <details className="text-xs">
                  <summary className="cursor-pointer font-bold mb-1">ADVANCED CONFIGURATION</summary>
                  <div className="mt-2 space-y-2">
                    {/* Parameters */}
                    <div>
                      <label className="block text-xs font-medium mb-1">Command Parameters (JSON)</label>
                      <textarea
                        value={JSON.stringify(action.login_method.parameters, null, 2)}
                        onChange={(e) => {
                          try {
                            updateAction(actionIndex, 'login_method.parameters', JSON.parse(e.target.value));
                          } catch (err) {
                            // Invalid JSON, don't update
                          }
                        }}
                        className="w-full p-1 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                        rows={2}
                      />
                    </div>

                    {/* Success Criteria */}
                    <div>
                      <label className="block text-xs font-medium mb-1">Success Criteria (JSON)</label>
                      <textarea
                        value={JSON.stringify(action.login_method.success_criteria, null, 2)}
                        onChange={(e) => {
                          try {
                            updateAction(actionIndex, 'login_method.success_criteria', JSON.parse(e.target.value));
                          } catch (err) {
                            // Invalid JSON, don't update
                          }
                        }}
                        className="w-full p-1 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                        rows={2}
                      />
                    </div>

                    {/* Parsing Patterns */}
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="block text-xs font-medium">Parsing Patterns</label>
                        <button onClick={() => addParsingPattern(actionIndex)} className="px-2 py-1 bg-green-500 text-white rounded text-xs">Add Pattern</button>
                      </div>
                      {action.result_parsing.patterns?.map((pattern, patternIndex) => (
                        <div key={patternIndex} className="border rounded p-1 mb-1">
                          <div className="grid grid-cols-2 gap-1">
                            <input
                              type="text"
                              value={pattern.name}
                              onChange={(e) => updateParsingPattern(actionIndex, patternIndex, 'name', e.target.value)}
                              placeholder="Pattern name"
                              className="w-full p-1 border rounded text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                            />
                            <input
                              type="text"
                              value={pattern.regex}
                              onChange={(e) => updateParsingPattern(actionIndex, patternIndex, 'regex', e.target.value)}
                              placeholder="Regex pattern"
                              className="w-full p-1 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                            />
                          </div>
                          <textarea
                            value={JSON.stringify(pattern.field_mapping, null, 2)}
                            onChange={(e) => {
                              try {
                                updateParsingPattern(actionIndex, patternIndex, 'field_mapping', JSON.parse(e.target.value));
                              } catch (err) {
                                // Invalid JSON, don't update
                              }
                            }}
                            placeholder="Field mapping (JSON)"
                            className="w-full p-1 border rounded font-mono text-xs mt-1"
                            rows={1}
                          />
                        </div>
                      ))}
                    </div>

                    {/* Database Config */}
                    <div>
                      <label className="block text-xs font-medium mb-1">Database Config (JSON)</label>
                      <textarea
                        value={JSON.stringify({
                          key_fields: action.database.key_fields,
                          field_types: action.database.field_types,
                          indexes: action.database.indexes
                        }, null, 2)}
                        onChange={(e) => {
                          try {
                            const config = JSON.parse(e.target.value);
                            updateAction(actionIndex, 'database.key_fields', config.key_fields);
                            updateAction(actionIndex, 'database.field_types', config.field_types);
                            updateAction(actionIndex, 'database.indexes', config.indexes);
                          } catch (err) {
                            // Invalid JSON, don't update
                          }
                        }}
                        className="w-full p-1 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                        rows={3}
                      />
                    </div>
                  </div>
                </details>
              </div>
            </details>
          ))}
        </div>

        {/* Raw JSON View - Collapsible */}
        <details className="bg-gray-800 text-green-400 rounded shadow p-3 border-2 border-gray-600">
          <summary className="cursor-pointer font-bold text-green-300 flex items-center gap-2">
            <span>📋</span> RAW JSON DEFINITION 
            <span className="text-xs font-normal text-gray-400">(Final Output - Read Only)</span>
          </summary>
          <div className="mt-2">
            <div className="text-xs text-gray-400 mb-2 font-mono">
              // This is the complete job configuration that will be saved and executed
              // Copy this JSON to backup, share, or import your job definition
            </div>
            <textarea
              value={JSON.stringify(currentJob, null, 2)}
              readOnly
              className="w-full p-3 bg-gray-900 text-green-400 border border-gray-600 rounded font-mono text-xs bg-gray-800 focus:bg-gray-800 focus:ring-2 focus:ring-green-400"
              rows={12}
              style={{ resize: 'vertical' }}
            />
          </div>
        </details>
          </div>

          {/* Right Column - 1/3 width */}
          <div className="lg:col-span-1">
            {testMode ? (
              <div className="bg-white rounded shadow p-3">
                <h2 className="text-lg font-bold mb-2">
                  REGEX TESTING
                  <span className="text-xs font-normal text-gray-600 ml-2">
                    (Test your regex patterns in real-time)
                  </span>
                </h2>
                
                {/* Action Selector */}
                <div className="mb-3">
                  <label className="block text-xs font-medium mb-1">Test Action</label>
                  <select
                    value={testActionIndex}
                    onChange={(e) => setTestActionIndex(parseInt(e.target.value))}
                    className="w-full p-1 border rounded text-sm bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                  >
                    {currentJob.actions.map((action, index) => (
                      <option key={index} value={index}>
                        Action {index + 1}: {action.type.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Test Input */}
                <div className="mb-3">
                  <label className="block text-xs font-medium mb-1">Test Input</label>
                  <textarea
                    value={testInput}
                    onChange={(e) => setTestInput(e.target.value)}
                    className="w-full p-2 border rounded font-mono text-xs bg-gray-200 focus:bg-white focus:ring-2 focus:ring-blue-300"
                    rows={4}
                    placeholder="Enter sample command output to test regex patterns..."
                  />
                </div>

                {/* Test Results */}
                <div className="mb-3">
                  <h3 className="text-sm font-bold mb-2">Test Results</h3>
                  {testResults.length > 0 ? (
                    <div className="space-y-2">
                      {testResults.map((result, resultIndex) => (
                        <div key={resultIndex} className="border rounded p-2">
                          {/* Parsed Fields */}
                          <div className="mb-2">
                            <h4 className="text-xs font-bold mb-1">Parsed Fields:</h4>
                            <div className="bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
                              {Object.entries(result.parsedFields).map(([field, value]) => (
                                <div key={field} className="text-xs font-mono mb-1">
                                  <span className="font-medium">{field}:</span> {JSON.stringify(value)}
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Pattern Results */}
                          <div>
                            <h4 className="text-xs font-bold mb-1">Pattern Matches:</h4>
                            <div className="space-y-1 max-h-32 overflow-y-auto">
                              {result.patterns.map((pattern, patternIndex) => (
                                <div key={patternIndex} className={`text-xs p-1 rounded ${pattern.success ? 'bg-green-50' : 'bg-red-50'}`}>
                                  <div className="font-medium">{pattern.patternName}</div>
                                  <div className="font-mono text-gray-600 text-xs break-all">{pattern.regex}</div>
                                  {pattern.success ? (
                                    <div className="text-green-700">
                                      {pattern.matches.length} matches found
                                    </div>
                                  ) : (
                                    <div className="text-red-700 text-xs">
                                      Error: {pattern.error}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500 italic">
                      No patterns to test. Add regex patterns to the action's result parsing.
                    </div>
                  )}
                </div>

                {/* Sample Data Templates */}
                <div className="border-t pt-2">
                  <h4 className="text-xs font-bold mb-1">Sample Data:</h4>
                  <div className="space-y-1">
                    <button
                      onClick={() => setTestInput('PING 192.168.1.1 (192.168.1.1): 56 data bytes\n64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.123 ms\n64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=0.456 ms')}
                      className="w-full px-2 py-1 bg-blue-500 text-white rounded text-xs"
                    >
                      Ping Success
                    </button>
                    <button
                      onClick={() => setTestInput('PING 192.168.1.1 (192.168.1.1): 56 data bytes\n--- 192.168.1.1 ping statistics ---\n3 packets transmitted, 0 received, 100% packet loss')}
                      className="w-full px-2 py-1 bg-blue-500 text-white rounded text-xs"
                    >
                      Ping Failure
                    </button>
                    <button
                      onClick={() => setTestInput('SNMPv2c: Community is public\nsysDescr.0 = STRING: "Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 15.0(2)SE"')}
                      className="w-full px-2 py-1 bg-blue-500 text-white rounded text-xs"
                    >
                      SNMP Success
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 rounded border-2 border-dashed border-gray-300 p-6 text-center">
                <div className="text-gray-400">
                  <div className="text-lg font-medium mb-2">Test Mode</div>
                  <div className="text-sm">Enable test mode to see real-time regex testing results here</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompleteJobBuilder;
