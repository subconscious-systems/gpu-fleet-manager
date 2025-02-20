from typing import Optional, List, Dict, Any
from datetime import datetime
from src.core.dependencies import SupabaseClient
from src.models.domain import JobStatus
from .base import BaseService
from .gpu import GPUService

class JobService(BaseService):
    """Service for managing jobs"""
    
    def __init__(self, db: SupabaseClient):
        super().__init__(db, 'jobs')
        self.gpu_service = GPUService(db)
    
    async def create_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job and attempt GPU allocation"""
        # Create job in pending state
        job_data = {
            **data,
            'status': JobStatus.QUEUED.value,
            'created_at': datetime.utcnow().isoformat()
        }
        job = await self.create(job_data)
        
        # Try to allocate a GPU
        gpu = await self.gpu_service.allocate_for_job(
            job['id'],
            job['organization_id'],
            job['memory_required']
        )
        
        if not gpu:
            # No GPU available, job remains in queue
            return job
        
        # GPU allocated successfully
        return await self.get(job['id'])
    
    async def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mark a job as completed and release its GPU"""
        job = await self.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job['gpu_id']:
            # Release the GPU
            await self.gpu_service.release_gpu(
                job['gpu_id'],
                job_id,
                job['memory_required']
            )
        
        # Update job status
        updated = await self.update(job_id, {
            'status': JobStatus.COMPLETED.value,
            'completed_at': datetime.utcnow().isoformat(),
            'result': result
        })
        
        return updated
    
    async def fail_job(self, job_id: str, error: str) -> Dict[str, Any]:
        """Mark a job as failed and release its GPU"""
        job = await self.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job['gpu_id']:
            # Release the GPU
            await self.gpu_service.release_gpu(
                job['gpu_id'],
                job_id,
                job['memory_required']
            )
        
        # Update job status
        updated = await self.update(job_id, {
            'status': JobStatus.FAILED.value,
            'completed_at': datetime.utcnow().isoformat(),
            'error': error
        })
        
        return updated
    
    async def list_organization_jobs(
        self,
        organization_id: str,
        status: Optional[JobStatus] = None
    ) -> List[Dict[str, Any]]:
        """List jobs for an organization with optional status filter"""
        params = {
            'select': '*',
            'organization_id': f'eq.{organization_id}'
        }
        
        if status:
            params['status'] = f'eq.{status.value}'
        
        response = await self.db.client.get(
            '/rest/v1/jobs',
            params=params
        )
        response.raise_for_status()
        return response.json()
