#!/usr/bin/env python3
"""Flask API routes for the poller system"""

import json
import logging
import threading
from flask import jsonify, request
from poller_manager import get_poller_manager, run_discovery_scan, run_interface_scan, run_optical_scan
from poller_database import extend_database_with_poller
from database import db

logger = logging.getLogger(__name__)

def get_poller_status():
    """Get current status of all polling jobs"""
    try:
        manager = get_poller_manager()
        status = manager.get_job_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting poller status: {e}")
        return jsonify({'error': str(e)}), 500

def get_poller_configs():
    """Get all poller configurations"""
    try:
        # Get default configs since database extension isn't working
        configs = [
            {
                'job_type': 'discovery',
                'enabled': False,
                'interval_seconds': 3600,
                'config': {
                    'enabled': False,
                    'interval': 3600,
                    'network': '10.127.0.0/24',
                    'retention': 30,
                    'ping': True,
                    'snmp': True,
                    'ssh': True,
                    'rdp': False
                }
            },
            {
                'job_type': 'interface',
                'enabled': False,
                'interval_seconds': 1800,
                'config': {
                    'enabled': False,
                    'interval': 1800,
                    'targets': 'all',
                    'custom': '',
                    'retention': 7
                }
            },
            {
                'job_type': 'optical',
                'enabled': False,
                'interval_seconds': 300,
                'config': {
                    'enabled': False,
                    'interval': 300,
                    'targets': 'all',
                    'retention': 90,
                    'temperature_threshold': 70
                }
            }
        ]
        return jsonify(configs)
    except Exception as e:
        logger.error(f"Error getting poller configs: {e}")
        return jsonify({'error': str(e)}), 500

def save_poller_config():
    """Save poller configuration (global config endpoint)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # Save each job type configuration
        results = {}
        for job_type in ['discovery', 'interface', 'optical']:
            if job_type in data:
                success = db.save_poller_config(job_type, data[job_type])
                results[job_type] = success
                
                # Update running job if scheduler is running
                if success:
                    manager = get_poller_manager()
                    manager.start_job(job_type, data[job_type])
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        logger.error(f"Error saving poller config: {e}")
        return jsonify({'error': str(e)}), 500

def start_discovery_poller():
    """Start the discovery polling job"""
    try:
        # Use default config for now
        config = {
            'enabled': True,
            'interval': 3600,
            'network': '10.127.0.0/24',
            'retention': 30,
            'ping': True,
            'snmp': True,
            'ssh': True,
            'rdp': False
        }
        
        manager = get_poller_manager()
        success = manager.start_job('discovery', config)
        
        if success:
            return jsonify({'success': True, 'message': 'Discovery poller started successfully'})
        else:
            return jsonify({'error': 'Failed to start discovery poller'}), 500
    except Exception as e:
        logger.error(f"Error starting discovery poller: {e}")
        return jsonify({'error': str(e)}), 500

def stop_discovery_poller():
    """Stop the discovery polling job"""
    try:
        manager = get_poller_manager()
        success = manager.stop_job('discovery')
        
        if success:
            return jsonify({'success': True, 'message': 'Discovery poller stopped successfully'})
        else:
            return jsonify({'error': 'Failed to stop discovery poller'}), 500
    except Exception as e:
        logger.error(f"Error stopping discovery poller: {e}")
        return jsonify({'error': str(e)}), 500

def save_discovery_config():
    """Save discovery poller configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # For now, just start/stop the job based on config
        manager = get_poller_manager()
        if data.get('enabled'):
            success = manager.start_job('discovery', data)
            if success:
                return jsonify({'success': True, 'message': 'Discovery configuration saved and started successfully'})
            else:
                return jsonify({'error': 'Failed to start discovery poller'}), 500
        else:
            manager.stop_job('discovery')
            return jsonify({'success': True, 'message': 'Discovery configuration saved and stopped successfully'})
    except Exception as e:
        logger.error(f"Error saving discovery config: {e}")
        return jsonify({'error': str(e)}), 500

def start_interface_poller():
    """Start the interface polling job"""
    try:
        config = db.get_poller_config('interface')
        if not config:
            return jsonify({'error': 'No configuration found for interface poller'}), 400
        
        manager = get_poller_manager()
        success = manager.start_job('interface', config['config'])
        
        if success:
            return jsonify({'success': True, 'message': 'Interface poller started successfully'})
        else:
            return jsonify({'error': 'Failed to start interface poller'}), 500
    except Exception as e:
        logger.error(f"Error starting interface poller: {e}")
        return jsonify({'error': str(e)}), 500

def stop_interface_poller():
    """Stop the interface polling job"""
    try:
        manager = get_poller_manager()
        success = manager.stop_job('interface')
        
        if success:
            return jsonify({'success': True, 'message': 'Interface poller stopped successfully'})
        else:
            return jsonify({'error': 'Failed to stop interface poller'}), 500
    except Exception as e:
        logger.error(f"Error stopping interface poller: {e}")
        return jsonify({'error': str(e)}), 500

