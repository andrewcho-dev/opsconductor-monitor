"""
Health API Endpoints

REST API for accessing health scores and network health data.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from ..services.health_service import get_health_service

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/api/health')


@health_bp.route('/status', methods=['GET'])
def health_status():
    """
    Get overall API health status.
    
    Returns basic health check for the API itself.
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'opsconductor-api',
    })


@health_bp.route('/device/<device_ip>', methods=['GET'])
def get_device_health(device_ip):
    """
    Get health score for a specific device.
    
    Query params:
        calculate: Optional - If true, calculate fresh score (default false)
        history: Optional - Number of historical scores to return (default 1)
    """
    calculate = request.args.get('calculate', 'false').lower() == 'true'
    history = int(request.args.get('history', 1))
    
    try:
        service = get_health_service()
        
        if calculate:
            # Calculate fresh health score
            scores = service.calculate_device_health(device_ip)
            # Store it
            service.store_health_score(device_ip, scores)
            return jsonify({
                'device_ip': device_ip,
                'calculated': True,
                'health': scores,
            })
        else:
            # Get stored health scores
            scores = service.get_device_health(device_ip, limit=history)
            
            # Convert datetime objects
            for s in scores:
                if 'calculated_at' in s and s['calculated_at']:
                    s['calculated_at'] = s['calculated_at'].isoformat()
            
            return jsonify({
                'device_ip': device_ip,
                'calculated': False,
                'count': len(scores),
                'health': scores[0] if scores else None,
                'history': scores if history > 1 else None,
            })
    except Exception as e:
        logger.error(f"Error getting device health: {e}")
        return jsonify({'error': str(e)}), 500


@health_bp.route('/device/<device_ip>/calculate', methods=['POST'])
def calculate_device_health(device_ip):
    """
    Calculate and store a fresh health score for a device.
    
    Body (optional):
        hours: Hours of data to consider (default 1)
    """
    data = request.get_json() or {}
    hours = data.get('hours', 1)
    
    try:
        service = get_health_service()
        scores = service.calculate_device_health(device_ip, hours=hours)
        
        # Store the score
        record_id = service.store_health_score(
            device_ip,
            scores,
            netbox_device_id=data.get('netbox_device_id'),
            site_id=data.get('site_id'),
        )
        
        return jsonify({
            'device_ip': device_ip,
            'id': record_id,
            'health': scores,
        })
    except Exception as e:
        logger.error(f"Error calculating device health: {e}")
        return jsonify({'error': str(e)}), 500


@health_bp.route('/site/<int:site_id>', methods=['GET'])
def get_site_health(site_id):
    """
    Get health score for a site.
    
    Query params:
        history: Optional - Number of historical scores to return (default 1)
    """
    history = int(request.args.get('history', 1))
    
    try:
        service = get_health_service()
        scores = service.get_site_health(site_id, limit=history)
        
        for s in scores:
            if 'calculated_at' in s and s['calculated_at']:
                s['calculated_at'] = s['calculated_at'].isoformat()
        
        return jsonify({
            'site_id': site_id,
            'count': len(scores),
            'health': scores[0] if scores else None,
            'history': scores if history > 1 else None,
        })
    except Exception as e:
        logger.error(f"Error getting site health: {e}")
        return jsonify({'error': str(e)}), 500


@health_bp.route('/network', methods=['GET'])
def get_network_health():
    """
    Get overall network health summary.
    
    Returns aggregated health metrics across all devices.
    """
    try:
        service = get_health_service()
        summary = service.get_network_health_summary()
        
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'summary': summary,
        })
    except Exception as e:
        logger.error(f"Error getting network health: {e}")
        return jsonify({'error': str(e)}), 500


@health_bp.route('/calculate-all', methods=['POST'])
def calculate_all_health():
    """
    Calculate and store health scores for all devices with recent metrics.
    
    This is typically called by a scheduled job.
    """
    try:
        service = get_health_service()
        count = service.calculate_and_store_all_device_health()
        
        return jsonify({
            'status': 'ok',
            'devices_processed': count,
            'timestamp': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f"Error calculating all health scores: {e}")
        return jsonify({'error': str(e)}), 500
