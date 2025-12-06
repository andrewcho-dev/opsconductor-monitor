export const createEmptyAction = () => ({
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
    source: 'network_groups',
    network_range: '10.127.0.0/24',
    target_list: '',
    exclude_list: '',
    file_path: '',
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
      last_seen: 'NOW()'
    }
  },
  database: {
    table: 'devices',
    operation: 'upsert',
    key_fields: ['ip_address'],
    field_types: {},
    indexes: []
  }
});

export const DEFAULT_JOB = {
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
        file_path: '',
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
              ping_time: '$1',
              ping_status: 'online'
            }
          },
          {
            name: 'ping_failure',
            regex: 'no answer|100% packet loss|Destination host unreachable',
            field_mapping: {
              ping_status: 'offline',
              ping_time: '0'
            }
          }
        ],
        default_values: {
          ping_status: 'offline',
          ping_time: '0',
          last_seen: 'NOW()'
        }
      },
      database: {
        table: 'devices',
        operation: 'upsert',
        key_fields: ['ip_address'],
        field_types: {
          ip_address: 'INET',
          ping_status: 'VARCHAR(20)',
          ping_time: 'FLOAT',
          last_seen: 'TIMESTAMP'
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
        file_path: '',
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
            regex: 'sysDescr\\.0 = STRING: "(.*?)"',
            field_mapping: {
              system_description: '$1',
              snmp_status: 'YES'
            }
          },
          {
            name: 'snmp_name',
            regex: 'sysName\\.0 = STRING: "(.*?)"',
            field_mapping: {
              hostname: '$1'
            }
          },
          {
            name: 'snmp_location',
            regex: 'sysLocation\\.0 = STRING: "(.*?)"',
            field_mapping: {
              location: '$1'
            }
          },
          {
            name: 'snmp_failure',
            regex: 'Timeout|No Response',
            field_mapping: {
              snmp_status: 'NO'
            }
          }
        ],
        default_values: {
          snmp_status: 'NO',
          last_seen: 'NOW()'
        }
      },
      database: {
        table: 'devices',
        operation: 'upsert',
        key_fields: ['ip_address'],
        field_types: {
          ip_address: 'INET',
          system_description: 'TEXT',
          hostname: 'VARCHAR(255)',
          location: 'VARCHAR(255)',
          snmp_status: 'VARCHAR(10)',
          last_seen: 'TIMESTAMP'
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
          output_regex: 'Connection to .* port .* succeeded!'
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
              ssh_status: 'YES',
              ssh_port: '22'
            }
          },
          {
            name: 'ssh_failure',
            regex: 'failed|refused|timeout',
            field_mapping: {
              ssh_status: 'NO',
              ssh_port: '22'
            }
          }
        ],
        default_values: {
          ssh_status: 'NO',
          ssh_port: '22',
          last_seen: 'NOW()'
        }
      },
      database: {
        table: 'devices',
        operation: 'upsert',
        key_fields: ['ip_address'],
        field_types: {
          ip_address: 'INET',
          ssh_status: 'VARCHAR(10)',
          ssh_port: 'INTEGER',
          last_seen: 'TIMESTAMP'
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
          output_regex: 'Connection to .* port .* succeeded!'
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
              rdp_status: 'YES',
              rdp_port: '3389'
            }
          },
          {
            name: 'rdp_failure',
            regex: 'failed|refused|timeout',
            field_mapping: {
              rdp_status: 'NO',
              rdp_port: '3389'
            }
          }
        ],
        default_values: {
          rdp_status: 'NO',
          rdp_port: '3389',
          last_seen: 'NOW()'
        }
      },
      database: {
        table: 'devices',
        operation: 'upsert',
        key_fields: ['ip_address'],
        field_types: {
          ip_address: 'INET',
          rdp_status: 'VARCHAR(10)',
          rdp_port: 'INTEGER',
          last_seen: 'TIMESTAMP'
        },
        indexes: ['ip_address', 'rdp_status']
      }
    }
  ],
  config: {
    network: '10.127.0.0/24',
    parallel_threads: 20,
    batch_size: 50,
    timeout_seconds: 300,
    retry_attempts: 3,
    error_handling: 'continue'
  }
};
