// Multi-Platform Command Libraries
// Ubuntu Linux (Local OpsConductor Server) and Ciena SAOS Switch Commands

console.log('Command libraries loading...');

export const COMMAND_LIBRARIES = {
  'ubuntu-20.04': {
    name: "Ubuntu Linux 20.04 (Local)",
    category: "server",
    description: "Commands available on the local OpsConductor server",
    icon: "🐧",
    commands: {
      ping: {
        name: "ICMP Ping Discovery",
        description: "Test network connectivity using ICMP ping",
        category: "discovery",
        syntax: "ping -c {count} -W {timeout} -i {interval} {target}",
        parameters: {
          count: {
            type: "number",
            label: "Ping Count",
            default: 1,
            min: 1,
            max: 10,
            required: true,
            unit: "packets",
            validation: {
              pattern: /^[1-9]\d*$/,
              message: "Must be a positive integer between 1-10",
              warning: { min: 5, message: "High count may slow discovery" }
            },
            help: "Number of ping packets to send to each target"
          },
          timeout: {
            type: "number",
            label: "Timeout",
            default: 1,
            min: 0.1,
            max: 30,
            required: true,
            unit: "seconds",
            validation: {
              pattern: /^[0-9]+(\.[0-9]+)?$/,
              message: "Must be a number between 0.1-30 seconds",
              error: { max: 10, message: "Timeout >10s may cause delays" }
            },
            help: "Time to wait for each ping response"
          },
          interval: {
            type: "number",
            label: "Interval",
            default: 0.2,
            min: 0.1,
            max: 5,
            required: false,
            unit: "seconds",
            validation: {
              message: "Interval between pings (0.1-5 seconds)",
              info: "Smaller intervals = faster but more network load"
            },
            help: "Delay between successive ping packets"
          }
        },
        variables: {
          "{target}": {
            required: true,
            description: "IP address or hostname to ping",
            validation: {
              pattern: /^([a-zA-Z0-9.-]+|\d+\.\d+\.\d+\.\d+)$/,
              message: "Must be valid IP address or hostname"
            }
          }
        },
        success_criteria: {
          return_code: 0,
          output_contains: ["bytes from"],
          output_regex: "bytes from .*: icmp_seq=\\d+ ttl=\\d+ time=([0-9.]+)"
        },
        examples: [
          { command: "ping -c 1 -W 1 -i 0.2 192.168.1.1", description: "Basic ping test" },
          { command: "ping -c 3 -W 2 -i 0.5 10.0.0.1", description: "Extended ping test" }
        ]
      },

      traceroute: {
        name: "Network Path Tracing",
        description: "Trace network route to target",
        category: "discovery",
        syntax: "traceroute -n -w {timeout} -m {max_hops} {target}",
        parameters: {
          timeout: {
            type: "number",
            label: "Timeout",
            default: 3,
            min: 1,
            max: 30,
            required: true,
            unit: "seconds",
            validation: {
              message: "Timeout for each hop (1-30 seconds)"
            }
          },
          max_hops: {
            type: "number",
            label: "Max Hops",
            default: 30,
            min: 1,
            max: 64,
            required: true,
            validation: {
              message: "Maximum number of hops to trace (1-64)"
            }
          }
        },
        variables: {
          "{target}": {
            required: true,
            description: "Destination IP or hostname"
          }
        }
      },

      nmap: {
        name: "Network Scanner",
        description: "Advanced network scanning and port discovery",
        category: "discovery",
        syntax: "nmap -{scan_type} -p {ports} -T{timing} {target}",
        parameters: {
          scan_type: {
            type: "select",
            label: "Scan Type",
            default: "sP",
            required: true,
            options: [
              { value: "sP", label: "Ping Scan (Host Discovery)" },
              { value: "sS", label: "SYN Scan (Stealth Port Scan)" },
              { value: "sT", label: "TCP Connect Scan" },
              { value: "sU", label: "UDP Scan" },
              { value: "sV", label: "Version Detection" }
            ],
            validation: {
              message: "Choose appropriate scan type for your needs"
            }
          },
          ports: {
            type: "text",
            label: "Port Range",
            default: "22,80,443,161,162",
            required: false,
            validation: {
              pattern: /^(\d+(-\d+)?)(,\d+(-\d+)?)*$/,
              message: "Format: 80,443,1000-2000"
            },
            help: "Comma-separated ports or ranges (e.g., 22,80,443,1000-2000)"
          },
          timing: {
            type: "select",
            label: "Timing Template",
            default: "3",
            required: true,
            options: [
              { value: "0", label: "T0 - Paranoid (very slow)" },
              { value: "1", label: "T1 - Sneaky (slow)" },
              { value: "2", label: "T2 - Polite (slower)" },
              { value: "3", label: "T3 - Normal (default)" },
              { value: "4", label: "T4 - Fast (aggressive)" },
              { value: "5", label: "T5 - Insane (very aggressive)" }
            ]
          }
        }
      },

      snmpwalk: {
        name: "SNMP Walk",
        description: "Walk SNMP tree for device information",
        category: "inventory",
        syntax: "snmpwalk -v{version} -c {community} {target}:{port} {oid}",
        parameters: {
          version: {
            type: "select",
            label: "SNMP Version",
            default: "2c",
            required: true,
            options: [
              { value: "1", label: "SNMPv1" },
              { value: "2c", label: "SNMPv2c" },
              { value: "3", label: "SNMPv3" }
            ]
          },
          community: {
            type: "text",
            label: "Community String",
            default: "public",
            required: true,
            validation: {
              pattern: /^[a-zA-Z0-9_-]+$/,
              message: "Alphanumeric characters, hyphens, underscores only"
            }
          },
          port: {
            type: "number",
            label: "SNMP Port",
            default: 161,
            min: 1,
            max: 65535,
            required: true
          },
          oid: {
            type: "text",
            label: "OID",
            default: "1.3.6.1.2.1.1",
            required: false,
            validation: {
              pattern: /^(\d+\.)*\d+$/,
              message: "Must be valid OID format (e.g., 1.3.6.1.2.1.1)"
            }
          }
        }
      },

      curl: {
        name: "HTTP Request",
        description: "Make HTTP requests to web services",
        category: "web",
        syntax: "curl -{method} -s -w '{format}' --connect-timeout {timeout} {url}",
        parameters: {
          method: {
            type: "select",
            label: "HTTP Method",
            default: "GET",
            required: true,
            options: [
              { value: "GET", label: "GET" },
              { value: "POST", label: "POST" },
              { value: "PUT", label: "PUT" },
              { value: "DELETE", label: "DELETE" },
              { value: "HEAD", label: "HEAD" }
            ]
          },
          timeout: {
            type: "number",
            label: "Connect Timeout",
            default: 10,
            min: 1,
            max: 300,
            required: true,
            unit: "seconds"
          },
          format: {
            type: "select",
            label: "Output Format",
            default: "%{http_code}",
            required: true,
            options: [
              { value: "%{http_code}", label: "HTTP Status Code" },
              { value: "%{time_total}", label: "Total Time" },
              { value: "%{size_download}", label: "Response Size" },
              { value: "HTTP Code: %{http_code}, Time: %{time_total}s", label: "Detailed" }
            ]
          }
        },
        variables: {
          "{url}": {
            required: true,
            description: "Target URL",
            validation: {
              pattern: /^https?:\/\/.+/,
              message: "Must be valid HTTP/HTTPS URL"
            }
          }
        }
      },

      // NETWORK SCANNING COMMANDS
      nmap: {
        name: "Network Port Scanner",
        description: "Scan for open ports and services on target hosts",
        category: "scanning",
        syntax: "nmap -{scan_type} -p {port_range} -{timing} {target}",
        parameters: {
          scan_type: {
            type: "select",
            label: "Scan Type",
            default: "sS",
            required: true,
            options: [
              { value: "sS", label: "SYN Scan (Stealth)" },
              { value: "sT", label: "TCP Connect Scan" },
              { value: "sU", label: "UDP Scan" },
              { value: "sP", label: "Ping Scan" },
              { value: "sV", label: "Version Detection" }
            ]
          },
          port_range: {
            type: "text",
            label: "Port Range",
            default: "1-1000",
            required: true,
            placeholder: "e.g., 22,80,443 or 1-65535"
          },
          timing: {
            type: "select",
            label: "Timing Template",
            default: "T4",
            required: true,
            options: [
              { value: "T3", label: "Normal" },
              { value: "T4", label: "Fast" },
              { value: "T5", label: "Aggressive" }
            ]
          }
        },
        variables: {
          "{target}": {
            required: true,
            description: "IP address, hostname, or CIDR range"
          }
        },
        warnings: ["Port scanning may be detected by security systems"],
        examples: [
          { command: "nmap -sS -p 22,80,443 -T4 192.168.1.100", description: "Quick common port scan" }
        ]
      },

      netcat: {
        name: "Netcat Port Test",
        description: "Test TCP/UDP port connectivity using netcat",
        category: "scanning",
        syntax: "nc -{protocol} -v -z -w {timeout} {target} {port}",
        parameters: {
          protocol: {
            type: "select",
            label: "Protocol",
            default: "",
            required: true,
            options: [
              { value: "", label: "TCP" },
              { value: "u", label: "UDP" }
            ]
          },
          timeout: {
            type: "number",
            label: "Timeout",
            default: 3,
            min: 1,
            max: 30,
            required: true,
            unit: "seconds"
          }
        },
        variables: {
          "{target}": { required: true, description: "Target IP address or hostname" },
          "{port}": { required: true, description: "Port number to test" }
        },
        examples: [
          { command: "nc -v -z -w 3 192.168.1.100 80", description: "Test HTTP port" }
        ]
      },

      // SYSTEM INFORMATION COMMANDS
      hostname: {
        name: "Hostname Information",
        description: "Get system hostname and domain information",
        category: "system",
        syntax: "hostname -{detail_level}",
        parameters: {
          detail_level: {
            type: "select",
            label: "Detail Level",
            default: "f",
            required: true,
            options: [
              { value: "s", label: "Short hostname" },
              { value: "f", label: "Fully qualified domain name" },
              { value: "i", label: "IP address" },
              { value: "a", label: "All information" }
            ]
          }
        }
      },

      uname: {
        name: "System Information",
        description: "Get detailed system information",
        category: "system",
        syntax: "uname -{options}",
        parameters: {
          options: {
            type: "select",
            label: "Information Type",
            default: "a",
            required: true,
            options: [
              { value: "s", label: "Kernel name" },
              { value: "r", label: "Kernel release" },
              { value: "v", label: "Kernel version" },
              { value: "m", label: "Machine hardware" },
              { value: "a", label: "All information" }
            ]
          }
        }
      },

      df: {
        name: "Disk Space Usage",
        description: "Check disk space usage and availability",
        category: "system",
        syntax: "df -{format} {path}",
        parameters: {
          format: {
            type: "select",
            label: "Output Format",
            default: "h",
            required: true,
            options: [
              { value: "h", label: "Human readable" },
              { value: "k", label: "Kilobytes" },
              { value: "m", label: "Megabytes" },
              { value: "g", label: "Gigabytes" }
            ]
          }
        },
        variables: {
          "{path}": {
            required: false,
            description: "Specific path to check (default: all filesystems)",
            default: ""
          }
        }
      },

      free: {
        name: "Memory Usage",
        description: "Check system memory usage and availability",
        category: "system",
        syntax: "free -{format}",
        parameters: {
          format: {
            type: "select",
            label: "Display Format",
            default: "h",
            required: true,
            options: [
              { value: "b", label: "Bytes" },
              { value: "k", label: "Kilobytes" },
              { value: "m", label: "Megabytes" },
              { value: "g", label: "Gigabytes" },
              { value: "h", label: "Human readable" }
            ]
          }
        }
      },

      // NETWORK CONFIGURATION COMMANDS
      ip_addr: {
        name: "IP Address Information",
        description: "Show network interface IP addresses",
        category: "networking",
        syntax: "ip addr show {interface}",
        parameters: {},
        variables: {
          "{interface}": {
            required: false,
            description: "Specific interface (default: all interfaces)",
            default: ""
          }
        }
      },

      ip_route: {
        name: "Routing Table",
        description: "Display network routing table",
        category: "networking",
        syntax: "ip route show"
      },

      ss: {
        name: "Socket Statistics",
        description: "Display network socket information",
        category: "networking",
        syntax: "ss -{options}",
        parameters: {
          options: {
            type: "text",
            label: "SS Options",
            default: "tuln",
            required: true,
            placeholder: "e.g., tuln, -a, -p"
          }
        }
      },

      // PROCESS MANAGEMENT COMMANDS
      ps: {
        name: "Process List",
        description: "Display running processes",
        category: "processes",
        syntax: "ps -{format} {sort}",
        parameters: {
          format: {
            type: "select",
            label: "Output Format",
            default: "aux",
            required: true,
            options: [
              { value: "aux", label: "All processes (BSD style)" },
              { value: "ef", label: "All processes (System V style)" },
              { value: "u", label: "User processes" }
            ]
          },
          sort: {
            type: "select",
            label: "Sort By",
            default: "",
            required: false,
            options: [
              { value: "", label: "Default" },
              { value: "--sort=-%cpu", label: "CPU usage (descending)" },
              { value: "--sort=-%mem", label: "Memory usage (descending)" }
            ]
          }
        }
      },

      top: {
        name: "Process Monitor",
        description: "Display and update running processes",
        category: "processes",
        syntax: "top -b -n {iterations}",
        parameters: {
          iterations: {
            type: "number",
            label: "Iterations",
            default: 1,
            min: 1,
            max: 10,
            required: true
          }
        }
      },

      // SECURITY COMMANDS
      iptables: {
        name: "Firewall Rules",
        description: "Display iptables firewall rules",
        category: "security",
        syntax: "iptables -{chain} -L -{format}",
        parameters: {
          chain: {
            type: "select",
            label: "Chain",
            default: "",
            required: false,
            options: [
              { value: "", label: "All chains" },
              { value: "INPUT", label: "INPUT chain" },
              { value: "OUTPUT", label: "OUTPUT chain" },
              { value: "FORWARD", label: "FORWARD chain" }
            ]
          },
          format: {
            type: "select",
            label: "Output Format",
            default: "n",
            required: true,
            options: [
              { value: "n", label: "Numeric (no DNS lookup)" },
              { value: "v", label: "Verbose" },
              { value: "nv", label: "Numeric and verbose" }
            ]
          }
        },
        warnings: ["Requires root privileges to modify firewall rules"]
      },

      ufw: {
        name: "UFW Firewall Status",
        description: "Check Uncomplicated Firewall status and rules",
        category: "security",
        syntax: "ufw {action}",
        parameters: {
          action: {
            type: "select",
            label: "Action",
            default: "status",
            required: true,
            options: [
              { value: "status", label: "Show status" },
              { value: "status verbose", label: "Show verbose status" },
              { value: "status numbered", label: "Show numbered rules" }
            ]
          }
        }
      },

      // MONITORING COMMANDS
      iostat: {
        name: "I/O Statistics",
        description: "Monitor disk I/O and CPU statistics",
        category: "monitoring",
        syntax: "iostat -{options} {interval} {count}",
        parameters: {
          options: {
            type: "select",
            label: "Iostat Options",
            default: "x",
            required: true,
            options: [
              { value: "x", label: "Extended" },
              { value: "d", label: "Device stats" },
              { value: "m", label: "Metrics" }
            ]
          },
          interval: {
            type: "number",
            label: "Interval",
            default: 1,
            min: 1,
            max: 60,
            required: true,
            unit: "seconds"
          },
          count: {
            type: "number",
            label: "Count",
            default: 1,
            min: 1,
            max: 10,
            required: true
          }
        }
      },

      vmstat: {
        name: "Virtual Memory Statistics",
        description: "Monitor virtual memory, processes, and CPU activity",
        category: "monitoring",
        syntax: "vmstat -{options} {interval} {count}",
        parameters: {
          options: {
            type: "select",
            label: "Vmstat Options",
            default: "a",
            required: true,
            options: [
              { value: "a", label: "Active memory" },
              { value: "s", label: "Stats summary" },
              { value: "d", label: "Disk stats" }
            ]
          },
          interval: {
            type: "number",
            label: "Interval",
            default: 1,
            min: 1,
            max: 60,
            required: true,
            unit: "seconds"
          },
          count: {
            type: "number",
            label: "Count",
            default: 1,
            min: 1,
            max: 10,
            required: true
          }
        }
      },

      netstat: {
        name: "Network Statistics",
        description: "Display network connections and statistics",
        category: "monitoring",
        syntax: "netstat -{options}",
        parameters: {
          options: {
            type: "select",
            label: "Netstat Options",
            default: "tuln",
            required: true,
            options: [
              { value: "tuln", label: "TCP/UDP listening ports" },
              { value: "an", label: "All connections" },
              { value: "i", label: "Interface statistics" }
            ]
          }
        }
      },

      // FILE SYSTEM COMMANDS
      lsblk: {
        name: "Block Device List",
        description: "List block devices and disk partitions",
        category: "storage",
        syntax: "lsblk -{options}",
        parameters: {
          options: {
            type: "select",
            label: "Lsblk Options",
            default: "f",
            required: true,
            options: [
              { value: "f", label: "Filesystem info" },
              { value: "m", label: "Major-minor numbers" },
              { value: "d", label: "Disk devices only" }
            ]
          }
        }
      },

      mount: {
        name: "Mounted Filesystems",
        description: "Display currently mounted filesystems",
        category: "storage",
        syntax: "mount -{options}",
        parameters: {
          options: {
            type: "select",
            label: "Display Options",
            default: "",
            required: false,
            options: [
              { value: "", label: "Standard format" },
              { value: "l", label: "Verbose labels" }
            ]
          }
        }
      },

      // SERVICE MANAGEMENT COMMANDS
      systemctl: {
        name: "Service Control",
        description: "Control and monitor systemd services",
        category: "services",
        syntax: "systemctl {action} {service}",
        parameters: {
          action: {
            type: "select",
            label: "Action",
            default: "status",
            required: true,
            options: [
              { value: "status", label: "Show status" },
              { value: "is-active", label: "Check if active" },
              { value: "is-enabled", label: "Check if enabled" },
              { value: "list-units", label: "List all units" },
              { value: "list-failed", label: "List failed units" }
            ]
          }
        },
        variables: {
          "{service}": {
            required: false,
            description: "Service name (default: all services)",
            default: ""
          }
        },
        warnings: ["Service management requires appropriate privileges"]
      },

      // LOG COMMANDS
      journalctl: {
        name: "System Journal Logs",
        description: "Query systemd journal logs",
        category: "logging",
        syntax: "journalctl -{options} -n {lines}",
        parameters: {
          options: {
            type: "text",
            label: "Journal Options",
            default: "xe",
            required: true,
            placeholder: "e.g., xe, unginx, f"
          },
          lines: {
            type: "number",
            label: "Number of Lines",
            default: 50,
            min: 10,
            max: 500,
            required: true
          }
        }
      },

      // PACKAGE MANAGEMENT COMMANDS
      apt: {
        name: "Package Management",
        description: "Manage Debian/Ubuntu packages",
        category: "packages",
        syntax: "apt {action} {package}",
        parameters: {
          action: {
            type: "select",
            label: "Action",
            default: "list",
            required: true,
            options: [
              { value: "list", label: "List packages" },
              { value: "search", label: "Search packages" },
              { value: "show", label: "Show package info" },
              { value: "policy", label: "Show package policy" }
            ]
          }
        },
        variables: {
          "{package}": {
            required: false,
            description: "Package name or search pattern",
            default: ""
          }
        },
        warnings: ["Only read-only operations are supported for safety"]
      },

      // TIME AND DATE COMMANDS
      timedatectl: {
        name: "Time and Date Settings",
        description: "Control system time and date settings",
        category: "system",
        syntax: "timedatectl {action}",
        parameters: {
          action: {
            type: "select",
            label: "Action",
            default: "status",
            required: true,
            options: [
              { value: "status", label: "Show time status" },
              { value: "list-timezones", label: "List timezones" },
              { value: "timesync-status", label: "Show time sync status" }
            ]
          }
        }
      }
    }
  },

  'ciena-saos-8.2': {
    name: "Ciena SAOS 8.2",
    category: "network-switch",
    description: "Ciena Service Access Operating System commands",
    icon: "🌐",
    commands: {
      'show interface': {
        name: "Interface Status",
        description: "Display interface configuration and operational status",
        category: "interface",
        syntax: "show interface {interface-name}",
        parameters: {
          'interface-name': {
            type: "select",
            label: "Interface",
            default: "all",
            required: false,
            options: [
              { value: "all", label: "All Interfaces" },
              { value: "1/1", label: "Ethernet 1/1" },
              { value: "1/2", label: "Ethernet 1/2" },
              { value: "1/3", label: "Ethernet 1/3" },
              { value: "1/4", label: "Ethernet 1/4" },
              { value: "2/1", label: "Ethernet 2/1" },
              { value: "2/2", label: "Ethernet 2/2" },
              { value: "2/3", label: "Ethernet 2/3" },
              { value: "2/4", label: "Ethernet 2/4" }
            ],
            validation: {
              pattern: /^(all|[1-2]\/[1-24])$/,
              message: "Format: slot/port (1/1-2/24) or 'all'"
            },
            help: "Ciena SAOS interface format: slot/port where slot is 1-2, port is 1-24"
          }
        },
        examples: [
          { command: "show interface all", description: "Show all interfaces" },
          { command: "show interface 1/1", description: "Show specific interface" }
        ]
      },

      'show configuration': {
        name: "System Configuration",
        description: "Display system configuration information",
        category: "system",
        syntax: "show configuration {section}",
        parameters: {
          section: {
            type: "select",
            label: "Configuration Section",
            default: "system",
            required: false,
            options: [
              { value: "system", label: "System Configuration" },
              { value: "interface", label: "Interface Configuration" },
              { value: "lldp", label: "LLDP Configuration" },
              { value: "ethernet", label: "Ethernet Configuration" },
              { value: "sonet", label: "SONET Configuration" }
            ]
          }
        }
      },

      'show lldp neighbors': {
        name: "LLDP Neighbor Discovery",
        description: "Display LLDP neighbor information",
        category: "discovery",
        syntax: "show lldp neighbors {detail}",
        parameters: {
          detail: {
            type: "checkbox",
            label: "Show Detailed Information",
            default: false
          }
        },
        examples: [
          { command: "show lldp neighbors", description: "Basic neighbor list" },
          { command: "show lldp neighbors detail", description: "Detailed neighbor info" }
        ]
      },

      'show optics': {
        name: "Optical Interface Status",
        description: "Display optical power levels and laser status",
        category: "optical",
        syntax: "show optics {interface-name}",
        parameters: {
          'interface-name': {
            type: "select",
            label: "Interface",
            default: "all",
            required: false,
            options: [
              { value: "all", label: "All Interfaces" },
              { value: "1/1", label: "Ethernet 1/1" },
              { value: "1/2", label: "Ethernet 1/2" },
              { value: "2/1", label: "Ethernet 2/1" },
              { value: "2/2", label: "Ethernet 2/2" }
            ],
            validation: {
              pattern: /^(all|[1-2]\/[1-24])$/,
              message: "Format: slot/port or 'all'"
            }
          }
        }
      },

      'show alarms': {
        name: "System Alarms",
        description: "Display active and cleared system alarms",
        category: "monitoring",
        syntax: "show alarms {severity}",
        parameters: {
          severity: {
            type: "select",
            label: "Alarm Severity",
            default: "all",
            required: false,
            options: [
              { value: "all", label: "All Alarms" },
              { value: "critical", label: "Critical Only" },
              { value: "major", label: "Major and Above" },
              { value: "minor", label: "Minor and Above" }
            ]
          }
        }
      },

      'configure terminal': {
        name: "Configuration Mode",
        description: "Enter global configuration mode",
        category: "configuration",
        syntax: "configure terminal",
        parameters: {},
        requires_privileged: true,
        warnings: [
          "This will enter configuration mode",
          "Configuration changes can affect network service",
          "Use with caution on production systems"
        ]
      },

      'interface ethernet': {
        name: "Configure Ethernet Interface",
        description: "Enter interface configuration mode for Ethernet ports",
        category: "configuration",
        syntax: "interface ethernet {slot/port}",
        parameters: {
          'slot/port': {
            type: "text",
            label: "Interface",
            required: true,
            validation: {
              pattern: /^[1-2]\/[1-24]$/,
              message: "Must be in format slot/port (e.g., 1/1, 2/24)"
            },
            help: "Format: slot/port where slot is 1-2, port is 1-24"
          }
        },
        requires_privileged: true
      },

      'show version': {
        name: "Software Version",
        description: "Display SAOS software version and hardware information",
        category: "system",
        syntax: "show version",
        parameters: {}
      },

      'show hardware': {
        name: "Hardware Information",
        description: "Display hardware details and inventory",
        category: "system",
        syntax: "show hardware",
        parameters: {}
      }
    }
  }
};

export const getCommandLibrary = (platform) => {
  return COMMAND_LIBRARIES[platform] || null;
};

export const getAvailablePlatforms = () => {
  return Object.keys(COMMAND_LIBRARIES).map(key => ({
    id: key,
    ...COMMAND_LIBRARIES[key]
  }));
};

export const getCommand = (platform, commandId) => {
  const library = getCommandLibrary(platform);
  return library?.commands?.[commandId] || null;
};
