from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    """Application settings with validation"""
    # Environment
    ENV: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_TIMEOUT: int = 30
    
    # GPU Fleet
    DEFAULT_GPU_MEMORY: int = 8000  # MB
    MIN_GPU_MEMORY: int = 4000  # MB
    MAX_JOBS_PER_GPU: int = 4
    SPOT_INSTANCE_MAX_PRICE: float = 1.0  # USD per hour
    
    # GPU Providers
    BASE_GPU_PROVIDER: str = "rune.compute"
    SPOT_GPU_PROVIDER: str = "sfcompute.com"
    
    # Model Cache
    MODEL_CACHE_DIR: str = "./model_cache"
    MAX_MODEL_CACHE_SIZE_GB: int = 100
    
    # Monitoring
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None
    ENABLE_TELEMETRY: bool = True
    
    # Cache
    CACHE_TTL: int = 3600  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the settings
    
    def configure_logging(self) -> None:
        """Configure logging based on environment"""
        log_level = getattr(logging, self.LOG_LEVEL.upper())
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "root": {"handlers": ["console"], "level": log_level},
        }
        
        if self.ENV == Environment.PRODUCTION and self.SENTRY_DSN:
            # Add Sentry logging in production
            import sentry_sdk
            sentry_sdk.init(
                dsn=self.SENTRY_DSN,
                environment=self.ENV,
                traces_sample_rate=1.0,
            )
        
        logging.config.dictConfig(logging_config)

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.configure_logging()
    return settings
