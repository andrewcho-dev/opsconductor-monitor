"""
Connector Manager

Manages lifecycle of connectors that need to run as background services
(e.g., SNMP trap receiver).
"""

import logging
from typing import Optional

from backend.database import DatabaseConnection
from backend.connectors.registry import create_connector

logger = logging.getLogger(__name__)

# Global reference to running trap connector
_snmp_trap_connector = None


async def start_snmp_trap_receiver():
    """
    Start the SNMP trap receiver if enabled in database.
    
    Returns:
        SNMPTrapConnector instance if started, None otherwise
    """
    global _snmp_trap_connector
    
    db = DatabaseConnection()
    
    try:
        # Check if SNMP trap connector is enabled
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, type, config, enabled
                FROM connectors
                WHERE type = 'snmp_trap'
                LIMIT 1
            """)
            row = cursor.fetchone()
        
        if not row:
            logger.info("No SNMP trap connector configured")
            return None
        
        if not row.get('enabled'):
            logger.info("SNMP trap connector is disabled")
            return None
        
        config = dict(row.get('config') or {})
        config['connector_id'] = str(row['id'])
        config['connector_name'] = row['name']
        
        # Create and start the connector
        connector = create_connector('snmp_trap', config)
        if not connector:
            logger.error("Failed to create SNMP trap connector")
            return None
        
        await connector.start()
        _snmp_trap_connector = connector
        
        # Update connector status in database
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE connectors
                SET status = 'connected',
                    error_message = NULL,
                    updated_at = NOW()
                WHERE id = %s
            """, (row['id'],))
            db.get_connection().commit()
        
        logger.info(f"SNMP trap receiver started on port {config.get('port', 162)}")
        return connector
        
    except Exception as e:
        logger.error(f"Failed to start SNMP trap receiver: {e}")
        
        # Update error status
        if row:
            try:
                with db.cursor() as cursor:
                    cursor.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            error_message = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (str(e), row['id']))
                    db.get_connection().commit()
            except:
                pass
        
        return None


async def stop_snmp_trap_receiver():
    """Stop the SNMP trap receiver if running."""
    global _snmp_trap_connector
    
    if _snmp_trap_connector:
        try:
            await _snmp_trap_connector.stop()
            logger.info("SNMP trap receiver stopped")
        except Exception as e:
            logger.error(f"Error stopping SNMP trap receiver: {e}")
        finally:
            _snmp_trap_connector = None


def get_snmp_trap_connector():
    """Get the running SNMP trap connector instance."""
    return _snmp_trap_connector
