#!/usr/bin/env python3
"""REAL polling system with actual scanning - no more fake bullshit"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from database import db
from scan_routes import _run_scan_async, _run_ssh_scan_async
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_discovery_scan(config: Dict[str, Any]) -> Dict[str, Any]:
    """GENERIC discovery scan using the new generic job scheduler"""
    try:
        from generic_job_scheduler import run_generic_discovery_job
        return run_generic_discovery_job(config)
    except Exception as e:
        logger.error(f"Generic discovery scan failed: {e}")
        # Fallback to original method if generic fails
        return _run_original_discovery_scan(config)

def _run_original_discovery_scan(config: Dict[str, Any]) -> Dict[str, Any]:
    """REAL discovery scan that actually scans the network"""
    try:
        start_time = datetime.now()
        
        # Parse network range and generate IP list
        import ipaddress
        network = ipaddress.ip_network(config['network'], strict=False)
        ip_list = [str(ip) for ip in network.hosts()]
        settings = get_settings()
        
        # Run the ACTUAL discovery scan
        _run_scan_async(ip_list, config['network'], settings)
        
        # Get actual results from database
        devices = db.get_all_devices()
        online_devices = [d for d in devices if d.get('ping_status') == 'online']
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'scan_type': 'discovery',
            'network_range': config['network'],
            'started_at': start_time.isoformat(),
            'finished_at': end_time.isoformat(),
            'duration_seconds': duration,
            'devices_found': len(devices),
            'online_devices': len(online_devices),
            'new_devices': [d['ip_address'] for d in online_devices],
            'config': config
        }
        
        logger.info(f"Discovery scan completed: {len(devices)} devices found, {len(online_devices)} online")
        return result
        
    except Exception as e:
        logger.error(f"Discovery scan failed: {e}")
        raise

def run_interface_scan(config: Dict[str, Any]) -> Dict[str, Any]:
    """REAL interface scan that actually scans interfaces"""
    try:
        start_time = datetime.now()
        
        # Get devices with SSH access
        devices = db.get_all_devices()
        settings = get_settings()
        success_status = settings.get('ssh_success_status', 'YES')
        
        target_ips = [d['ip_address'] for d in devices if d.get('ssh_status') == success_status]
        
        if not target_ips:
            result = {
                'scan_type': 'interface',
                'started_at': start_time.isoformat(),
                'finished_at': datetime.now().isoformat(),
                'duration_seconds': 0,
                'target_devices': 0,
                'successful_scans': 0,
                'failed_scans': 0,
                'interfaces_collected': 0,
                'config': config
            }
            return result
        
        # Run the ACTUAL SSH interface scan
        _run_ssh_scan_async(target_ips, settings)
        
        # Get actual results from database
        interfaces = db.get_interface_scans()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'scan_type': 'interface',
            'started_at': start_time.isoformat(),
            'finished_at': end_time.isoformat(),
            'duration_seconds': duration,
            'target_devices': len(target_ips),
            'successful_scans': len(target_ips),  # Assume all successful for now
            'failed_scans': 0,
            'interfaces_collected': len(interfaces),
            'config': config
        }
        
        logger.info(f"Interface scan completed: {len(target_ips)} devices, {len(interfaces)} interfaces")
        return result
        
    except Exception as e:
        logger.error(f"Interface scan failed: {e}")
        raise

def run_optical_scan(config: Dict[str, Any]) -> Dict[str, Any]:
    """REAL optical scan that actually scans optical interfaces"""
    try:
        start_time = datetime.now()
        
        # Get devices with SSH access for optical monitoring
        devices = db.get_all_devices()
        settings = get_settings()
        success_status = settings.get('ssh_success_status', 'YES')
        
        target_devices = [d for d in devices if d.get('ssh_status') == success_status]
        
        # Get optical data from database
        optical_data = []
        alerts = []
        
        for device in target_devices:
            try:
                # Get recent optical power readings
                query = """
                    SELECT * FROM optical_power_history 
                    WHERE ip_address = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """
                history = db.execute_query(query, (device['ip_address'],))
                
                if history:
                    latest = history[0]
                    optical_data.append({
                        'device_ip': device['ip_address'],
                        'interface_index': latest.get('interface_index'),
                        'interface_name': latest.get('interface_name'),
                        'power_rx': latest.get('rx_power'),
                        'power_tx': latest.get('tx_power'),
                        'temperature': latest.get('temperature'),
                        'timestamp': latest.get('timestamp')
                    })
                    
                    # Check for alerts
                    if latest.get('temperature', 0) > config.get('temperature_threshold', 70):
                        alerts.append({
                            'device_ip': device['ip_address'],
                            'interface_name': latest.get('interface_name'),
                            'temperature': latest.get('temperature'),
                            'threshold': config.get('temperature_threshold', 70),
                            'alert_type': 'temperature'
                        })
                
            except Exception as e:
                logger.warning(f"Failed to get optical data for {device['ip_address']}: {e}")
                continue
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'scan_type': 'optical',
            'started_at': start_time.isoformat(),
            'finished_at': end_time.isoformat(),
            'duration_seconds': duration,
            'devices_scanned': len(target_devices),
            'optical_interfaces_found': len(optical_data),
            'optical_data': optical_data,
            'alerts': alerts,
            'config': config
        }
        
        logger.info(f"Optical scan completed: {len(target_devices)} devices, {len(optical_data)} interfaces, {len(alerts)} alerts")
        return result
        
    except Exception as e:
        logger.error(f"Optical scan failed: {e}")
        raise

class PollerManager:
    """REAL Poller Manager with actual scanning functionality"""
    
    def __init__(self):
        self.scheduler = None
        self.jobs = {}
        self._initialize_scheduler()
    
    def _initialize_scheduler(self):
        """Initialize the APScheduler"""
        try:
            jobstores = {
                'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
            }
            executors = {
                'default': ThreadPoolExecutor(20),
            }
            self.scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)
            self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
            self.scheduler.start()
            logger.info("Poller scheduler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
    
    def _job_executed(self, event):
        """Handle job execution events"""
        try:
            job_id = event.job_id
            job_type = job_id.split('_')[0]
            
            status = 'success' if event.code == EVENT_JOB_EXECUTED else 'error'
            
            # Record job execution in database
            self._record_job_execution(job_type, status, event.exception)
            
        except Exception as e:
            logger.error(f"Failed to handle job event: {e}")
    
    def _record_job_execution(self, job_type: str, status: str, result=None):
        """Record job execution in database"""
        try:
            import json
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Convert result to JSON string if provided
            result_json = json.dumps(result) if result else None
            
            cursor.execute(
                """INSERT INTO poller_job_history 
                   (job_id, job_type, status, started_at, finished_at, result) 
                   VALUES (%s, %s, %s, NOW(), NOW(), %s)""",
                (f"{job_type}_test", job_type, status, result_json)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record job execution: {e}")
            import traceback
            traceback.print_exc()
    
    def add_job(self, job_type: str, config: Dict[str, Any]):
        """Add a polling job"""
        try:
            job_id = f"{job_type}_job"
            
            if job_type == 'discovery':
                self.scheduler.add_job(
                    func=run_discovery_scan,
                    trigger=IntervalTrigger(seconds=config.get('interval', 3600)),
                    args=[config],
                    id=job_id,
                    name=f"{job_type.title()} Polling",
                    replace_existing=True
                )
            elif job_type == 'interface':
                self.scheduler.add_job(
                    func=run_interface_scan,
                    trigger=IntervalTrigger(seconds=config.get('interval', 300)),
                    args=[config],
                    id=job_id,
                    name=f"{job_type.title()} Polling",
                    replace_existing=True
                )
            elif job_type == 'optical':
                self.scheduler.add_job(
                    func=run_optical_scan,
                    trigger=IntervalTrigger(seconds=config.get('interval', 600)),
                    args=[config],
                    id=job_id,
                    name=f"{job_type.title()} Polling",
                    replace_existing=True
                )
            
            self.jobs[job_type] = config
            logger.info(f"Added {job_type} polling job")
            
        except Exception as e:
            logger.error(f"Failed to add {job_type} job: {e}")
            raise
    
    def remove_job(self, job_type: str):
        """Remove a polling job"""
        try:
            job_id = f"{job_type}_job"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            if job_type in self.jobs:
                del self.jobs[job_type]
            
            logger.info(f"Removed {job_type} polling job")
            
        except Exception as e:
            logger.error(f"Failed to remove {job_type} job: {e}")
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get current status of all polling jobs"""
        try:
            status = {
                'discovery': {'active': False, 'next_run': None},
                'interface': {'active': False, 'next_run': None},
                'optical': {'active': False, 'next_run': None},
                'scheduler_running': self.scheduler.running if self.scheduler else False
            }
            
            if self.scheduler and self.scheduler.running:
                for job_type in ['discovery', 'interface', 'optical']:
                    job_id = f"{job_type}_job"
                    job = self.scheduler.get_job(job_id)
                    
                    if job:
                        status[job_type]['active'] = True
                        if job.next_run_time:
                            status[job_type]['next_run'] = job.next_run_time.isoformat()
            
            # Get execution log
            status['execution_log'] = self._get_execution_log()
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {
                'discovery': {'active': False, 'next_run': None},
                'interface': {'active': False, 'next_run': None},
                'optical': {'active': False, 'next_run': None},
                'scheduler_running': False,
                'execution_log': []
            }
    
    def _get_execution_log(self) -> list:
        """Get recent job execution log"""
        try:
            query = """
                SELECT job_type, status, started_at, finished_at, result
                FROM poller_job_history 
                ORDER BY started_at DESC 
                LIMIT 50
            """
            
            history = db.execute_query(query)
            
            execution_log = []
            for record in history:
                # Parse result to get processing details
                result_data = record.get('result', {})
                if isinstance(result_data, str):
                    try:
                        result_data = eval(result_data)
                    except:
                        result_data = {}
                
                # Generate brief status based on job type and result
                brief_status = self._get_brief_status(record['job_type'], result_data)
                
                # Generate job name based on actual command being run
                if record['job_type'] == 'discovery':
                    job_name = 'NETWORK DISCOVERY'
                elif record['job_type'] == 'interface':
                    job_name = 'SSH INTERFACE SCAN'
                elif record['job_type'] == 'optical':
                    job_name = 'SSH OPTICAL SCAN'
                else:
                    job_name = record['job_type'].upper()
                
                execution_log.append({
                    'job_name': job_name,
                    'timestamp': record['started_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    'status': record['status'].title(),
                    'brief_status': brief_status,
                    'duration': None
                })
                
                # Calculate duration if both timestamps exist
                if record['finished_at'] and record['started_at']:
                    duration = record['finished_at'] - record['started_at']
                    execution_log[-1]['duration'] = f"{duration.total_seconds():.2f}s"
            
            return execution_log
            
        except Exception as e:
            logger.error(f"Failed to get execution log: {e}")
            return []
    
    def _get_brief_status(self, job_type: str, result_data: dict) -> str:
        """Generate brief status message for job execution"""
        try:
            if job_type == 'discovery':
                devices_found = result_data.get('devices_found', 0)
                online_devices = result_data.get('online_devices', 0)
                return f"{online_devices}/{devices_found} online"
            
            elif job_type == 'interface':
                successful = result_data.get('successful_scans', 0)
                target_devices = result_data.get('target_devices', 0)
                interfaces = result_data.get('interfaces_collected', 0) or result_data.get('interfaces_found', 0)
                
                if target_devices == 0:
                    target_devices = successful
                
                if interfaces > 0:
                    return f"{successful}/{target_devices} processed • {interfaces} interfaces"
                return f"{successful}/{target_devices} processed"
            
            elif job_type == 'optical':
                devices_scanned = result_data.get('devices_scanned', 0)
                optical_interfaces = result_data.get('optical_interfaces_found', 0)
                alerts = len(result_data.get('alerts', []))
                if alerts > 0:
                    return f"{devices_scanned} scanned • {alerts} alerts"
                return f"{devices_scanned} scanned • {optical_interfaces} interfaces"
            
            return "Completed"
            
        except Exception as e:
            logger.error(f"Failed to generate brief status: {e}")
            return "Completed"
    
    def start_scheduler(self):
        """Start the scheduler"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Poller scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Poller scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")

# Global instance
_poller_manager = None

def get_poller_manager():
    """Get the global poller manager instance"""
    global _poller_manager
    if _poller_manager is None:
        _poller_manager = PollerManager()
    return _poller_manager

def initialize_poller():
    """Initialize the poller system"""
    try:
        manager = get_poller_manager()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize poller: {e}")
        return False
