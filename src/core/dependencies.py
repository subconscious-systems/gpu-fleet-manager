from typing import Dict, Any, AsyncGenerator
from functools import lru_cache
from fastapi import Depends, HTTPException, status
import os
from contextlib import asynccontextmanager
import httpx
import logging
from dotenv import load_dotenv

# Initialize logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass

class ConfigError(Exception):
    """Custom exception for configuration-related errors"""
    pass

class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.client = httpx.AsyncClient(
            base_url=self.url,
            headers={
                'apikey': self.key,
                'Authorization': f'Bearer {self.key}'
            }
        )

    async def test_connection(self):
        """Test the database connection"""
        try:
            # Just check if we can reach the Supabase API
            response = await self.client.get('/rest/v1/')
            response.raise_for_status()
            return True
        except Exception as e:
            raise DatabaseError(f"Failed to connect to Supabase: {str(e)}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

@lru_cache()
def get_supabase_config() -> Dict[str, str]:
    """Get Supabase configuration with validation"""
    config = {
        "url": os.getenv("SUPABASE_URL"),
        "key": os.getenv("SUPABASE_KEY"),
    }
    
    missing = [k for k, v in config.items() if not v]
    if missing:
        error_msg = f"Missing required Supabase configuration: {', '.join(missing)}"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    return config

async def create_supabase_client() -> SupabaseClient:
    """Create and configure Supabase client"""
    try:
        config = get_supabase_config()
        client = SupabaseClient(config["url"], config["key"])
        
        # Test the connection
        await client.test_connection()
        logger.info("Successfully connected to Supabase")
        return client
        
    except Exception as e:
        error_msg = f"Failed to initialize Supabase client: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise DatabaseError(error_msg) from e

@asynccontextmanager
async def get_db() -> AsyncGenerator[SupabaseClient, None]:
    """Async context manager for database access"""
    client = None
    try:
        client = await create_supabase_client()
        yield client
    except DatabaseError as e:
        logger.error("Database error during request", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable"
        ) from e
    except Exception as e:
        logger.error("Unexpected error during database operation", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e
    finally:
        if client:
            await client.close()

# Dependency to inject the database
async def get_db_dependency() -> AsyncGenerator[SupabaseClient, None]:
    """FastAPI dependency for database injection"""
    async with get_db() as db:
        yield db

# Export the dependency
db = Depends(get_db_dependency)
