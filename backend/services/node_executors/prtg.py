"""
PRTG Node Executors

Workflow node executors for PRTG Network Monitor integration.
"""

import logging
from typing import Dict, Any

from backend.services.prtg_service import PRTGService

logger = logging.getLogger(__name__)


class PRTGGetDevicesExecutor:
    """Get devices from PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            devices = service.get_devices(
                group=params.get('group'),
                status=params.get('status'),
                search=params.get('search')
            )
            
            return {
                'success': True,
                'outputs': {
                    'devices': devices,
                    'count': len(devices)
                }
            }
        except Exception as e:
            logger.error(f"Error getting PRTG devices: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'devices': [],
                    'count': 0
                }
            }


class PRTGGetSensorsExecutor:
    """Get sensors from PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            device_id = params.get('device_id')
            if device_id:
                device_id = int(device_id)
            
            sensors = service.get_sensors(
                device_id=device_id,
                status=params.get('status'),
                sensor_type=params.get('sensor_type')
            )
            
            return {
                'success': True,
                'outputs': {
                    'sensors': sensors,
                    'count': len(sensors)
                }
            }
        except Exception as e:
            logger.error(f"Error getting PRTG sensors: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'sensors': [],
                    'count': 0
                }
            }


class PRTGGetSensorDetailsExecutor:
    """Get detailed sensor information."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            sensor_id = int(params.get('sensor_id'))
            sensor = service.get_sensor_details(sensor_id)
            
            return {
                'success': True,
                'outputs': {
                    'sensor': sensor,
                    'channels': sensor.get('channels', [])
                }
            }
        except Exception as e:
            logger.error(f"Error getting sensor details: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'sensor': None,
                    'channels': []
                }
            }


class PRTGGetAlertsExecutor:
    """Get current alerts from PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            alerts = service.get_alerts(status=params.get('status'))
            
            return {
                'success': True,
                'outputs': {
                    'alerts': alerts,
                    'count': len(alerts)
                }
            }
        except Exception as e:
            logger.error(f"Error getting PRTG alerts: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'alerts': [],
                    'count': 0
                }
            }


class PRTGGetGroupsExecutor:
    """Get device groups from PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            groups = service.get_groups()
            
            return {
                'success': True,
                'outputs': {
                    'groups': groups,
                    'count': len(groups)
                }
            }
        except Exception as e:
            logger.error(f"Error getting PRTG groups: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'groups': [],
                    'count': 0
                }
            }


class PRTGGetSensorHistoryExecutor:
    """Get historical data for a sensor."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            sensor_id = int(params.get('sensor_id'))
            result = service.get_sensor_history(
                sensor_id=sensor_id,
                start_date=params.get('start_date'),
                end_date=params.get('end_date'),
                avg=params.get('avg', 0)
            )
            
            return {
                'success': True,
                'outputs': {
                    'history': result.get('histdata', []),
                    'channels': result.get('channels', [])
                }
            }
        except Exception as e:
            logger.error(f"Error getting sensor history: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'history': [],
                    'channels': []
                }
            }


class PRTGAcknowledgeAlarmExecutor:
    """Acknowledge an alarm in PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            sensor_id = int(params.get('sensor_id'))
            message = params.get('message', 'Acknowledged by OpsConductor workflow')
            
            success = service.acknowledge_alarm(sensor_id, message)
            
            return {
                'success': success,
                'outputs': {
                    'success': success
                }
            }
        except Exception as e:
            logger.error(f"Error acknowledging alarm: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'success': False
                }
            }


class PRTGPauseObjectExecutor:
    """Pause a sensor, device, or group in PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            object_id = int(params.get('object_id'))
            duration = params.get('duration')
            if duration:
                duration = int(duration)
            message = params.get('message', 'Paused by OpsConductor workflow')
            
            success = service.pause_object(object_id, duration, message)
            
            return {
                'success': success,
                'outputs': {
                    'success': success
                }
            }
        except Exception as e:
            logger.error(f"Error pausing object: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'success': False
                }
            }


class PRTGResumeObjectExecutor:
    """Resume a paused object in PRTG."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            object_id = int(params.get('object_id'))
            success = service.resume_object(object_id)
            
            return {
                'success': success,
                'outputs': {
                    'success': success
                }
            }
        except Exception as e:
            logger.error(f"Error resuming object: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'success': False
                }
            }


class PRTGSyncToNetBoxExecutor:
    """Sync PRTG devices to NetBox."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            result = service.sync_to_netbox(
                dry_run=params.get('dry_run', True),
                device_ids=params.get('device_ids'),
                default_site=params.get('default_site'),
                default_role=params.get('default_role'),
                update_existing=params.get('update_existing', False),
                create_missing=params.get('create_missing', True)
            )
            
            return {
                'success': True,
                'outputs': {
                    'processed': result.get('processed', 0),
                    'created': result.get('created', 0),
                    'updated': result.get('updated', 0),
                    'skipped': result.get('skipped', 0),
                    'errors': result.get('errors', []),
                    'details': result.get('details', [])
                }
            }
        except Exception as e:
            logger.error(f"Error syncing to NetBox: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'processed': 0,
                    'created': 0,
                    'updated': 0,
                    'skipped': 0,
                    'errors': [{'error': str(e)}],
                    'details': []
                }
            }


class PRTGPreviewSyncExecutor:
    """Preview what would be synced to NetBox."""
    
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            service = PRTGService()
            
            result = service.preview_netbox_sync()
            
            return {
                'success': True,
                'outputs': {
                    'total_prtg_devices': result.get('total_prtg_devices', 0),
                    'existing_in_netbox': result.get('existing_in_netbox', 0),
                    'to_create': result.get('to_create', 0),
                    'devices_to_create': result.get('devices_to_create', []),
                    'devices_existing': result.get('devices_existing', [])
                }
            }
        except Exception as e:
            logger.error(f"Error previewing sync: {e}")
            return {
                'success': False,
                'error': str(e),
                'outputs': {
                    'total_prtg_devices': 0,
                    'existing_in_netbox': 0,
                    'to_create': 0,
                    'devices_to_create': [],
                    'devices_existing': []
                }
            }


# Executor registry for PRTG nodes
PRTG_EXECUTORS = {
    'prtg.get_devices': PRTGGetDevicesExecutor(),
    'prtg.get_sensors': PRTGGetSensorsExecutor(),
    'prtg.get_sensor_details': PRTGGetSensorDetailsExecutor(),
    'prtg.get_alerts': PRTGGetAlertsExecutor(),
    'prtg.get_groups': PRTGGetGroupsExecutor(),
    'prtg.get_sensor_history': PRTGGetSensorHistoryExecutor(),
    'prtg.acknowledge_alarm': PRTGAcknowledgeAlarmExecutor(),
    'prtg.pause_object': PRTGPauseObjectExecutor(),
    'prtg.resume_object': PRTGResumeObjectExecutor(),
    'prtg.sync_to_netbox': PRTGSyncToNetBoxExecutor(),
    'prtg.preview_sync': PRTGPreviewSyncExecutor(),
}
