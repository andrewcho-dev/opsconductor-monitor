"""
Centralized Logging Service

Provides comprehensive logging with database storage, file rotation,
and structured JSON output. All application components should use this
service for consistent, queryable logging.
"""

import os
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from logging.handlers import RotatingFileHandler
from queue import Queue
from contextlib import contextmanager

from backend.utils.time import now_utc

# Thread-local storage for request context
_context = threading.local()


class LogLevel:
    """Log level constants."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class LogSource:
    """Log source/component constants."""
    API = 'api'
    SCHEDULER = 'scheduler'
    WORKER = 'worker'
    SSH = 'ssh'
    SNMP = 'snmp'
    PING = 'ping'
    DATABASE = 'database'
    WORKFLOW = 'workflow'
    SYSTEM = 'system'
    NOTIFICATION = 'notification'
    MIGRATION = 'migration'


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes logs to PostgreSQL database.
    Uses a background thread and queue for non-blocking writes.
    """
    
    def __init__(self, db_connection=None, batch_size=50, flush_interval=5.0):
        super().__init__()
        self.db_connection = db_connection
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.log_queue = Queue()
        self._stop_event = threading.Event()
        self._flush_thread = None
        
        if db_connection:
            self._start_flush_thread()
    
    def _start_flush_thread(self):
        """Start the background flush thread."""
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def _flush_loop(self):
        """Background loop that flushes logs to database."""
        while not self._stop_event.is_set():
            self._flush_batch()
            self._stop_event.wait(self.flush_interval)
        # Final flush on shutdown
        self._flush_batch()
    
    def _flush_batch(self):
        """Flush queued logs to database."""
        if not self.db_connection:
            return
        
        batch = []
        while not self.log_queue.empty() and len(batch) < self.batch_size:
            try:
                batch.append(self.log_queue.get_nowait())
            except:
                break
        
        if not batch:
            return
        
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            insert_sql = """
                INSERT INTO system_logs (
                    timestamp, level, source, category, message, details,
                    request_id, user_id, ip_address, job_id, workflow_id,
                    execution_id, device_ip, duration_ms, status_code
                ) VALUES (
                    %(timestamp)s, %(level)s, %(source)s, %(category)s, 
                    %(message)s, %(details)s, %(request_id)s, %(user_id)s,
                    %(ip_address)s, %(job_id)s, %(workflow_id)s, %(execution_id)s,
                    %(device_ip)s, %(duration_ms)s, %(status_code)s
                )
            """
            
            for log_entry in batch:
                cursor.execute(insert_sql, log_entry)
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            # Log to stderr if database write fails
            import sys
            print(f"Failed to write logs to database: {e}", file=sys.stderr)
    
    def emit(self, record):
        """Handle a log record."""
        try:
            # Extract extra context from record
            log_entry = {
                'timestamp': now_utc(),
                'level': record.levelname,
                'source': getattr(record, 'source', LogSource.SYSTEM),
                'category': getattr(record, 'category', None),
                'message': self.format(record),
                'details': json.dumps(getattr(record, 'details', None)),
                'request_id': getattr(record, 'request_id', getattr(_context, 'request_id', None)),
                'user_id': getattr(record, 'user_id', getattr(_context, 'user_id', None)),
                'ip_address': getattr(record, 'ip_address', getattr(_context, 'ip_address', None)),
                'job_id': getattr(record, 'job_id', None),
                'workflow_id': getattr(record, 'workflow_id', None),
                'execution_id': getattr(record, 'execution_id', None),
                'device_ip': getattr(record, 'device_ip', None),
                'duration_ms': getattr(record, 'duration_ms', None),
                'status_code': getattr(record, 'status_code', None),
            }
            
            self.log_queue.put(log_entry)
            
        except Exception:
            self.handleError(record)
    
    def close(self):
        """Clean shutdown."""
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
        super().close()


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""
    
    def format(self, record):
        log_data = {
            'timestamp': now_utc().isoformat(),
            'level': record.levelname,
            'source': getattr(record, 'source', 'system'),
            'category': getattr(record, 'category', None),
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        for key in ['request_id', 'job_id', 'workflow_id', 'execution_id', 
                    'device_ip', 'duration_ms', 'status_code', 'details']:
            value = getattr(record, key, None)
            if value is not None:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class LoggingService:
    """
    Centralized logging service for the application.
    
    Provides:
    - Database-backed log storage
    - File rotation
    - Structured JSON logging
    - Request context tracking
    - Component-specific loggers
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.db_connection = None
        self.db_handler = None
        self._loggers = {}
    
    def initialize(self, db_connection=None, log_level='INFO', log_dir=None):
        """
        Initialize the logging service.
        
        Args:
            db_connection: Database connection for log storage
            log_level: Minimum log level
            log_dir: Directory for log files
        """
        self.db_connection = db_connection
        
        # Determine log directory
        if log_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            log_dir = os.path.join(project_root, 'logs')
        
        os.makedirs(log_dir, exist_ok=True)
        
        # Get numeric log level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler with standard format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
        
        # JSON file handler for structured logs
        json_file = os.path.join(log_dir, 'opsconductor.json.log')
        json_handler = RotatingFileHandler(
            json_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        json_handler.setLevel(numeric_level)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)
        
        # Standard text file handler
        text_file = os.path.join(log_dir, 'opsconductor.log')
        text_handler = RotatingFileHandler(
            text_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        text_handler.setLevel(numeric_level)
        text_handler.setFormatter(console_format)
        root_logger.addHandler(text_handler)
        
        # Database handler (if db_connection provided)
        if db_connection:
            self.db_handler = DatabaseLogHandler(db_connection)
            self.db_handler.setLevel(numeric_level)
            root_logger.addHandler(self.db_handler)
        
        # Log initialization
        root_logger.info(
            "Logging service initialized",
            extra={'source': LogSource.SYSTEM, 'category': 'startup'}
        )
    
    def get_logger(self, name: str, source: str = LogSource.SYSTEM) -> 'ComponentLogger':
        """
        Get a component-specific logger.
        
        Args:
            name: Logger name (typically __name__)
            source: Component source identifier
        
        Returns:
            ComponentLogger instance
        """
        key = f"{source}:{name}"
        if key not in self._loggers:
            self._loggers[key] = ComponentLogger(name, source)
        return self._loggers[key]
    
    @contextmanager
    def request_context(self, request_id: str = None, user_id: str = None, ip_address: str = None):
        """
        Context manager for request-scoped logging context.
        
        Usage:
            with logging_service.request_context(request_id='abc123'):
                logger.info("Processing request")  # Will include request_id
        """
        _context.request_id = request_id or str(uuid.uuid4())
        _context.user_id = user_id
        _context.ip_address = ip_address
        
        try:
            yield _context.request_id
        finally:
            _context.request_id = None
            _context.user_id = None
            _context.ip_address = None
    
    def query_logs(
        self,
        source: str = None,
        level: str = None,
        category: str = None,
        search: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        job_id: str = None,
        workflow_id: str = None,
        execution_id: str = None,
        device_ip: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Query logs from the database.
        
        Returns:
            Dict with 'logs' list and 'total' count
        """
        if not self.db_connection:
            return {'logs': [], 'total': 0, 'error': 'Database not configured'}
        
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            # Build query
            conditions = []
            params = []
            
            if source and source != 'all':
                conditions.append("source = %s")
                params.append(source)
            
            if level and level != 'all':
                conditions.append("level = %s")
                params.append(level.upper())
            
            if category:
                conditions.append("category = %s")
                params.append(category)
            
            if search:
                conditions.append("message ILIKE %s")
                params.append(f"%{search}%")
            
            if start_time:
                conditions.append("timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= %s")
                params.append(end_time)
            
            if job_id:
                conditions.append("job_id = %s")
                params.append(job_id)
            
            if workflow_id:
                conditions.append("workflow_id = %s")
                params.append(workflow_id)
            
            if execution_id:
                conditions.append("execution_id = %s")
                params.append(execution_id)
            
            if device_ip:
                conditions.append("device_ip = %s")
                params.append(device_ip)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get total count
            count_sql = f"SELECT COUNT(*) as cnt FROM system_logs WHERE {where_clause}"
            cursor.execute(count_sql, params)
            count_row = cursor.fetchone()
            total = count_row['cnt'] if isinstance(count_row, dict) else count_row[0]
            
            # Get logs
            query_sql = f"""
                SELECT id, timestamp, level, source, category, message, details,
                       request_id, job_id, workflow_id, execution_id, device_ip,
                       duration_ms, status_code
                FROM system_logs
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query_sql, params + [limit, offset])
            
            logs = []
            for row in cursor.fetchall():
                # RealDictCursor already returns dicts
                log_entry = dict(row) if isinstance(row, dict) else dict(zip([desc[0] for desc in cursor.description], row))
                # Convert timestamp to UTC ISO format
                if log_entry.get('timestamp'):
                    ts = log_entry['timestamp']
                    # Convert to UTC if it has timezone info
                    if hasattr(ts, 'astimezone'):
                        ts = ts.astimezone(timezone.utc)
                    log_entry['timestamp'] = ts.isoformat().replace('+00:00', 'Z')
                # Parse JSON details
                if log_entry.get('details'):
                    try:
                        log_entry['details'] = json.loads(log_entry['details'])
                    except:
                        pass
                logs.append(log_entry)
            
            cursor.close()
            
            return {
                'logs': logs,
                'total': total,
                'limit': limit,
                'offset': offset,
            }
            
        except Exception as e:
            return {'logs': [], 'total': 0, 'error': str(e)}
    
    def get_log_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get log statistics for the dashboard."""
        if not self.db_connection:
            return {'error': 'Database not configured'}
        
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            since = now_utc() - timedelta(hours=hours)
            
            # Count by level
            cursor.execute("""
                SELECT level, COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= %s
                GROUP BY level
            """, (since,))
            
            by_level = {row['level']: row['count'] for row in cursor.fetchall()}
            
            # Count by source
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= %s
                GROUP BY source
                ORDER BY count DESC
            """, (since,))
            
            by_source = {row['source']: row['count'] for row in cursor.fetchall()}
            
            # Recent errors
            cursor.execute("""
                SELECT timestamp, source, message
                FROM system_logs
                WHERE timestamp >= %s AND level IN ('ERROR', 'CRITICAL')
                ORDER BY timestamp DESC
                LIMIT 10
            """, (since,))
            
            recent_errors = []
            for row in cursor.fetchall():
                ts = row['timestamp']
                if hasattr(ts, 'astimezone'):
                    ts = ts.astimezone(timezone.utc)
                recent_errors.append({
                    'timestamp': ts.isoformat().replace('+00:00', 'Z'),
                    'source': row['source'],
                    'message': row['message']
                })
            
            cursor.close()
            
            return {
                'period_hours': hours,
                'by_level': by_level,
                'by_source': by_source,
                'recent_errors': recent_errors,
                'total': sum(by_level.values()),
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """Delete logs older than retention period."""
        if not self.db_connection:
            return 0
        
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM system_logs 
                WHERE timestamp < NOW() - INTERVAL '%s days'
            """, (retention_days,))
            deleted = cursor.rowcount
            
            conn.commit()
            cursor.close()
            
            return deleted
            
        except Exception as e:
            logging.error(f"Failed to cleanup old logs: {e}")
            return 0


class ComponentLogger:
    """
    Logger wrapper for a specific component.
    Automatically adds source and provides convenience methods.
    """
    
    def __init__(self, name: str, source: str):
        self.logger = logging.getLogger(name)
        self.source = source
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with extra context."""
        extra = {
            'source': self.source,
            'category': kwargs.pop('category', None),
            'details': kwargs.pop('details', None),
            'job_id': kwargs.pop('job_id', None),
            'workflow_id': kwargs.pop('workflow_id', None),
            'execution_id': kwargs.pop('execution_id', None),
            'device_ip': kwargs.pop('device_ip', None),
            'duration_ms': kwargs.pop('duration_ms', None),
            'status_code': kwargs.pop('status_code', None),
        }
        self.logger.log(level, message, extra=extra, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log an exception with traceback."""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, message, **kwargs)


# Global singleton instance
logging_service = LoggingService()


def get_logger(name: str, source: str = LogSource.SYSTEM) -> ComponentLogger:
    """Convenience function to get a component logger."""
    return logging_service.get_logger(name, source)
