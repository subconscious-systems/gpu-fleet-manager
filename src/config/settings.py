"""
Configuration Management System for GPU Fleet Manager

This module provides a centralized configuration system using Pydantic for type validation
and environment variable loading with sensible defaults.
"""

import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from pydantic import BaseSettings, Field, SecretStr, validator, PostgresDsn, AnyHttpUrl
from functools import lru_cache
import json

class DatabaseSettings(BaseSettings):
    """Database connection settings"""
    host: str = Field(..., env="POSTGRES_HOST")
    port: int = Field(5432, env="POSTGRES_PORT")
    username: str = Field(..., env="POSTGRES_USER")
    password: SecretStr = Field(..., env="POSTGRES_PASSWORD")
    database: str = Field(..., env="POSTGRES_DB")
    schema: str = Field("public", env="POSTGRES_SCHEMA")
    ssl_mode: str = Field("require", env="POSTGRES_SSL_MODE")
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class SupabaseSettings(BaseSettings):
    """Supabase connection settings"""
    url: AnyHttpUrl = Field(..., env="SUPABASE_URL")
    key: SecretStr = Field(..., env="SUPABASE_KEY")
    jwt_secret: SecretStr = Field(..., env="SUPABASE_JWT_SECRET")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class GPUProviderSettings(BaseSettings):
    """GPU provider settings"""
    provider_type: str = Field("on-premise", env="GPU_PROVIDER_TYPE")
    aws_access_key: Optional[SecretStr] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_key: Optional[SecretStr] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: Optional[str] = Field(None, env="AWS_REGION")
    gcp_project_id: Optional[str] = Field(None, env="GCP_PROJECT_ID")
    gcp_credentials_file: Optional[Path] = Field(None, env="GCP_CREDENTIALS_FILE")
    gcp_zone: Optional[str] = Field(None, env="GCP_ZONE")
    
    @validator("provider_type")
    def validate_provider_type(cls, v):
        allowed_providers = ["on-premise", "aws", "gcp", "azure"]
        if v not in allowed_providers:
            raise ValueError(f"Provider type must be one of {allowed_providers}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class APISettings(BaseSettings):
    """API service settings"""
    host: str = Field("0.0.0.0", env="API_HOST")
    port: int = Field(8000, env="API_PORT")
    debug: bool = Field(False, env="API_DEBUG")
    reload: bool = Field(False, env="API_RELOAD")
    workers: int = Field(1, env="API_WORKERS")
    cors_origins: List[str] = Field(["*"], env="API_CORS_ORIGINS")
    auth_required: bool = Field(True, env="API_AUTH_REQUIRED")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class LoggingSettings(BaseSettings):
    """Logging configuration"""
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    output_file: Optional[Path] = Field(None, env="LOG_FILE")
    
    @validator("level")
    def validate_log_level(cls, v):
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_v = v.upper()
        if upper_v not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return upper_v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""
    enable_prometheus: bool = Field(False, env="ENABLE_PROMETHEUS")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")
    enable_tracing: bool = Field(False, env="ENABLE_TRACING")
    tracing_provider: str = Field("jaeger", env="TRACING_PROVIDER")
    tracing_endpoint: Optional[str] = Field(None, env="TRACING_ENDPOINT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class WebhookSettings(BaseSettings):
    """Webhook settings"""
    signing_secret: SecretStr = Field(..., env="WEBHOOK_SIGNING_SECRET")
    timeout_seconds: int = Field(5, env="WEBHOOK_TIMEOUT_SECONDS")
    retry_attempts: int = Field(3, env="WEBHOOK_RETRY_ATTEMPTS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class SecuritySettings(BaseSettings):
    """Security settings"""
    secret_key: SecretStr = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class Settings(BaseSettings):
    """Main application settings"""
    environment: str = Field("development", env="ENVIRONMENT")
    project_name: str = Field("GPU Fleet Manager", env="PROJECT_NAME")
    api_version: str = Field("v1", env="API_VERSION")
    
    # Nested settings
    database: DatabaseSettings = DatabaseSettings()
    supabase: SupabaseSettings = SupabaseSettings()
    gpu_provider: GPUProviderSettings = GPUProviderSettings()
    api: APISettings = APISettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    webhooks: WebhookSettings = WebhookSettings()
    security: SecuritySettings = SecuritySettings()
    
    @validator("environment")
    def validate_environment(cls, v):
        allowed_environments = ["development", "testing", "staging", "production"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of {allowed_environments}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, using caching for performance
    
    Caching is important to avoid re-parsing environment variables
    on each function call when using FastAPI dependency injection
    """
    return Settings()
