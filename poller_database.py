#!/usr/bin/env python3
"""Database schema and operations for the poller system"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class PollerDatabase:
    """Poller-specific database operations"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self._create_tables()
    
    def _create_tables(self):
        """Create poller-specific database tables"""
        try:
            # Poller configurations table
            configs_table = """
                CREATE TABLE IF NOT EXISTS poller_configs (
                    id SERIAL PRIMARY KEY,
                    job_type VARCHAR(50) NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    interval_seconds INTEGER NOT NULL DEFAULT 3600,
                    config JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """
            
            # Job execution history table
            history_table = """
                CREATE TABLE IF NOT EXISTS poller_job_history (
                    id SERIAL PRIMARY KEY,
                    job_id VARCHAR(100) NOT NULL,
                    job_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL, -- running, success, failed, missed
                    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    finished_at TIMESTAMP,
                    duration_seconds FLOAT,
                    result JSONB,
                    error_message TEXT,
                    config JSONB
                );
            """
            
            # Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_poller_history_job_type ON poller_job_history(job_type);",
                "CREATE INDEX IF NOT EXISTS idx_poller_history_status ON poller_job_history(status);",
                "CREATE INDEX IF NOT EXISTS idx_poller_history_started_at ON poller_job_history(started_at);",
                "CREATE INDEX IF NOT EXISTS idx_poller_history_job_id ON poller_job_history(job_id);"
            ]
            
            # Execute table creation
            self.db.execute_query(configs_table, fetch=False)
            self.db.execute_query(history_table, fetch=False)
            
            for index in indexes:
                self.db.execute_query(index, fetch=False)
            
            logger.info("Poller database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create poller tables: {e}")
            raise
    
    def save_poller_config(self, job_type: str, config: Dict[str, Any]) -> bool:
        """Save or update poller configuration"""
        try:
            query = """
                INSERT INTO poller_configs (job_type, enabled, interval_seconds, config, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (job_type) 
                DO UPDATE SET 
                    enabled = EXCLUDED.enabled,
                    interval_seconds = EXCLUDED.interval_seconds,
                    config = EXCLUDED.config,
                    updated_at = NOW()
            """
            
            self.db.execute_query(query, (
                job_type,
                config.get('enabled', False),
                config.get('interval', 3600),
                json.dumps(config)
            ), fetch=False)
            
            logger.info(f"Saved poller config for {job_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save poller config for {job_type}: {e}")
            return False
    
    def get_poller_config(self, job_type: str) -> Optional[Dict[str, Any]]:
        """Get poller configuration for a specific job type"""
        try:
            query = "SELECT * FROM poller_configs WHERE job_type = %s"
            result = self.db.execute_query(query, (job_type,))
            
            if result:
                config = result[0]
                # Parse JSON config
                if isinstance(config['config'], str):
                    config['config'] = json.loads(config['config'])
                return config
            
            # Return default config if not found
            return self._get_default_config(job_type)
            
        except Exception as e:
            logger.error(f"Failed to get poller config for {job_type}: {e}")
            return None
    
    def get_all_poller_configs(self) -> List[Dict[str, Any]]:
        """Get all poller configurations"""
        try:
            query = "SELECT * FROM poller_configs ORDER BY job_type"
            results = self.db.execute_query(query)
            
            configs = []
            for result in results:
                # Parse JSON config
                if isinstance(result['config'], str):
                    result['config'] = json.loads(result['config'])
                configs.append(result)
            
            return configs
            
        except Exception as e:
            logger.error(f"Failed to get all poller configs: {e}")
            return []
    
    def _get_default_config(self, job_type: str) -> Dict[str, Any]:
        """Get default configuration for a job type"""
        defaults = {
            'discovery': {
                'enabled': False,
                'interval': 3600,
                'network': '10.127.0.0/24',
                'retention': 30,
                'ping': True,
                'snmp': True,
                'ssh': True,
                'rdp': False
            },
            'interface': {
                'enabled': False,
                'interval': 1800,
                'targets': 'all',
                'custom': '',
                'retention': 7
            },
            'optical': {
                'enabled': False,
                'interval': 300,
                'targets': 'all',
                'retention': 90,
                'temperature_threshold': 70
            }
        }
        
        return {
            'id': None,
            'job_type': job_type,
            'enabled': False,
            'interval_seconds': defaults.get(job_type, {}).get('interval', 3600),
            'config': defaults.get(job_type, {}),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    
    def record_job_execution(self, job_id: str, job_type: str, status: str, 
                            result: Dict[str, Any] = None, error_message: str = None,
                            config: Dict[str, Any] = None, duration: float = None) -> bool:
        """Record job execution in history"""
        try:
            query = """
                INSERT INTO poller_job_history 
                (job_id, job_type, status, result, error_message, config, duration_seconds, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            self.db.execute_query(query, (
                job_id,
                job_type,
                status,
                json.dumps(result) if result else None,
                error_message,
                json.dumps(config) if config else None,
                duration
            ), fetch=False)
            
            logger.debug(f"Recorded job execution: {job_id} - {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record job execution: {e}")
            return False
    
    def get_job_history(self, job_type: str = None, limit: int = 100, 
                       status: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get job execution history"""
        try:
            where_conditions = ["started_at >= NOW() - INTERVAL '%s hours'" % hours]
            params = []
            
            if job_type:
                where_conditions.append("job_type = %s")
                params.append(job_type)
            
            if status:
                where_conditions.append("status = %s")
                params.append(status)
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
                SELECT * FROM poller_job_history 
                WHERE {where_clause}
                ORDER BY started_at DESC 
                LIMIT %s
            """
            
            params.append(limit)
            results = self.db.execute_query(query, tuple(params))
            
            # Parse JSON fields
            for result in results:
                if result.get('result') and isinstance(result['result'], str):
                    result['result'] = json.loads(result['result'])
                if result.get('config') and isinstance(result['config'], str):
                    result['config'] = json.loads(result['config'])
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get job history: {e}")
            return []
    
    def get_job_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get job execution statistics"""
        try:
            # Get execution counts by job type and status
            query = """
                SELECT job_type, status, COUNT(*) as count,
                       AVG(duration_seconds) as avg_duration
                FROM poller_job_history 
                WHERE started_at >= NOW() - INTERVAL '%s hours'
                GROUP BY job_type, status
            """ % hours
            
            results = self.db.execute_query(query)
            
            stats = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'by_job_type': {},
                'period_hours': hours
            }
            
            for result in results:
                job_type = result['job_type']
                status = result['status']
                count = result['count']
                avg_duration = result['avg_duration']
                
                stats['total_executions'] += count
                
                if status == 'success':
                    stats['successful_executions'] += count
                elif status == 'failed':
                    stats['failed_executions'] += count
                
                if job_type not in stats['by_job_type']:
                    stats['by_job_type'][job_type] = {
                        'total': 0,
                        'success': 0,
                        'failed': 0,
                        'avg_duration': 0
                    }
                
                stats['by_job_type'][job_type]['total'] += count
                stats['by_job_type'][job_type][status] = count
                if avg_duration:
                    stats['by_job_type'][job_type]['avg_duration'] = avg_duration
            
            # Calculate success rate
            if stats['total_executions'] > 0:
                stats['success_rate'] = (stats['successful_executions'] / stats['total_executions']) * 100
            else:
                stats['success_rate'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get job statistics: {e}")
            return {}
    
    def cleanup_old_history(self, days: int = 30) -> bool:
        """Clean up old job history records"""
        try:
            query = """
                DELETE FROM poller_job_history 
                WHERE started_at < NOW() - INTERVAL '%s days'
            """ % days
            
            result = self.db.execute_query(query, fetch=False)
            
            logger.info(f"Cleaned up job history older than {days} days")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")
            return False
    
    def get_recent_job_results(self, job_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent successful job results"""
        try:
            query = """
                SELECT * FROM poller_job_history 
                WHERE job_type = %s AND status = 'success' AND result IS NOT NULL
                ORDER BY started_at DESC 
                LIMIT %s
            """
            
            results = self.db.execute_query(query, (job_type, limit))
            
            # Parse JSON result field
            for result in results:
                if result.get('result') and isinstance(result['result'], str):
                    result['result'] = json.loads(result['result'])
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get recent job results: {e}")
            return []
    
    def get_devices_with_optical_interfaces(self) -> List[Dict[str, Any]]:
        """Get devices that have optical interfaces"""
        try:
            query = """
                SELECT DISTINCT d.ip_address, d.hostname
                FROM scan_results d
                JOIN ssh_cli_interfaces i ON d.ip_address = i.ip_address
                WHERE i.interface_type LIKE '%optical%' 
                   OR i.interface_name LIKE '%optical%'
                   OR i.interface_description LIKE '%optical%'
                   OR i.interface_name LIKE '%transceiver%'
                   OR i.interface_description LIKE '%transceiver%'
                ORDER BY d.ip_address
            """
            
            return self.db.execute_query(query)
            
        except Exception as e:
            logger.error(f"Failed to get devices with optical interfaces: {e}")
            return []

# Extend the main database class with poller methods
def extend_database_with_poller(db_class):
    """Extend the main database class with poller-specific methods"""
    
    def init_poller_db(self):
        """Initialize poller database extension"""
        if not hasattr(self, 'poller_db'):
            self.poller_db = PollerDatabase(self)
    
    def get_poller_config(self, job_type: str):
        """Get poller configuration"""
        if not hasattr(self, 'poller_db'):
            self.init_poller_db()
        return self.poller_db.get_poller_config(job_type)
    
    def save_poller_config(self, job_type: str, config: Dict[str, Any]):
        """Save poller configuration"""
        if not hasattr(self, 'poller_db'):
            self.init_poller_db()
        return self.poller_db.save_poller_config(job_type, config)
    
    def get_all_poller_configs(self):
        """Get all poller configurations"""
        if not hasattr(self, 'poller_db'):
            self.init_poller_db()
        return self.poller_db.get_all_poller_configs()
    
    def get_job_history(self, job_type: str = None, limit: int = 100, 
                       status: str = None, hours: int = 24):
        """Get job execution history"""
        if not hasattr(self, 'poller_db'):
            self.init_poller_db()
        return self.poller_db.get_job_history(job_type, limit, status, hours)
    
    def get_job_statistics(self, hours: int = 24):
        """Get job execution statistics"""
        if not hasattr(self, 'poller_db'):
            self.init_poller_db()
        return self.poller_db.get_job_statistics(hours)
    
    def get_devices_with_optical_interfaces(self):
        """Get devices with optical interfaces"""
        if not hasattr(self, 'poller_db'):
            self.init_poller_db()
        return self.poller_db.get_devices_with_optical_interfaces()
    
    # Add methods to the database class
    db_class.init_poller_db = init_poller_db
    db_class.get_poller_config = get_poller_config
    db_class.save_poller_config = save_poller_config
    db_class.get_all_poller_configs = get_all_poller_configs
    db_class.get_job_history = get_job_history
    db_class.get_job_statistics = get_job_statistics
    db_class.get_devices_with_optical_interfaces = get_devices_with_optical_interfaces
