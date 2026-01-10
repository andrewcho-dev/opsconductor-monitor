-- Migration: 026_seed_all_connector_mappings.sql
-- Description: Seed severity and category mappings for all connectors

-- ============================================================================
-- AXIS CAMERA MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('axis', 'video_loss', 'event_type', 'critical', true, 'Camera video loss'),
('axis', 'video_restored', 'event_type', 'clear', true, 'Camera video restored'),
('axis', 'motion', 'event_type', 'info', true, 'Motion detected'),
('axis', 'tampering', 'event_type', 'major', true, 'Camera tampering detected'),
('axis', 'storage_full', 'event_type', 'warning', true, 'Storage capacity full'),
('axis', 'disk_error', 'event_type', 'critical', true, 'Storage disk error'),
('axis', 'high_temperature', 'event_type', 'warning', true, 'Camera temperature high'),
('axis', 'device_offline', 'event_type', 'critical', true, 'Camera offline'),
('axis', 'device_online', 'event_type', 'clear', true, 'Camera online')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('axis', 'video_loss', 'event_type', 'video', true, 'Video events'),
('axis', 'motion', 'event_type', 'video', true, 'Motion events'),
('axis', 'tampering', 'event_type', 'security', true, 'Security events'),
('axis', 'storage_full', 'event_type', 'storage', true, 'Storage events'),
('axis', 'high_temperature', 'event_type', 'environment', true, 'Environment events'),
('axis', 'device_offline', 'event_type', 'video', true, 'Device events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- CRADLEPOINT MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('cradlepoint', 'signal_critical', 'alert_type', 'critical', true, 'Cellular signal critical'),
('cradlepoint', 'signal_low', 'alert_type', 'warning', true, 'Cellular signal low'),
('cradlepoint', 'signal_normal', 'alert_type', 'clear', true, 'Cellular signal normal'),
('cradlepoint', 'connection_lost', 'alert_type', 'critical', true, 'Cellular connection lost'),
('cradlepoint', 'connection_restored', 'alert_type', 'clear', true, 'Cellular connection restored'),
('cradlepoint', 'wan_failover', 'alert_type', 'warning', true, 'WAN failover active'),
('cradlepoint', 'wan_restored', 'alert_type', 'clear', true, 'WAN primary restored'),
('cradlepoint', 'device_offline', 'alert_type', 'critical', true, 'Router offline'),
('cradlepoint', 'device_online', 'alert_type', 'clear', true, 'Router online')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('cradlepoint', 'signal_critical', 'alert_type', 'wireless', true, 'Wireless events'),
('cradlepoint', 'connection_lost', 'alert_type', 'wireless', true, 'Wireless events'),
('cradlepoint', 'wan_failover', 'alert_type', 'network', true, 'Network events'),
('cradlepoint', 'device_offline', 'alert_type', 'network', true, 'Device events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- SIKLU RADIO MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('siklu', 'link_down', 'alert_type', 'critical', true, 'Radio link down'),
('siklu', 'link_up', 'alert_type', 'clear', true, 'Radio link up'),
('siklu', 'rsl_low', 'alert_type', 'warning', true, 'RSL below threshold'),
('siklu', 'rsl_critical', 'alert_type', 'critical', true, 'RSL critically low'),
('siklu', 'ethernet_down', 'alert_type', 'major', true, 'Ethernet port down'),
('siklu', 'ethernet_up', 'alert_type', 'clear', true, 'Ethernet port up'),
('siklu', 'high_temperature', 'alert_type', 'warning', true, 'Radio temperature high'),
('siklu', 'device_offline', 'alert_type', 'critical', true, 'Radio offline'),
('siklu', 'device_online', 'alert_type', 'clear', true, 'Radio online')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('siklu', 'link_down', 'alert_type', 'wireless', true, 'Wireless events'),
('siklu', 'rsl_low', 'alert_type', 'wireless', true, 'Signal events'),
('siklu', 'ethernet_down', 'alert_type', 'network', true, 'Network events'),
('siklu', 'high_temperature', 'alert_type', 'environment', true, 'Environment events'),
('siklu', 'device_offline', 'alert_type', 'wireless', true, 'Device events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- UBIQUITI MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('ubiquiti', 'device_offline', 'alert_type', 'critical', true, 'AP offline'),
('ubiquiti', 'device_online', 'alert_type', 'clear', true, 'AP online'),
('ubiquiti', 'high_cpu', 'alert_type', 'warning', true, 'CPU utilization high'),
('ubiquiti', 'interface_down', 'alert_type', 'major', true, 'Interface down'),
('ubiquiti', 'interface_up', 'alert_type', 'clear', true, 'Interface up'),
('ubiquiti', 'outage_started', 'alert_type', 'critical', true, 'Outage started'),
('ubiquiti', 'outage_ended', 'alert_type', 'clear', true, 'Outage ended')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('ubiquiti', 'device_offline', 'alert_type', 'wireless', true, 'AP events'),
('ubiquiti', 'high_cpu', 'alert_type', 'compute', true, 'Resource events'),
('ubiquiti', 'interface_down', 'alert_type', 'network', true, 'Interface events'),
('ubiquiti', 'outage_started', 'alert_type', 'network', true, 'Outage events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- CISCO ASA MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('cisco_asa', 'vpn_tunnel_down', 'event_type', 'critical', true, 'VPN tunnel down'),
('cisco_asa', 'vpn_tunnel_up', 'event_type', 'clear', true, 'VPN tunnel established'),
('cisco_asa', 'interface_down', 'event_type', 'critical', true, 'Interface down'),
('cisco_asa', 'interface_up', 'event_type', 'clear', true, 'Interface up'),
('cisco_asa', 'failover_active', 'event_type', 'warning', true, 'Failover to standby'),
('cisco_asa', 'threat_detected', 'event_type', 'major', true, 'Security threat detected'),
('cisco_asa', 'device_offline', 'event_type', 'critical', true, 'Firewall offline'),
('cisco_asa', 'device_online', 'event_type', 'clear', true, 'Firewall online')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('cisco_asa', 'vpn_tunnel_down', 'event_type', 'security', true, 'VPN events'),
('cisco_asa', 'interface_down', 'event_type', 'network', true, 'Interface events'),
('cisco_asa', 'failover_active', 'event_type', 'network', true, 'Failover events'),
('cisco_asa', 'threat_detected', 'event_type', 'security', true, 'Security events'),
('cisco_asa', 'device_offline', 'event_type', 'security', true, 'Device events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- EATON UPS MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('eaton', 'on_battery', 'alarm_type', 'critical', true, 'UPS on battery'),
('eaton', 'utility_restored', 'alarm_type', 'clear', true, 'Utility power restored'),
('eaton', 'low_battery', 'alarm_type', 'critical', true, 'Battery low'),
('eaton', 'battery_fault', 'alarm_type', 'critical', true, 'Battery fault detected'),
('eaton', 'overload', 'alarm_type', 'critical', true, 'UPS overload'),
('eaton', 'high_temperature', 'alarm_type', 'warning', true, 'UPS temperature high'),
('eaton', 'bypass_active', 'alarm_type', 'warning', true, 'UPS on bypass'),
('eaton', 'device_offline', 'alarm_type', 'critical', true, 'UPS offline'),
('eaton', 'device_online', 'alarm_type', 'clear', true, 'UPS online'),
('eaton', 'normal', 'alarm_type', 'clear', true, 'UPS status normal')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('eaton', 'on_battery', 'alarm_type', 'power', true, 'Power events'),
('eaton', 'low_battery', 'alarm_type', 'power', true, 'Battery events'),
('eaton', 'overload', 'alarm_type', 'power', true, 'Load events'),
('eaton', 'high_temperature', 'alarm_type', 'environment', true, 'Environment events'),
('eaton', 'bypass_active', 'alarm_type', 'power', true, 'Bypass events'),
('eaton', 'device_offline', 'alarm_type', 'power', true, 'Device events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- MILESTONE VMS MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('milestone', 'camera_offline', 'event_type', 'critical', true, 'Camera offline'),
('milestone', 'camera_online', 'event_type', 'clear', true, 'Camera online'),
('milestone', 'recording_stopped', 'event_type', 'critical', true, 'Recording stopped'),
('milestone', 'recording_started', 'event_type', 'clear', true, 'Recording started'),
('milestone', 'storage_warning', 'event_type', 'warning', true, 'Storage space low'),
('milestone', 'storage_critical', 'event_type', 'critical', true, 'Storage space critical'),
('milestone', 'server_down', 'event_type', 'critical', true, 'Server offline'),
('milestone', 'server_started', 'event_type', 'clear', true, 'Server started'),
('milestone', 'motion_started', 'event_type', 'info', true, 'Motion detected'),
('milestone', 'motion_stopped', 'event_type', 'clear', true, 'Motion stopped'),
('milestone', 'backup_failed', 'event_type', 'major', true, 'Backup failed'),
('milestone', 'database_error', 'event_type', 'critical', true, 'Database error')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('milestone', 'camera_offline', 'event_type', 'video', true, 'Camera events'),
('milestone', 'recording_stopped', 'event_type', 'video', true, 'Recording events'),
('milestone', 'storage_warning', 'event_type', 'storage', true, 'Storage events'),
('milestone', 'server_down', 'event_type', 'compute', true, 'Server events'),
('milestone', 'motion_started', 'event_type', 'video', true, 'Motion events'),
('milestone', 'backup_failed', 'event_type', 'storage', true, 'Backup events'),
('milestone', 'database_error', 'event_type', 'application', true, 'Database events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;

-- ============================================================================
-- SNMP TRAP GENERIC MAPPINGS
-- ============================================================================

INSERT INTO severity_mappings (connector_type, source_value, source_field, target_severity, enabled, description) VALUES
('snmp_trap', 'linkDown', 'trap_type', 'critical', true, 'Interface link down'),
('snmp_trap', 'linkUp', 'trap_type', 'clear', true, 'Interface link up'),
('snmp_trap', 'coldStart', 'trap_type', 'warning', true, 'Device cold start'),
('snmp_trap', 'warmStart', 'trap_type', 'info', true, 'Device warm start'),
('snmp_trap', 'authenticationFailure', 'trap_type', 'warning', true, 'SNMP authentication failure')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

INSERT INTO category_mappings (connector_type, source_value, source_field, target_category, enabled, description) VALUES
('snmp_trap', 'linkDown', 'trap_type', 'network', true, 'Interface events'),
('snmp_trap', 'linkUp', 'trap_type', 'network', true, 'Interface events'),
('snmp_trap', 'coldStart', 'trap_type', 'network', true, 'Device events'),
('snmp_trap', 'warmStart', 'trap_type', 'network', true, 'Device events'),
('snmp_trap', 'authenticationFailure', 'trap_type', 'security', true, 'Security events')
ON CONFLICT (connector_type, source_value, source_field) DO UPDATE SET
    target_category = EXCLUDED.target_category,
    description = EXCLUDED.description;
