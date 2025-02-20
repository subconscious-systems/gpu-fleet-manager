from typing import List, Optional, Dict, Any
from datetime import datetime

from src.models.domain import (
    JobCreate, JobUpdate, JobResponse,
    GPUCreate, GPUUpdate, GPUResponse,
    JobStatus, GPUStatus
)
from src.db.supabase_client import SupabaseClient

class Repository:
    """Repository for database operations"""
    
    def __init__(self, client: SupabaseClient):
        """Initialize repository with database client"""
        self.client = client

    async def create_job(self, job: JobCreate) -> JobResponse:
        """Create a new job"""
        job_data = {
            **job.model_dump(),
            "status": JobStatus.QUEUED,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("jobs").insert(job_data).execute()
        if result.error:
            raise Exception(f"Failed to create job: {result.error}")
            
        return JobResponse(**result.data[0])

    async def get_job(self, job_id: str) -> Optional[JobResponse]:
        """Get job by ID"""
        result = await self.client.table("jobs").select("*").eq("id", job_id).execute()
        if result.error:
            raise Exception(f"Failed to get job: {result.error}")
            
        return JobResponse(**result.data[0]) if result.data else None

    async def list_jobs(
        self,
        organization_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[JobResponse]:
        """List jobs for organization"""
        query = self.client.table("jobs").select("*").eq("organization_id", organization_id)
        
        if status:
            query = query.eq("status", status)
            
        result = await query.limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list jobs: {result.error}")
            
        return [JobResponse(**item) for item in result.data]

    async def update_job(self, job_id: str, job_update: JobUpdate) -> Optional[JobResponse]:
        """Update job details"""
        result = await self.client.table("jobs").update(job_update.model_dump()).eq("id", job_id).execute()
        if result.error:
            raise Exception(f"Failed to update job: {result.error}")
            
        return JobResponse(**result.data[0]) if result.data else None

    async def create_gpu(self, gpu: GPUCreate) -> GPUResponse:
        """Create a new GPU"""
        gpu_data = {
            **gpu.model_dump(),
            "status": GPUStatus.AVAILABLE,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("gpus").insert(gpu_data).execute()
        if result.error:
            raise Exception(f"Failed to create GPU: {result.error}")
            
        return GPUResponse(**result.data[0])

    async def get_gpu(self, gpu_id: str) -> Optional[GPUResponse]:
        """Get GPU by ID"""
        result = await self.client.table("gpus").select("*").eq("id", gpu_id).execute()
        if result.error:
            raise Exception(f"Failed to get GPU: {result.error}")
            
        return GPUResponse(**result.data[0]) if result.data else None

    async def list_gpus(
        self,
        organization_id: str,
        status: Optional[GPUStatus] = None,
        limit: int = 100
    ) -> List[GPUResponse]:
        """List GPUs for organization"""
        query = self.client.table("gpus").select("*").eq("organization_id", organization_id)
        
        if status:
            query = query.eq("status", status)
            
        result = await query.limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list GPUs: {result.error}")
            
        return [GPUResponse(**item) for item in result.data]

    async def update_gpu(self, gpu_id: str, gpu_update: GPUUpdate) -> Optional[GPUResponse]:
        """Update GPU details"""
        result = await self.client.table("gpus").update(gpu_update.model_dump()).eq("id", gpu_id).execute()
        if result.error:
            raise Exception(f"Failed to update GPU: {result.error}")
            
        return GPUResponse(**result.data[0]) if result.data else None
