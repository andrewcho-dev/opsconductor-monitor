"""
Metrics Service

Service for storing and retrieving time-series metrics from the database.
Handles optical, interface, path, and availability metrics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Service for managing time-series metrics.
    
    Provides methods for:
    - Storing metrics from polling results
    - Retrieving metrics for dashboards and analysis
    - Aggregating metrics for reporting
    """
    
    def __init__(self, db_config: Dict[str, Any] = None):
        """
        Initialize the metrics service.
        
        Args:
            db_config: Database configuration dict with host, port, database, user, password
        """
        self.db_config = db_config or self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default database configuration from environment."""
        import os
        return {
            'host': os.getenv('PG_HOST', 'localhost'),
            'port': int(os.getenv('PG_PORT', 5432)),
            'database': os.getenv('PG_DATABASE', 'network_scan'),
            'user': os.getenv('PG_USER', 'postgres'),
            'password': os.getenv('PG_PASSWORD', 'postgres'),
        }
    
    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(**self.db_config)
    
    # =========================================================================
    # OPTICAL METRICS
    # =========================================================================
    
    def store_optical_metrics(
        self,
        device_ip: str,
        interface_name: str,
        tx_power: float = None,
        rx_power: float = None,
        temperature: float = None,
        voltage: float = None,
        bias_current: float = None,
        netbox_device_id: int = None,
        site_id: int = None,
        interface_index: int = None,
        recorded_at: datetime = None,
    ) -> int:
        """
        Store optical power metrics for an interface.
        
        Args:
            device_ip: Device IP address
            interface_name: Interface name (e.g., 'GigabitEthernet0/1')
            tx_power: Transmit power in dBm
            rx_power: Receive power in dBm
            temperature: Transceiver temperature in Celsius
            voltage: Transceiver voltage in Volts
            bias_current: Laser bias current in mA
            netbox_device_id: Optional NetBox device ID
            site_id: Optional site ID
            interface_index: Optional SNMP interface index
            recorded_at: Optional timestamp (defaults to now)
        
        Returns:
            ID of inserted record
        """
        sql = """
            INSERT INTO optical_metrics (
                device_ip, interface_name, tx_power, rx_power,
                temperature, voltage, bias_current,
                netbox_device_id, site_id, interface_index, recorded_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    device_ip, interface_name, tx_power, rx_power,
                    temperature, voltage, bias_current,
                    netbox_device_id, site_id, interface_index,
                    recorded_at or datetime.utcnow()
                ))
                result = cur.fetchone()
                conn.commit()
                return result[0]
    
    def store_optical_metrics_batch(
        self,
        metrics: List[Dict[str, Any]],
    ) -> int:
        """
        Store multiple optical metrics in a single batch.
        
        Args:
            metrics: List of metric dicts with keys:
                device_ip, interface_name, tx_power, rx_power, etc.
        
        Returns:
            Number of records inserted
        """
        if not metrics:
            return 0
        
        sql = """
            INSERT INTO optical_metrics (
                device_ip, interface_name, tx_power, rx_power,
                temperature, voltage, bias_current,
                netbox_device_id, site_id, interface_index, recorded_at
            ) VALUES %s
        """
        
        values = [
            (
                m['device_ip'],
                m['interface_name'],
                m.get('tx_power'),
                m.get('rx_power'),
                m.get('temperature'),
                m.get('voltage'),
                m.get('bias_current'),
                m.get('netbox_device_id'),
                m.get('site_id'),
                m.get('interface_index'),
                m.get('recorded_at', datetime.utcnow()),
            )
            for m in metrics
        ]
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
                conn.commit()
                return len(values)
    
    def get_optical_metrics(
        self,
        device_ip: str,
        interface_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get optical metrics for a device.
        
        Args:
            device_ip: Device IP address
            interface_name: Optional interface filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum records to return
        
        Returns:
            List of metric records
        """
        sql = """
            SELECT * FROM optical_metrics
            WHERE device_ip = %s::inet
        """
        params = [device_ip]
        
        if interface_name:
            sql += " AND interface_name = %s"
            params.append(interface_name)
        
        if start_time:
            sql += " AND recorded_at >= %s"
            params.append(start_time)
        
        if end_time:
            sql += " AND recorded_at <= %s"
            params.append(end_time)
        
        sql += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(limit)
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # INTERFACE METRICS
    # =========================================================================
    
    def get_interface_metrics(
        self,
        device_ip: str = None,
        interface_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get interface metrics."""
        sql = "SELECT * FROM interface_metrics WHERE 1=1"
        params = []
        
        if device_ip:
            sql += " AND device_ip = %s::inet"
            params.append(device_ip)
        
        if interface_name:
            sql += " AND interface_name = %s"
            params.append(interface_name)
        
        if start_time:
            sql += " AND recorded_at >= %s"
            params.append(start_time)
        
        if end_time:
            sql += " AND recorded_at <= %s"
            params.append(end_time)
        
        sql += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(limit)
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
    
    def store_interface_metrics(
        self,
        device_ip: str,
        interface_name: str,
        rx_bytes: int = None,
        tx_bytes: int = None,
        rx_bps: int = None,
        tx_bps: int = None,
        rx_errors: int = None,
        tx_errors: int = None,
        oper_status: int = None,
        speed_mbps: int = None,
        netbox_device_id: int = None,
        site_id: int = None,
        recorded_at: datetime = None,
    ) -> int:
        """Store interface traffic metrics."""
        sql = """
            INSERT INTO interface_metrics (
                device_ip, interface_name, rx_bytes, tx_bytes,
                rx_bps, tx_bps, rx_errors, tx_errors,
                oper_status, speed_mbps,
                netbox_device_id, site_id, recorded_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    device_ip, interface_name, rx_bytes, tx_bytes,
                    rx_bps, tx_bps, rx_errors, tx_errors,
                    oper_status, speed_mbps,
                    netbox_device_id, site_id,
                    recorded_at or datetime.utcnow()
                ))
                result = cur.fetchone()
                conn.commit()
                return result[0]
    
    def store_interface_metrics_batch(
        self,
        metrics: List[Dict[str, Any]],
    ) -> int:
        """Store multiple interface metrics in a batch."""
        if not metrics:
            return 0
        
        sql = """
            INSERT INTO interface_metrics (
                device_ip, interface_name, rx_bytes, tx_bytes,
                rx_bps, tx_bps, rx_errors, tx_errors,
                oper_status, speed_mbps,
                netbox_device_id, site_id, recorded_at
            ) VALUES %s
        """
        
        values = [
            (
                m['device_ip'],
                m['interface_name'],
                m.get('rx_bytes'),
                m.get('tx_bytes'),
                m.get('rx_bps'),
                m.get('tx_bps'),
                m.get('rx_errors'),
                m.get('tx_errors'),
                m.get('oper_status'),
                m.get('speed_mbps'),
                m.get('netbox_device_id'),
                m.get('site_id'),
                m.get('recorded_at', datetime.utcnow()),
            )
            for m in metrics
        ]
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
                conn.commit()
                return len(values)
    
    # =========================================================================
    # AVAILABILITY METRICS
    # =========================================================================
    
    def store_availability_metrics(
        self,
        device_ip: str,
        ping_status: str = None,
        snmp_status: str = None,
        ping_latency_ms: float = None,
        snmp_response_ms: float = None,
        uptime_seconds: int = None,
        cpu_utilization_pct: float = None,
        memory_utilization_pct: float = None,
        netbox_device_id: int = None,
        site_id: int = None,
        device_role: str = None,
        recorded_at: datetime = None,
    ) -> int:
        """Store device availability metrics."""
        sql = """
            INSERT INTO availability_metrics (
                device_ip, ping_status, snmp_status,
                ping_latency_ms, snmp_response_ms, uptime_seconds,
                cpu_utilization_pct, memory_utilization_pct,
                netbox_device_id, site_id, device_role, recorded_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    device_ip, ping_status, snmp_status,
                    ping_latency_ms, snmp_response_ms, uptime_seconds,
                    cpu_utilization_pct, memory_utilization_pct,
                    netbox_device_id, site_id, device_role,
                    recorded_at or datetime.utcnow()
                ))
                result = cur.fetchone()
                conn.commit()
                return result[0]
    
    def store_availability_metrics_batch(
        self,
        metrics: List[Dict[str, Any]],
    ) -> int:
        """Store multiple availability metrics in a batch."""
        if not metrics:
            return 0
        
        sql = """
            INSERT INTO availability_metrics (
                device_ip, ping_status, snmp_status,
                ping_latency_ms, snmp_response_ms, uptime_seconds,
                cpu_utilization_pct, memory_utilization_pct,
                netbox_device_id, site_id, device_role, recorded_at
            ) VALUES %s
        """
        
        values = [
            (
                m['device_ip'],
                m.get('ping_status'),
                m.get('snmp_status'),
                m.get('ping_latency_ms'),
                m.get('snmp_response_ms'),
                m.get('uptime_seconds'),
                m.get('cpu_utilization_pct'),
                m.get('memory_utilization_pct'),
                m.get('netbox_device_id'),
                m.get('site_id'),
                m.get('device_role'),
                m.get('recorded_at', datetime.utcnow()),
            )
            for m in metrics
        ]
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
                conn.commit()
                return len(values)
    
    def get_availability_metrics(
        self,
        device_ip: str = None,
        site_id: int = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get availability metrics."""
        sql = "SELECT * FROM availability_metrics WHERE 1=1"
        params = []
        
        if device_ip:
            sql += " AND device_ip = %s::inet"
            params.append(device_ip)
        
        if site_id:
            sql += " AND site_id = %s"
            params.append(site_id)
        
        if start_time:
            sql += " AND recorded_at >= %s"
            params.append(start_time)
        
        if end_time:
            sql += " AND recorded_at <= %s"
            params.append(end_time)
        
        sql += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(limit)
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
    
    # =========================================================================
    # POLL HISTORY
    # =========================================================================
    
    def record_poll_start(
        self,
        job_type: str,
        device_ip: str = None,
    ) -> int:
        """Record the start of a polling job."""
        sql = """
            INSERT INTO poll_history (job_type, device_ip, started_at, status)
            VALUES (%s, %s, %s, 'running')
            RETURNING id
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (job_type, device_ip, datetime.utcnow()))
                result = cur.fetchone()
                conn.commit()
                return result[0]
    
    def record_poll_complete(
        self,
        poll_id: int,
        status: str,
        records_collected: int = 0,
        error_message: str = None,
    ):
        """Record the completion of a polling job."""
        sql = """
            UPDATE poll_history
            SET completed_at = %s,
                duration_ms = EXTRACT(EPOCH FROM (%s - started_at)) * 1000,
                status = %s,
                records_collected = %s,
                error_message = %s
            WHERE id = %s
        """
        
        now = datetime.utcnow()
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (now, now, status, records_collected, error_message, poll_id))
                conn.commit()
    
    # =========================================================================
    # AGGREGATION QUERIES
    # =========================================================================
    
    def get_device_summary(
        self,
        device_ip: str,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get a summary of metrics for a device over the last N hours.
        
        Returns:
            Dict with availability, avg latency, error counts, etc.
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        sql = """
            SELECT
                COUNT(*) as sample_count,
                AVG(CASE WHEN ping_status = 'up' THEN 1 ELSE 0 END) * 100 as availability_pct,
                AVG(ping_latency_ms) as avg_latency_ms,
                MIN(ping_latency_ms) as min_latency_ms,
                MAX(ping_latency_ms) as max_latency_ms,
                MAX(uptime_seconds) as uptime_seconds,
                AVG(cpu_utilization_pct) as avg_cpu_pct,
                AVG(memory_utilization_pct) as avg_memory_pct
            FROM availability_metrics
            WHERE device_ip = %s AND recorded_at >= %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (device_ip, start_time))
                row = cur.fetchone()
                return dict(row) if row else {}
    
    def get_site_summary(
        self,
        site_id: int,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Get a summary of metrics for a site."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        sql = """
            SELECT
                COUNT(DISTINCT device_ip) as device_count,
                AVG(CASE WHEN ping_status = 'up' THEN 1 ELSE 0 END) * 100 as avg_availability_pct,
                AVG(ping_latency_ms) as avg_latency_ms,
                COUNT(DISTINCT CASE WHEN ping_status = 'up' THEN device_ip END) as devices_up,
                COUNT(DISTINCT CASE WHEN ping_status != 'up' THEN device_ip END) as devices_down
            FROM availability_metrics
            WHERE site_id = %s AND recorded_at >= %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (site_id, start_time))
                row = cur.fetchone()
                return dict(row) if row else {}


# Singleton instance
_metrics_service = None

def get_metrics_service() -> MetricsService:
    """Get the singleton metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
