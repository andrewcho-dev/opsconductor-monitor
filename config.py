#!/usr/bin/env python3
"""Simple JSON config - NO ENV VARIABLES"""

import json

def get_settings():
    """Get settings from JSON file"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "ping_command": "ping",
            "ping_count": "1",
            "ping_timeout": "0.3",
            "online_status": "online",
            "offline_status": "offline",
            "snmp_version": "2c",
            "snmp_community": "public",
            "snmp_port": "161",
            "snmp_timeout": "1",
            "snmp_success_status": "YES",
            "snmp_fail_status": "NO",
            "ssh_port": "22",
            "ssh_timeout": "3",
            "ssh_username": "admin",
            "ssh_password": "admin",
            "ssh_success_status": "YES",
            "ssh_fail_status": "NO",
            "rdp_port": "3389",
            "rdp_timeout": "3",
            "rdp_success_status": "YES",
            "rdp_fail_status": "NO",
            "max_threads": "100",
            "completion_message": "Capability scan completed: {online}/{total} hosts online",
            # Notification settings (Apprise)
            "notifications_enabled": False,
            "notification_targets": "",
            "notify_discovery_on_success": False,
            "notify_discovery_on_error": True,
            "notify_interface_on_success": False,
            "notify_interface_on_error": True,
            "notify_optical_on_success": False,
            "notify_optical_on_error": True,
        }

def save_settings(data):
    """Save settings to JSON file"""
    settings = {
        "ping_command": data.get('ping_command', 'ping'),
        "ping_count": data.get('ping_count', '1'),
        "ping_timeout": data.get('ping_timeout', '0.3'),
        "online_status": data.get('online_status', 'online'),
        "offline_status": data.get('offline_status', 'offline'),
        "snmp_version": data.get('snmp_version', '2c'),
        "snmp_community": data.get('snmp_community', 'public'),
        "snmp_port": data.get('snmp_port', '161'),
        "snmp_timeout": data.get('snmp_timeout', '1'),
        "snmp_success_status": data.get('snmp_success_status', 'YES'),
        "snmp_fail_status": data.get('snmp_fail_status', 'NO'),
        "ssh_port": data.get('ssh_port', '22'),
        "ssh_timeout": data.get('ssh_timeout', '3'),
        "ssh_username": data.get('ssh_username', 'admin'),
        "ssh_password": data.get('ssh_password', 'admin'),
        "ssh_success_status": data.get('ssh_success_status', 'YES'),
        "ssh_fail_status": data.get('ssh_fail_status', 'NO'),
        "rdp_port": data.get('rdp_port', '3389'),
        "rdp_timeout": data.get('rdp_timeout', '3'),
        "rdp_success_status": data.get('rdp_success_status', 'YES'),
        "rdp_fail_status": data.get('rdp_fail_status', 'NO'),
        "max_threads": data.get('max_threads', '100'),
        "completion_message": data.get('completion_message', 'Capability scan completed: {online}/{total} hosts online'),
        # Notification settings (Apprise)
        "notifications_enabled": bool(data.get('notifications_enabled', False)),
        "notification_targets": data.get('notification_targets', ''),
        "notify_discovery_on_success": bool(data.get('notify_discovery_on_success', False)),
        "notify_discovery_on_error": bool(data.get('notify_discovery_on_error', True)),
        "notify_interface_on_success": bool(data.get('notify_interface_on_success', False)),
        "notify_interface_on_error": bool(data.get('notify_interface_on_error', True)),
        "notify_optical_on_success": bool(data.get('notify_optical_on_success', False)),
        "notify_optical_on_error": bool(data.get('notify_optical_on_error', True)),
    }
    
    with open('config.json', 'w') as f:
        json.dump(settings, f, indent=2)
