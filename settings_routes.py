#!/usr/bin/env python3
"""Settings routes - separated from main server"""

from flask import jsonify, request
from config import get_settings, save_settings
import subprocess
import socket
from database import db

def get_settings_route():
    """Get current scan settings"""
    try:
        return jsonify(get_settings())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def save_settings_route():
    """Save scan settings"""
    try:
        data = request.get_json()
        save_settings(data)
        return jsonify({'status': 'success', 'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def test_settings_route():
    """Test current settings"""
    try:
        results = []
        settings = get_settings()
        
        # Test ping command
        try:
            result = subprocess.run([settings['ping_command'], '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                results.append('✓ Ping command accessible')
            else:
                results.append('✗ Ping command failed')
        except Exception as e:
            results.append(f'✗ Ping command error: {str(e)}')
        
        # Test SNMP tools
        try:
            result = subprocess.run(['snmpget', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                results.append('✓ SNMP tools accessible')
            else:
                results.append('✗ SNMP tools failed')
        except Exception as e:
            results.append(f'✗ SNMP tools error: {str(e)}')
        
        # Test SSH connectivity (localhost)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', int(settings['ssh_port'])))
            sock.close()
            if result == 0:
                results.append(f'✓ SSH port {settings["ssh_port"]} accessible on localhost')
            else:
                results.append(f'✗ SSH port {settings["ssh_port"]} not accessible on localhost')
        except Exception as e:
            results.append(f'✗ SSH test error: {str(e)}')
        
        # Test database connection
        try:
            conn = db.get_connection()
            conn.close()
            results.append('✓ Database connection successful')
        except Exception as e:
            results.append(f'✗ Database connection error: {str(e)}')
        
        return jsonify({
            'status': 'success', 
            'message': 'Settings test completed',
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
