"""
Daily Reset Tasks

Tasks that run once per day to reset counters.
"""

import logging
from datetime import datetime

from celery import Celery
from backend.utils.db import db_execute

logger = logging.getLogger(__name__)

# Get Celery app
from celery_app import celery_app


@celery_app.task(bind=True, name="reset_daily_alert_counters")
def reset_daily_alert_counters(self):
    """
    Reset daily alert counters for all connectors.
    
    Runs at midnight to reset the alerts_today counter.
    """
    logger.info("Resetting daily alert counters")
    
    try:
        result = db_execute("""
            UPDATE connectors 
            SET alerts_today = 0
        """)
        
        logger.info(f"Reset daily counters for {result} connectors")
        return {"reset": result}
        
    except Exception as e:
        logger.error(f"Error resetting daily counters: {e}")
        return {"error": str(e)}
