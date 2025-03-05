"""
Rune.AI API configuration for GPU Fleet Manager

This module provides configuration settings for the Rune.AI API integration.
"""

from pydantic import BaseModel, Field, SecretStr
from src.config import get_settings

class RuneConfig(BaseModel):
    """
    Rune.AI API configuration settings
    
    Attributes:
        api_key: API key for authenticating with Rune.AI
        base_url: Base URL for Rune.AI API endpoints
        cluster_id: Identifier for the Rune.AI cluster to use
    """
    api_key: SecretStr
    base_url: str
    cluster_id: str

def get_rune_config() -> RuneConfig:
    """
    Get Rune.AI configuration from the central settings
    
    Returns:
        RuneConfig object with Rune.AI configuration settings
    """
    settings = get_settings()
    
    return RuneConfig(
        api_key=settings.gpu_provider.rune_api_key,
        base_url=settings.gpu_provider.rune_api_base_url,
        cluster_id=settings.gpu_provider.rune_cluster_id
    )
