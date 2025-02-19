from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Union

from fastapi import HTTPException

from .supabase_client import SupabaseClient, requires_db

class Repository:
    """Repository pattern implementation for database operations."""
    
    def __init__(self, client: SupabaseClient) -> None:
        self.client = client

    @requires_db
    async def get_organization(self, org_id: str) -> Dict[str, Any]:
        """Get organization by ID."""
        result = await self.client.select(
            "organizations",
            filters={"id": f"eq.{org_id}"},
            limit=1
        )
        if not result:
            raise HTTPException(status_code=404, detail="Organization not found")
        return result[0]

    @requires_db
    async def get_gpu_jobs(
        self,
        org_id: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get GPU jobs for organization."""
        filters = {"organization_id": f"eq.{org_id}"}
        if status:
            filters["status"] = f"eq.{status}"
            
        return await self.client.select(
            "gpu_jobs",
            filters=filters,
            order="created_at.desc",
            limit=limit
        )

    @requires_db
    async def create_gpu_job(
        self,
        org_id: str,
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new GPU job."""
        job_data.update({
            "organization_id": org_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        })
        
        return await self.client.insert("gpu_jobs", job_data)

    @requires_db
    async def update_gpu_job(
        self,
        job_id: str,
        org_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update GPU job."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        result = await self.client.update(
            "gpu_jobs",
            updates,
            filters={
                "id": f"eq.{job_id}",
                "organization_id": f"eq.{org_id}"
            }
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result[0]

    @requires_db
    async def get_available_gpus(
        self,
        org_id: str,
        min_memory: Optional[int] = None,
        gpu_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available GPUs matching criteria."""
        filters = {
            "organization_id": f"eq.{org_id}",
            "status": "eq.available"
        }
        
        if min_memory:
            filters["memory_gb"] = f"gte.{min_memory}"
        if gpu_type:
            filters["gpu_type"] = f"eq.{gpu_type}"
            
        return await self.client.select(
            "gpus",
            filters=filters,
            order="memory_gb.desc"
        )

    @requires_db
    async def allocate_gpu(
        self,
        gpu_id: str,
        job_id: str,
        org_id: str
    ) -> Dict[str, Any]:
        """Allocate GPU to job with optimistic locking."""
        # First verify GPU is available
        gpu = await self.client.select(
            "gpus",
            filters={
                "id": f"eq.{gpu_id}",
                "organization_id": f"eq.{org_id}",
                "status": "eq.available"
            }
        )
        
        if not gpu:
            raise HTTPException(
                status_code=409,
                detail="GPU not available for allocation"
            )
            
        # Update GPU status atomically
        return await self.client.update(
            "gpus",
            {
                "status": "allocated",
                "job_id": job_id,
                "allocated_at": datetime.utcnow().isoformat()
            },
            filters={
                "id": f"eq.{gpu_id}",
                "status": "eq.available"  # Ensures GPU wasn't allocated elsewhere
            }
        )

    @requires_db
    async def release_gpu(
        self,
        gpu_id: str,
        org_id: str
    ) -> Dict[str, Any]:
        """Release GPU back to available pool."""
        return await self.client.update(
            "gpus",
            {
                "status": "available",
                "job_id": None,
                "allocated_at": None
            },
            filters={
                "id": f"eq.{gpu_id}",
                "organization_id": f"eq.{org_id}"
            }
        )
