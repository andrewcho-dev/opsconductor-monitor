"""
Metrics API Endpoints

REST API for accessing time-series metrics data.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging

from ..services.metrics_service import get_metrics_service

logger = logging.getLogger(__name__)

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@metrics_bp.route('/optical', methods=['GET'])
def get_optical_metrics():
    """
    Get optical power metrics.
    
    Query params:
        device_ip: Required - Device IP address
        interface: Optional - Interface name filter
        hours: Optional - Hours of data (default 24)
        limit: Optional - Max records (default 100)
    """
    device_ip = request.args.get('device_ip')
    if not device_ip:
        return jsonify({'error': 'device_ip is required'}), 400
    
    interface = request.args.get('interface')
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 100))
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    try:
        service = get_metrics_service()
        metrics = service.get_optical_metrics(
            device_ip=device_ip,
            interface_name=interface,
            start_time=start_time,
            limit=limit,
        )
        
        # Convert datetime objects to ISO format
        for m in metrics:
            if 'recorded_at' in m and m['recorded_at']:
                m['recorded_at'] = m['recorded_at'].isoformat()
        
        return jsonify({
            'device_ip': device_ip,
            'count': len(metrics),
            'metrics': metrics,
        })
    except Exception as e:
        logger.error(f"Error getting optical metrics: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/optical', methods=['POST'])
def store_optical_metrics():
    """
    Store optical power metrics.
    
    Body (single):
        device_ip, interface_name, tx_power, rx_power, etc.
    
    Body (batch):
        metrics: List of metric objects
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        service = get_metrics_service()
        
        if 'metrics' in data:
            # Batch insert
            count = service.store_optical_metrics_batch(data['metrics'])
            return jsonify({'inserted': count})
        else:
            # Single insert
            record_id = service.store_optical_metrics(
                device_ip=data['device_ip'],
                interface_name=data['interface_name'],
                tx_power=data.get('tx_power'),
                rx_power=data.get('rx_power'),
                temperature=data.get('temperature'),
                voltage=data.get('voltage'),
                bias_current=data.get('bias_current'),
                netbox_device_id=data.get('netbox_device_id'),
                site_id=data.get('site_id'),
            )
            return jsonify({'id': record_id})
    except Exception as e:
        logger.error(f"Error storing optical metrics: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/availability', methods=['GET'])
def get_availability_metrics():
    """
    Get device availability metrics.
    
    Query params:
        device_ip: Optional - Device IP address
        site_id: Optional - Site ID
        hours: Optional - Hours of data (default 24)
        limit: Optional - Max records (default 100)
    """
    device_ip = request.args.get('device_ip')
    site_id = request.args.get('site_id', type=int)
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 100))
    
    if not device_ip and not site_id:
        return jsonify({'error': 'device_ip or site_id is required'}), 400
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    try:
        service = get_metrics_service()
        metrics = service.get_availability_metrics(
            device_ip=device_ip,
            site_id=site_id,
            start_time=start_time,
            limit=limit,
        )
        
        for m in metrics:
            if 'recorded_at' in m and m['recorded_at']:
                m['recorded_at'] = m['recorded_at'].isoformat()
        
        return jsonify({
            'device_ip': device_ip,
            'site_id': site_id,
            'count': len(metrics),
            'metrics': metrics,
        })
    except Exception as e:
        logger.error(f"Error getting availability metrics: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/availability', methods=['POST'])
def store_availability_metrics():
    """Store availability metrics."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        service = get_metrics_service()
        
        if 'metrics' in data:
            count = service.store_availability_metrics_batch(data['metrics'])
            return jsonify({'inserted': count})
        else:
            record_id = service.store_availability_metrics(
                device_ip=data['device_ip'],
                ping_status=data.get('ping_status'),
                snmp_status=data.get('snmp_status'),
                ping_latency_ms=data.get('ping_latency_ms'),
                snmp_response_ms=data.get('snmp_response_ms'),
                uptime_seconds=data.get('uptime_seconds'),
                cpu_utilization_pct=data.get('cpu_utilization_pct'),
                memory_utilization_pct=data.get('memory_utilization_pct'),
                netbox_device_id=data.get('netbox_device_id'),
                site_id=data.get('site_id'),
                device_role=data.get('device_role'),
            )
            return jsonify({'id': record_id})
    except Exception as e:
        logger.error(f"Error storing availability metrics: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/interface', methods=['POST'])
def store_interface_metrics():
    """Store interface metrics."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        service = get_metrics_service()
        
        if 'metrics' in data:
            count = service.store_interface_metrics_batch(data['metrics'])
            return jsonify({'inserted': count})
        else:
            record_id = service.store_interface_metrics(
                device_ip=data['device_ip'],
                interface_name=data['interface_name'],
                rx_bytes=data.get('rx_bytes'),
                tx_bytes=data.get('tx_bytes'),
                rx_bps=data.get('rx_bps'),
                tx_bps=data.get('tx_bps'),
                rx_errors=data.get('rx_errors'),
                tx_errors=data.get('tx_errors'),
                oper_status=data.get('oper_status'),
                speed_mbps=data.get('speed_mbps'),
                netbox_device_id=data.get('netbox_device_id'),
                site_id=data.get('site_id'),
            )
            return jsonify({'id': record_id})
    except Exception as e:
        logger.error(f"Error storing interface metrics: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/device/<device_ip>/summary', methods=['GET'])
def get_device_summary(device_ip):
    """
    Get a summary of metrics for a device.
    
    Query params:
        hours: Optional - Hours of data (default 24)
    """
    hours = int(request.args.get('hours', 24))
    
    try:
        service = get_metrics_service()
        summary = service.get_device_summary(device_ip, hours)
        
        return jsonify({
            'device_ip': device_ip,
            'hours': hours,
            'summary': summary,
        })
    except Exception as e:
        logger.error(f"Error getting device summary: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/site/<int:site_id>/summary', methods=['GET'])
def get_site_summary(site_id):
    """
    Get a summary of metrics for a site.
    
    Query params:
        hours: Optional - Hours of data (default 24)
    """
    hours = int(request.args.get('hours', 24))
    
    try:
        service = get_metrics_service()
        summary = service.get_site_summary(site_id, hours)
        
        return jsonify({
            'site_id': site_id,
            'hours': hours,
            'summary': summary,
        })
    except Exception as e:
        logger.error(f"Error getting site summary: {e}")
        return jsonify({'error': str(e)}), 500