def save_interface_config():
    """Save interface poller configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # For now, just start/stop the job based on config
        manager = get_poller_manager()
        if data.get('enabled'):
            success = manager.start_job('interface', data)
            if success:
                return jsonify({'success': True, 'message': 'Interface configuration saved and started successfully'})
            else:
                return jsonify({'error': 'Failed to start interface poller'}), 500
        else:
            manager.stop_job('interface')
            return jsonify({'success': True, 'message': 'Interface configuration saved and stopped successfully'})
    except Exception as e:
        logger.error(f"Error saving interface config: {e}")
        return jsonify({'error': str(e)}), 500

def start_optical_poller():
    """Start the optical power polling job"""
    try:
        config = db.get_poller_config('optical')
        if not config:
            return jsonify({'error': 'No configuration found for optical poller'}), 400
        
        manager = get_poller_manager()
        success = manager.start_job('optical', config['config'])
        
        if success:
            return jsonify({'success': True, 'message': 'Optical power poller started successfully'})
        else:
            return jsonify({'error': 'Failed to start optical power poller'}), 500
    except Exception as e:
        logger.error(f"Error starting optical poller: {e}")
        return jsonify({'error': str(e)}), 500

def stop_optical_poller():
    """Stop the optical power polling job"""
    try:
        manager = get_poller_manager()
        success = manager.stop_job('optical')
        
        if success:
            return jsonify({'success': True, 'message': 'Optical power poller stopped successfully'})
        else:
            return jsonify({'error': 'Failed to stop optical power poller'}), 500
    except Exception as e:
        logger.error(f"Error stopping optical poller: {e}")
        return jsonify({'error': str(e)}), 500

def save_optical_config():
    """Save optical power poller configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # For now, just start/stop the job based on config
        manager = get_poller_manager()
        if data.get('enabled'):
            success = manager.start_job('optical', data)
            if success:
                return jsonify({'success': True, 'message': 'Optical power configuration saved and started successfully'})
            else:
                return jsonify({'error': 'Failed to start optical power poller'}), 500
        else:
            manager.stop_job('optical')
            return jsonify({'success': True, 'message': 'Optical power configuration saved and stopped successfully'})
    except Exception as e:
        logger.error(f"Error saving optical config: {e}")
        return jsonify({'error': str(e)}), 500

def run_all_pollers():
    """Run all polling jobs immediately"""
    try:
        results = {}
        
        for job_type in ['discovery', 'interface', 'optical']:
            success = run_job_now(job_type)
            results[job_type] = success
        
        all_success = all(results.values())
        
        if all_success:
            return jsonify({'success': True, 'message': 'All pollers started successfully', 'results': results})
        else:
            return jsonify({'success': False, 'message': 'Some pollers failed to start', 'results': results})
    except Exception as e:
        logger.error(f"Error running all pollers: {e}")
        return jsonify({'error': str(e)}), 500

