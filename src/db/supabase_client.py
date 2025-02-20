from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, ClassVar, Dict, Optional, TypeVar, cast
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")

from pydantic import BaseModel
from supabase import create_client, Client

class SupabaseConfig(BaseModel):
    """Supabase configuration"""
    url: str
    key: str

class SupabaseResponse(BaseModel):
    """Wrapper for Supabase responses"""
    data: list = []
    error: Optional[str] = None

class SupabaseClient:
    """Supabase client wrapper"""
    
    _instance: ClassVar[Optional[SupabaseClient]] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    
    def __init__(self, config: SupabaseConfig):
        """Initialize Supabase client"""
        self.config = config
        self._client: Optional[Client] = None
        
    @classmethod
    async def get_instance(cls, config: Optional[SupabaseConfig] = None) -> SupabaseClient:
        """Get or create singleton instance with double-checked locking."""
        if not cls._instance:
            async with cls._lock:
                if not cls._instance:
                    if not config:
                        raise ValueError("Config required for initial instance creation")
                    cls._instance = cls(config)
        return cls._instance
    
    @property
    def client(self) -> Client:
        """Get or create Supabase client"""
        if not self._client:
            self._client = create_client(
                self.config.url,
                self.config.key
            )
        return self._client
    
    def table(self, name: str) -> 'SupabaseTable':
        """Get table reference"""
        return SupabaseTable(self.client.table(name))
    
    async def close(self):
        """Close client connection"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup"""
        await self.close()

class SupabaseTable:
    """Wrapper for Supabase table operations"""
    
    def __init__(self, table):
        self.table = table
        self._query = table
    
    def select(self, columns: str = "*") -> 'SupabaseTable':
        """Select columns"""
        self._query = self.table.select(columns)
        return self
    
    def insert(self, data: Dict[str, Any]) -> 'SupabaseTable':
        """Insert data"""
        self._query = self.table.insert(data)
        return self
    
    def update(self, data: Dict[str, Any]) -> 'SupabaseTable':
        """Update data"""
        self._query = self.table.update(data)
        return self
    
    def delete(self) -> 'SupabaseTable':
        """Delete data"""
        self._query = self.table.delete()
        return self
    
    def eq(self, column: str, value: Any) -> 'SupabaseTable':
        """Add equality filter"""
        self._query = self._query.eq(column, value)
        return self
    
    def order(self, column: str, desc: bool = False) -> 'SupabaseTable':
        """Order results"""
        self._query = self._query.order(column, desc=desc)
        return self
    
    def limit(self, count: int) -> 'SupabaseTable':
        """Limit results"""
        self._query = self._query.limit(count)
        return self
    
    async def execute(self) -> SupabaseResponse:
        """Execute query"""
        try:
            result = await self._query.execute()
            return SupabaseResponse(data=result.data)
        except Exception as e:
            logger.error(f"Supabase query error: {str(e)}")
            return SupabaseResponse(error=str(e))

def requires_db(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure DB client is initialized."""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        if not SupabaseClient._instance:
            raise RuntimeError("Database client not initialized")
        return await func(*args, **kwargs)
    return wrapper
