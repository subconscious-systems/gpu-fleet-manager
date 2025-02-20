from pydantic_settings import BaseSettings

class RuneSettings(BaseSettings):
    RUNE_API_KEY: str = "ba5de503-952c-4557-aa81-f2d5ccf19450"  # Default from documentation
    RUNE_API_BASE_URL: str = "https://heartbeat-94692957.us-west1.run.app"  # Updated to match documentation
    RUNE_CLUSTER_ID: str = "ronin_0"  # Default cluster ID
    
    class Config:
        env_prefix = "RUNE_"
        case_sensitive = False