def get_poller_logs():
    """Get poller execution logs"""
    try:
        # Get query parameters
        job_type = request.args.get('job_type')
        status = request.args.get('status')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))
        
        logs = db.get_job_history(job_type=job_type, status=status, hours=hours, limit=limit)
        
        # Format logs for frontend
        formatted_logs = []
        for log in logs:
            formatted_log = {
                'timestamp': log['started_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'success' if log['status'] == 'success' else 'error' if log['status'] == 'failed' else 'warning',
                'message': f"{log['job_type'].title()} job {log['status']}",
                'details': {
                    'job_type': log['job_type'],
                    'status': log['status'],
                    'duration': log.get('duration_seconds'),
                    'result': log.get('result'),
                    'error': log.get('error_message')
                }
            }
            formatted_logs.append(formatted_log)
        
        return jsonify(formatted_logs)
    except Exception as e:
        logger.error(f"Error getting poller logs: {e}")
        return jsonify({'error': str(e)}), 500

def clear_poller_logs():
    """Clear poller execution logs"""
    try:
        # Get query parameters
        days = int(request.args.get('days', 30))
        
        # Clean up old history
        if hasattr(db, 'poller_db'):
            success = db.poller_db.cleanup_old_history(days)
        else:
            success = False
        
        if success:
            return jsonify({'success': True, 'message': f'Logs older than {days} days cleared successfully'})
        else:
            return jsonify({'error': 'Failed to clear logs'}), 500
    except Exception as e:
        logger.error(f"Error clearing poller logs: {e}")
        return jsonify({'error': str(e)}), 500

def get_poller_statistics():
    """Get poller execution statistics"""
    try:
        # Get query parameters
        hours = int(request.args.get('hours', 24))
        
        stats = db.get_job_statistics(hours=hours)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting poller statistics: {e}")
        return jsonify({'error': str(e)}), 500

def test_discovery_scan():
    """Test discovery scan with current configuration"""
    try:
        # Use default config for now
        config = {
            'enabled': True,
            'interval': 3600,
            'network': '10.127.0.0/24',
            'retention': 30,
            'ping': True,
            'snmp': True,
            'ssh': True,
            'rdp': False
        }
        
        manager = get_poller_manager()
        
        # Run test scan
        try:
            result = run_discovery_scan(config)
            
            # Record the scan in the execution log
            manager = get_poller_manager()
            manager._record_job_execution('discovery', 'success', result)
            
            return jsonify({
                'success': True,
                'message': 'Discovery test scan completed successfully',
                'result': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Discovery test scan failed: {str(e)}'
            }), 500
    except Exception as e:
        logger.error(f"Error testing discovery scan: {e}")
        return jsonify({'error': str(e)}), 500

def test_interface_scan():
    """Test interface scan with current configuration"""
    try:
        # Use default config for now
        config = {
            'enabled': True,
            'interval': 1800,
            'targets': 'all',
            'custom': '',
            'retention': 7
        }
        
        manager = get_poller_manager()
        
        # Run test scan
        try:
            result = run_interface_scan(config)
            
            # Record the scan in the execution log
            manager = get_poller_manager()
            manager._record_job_execution('interface', 'success', result)
            
            return jsonify({
                'success': True,
                'message': 'Interface test scan completed successfully',
                'result': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Interface test scan failed: {str(e)}'
            }), 500
    except Exception as e:
        logger.error(f"Error testing interface scan: {e}")
        return jsonify({'error': str(e)}), 500

def test_optical_scan():
    """Test optical power scan with current configuration"""
    try:
        # Use default config for now
        config = {
            'enabled': True,
            'interval': 300,
            'targets': 'all',
            'retention': 90,
            'temperature_threshold': 70
        }
        
        manager = get_poller_manager()
        
        # Run test scan
        try:
            result = run_optical_scan(config)
            
            # Record the scan in the execution log
            manager = get_poller_manager()
            manager._record_job_execution('optical', 'success', result)
            
            return jsonify({
                'success': True,
                'message': 'Optical power test scan completed successfully',
                'result': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Optical power test scan failed: {str(e)}'
            }), 500
    except Exception as e:
        logger.error(f"Error testing optical scan: {e}")
        return jsonify({'error': str(e)}), 500

def run_job_now(job_type: str) -> bool:
    """Run a job immediately"""
    try:
        # Use default configs for now
        configs = {
            'discovery': {
                'enabled': True,
                'interval': 3600,
                'network': '10.127.0.0/24',
                'retention': 30,
                'ping': True,
                'snmp': True,
                'ssh': True,
                'rdp': False
            },
            'interface': {
                'enabled': True,
                'interval': 1800,
                'targets': 'all',
                'custom': '',
                'retention': 7
            },
            'optical': {
                'enabled': True,
                'interval': 300,
                'targets': 'all',
                'retention': 90,
                'temperature_threshold': 70
            }
        }
        
        config = configs.get(job_type)
        if not config:
            logger.error(f"No configuration found for {job_type}")
            return False
        
        # Run job in background thread
        if job_type == 'discovery':
            threading.Thread(target=run_discovery_scan, args=(config,)).start()
        elif job_type == 'interface':
            threading.Thread(target=run_interface_scan, args=(config,)).start()
        elif job_type == 'optical':
            threading.Thread(target=run_optical_scan, args=(config,)).start()
        else:
            logger.error(f"Unknown job type: {job_type}")
            return False
        
        logger.info(f"Started immediate execution of {job_type} job")
        return True
        
    except Exception as e:
        logger.error(f"Failed to run {job_type} job now: {e}")
        return False

# Initialize poller database extension
def initialize_poller_database():
    """Initialize the poller database extension"""
    try:
        extend_database_with_poller(db)
        logger.info("Poller database extension initialized")
    except Exception as e:
        logger.error(f"Failed to initialize poller database extension: {e}")
        raise

# Initialize the poller system
def initialize_poller_system():
    """Initialize the complete poller system"""
    try:
        # Initialize database extension
        initialize_poller_database()
        
        # Initialize poller manager
        from poller_manager import initialize_poller
        success = initialize_poller()
        
        if success:
            logger.info("Poller system initialized successfully")
        else:
            logger.error("Poller system initialization failed")
            
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize poller system: {e}")
        return False

def save_discovery_config():
    """Save discovery polling configuration"""
    try:
        config = request.get_json()
        manager = get_poller_manager()
        
        # Save configuration to database or config file
        # For now, just update the manager's job configuration
        manager.jobs['discovery'] = config
        
        return jsonify({
            'success': True,
            'message': 'Discovery configuration saved successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to save discovery configuration: {str(e)}'
        }), 500

def save_interface_config():
    """Save interface polling configuration"""
    try:
        config = request.get_json()
        manager = get_poller_manager()
        
        # Save configuration to database or config file
        manager.jobs['interface'] = config
        
        return jsonify({
            'success': True,
            'message': 'Interface configuration saved successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to save interface configuration: {str(e)}'
        }), 500

def save_optical_config():
    """Save optical polling configuration"""
    try:
        config = request.get_json()
        manager = get_poller_manager()
        
        # Save configuration to database or config file
        manager.jobs['optical'] = config
        
        return jsonify({
            'success': True,
            'message': 'Optical configuration saved successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to save optical configuration: {str(e)}'
        }), 500
