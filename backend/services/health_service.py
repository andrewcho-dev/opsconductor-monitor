"""
Health Score Service

Calculates and stores health scores for devices, sites, and the network.
Health scores are composite metrics that provide an at-a-glance view of
network health for dashboards and alerting.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service for calculating and managing health scores.
    
    Health scores are calculated based on:
    - Availability (ping/SNMP responsiveness)
    - Performance (latency, throughput)
    - Errors (interface errors, packet loss)
    - Capacity (utilization headroom)
    """
    
    # Weights for health score components
    WEIGHTS = {
        'availability': 0.40,
        'performance': 0.25,
        'errors': 0.20,
        'capacity': 0.15,
    }
    
    def __init__(self, db_config: Dict[str, Any] = None):
        """Initialize the health service."""
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
    
    def calculate_device_health(
        self,
        device_ip: str,
        hours: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculate health score for a single device.
        
        Args:
            device_ip: Device IP address
            hours: Hours of data to consider
        
        Returns:
            Dict with health scores and component breakdowns
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get availability metrics
        availability_score = self._calculate_availability_score(device_ip, start_time)
        
        # Get performance metrics (latency-based)
        performance_score = self._calculate_performance_score(device_ip, start_time)
        
        # Get error metrics
        error_score = self._calculate_error_score(device_ip, start_time)
        
        # Get capacity metrics
        capacity_score = self._calculate_capacity_score(device_ip, start_time)
        
        # Calculate overall score
        overall_score = (
            availability_score * self.WEIGHTS['availability'] +
            performance_score * self.WEIGHTS['performance'] +
            error_score * self.WEIGHTS['errors'] +
            capacity_score * self.WEIGHTS['capacity']
        )
        
        return {
            'device_ip': device_ip,
            'overall_score': round(overall_score, 2),
            'availability_score': round(availability_score, 2),
            'performance_score': round(performance_score, 2),
            'error_score': round(error_score, 2),
            'capacity_score': round(capacity_score, 2),
            'calculated_at': datetime.utcnow(),
        }
    
    def _calculate_availability_score(
        self,
        device_ip: str,
        start_time: datetime,
    ) -> float:
        """Calculate availability score (0-100)."""
        sql = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN ping_status = 'up' THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN snmp_status = 'up' THEN 1 ELSE 0 END) as snmp_up_count
            FROM availability_metrics
            WHERE device_ip = %s AND recorded_at >= %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (device_ip, start_time))
                row = cur.fetchone()
                
                if not row or row['total'] == 0:
                    return 100.0  # No data = assume healthy
                
                ping_pct = (row['up_count'] / row['total']) * 100
                snmp_pct = (row['snmp_up_count'] / row['total']) * 100 if row['snmp_up_count'] else ping_pct
                
                # Weight ping more heavily
                return ping_pct * 0.7 + snmp_pct * 0.3
    
    def _calculate_performance_score(
        self,
        device_ip: str,
        start_time: datetime,
    ) -> float:
        """Calculate performance score based on latency (0-100)."""
        sql = """
            SELECT
                AVG(ping_latency_ms) as avg_latency,
                MAX(ping_latency_ms) as max_latency,
                STDDEV(ping_latency_ms) as latency_stddev
            FROM availability_metrics
            WHERE device_ip = %s AND recorded_at >= %s AND ping_latency_ms IS NOT NULL
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (device_ip, start_time))
                row = cur.fetchone()
                
                if not row or row['avg_latency'] is None:
                    return 100.0  # No data = assume healthy
                
                avg_latency = float(row['avg_latency'])
                
                # Score based on latency thresholds
                # < 10ms = 100, 10-50ms = 90-100, 50-100ms = 70-90, 100-500ms = 30-70, > 500ms = 0-30
                if avg_latency < 10:
                    return 100.0
                elif avg_latency < 50:
                    return 90 + (50 - avg_latency) / 40 * 10
                elif avg_latency < 100:
                    return 70 + (100 - avg_latency) / 50 * 20
                elif avg_latency < 500:
                    return 30 + (500 - avg_latency) / 400 * 40
                else:
                    return max(0, 30 - (avg_latency - 500) / 500 * 30)
    
    def _calculate_error_score(
        self,
        device_ip: str,
        start_time: datetime,
    ) -> float:
        """Calculate error score based on interface errors (0-100, higher = fewer errors)."""
        sql = """
            SELECT
                SUM(COALESCE(rx_errors, 0) + COALESCE(tx_errors, 0)) as total_errors,
                SUM(COALESCE(rx_packets, 0) + COALESCE(tx_packets, 0)) as total_packets
            FROM interface_metrics
            WHERE device_ip = %s AND recorded_at >= %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (device_ip, start_time))
                row = cur.fetchone()
                
                if not row or row['total_packets'] is None or row['total_packets'] == 0:
                    return 100.0  # No data = assume healthy
                
                error_rate = row['total_errors'] / row['total_packets']
                
                # Score based on error rate
                # 0% = 100, 0.001% = 95, 0.01% = 80, 0.1% = 50, 1% = 0
                if error_rate == 0:
                    return 100.0
                elif error_rate < 0.00001:
                    return 95 + (0.00001 - error_rate) / 0.00001 * 5
                elif error_rate < 0.0001:
                    return 80 + (0.0001 - error_rate) / 0.00009 * 15
                elif error_rate < 0.001:
                    return 50 + (0.001 - error_rate) / 0.0009 * 30
                elif error_rate < 0.01:
                    return max(0, 50 - (error_rate - 0.001) / 0.009 * 50)
                else:
                    return 0.0
    
    def _calculate_capacity_score(
        self,
        device_ip: str,
        start_time: datetime,
    ) -> float:
        """Calculate capacity score based on utilization (0-100, higher = more headroom)."""
        sql = """
            SELECT
                AVG(GREATEST(COALESCE(rx_utilization_pct, 0), COALESCE(tx_utilization_pct, 0))) as avg_util,
                MAX(GREATEST(COALESCE(rx_utilization_pct, 0), COALESCE(tx_utilization_pct, 0))) as max_util
            FROM interface_metrics
            WHERE device_ip = %s AND recorded_at >= %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (device_ip, start_time))
                row = cur.fetchone()
                
                if not row or row['avg_util'] is None:
                    return 100.0  # No data = assume healthy
                
                avg_util = float(row['avg_util'])
                max_util = float(row['max_util']) if row['max_util'] else avg_util
                
                # Score based on utilization (inverse - lower util = higher score)
                # < 50% = 100, 50-70% = 80-100, 70-85% = 50-80, 85-95% = 20-50, > 95% = 0-20
                if avg_util < 50:
                    return 100.0
                elif avg_util < 70:
                    return 80 + (70 - avg_util) / 20 * 20
                elif avg_util < 85:
                    return 50 + (85 - avg_util) / 15 * 30
                elif avg_util < 95:
                    return 20 + (95 - avg_util) / 10 * 30
                else:
                    return max(0, 20 - (avg_util - 95) / 5 * 20)
    
    def store_health_score(
        self,
        device_ip: str,
        scores: Dict[str, Any],
        netbox_device_id: int = None,
        site_id: int = None,
    ) -> int:
        """Store a calculated health score."""
        sql = """
            INSERT INTO health_scores (
                scope_type, device_ip, netbox_device_id, site_id,
                overall_score, availability_score, performance_score,
                error_score, capacity_score, calculated_at
            ) VALUES (
                'device', %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    device_ip, netbox_device_id, site_id,
                    scores.get('overall_score'),
                    scores.get('availability_score'),
                    scores.get('performance_score'),
                    scores.get('error_score'),
                    scores.get('capacity_score'),
                    scores.get('calculated_at', datetime.utcnow()),
                ))
                result = cur.fetchone()
                conn.commit()
                return result[0]
    
    def get_device_health(
        self,
        device_ip: str,
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get the most recent health scores for a device."""
        sql = """
            SELECT * FROM health_scores
            WHERE device_ip = %s AND scope_type = 'device'
            ORDER BY calculated_at DESC
            LIMIT %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (device_ip, limit))
                return [dict(row) for row in cur.fetchall()]
    
    def get_site_health(
        self,
        site_id: int,
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get the most recent health scores for a site."""
        sql = """
            SELECT * FROM health_scores
            WHERE site_id = %s AND scope_type = 'site'
            ORDER BY calculated_at DESC
            LIMIT %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (site_id, limit))
                return [dict(row) for row in cur.fetchall()]
    
    def calculate_and_store_all_device_health(self) -> int:
        """
        Calculate and store health scores for all devices with recent metrics.
        
        Returns:
            Number of devices processed
        """
        # Get all devices with recent availability metrics
        sql = """
            SELECT DISTINCT device_ip, netbox_device_id, site_id
            FROM availability_metrics
            WHERE recorded_at >= NOW() - INTERVAL '1 hour'
        """
        
        count = 0
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                devices = cur.fetchall()
        
        for device in devices:
            try:
                scores = self.calculate_device_health(device['device_ip'])
                self.store_health_score(
                    device['device_ip'],
                    scores,
                    netbox_device_id=device.get('netbox_device_id'),
                    site_id=device.get('site_id'),
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to calculate health for {device['device_ip']}: {e}")
        
        return count
    
    def get_network_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of network health across all devices.
        
        Returns:
            Dict with overall health metrics
        """
        sql = """
            WITH latest_scores AS (
                SELECT DISTINCT ON (device_ip)
                    device_ip, overall_score, availability_score,
                    performance_score, error_score, capacity_score
                FROM health_scores
                WHERE scope_type = 'device'
                    AND calculated_at >= NOW() - INTERVAL '1 hour'
                ORDER BY device_ip, calculated_at DESC
            )
            SELECT
                COUNT(*) as device_count,
                AVG(overall_score) as avg_health,
                MIN(overall_score) as min_health,
                MAX(overall_score) as max_health,
                AVG(availability_score) as avg_availability,
                AVG(performance_score) as avg_performance,
                AVG(error_score) as avg_error_score,
                AVG(capacity_score) as avg_capacity,
                SUM(CASE WHEN overall_score >= 90 THEN 1 ELSE 0 END) as healthy_count,
                SUM(CASE WHEN overall_score >= 70 AND overall_score < 90 THEN 1 ELSE 0 END) as warning_count,
                SUM(CASE WHEN overall_score < 70 THEN 1 ELSE 0 END) as critical_count
            FROM latest_scores
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                row = cur.fetchone()
                return dict(row) if row else {}


# Singleton instance
_health_service = None

def get_health_service() -> HealthService:
    """Get the singleton health service instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
