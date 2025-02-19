from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, ClassVar, Dict, Optional, TypeVar, cast
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential

T = TypeVar("T")

@dataclass
class SupabaseConfig:
    """Configuration for Supabase client."""
    url: str
    key: str
    timeout: float = 10.0
    max_connections: int = 10
    retry_attempts: int = 3

class SupabaseClient:
    """High-performance Supabase client with connection pooling and retry logic."""
    
    _instance: ClassVar[Optional[SupabaseClient]] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    
    def __init__(self, config: SupabaseConfig) -> None:
        """Initialize client with configuration."""
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.url,
            timeout=config.timeout,
            limits=httpx.Limits(max_connections=config.max_connections),
            headers={
                "apikey": config.key,
                "Authorization": f"Bearer {config.key}",
                "Content-Type": "application/json",
            },
        )
        
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

    def _build_endpoint(self, table: str) -> str:
        """Build REST endpoint for table."""
        return urljoin("/rest/v1/", table)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request with retry logic."""
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=e.response.status_code if hasattr(e, "response") else 500,
                detail=str(e)
            )

    async def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute SELECT query with filtering and pagination."""
        params = {"select": columns}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
            
        return await self._request(
            method="GET",
            endpoint=self._build_endpoint(table),
            params=params,
        )

    async def insert(
        self,
        table: str,
        data: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Dict[str, Any]:
        """Insert data with optional upsert."""
        headers = {"Prefer": "return=representation"}
        if upsert:
            headers["Prefer"] = "resolution=merge-duplicates," + headers["Prefer"]
            
        return await self._request(
            method="POST",
            endpoint=self._build_endpoint(table),
            json=data,
        )

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update data with filtering."""
        return await self._request(
            method="PATCH",
            endpoint=self._build_endpoint(table),
            json=data,
            params=filters,
        )

    async def delete(
        self,
        table: str,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Delete data with filtering."""
        return await self._request(
            method="DELETE",
            endpoint=self._build_endpoint(table),
            params=filters,
        )

    async def close(self) -> None:
        """Close client connections."""
        await self.client.aclose()

def requires_db(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure DB client is initialized."""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        if not SupabaseClient._instance:
            raise RuntimeError("Database client not initialized")
        return await func(*args, **kwargs)
    return wrapper
