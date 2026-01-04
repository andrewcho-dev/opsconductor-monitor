-- Seed Ciena SAOS6 MIB mappings from existing ciena_snmp_service.py

-- Get the Ciena profile ID
DO $$
DECLARE
    v_profile_id INTEGER;
    v_group_id INTEGER;
    v_mapping_id INTEGER;
BEGIN
    SELECT id INTO v_profile_id FROM snmp_profiles WHERE name = 'ciena_saos6';
    
    -- ============================================================================
    -- XCVR (Transceiver/SFP) Group - WWP-LEOS-PORT-XCVR-MIB
    -- ============================================================================
    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
    VALUES (v_profile_id, 'xcvr', 'SFP/XFP Transceiver DOM data', '1.3.6.1.4.1.6141.2.60.4', 'WWP-LEOS-PORT-XCVR-MIB', true)
    ON CONFLICT (profile_id, name) DO UPDATE SET description = EXCLUDED.description
    RETURNING id INTO v_group_id;
    
    -- XCVR OID mappings
    INSERT INTO snmp_oid_mappings (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index) VALUES
    (v_group_id, 'id', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.1', 'Port/Transceiver ID', 'wwpLeosPortXcvrId', 'integer', NULL, NULL, true),
    (v_group_id, 'oper_state', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.2', 'Operational state', 'wwpLeosPortXcvrOperState', 'integer', NULL, NULL, false),
    (v_group_id, 'identifier_type', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.3', 'SFP/XFP type', 'wwpLeosPortXcvrIdentiferType', 'integer', NULL, NULL, false),
    (v_group_id, 'vendor_name', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.7', 'Vendor name', 'wwpLeosPortXcvrVendorName', 'string', NULL, NULL, false),
    (v_group_id, 'vendor_pn', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.9', 'Vendor part number', 'wwpLeosPortXcvrVendorPN', 'string', NULL, NULL, false),
    (v_group_id, 'serial_num', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.11', 'Serial number', 'wwpLeosPortXcvrSerialNum', 'string', NULL, NULL, false),
    (v_group_id, 'wavelength', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.15', 'Wavelength', 'wwpLeosPortXcvrWaveLength', 'integer', NULL, 'nm', false),
    (v_group_id, 'temperature', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.16', 'Temperature', 'wwpLeosPortXcvrTemperature', 'integer', NULL, 'C', false),
    (v_group_id, 'rx_power_dbm', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.105', 'RX Power (dBm)', 'wwpLeosPortXcvrRxDbmPower', 'integer', 'divide:10000', 'dBm', false),
    (v_group_id, 'tx_power_dbm', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.106', 'TX Power (dBm)', 'wwpLeosPortXcvrTxDbmPower', 'integer', 'divide:10000', 'dBm', false),
    (v_group_id, 'los_state', '1.3.6.1.4.1.6141.2.60.4.1.1.1.1.28', 'Loss of Signal state', 'wwpLeosPortXcvrLosState', 'integer', NULL, NULL, false)
    ON CONFLICT (group_id, name) DO UPDATE SET oid = EXCLUDED.oid;
    
    -- XCVR identifier type enum
    SELECT id INTO v_mapping_id FROM snmp_oid_mappings WHERE group_id = v_group_id AND name = 'identifier_type';
    INSERT INTO snmp_enum_mappings (mapping_id, int_value, string_value) VALUES
    (v_mapping_id, 1, 'Unknown'), (v_mapping_id, 2, 'GBIC'), (v_mapping_id, 3, 'Soldered'),
    (v_mapping_id, 4, 'SFP'), (v_mapping_id, 5, 'Reserved'), (v_mapping_id, 6, 'Vendor'),
    (v_mapping_id, 7, 'XBI'), (v_mapping_id, 8, 'XENPAK'), (v_mapping_id, 9, 'XFP'),
    (v_mapping_id, 10, 'XFF'), (v_mapping_id, 11, 'XFP-E'), (v_mapping_id, 12, 'XPAK'), (v_mapping_id, 13, 'X2')
    ON CONFLICT (mapping_id, int_value) DO UPDATE SET string_value = EXCLUDED.string_value;

    -- ============================================================================
    -- Port Stats Group - WWP-LEOS-PORT-STATS-MIB
    -- ============================================================================
    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
    VALUES (v_profile_id, 'port_stats', 'Port traffic statistics', '1.3.6.1.4.1.6141.2.60.3', 'WWP-LEOS-PORT-STATS-MIB', true)
    ON CONFLICT (profile_id, name) DO UPDATE SET description = EXCLUDED.description
    RETURNING id INTO v_group_id;
    
    INSERT INTO snmp_oid_mappings (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index) VALUES
    (v_group_id, 'rx_bytes', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.2', 'RX Bytes', 'wwpLeosPortStatsRxBytes', 'counter', NULL, 'bytes', false),
    (v_group_id, 'rx_pkts', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.3', 'RX Packets', 'wwpLeosPortStatsRxPkts', 'counter', NULL, 'packets', false),
    (v_group_id, 'rx_crc_errors', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.4', 'RX CRC Errors', 'wwpLeosPortStatsRxCrcErrorPkts', 'counter', NULL, 'packets', false),
    (v_group_id, 'tx_bytes', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.16', 'TX Bytes', 'wwpLeosPortStatsTxBytes', 'counter', NULL, 'bytes', false),
    (v_group_id, 'tx_pkts', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.18', 'TX Packets', 'wwpLeosPortStatsTxPkts', 'counter', NULL, 'packets', false),
    (v_group_id, 'rx_discard', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.62', 'RX Discards', 'wwpLeosPortStatsRxDiscardPkts', 'counter', NULL, 'packets', false),
    (v_group_id, 'link_flap_count', '1.3.6.1.4.1.6141.2.60.3.1.1.2.1.58', 'Link Flap Count', 'wwpLeosPortStatsPortLinkFlap', 'counter', NULL, 'count', false)
    ON CONFLICT (group_id, name) DO UPDATE SET oid = EXCLUDED.oid;

    -- ============================================================================
    -- RAPS (G.8032 Ring) Group - WWP-LEOS-RAPS-MIB
    -- ============================================================================
    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
    VALUES (v_profile_id, 'raps', 'G.8032 Ring Protection (RAPS)', '1.3.6.1.4.1.6141.2.60.47', 'WWP-LEOS-RAPS-MIB', false)
    ON CONFLICT (profile_id, name) DO UPDATE SET description = EXCLUDED.description
    RETURNING id INTO v_group_id;
    
    INSERT INTO snmp_oid_mappings (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index) VALUES
    (v_group_id, 'global_state', '1.3.6.1.4.1.6141.2.60.47.1.1.1.1.0', 'RAPS Global State', 'wwpLeosRapsState', 'integer', NULL, NULL, false),
    (v_group_id, 'node_id', '1.3.6.1.4.1.6141.2.60.47.1.1.1.2.0', 'RAPS Node ID', 'wwpLeosRapsNodeId', 'string', NULL, NULL, false),
    (v_group_id, 'num_rings', '1.3.6.1.4.1.6141.2.60.47.1.1.1.4.0', 'Number of Rings', 'wwpLeosRapsNumberOfRings', 'integer', NULL, NULL, false)
    ON CONFLICT (group_id, name) DO UPDATE SET oid = EXCLUDED.oid;

    -- Virtual Ring Table
    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
    VALUES (v_profile_id, 'virtual_ring', 'G.8032 Virtual Ring entries', '1.3.6.1.4.1.6141.2.60.47.1.3.1', 'WWP-LEOS-RAPS-MIB', true)
    ON CONFLICT (profile_id, name) DO UPDATE SET description = EXCLUDED.description
    RETURNING id INTO v_group_id;
    
    INSERT INTO snmp_oid_mappings (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index) VALUES
    (v_group_id, 'name', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.2', 'Ring Name', 'wwpLeosRapsVirtualRingName', 'string', NULL, NULL, false),
    (v_group_id, 'vid', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.3', 'VLAN ID', 'wwpLeosRapsVirtualRingVid', 'integer', NULL, NULL, false),
    (v_group_id, 'state', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.7', 'Ring State', 'wwpLeosRapsVirtualRingState', 'integer', NULL, NULL, false),
    (v_group_id, 'status', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.8', 'Ring Status', 'wwpLeosRapsVirtualRingStatus', 'integer', NULL, NULL, false),
    (v_group_id, 'alarm', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.9', 'Ring Alarm', 'wwpLeosRapsVirtualRingAlarm', 'integer', NULL, NULL, false),
    (v_group_id, 'switchovers', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.10', 'Number of Switchovers', 'wwpLeosRapsVirtualRingNumOfSwitchOvers', 'counter', NULL, NULL, false),
    (v_group_id, 'west_port_state', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.14', 'West Port State', 'wwpLeosRapsVirtualRingWestPortState', 'integer', NULL, NULL, false),
    (v_group_id, 'east_port_state', '1.3.6.1.4.1.6141.2.60.47.1.3.1.1.25', 'East Port State', 'wwpLeosRapsVirtualRingEastPortState', 'integer', NULL, NULL, false)
    ON CONFLICT (group_id, name) DO UPDATE SET oid = EXCLUDED.oid;
    
    -- RAPS state enum
    SELECT id INTO v_mapping_id FROM snmp_oid_mappings WHERE group_id = v_group_id AND name = 'state';
    INSERT INTO snmp_enum_mappings (mapping_id, int_value, string_value, severity) VALUES
    (v_mapping_id, 1, 'adminDisabled', NULL), (v_mapping_id, 2, 'ok', NULL),
    (v_mapping_id, 3, 'protecting', 'warning'), (v_mapping_id, 4, 'recovering', 'info'),
    (v_mapping_id, 5, 'init', NULL), (v_mapping_id, 6, 'none', NULL)
    ON CONFLICT (mapping_id, int_value) DO UPDATE SET string_value = EXCLUDED.string_value;

    -- ============================================================================
    -- System Group - Standard MIB-II
    -- ============================================================================
    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
    VALUES (v_profile_id, 'system', 'Standard MIB-II System info', '1.3.6.1.2.1.1', 'SNMPv2-MIB', false)
    ON CONFLICT (profile_id, name) DO UPDATE SET description = EXCLUDED.description
    RETURNING id INTO v_group_id;
    
    INSERT INTO snmp_oid_mappings (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index) VALUES
    (v_group_id, 'descr', '1.3.6.1.2.1.1.1.0', 'System Description', 'sysDescr', 'string', NULL, NULL, false),
    (v_group_id, 'uptime', '1.3.6.1.2.1.1.3.0', 'System Uptime', 'sysUpTime', 'timeticks', NULL, 'ticks', false),
    (v_group_id, 'contact', '1.3.6.1.2.1.1.4.0', 'System Contact', 'sysContact', 'string', NULL, NULL, false),
    (v_group_id, 'name', '1.3.6.1.2.1.1.5.0', 'System Name', 'sysName', 'string', NULL, NULL, false),
    (v_group_id, 'location', '1.3.6.1.2.1.1.6.0', 'System Location', 'sysLocation', 'string', NULL, NULL, false)
    ON CONFLICT (group_id, name) DO UPDATE SET oid = EXCLUDED.oid;

    -- ============================================================================
    -- Alarms Group - CIENA-CES-ALARM-MIB
    -- ============================================================================
    INSERT INTO snmp_oid_groups (profile_id, name, description, base_oid, mib_name, is_table)
    VALUES (v_profile_id, 'alarms', 'Active Alarms', '1.3.6.1.4.1.1271.2.1.24', 'CIENA-CES-ALARM-MIB', true)
    ON CONFLICT (profile_id, name) DO UPDATE SET description = EXCLUDED.description
    RETURNING id INTO v_group_id;
    
    INSERT INTO snmp_oid_mappings (group_id, name, oid, description, mib_object_name, data_type, transform, unit, is_index) VALUES
    (v_group_id, 'severity', '1.3.6.1.4.1.1271.2.1.24.1.3.1.1.1', 'Alarm Severity', 'cienaCesAlarmActiveSeverity', 'integer', NULL, NULL, false),
    (v_group_id, 'object_class', '1.3.6.1.4.1.1271.2.1.24.1.3.1.1.3', 'Object Class', 'cienaCesAlarmActiveManagedObjectClass', 'integer', NULL, NULL, false),
    (v_group_id, 'object_instance', '1.3.6.1.4.1.1271.2.1.24.1.3.1.1.5', 'Object Instance', 'cienaCesAlarmActiveManagedObjectInstance', 'string', NULL, NULL, false),
    (v_group_id, 'description', '1.3.6.1.4.1.1271.2.1.24.1.3.1.1.7', 'Alarm Description', 'cienaCesAlarmActiveDescription', 'string', NULL, NULL, false),
    (v_group_id, 'timestamp', '1.3.6.1.4.1.1271.2.1.24.1.3.1.1.8', 'Alarm Timestamp', 'cienaCesAlarmActiveTimeStamp', 'string', NULL, NULL, false)
    ON CONFLICT (group_id, name) DO UPDATE SET oid = EXCLUDED.oid;
    
    -- Alarm severity enum
    SELECT id INTO v_mapping_id FROM snmp_oid_mappings WHERE group_id = v_group_id AND name = 'severity';
    INSERT INTO snmp_enum_mappings (mapping_id, int_value, string_value, severity) VALUES
    (v_mapping_id, 1, 'cleared', NULL), (v_mapping_id, 2, 'indeterminate', 'info'),
    (v_mapping_id, 3, 'critical', 'critical'), (v_mapping_id, 4, 'major', 'major'),
    (v_mapping_id, 5, 'minor', 'minor'), (v_mapping_id, 6, 'warning', 'warning')
    ON CONFLICT (mapping_id, int_value) DO UPDATE SET string_value = EXCLUDED.string_value;

    -- ============================================================================
    -- Create Poll Types
    -- ============================================================================
    INSERT INTO snmp_poll_types (name, display_name, description, profile_id, target_table)
    VALUES 
    ('ciena_optical', 'Ciena Optical Power', 'Poll SFP/XFP optical power levels (TX/RX dBm)', v_profile_id, 'optical_metrics'),
    ('ciena_traffic', 'Ciena Port Traffic', 'Poll port traffic statistics (bytes, packets, errors)', v_profile_id, 'interface_metrics'),
    ('ciena_raps', 'Ciena RAPS/G.8032', 'Poll G.8032 ring protection status', v_profile_id, 'raps_status'),
    ('ciena_alarms', 'Ciena Active Alarms', 'Poll active alarms from device', v_profile_id, 'device_alarms'),
    ('ciena_system', 'Ciena System Info', 'Poll basic system information', v_profile_id, NULL)
    ON CONFLICT (name) DO UPDATE SET display_name = EXCLUDED.display_name;

END $$;
