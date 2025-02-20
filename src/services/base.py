from typing import TypeVar, Generic, Optional, List, Dict, Any
from datetime import datetime
from src.core.dependencies import SupabaseClient

T = TypeVar('T')

class BaseService(Generic[T]):
    """Base service class with common database operations"""
    
    def __init__(self, db: SupabaseClient, table_name: str):
        self.db = db
        self.table_name = table_name
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        response = await self.db.client.get(
            f'/rest/v1/{self.table_name}',
            params={'id': f'eq.{id}', 'select': '*'}
        )
        response.raise_for_status()
        items = response.json()
        return items[0] if items else None
    
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List records with optional filters"""
        params = {'select': '*'}
        if filters:
            for key, value in filters.items():
                params[key] = f'eq.{value}'
        
        response = await self.db.client.get(
            f'/rest/v1/{self.table_name}',
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record"""
        response = await self.db.client.post(
            f'/rest/v1/{self.table_name}',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record"""
        response = await self.db.client.patch(
            f'/rest/v1/{self.table_name}',
            params={'id': f'eq.{id}'},
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def delete(self, id: str) -> None:
        """Delete a record"""
        response = await self.db.client.delete(
            f'/rest/v1/{self.table_name}',
            params={'id': f'eq.{id}'}
        )
        response.raise_for_status()
