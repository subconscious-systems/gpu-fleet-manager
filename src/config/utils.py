"""
Configuration utility functions for GPU Fleet Manager

This module provides utility functions to apply configuration settings 
across different components of the application.
"""

import logging
import os
from typing import Optional, Dict, Any, Union
from pathlib import Path

from src.config.settings import get_settings, Settings

def configure_logging() -> None:
    """
    Configure application logging based on settings
    
    This sets up logging levels, formats, and outputs according to the configuration.
    """
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.logging.level))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.logging.level))
    formatter = logging.Formatter(settings.logging.format)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Configure file handler if specified
    if settings.logging.output_file:
        file_handler = logging.FileHandler(settings.logging.output_file)
        file_handler.setLevel(getattr(logging, settings.logging.level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Log configuration summary
    logger.info(f"Logging configured. Level: {settings.logging.level}")

def get_database_url() -> str:
    """
    Get the database connection URL based on configuration
    
    Returns:
        Database connection URL string
    """
    settings = get_settings()
    return settings.database.connection_string

def get_supabase_credentials() -> Dict[str, str]:
    """
    Get Supabase credentials from configuration
    
    Returns:
        Dictionary with Supabase URL and API key
    """
    settings = get_settings()
    return {
        "url": str(settings.supabase.url),
        "key": settings.supabase.key.get_secret_value()
    }

def get_api_cors_origins() -> list:
    """
    Get list of allowed CORS origins from configuration
    
    Returns:
        List of allowed CORS origin URLs
    """
    settings = get_settings()
    return settings.api.cors_origins

def get_secret_key() -> str:
    """
    Get application secret key for security functions
    
    Returns:
        Secret key string
    """
    settings = get_settings()
    return settings.security.secret_key.get_secret_value()

def get_jwt_settings() -> Dict[str, Union[str, int]]:
    """
    Get JWT authentication settings
    
    Returns:
        Dictionary with JWT algorithm and expiration time
    """
    settings = get_settings()
    return {
        "algorithm": settings.security.algorithm,
        "access_token_expire_minutes": settings.security.access_token_expire_minutes
    }

def get_webhook_signing_secret() -> str:
    """
    Get webhook signing secret for signature verification
    
    Returns:
        Webhook signing secret string
    """
    settings = get_settings()
    return settings.webhooks.signing_secret.get_secret_value()

def get_gpu_provider_config() -> Dict[str, Any]:
    """
    Get GPU provider configuration
    
    Returns:
        Dictionary with GPU provider settings
    """
    settings = get_settings()
    provider_config = {
        "provider_type": settings.gpu_provider.provider_type
    }
    
    # Add provider-specific settings
    if settings.gpu_provider.provider_type == "aws":
        provider_config.update({
            "aws_access_key": settings.gpu_provider.aws_access_key.get_secret_value() if settings.gpu_provider.aws_access_key else None,
            "aws_secret_key": settings.gpu_provider.aws_secret_key.get_secret_value() if settings.gpu_provider.aws_secret_key else None,
            "aws_region": settings.gpu_provider.aws_region
        })
    elif settings.gpu_provider.provider_type == "gcp":
        provider_config.update({
            "gcp_project_id": settings.gpu_provider.gcp_project_id,
            "gcp_credentials_file": settings.gpu_provider.gcp_credentials_file,
            "gcp_zone": settings.gpu_provider.gcp_zone
        })
    
    return provider_config

def get_monitoring_enabled() -> bool:
    """
    Check if monitoring is enabled
    
    Returns:
        Boolean indicating if Prometheus monitoring is enabled
    """
    settings = get_settings()
    return settings.monitoring.enable_prometheus

def build_api_url(path: str = "") -> str:
    """
    Build a complete API URL from configuration
    
    Args:
        path: API path to append to the base URL
        
    Returns:
        Complete API URL
    """
    settings = get_settings()
    
    # Strip leading slash from path if present
    if path and path.startswith('/'):
        path = path[1:]
    
    # Build the base URL
    base_url = f"http://{settings.api.host}:{settings.api.port}"
    
    # Add API version if configured
    if settings.api_version:
        base_url = f"{base_url}/{settings.api_version}"
    
    # Add the path if provided
    if path:
        return f"{base_url}/{path}"
    
    return base_url

def is_development_mode() -> bool:
    """
    Check if application is running in development mode
    
    Returns:
        Boolean indicating if environment is development
    """
    settings = get_settings()
    return settings.environment.lower() == "development"

def is_test_mode() -> bool:
    """
    Check if application is running in test mode
    
    Returns:
        Boolean indicating if environment is testing
    """
    settings = get_settings()
    return settings.environment.lower() == "testing"

def is_production_mode() -> bool:
    """
    Check if application is running in production mode
    
    Returns:
        Boolean indicating if environment is production
    """
    settings = get_settings()
    return settings.environment.lower() == "production"
