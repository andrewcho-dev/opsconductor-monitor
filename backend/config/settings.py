"""
Application settings and configuration management.

Centralizes all configuration with environment variable support.
"""

import os
from typing import Optional
from functools import lru_cache


class Settings:
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults and can be overridden via environment.
    """
    
    def __init__(self):
        # Database settings
        self.db_host: str = os.getenv('PG_HOST', 'localhost')
        self.db_port: int = int(os.getenv('PG_PORT', '5432'))
        self.db_name: str = os.getenv('PG_DATABASE', 'network_scan')
        self.db_user: str = os.getenv('PG_USER', 'postgres')
        self.db_password: str = os.getenv('PG_PASSWORD', 'postgres')
        
        # Redis settings
        self.redis_host: str = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db: int = int(os.getenv('REDIS_DB', '0'))
        self.redis_password: Optional[str] = os.getenv('REDIS_PASSWORD')
        
        # Celery settings
        self.celery_broker_url: str = os.getenv(
            'CELERY_BROKER_URL', 
            f'redis://{self.redis_host}:{self.redis_port}/{self.redis_db}'
        )
        self.celery_result_backend: str = os.getenv(
            'CELERY_RESULT_BACKEND',
            f'redis://{self.redis_host}:{self.redis_port}/{self.redis_db}'
        )
        
        # Application settings
        self.debug: bool = os.getenv('DEBUG', 'false').lower() == 'true'
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        self.secret_key: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        
        # SSH settings
        self.ssh_default_username: str = os.getenv('SSH_DEFAULT_USERNAME', '')
        self.ssh_default_password: str = os.getenv('SSH_DEFAULT_PASSWORD', '')
        self.ssh_default_port: int = int(os.getenv('SSH_DEFAULT_PORT', '22'))
        self.ssh_default_timeout: int = int(os.getenv('SSH_DEFAULT_TIMEOUT', '30'))
        
        # SNMP settings
        self.snmp_default_community: str = os.getenv('SNMP_DEFAULT_COMMUNITY', 'public')
        self.snmp_default_version: str = os.getenv('SNMP_DEFAULT_VERSION', '2c')
        self.snmp_default_timeout: int = int(os.getenv('SNMP_DEFAULT_TIMEOUT', '5'))
        
        # Job execution settings
        self.job_default_timeout: int = int(os.getenv('JOB_DEFAULT_TIMEOUT', '300'))
        self.job_max_parallel: int = int(os.getenv('JOB_MAX_PARALLEL', '10'))
        self.job_batch_size: int = int(os.getenv('JOB_BATCH_SIZE', '20'))
        self.job_retry_attempts: int = int(os.getenv('JOB_RETRY_ATTEMPTS', '2'))
        
        # Data retention settings
        self.execution_history_days: int = int(os.getenv('EXECUTION_HISTORY_DAYS', '30'))
        self.optical_history_days: int = int(os.getenv('OPTICAL_HISTORY_DAYS', '90'))
        self.log_retention_days: int = int(os.getenv('LOG_RETENTION_DAYS', '7'))
        
        # Scheduler settings
        self.scheduler_stale_timeout: int = int(os.getenv('SCHEDULER_STALE_TIMEOUT', '600'))
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f'postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f'redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}'
        return f'redis://{self.redis_host}:{self.redis_port}/{self.redis_db}'
    
    def to_dict(self) -> dict:
        """
        Convert settings to dictionary (excluding sensitive values).
        
        Returns:
            Dictionary of non-sensitive settings
        """
        return {
            'db_host': self.db_host,
            'db_port': self.db_port,
            'db_name': self.db_name,
            'redis_host': self.redis_host,
            'redis_port': self.redis_port,
            'debug': self.debug,
            'log_level': self.log_level,
            'ssh_default_port': self.ssh_default_port,
            'ssh_default_timeout': self.ssh_default_timeout,
            'snmp_default_version': self.snmp_default_version,
            'snmp_default_timeout': self.snmp_default_timeout,
            'job_default_timeout': self.job_default_timeout,
            'job_max_parallel': self.job_max_parallel,
            'job_batch_size': self.job_batch_size,
            'execution_history_days': self.execution_history_days,
            'optical_history_days': self.optical_history_days,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance (cached)
    """
    return Settings()
