from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from src.db.repository import Repository
from src.models.domain import (
    JobCreate, JobUpdate, JobResponse,
    JobStatus, GPUStatus
)
from src.core.gpu_allocator import GPUAllocator
from src.utils.model_runner import ModelRunner

logger = logging.getLogger(__name__)

class JobManager:
    """Manager for job lifecycle and GPU allocation"""
    
    def __init__(self, repo: Repository):
        """Initialize job manager"""
        self.repo = repo
        self.gpu_allocator = GPUAllocator(repo)
        self.model_runner = ModelRunner()
    
    async def create_job(self, job: JobCreate) -> JobResponse:
        """Create and queue a new job"""
        try:
            # Create job in queued state
            created_job = await self.repo.create_job(job)
            logger.info(f"Created job {created_job.id} for organization {job.organization_id}")
            
            # Try to allocate GPU and start job immediately if possible
            await self._try_allocate_and_start(created_job)
            
            return created_job
            
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            raise
    
    async def get_job(self, job_id: str) -> Optional[JobResponse]:
        """Get job by ID"""
        return await self.repo.get_job(job_id)
    
    async def list_jobs(
        self,
        organization_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[JobResponse]:
        """List jobs for organization"""
        return await self.repo.list_jobs(organization_id, status, limit)
    
    async def update_job(self, job_id: str, job_update: JobUpdate) -> Optional[JobResponse]:
        """Update job details"""
        return await self.repo.update_job(job_id, job_update)
    
    async def cancel_job(self, job_id: str) -> Optional[JobResponse]:
        """Cancel a job"""
        try:
            # Get current job state
            job = await self.repo.get_job(job_id)
            if not job:
                return None
                
            # Can only cancel queued or running jobs
            if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
                raise ValueError(f"Cannot cancel job in {job.status} state")
                
            # Update job status
            updated_job = await self.repo.update_job(
                job_id,
                JobUpdate(
                    status=JobStatus.CANCELLED,
                    completed_at=datetime.utcnow().isoformat()
                )
            )
            
            # Release GPU if job was running
            if job.status == JobStatus.RUNNING and job.gpu_id:
                await self.gpu_allocator.release_gpu(job.gpu_id)
                # Try to start next job in queue
                await self._process_queue(job.organization_id)
                
            return updated_job
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {str(e)}")
            raise
    
    async def _try_allocate_and_start(self, job: JobResponse) -> None:
        """Try to allocate GPU and start job"""
        try:
            # Try to allocate GPU
            gpu = await self.gpu_allocator.allocate_for_job(job)
            if not gpu:
                logger.info(f"No GPU available for job {job.id}, keeping in queue")
                return
                
            # Update job with allocated GPU
            await self.repo.update_job(
                job.id,
                JobUpdate(
                    status=JobStatus.RUNNING,
                    gpu_id=gpu.id
                )
            )
            
            # Start job execution
            self._start_job_execution(job, gpu)
            
        except Exception as e:
            logger.error(f"Error allocating GPU for job {job.id}: {str(e)}")
            # Update job status to failed
            await self.repo.update_job(
                job.id,
                JobUpdate(
                    status=JobStatus.FAILED,
                    error=f"Failed to allocate GPU: {str(e)}",
                    completed_at=datetime.utcnow().isoformat()
                )
            )
    
    def _start_job_execution(self, job: JobResponse, gpu: Any) -> None:
        """Start job execution in background task"""
        try:
            # Run job asynchronously
            self.model_runner.run_job_async(
                job_id=job.id,
                model_type=job.model_type,
                prompt=job.prompt,
                gpu_id=gpu.id,
                callback=self._handle_job_completion
            )
            logger.info(f"Started execution of job {job.id} on GPU {gpu.id}")
            
        except Exception as e:
            logger.error(f"Error starting job {job.id}: {str(e)}")
            # Update job status to failed
            self._handle_job_completion(
                job.id,
                success=False,
                error=f"Failed to start job: {str(e)}"
            )
    
    async def _handle_job_completion(
        self,
        job_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Handle job completion callback"""
        try:
            # Get current job state
            job = await self.repo.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found for completion callback")
                return
                
            # Update job status
            status = JobStatus.COMPLETED if success else JobStatus.FAILED
            await self.repo.update_job(
                job_id,
                JobUpdate(
                    status=status,
                    result=result,
                    error=error,
                    completed_at=datetime.utcnow().isoformat()
                )
            )
            
            # Release GPU
            if job.gpu_id:
                await self.gpu_allocator.release_gpu(job.gpu_id)
                
            # Try to start next job in queue
            await self._process_queue(job.organization_id)
            
        except Exception as e:
            logger.error(f"Error handling completion of job {job_id}: {str(e)}")
    
    async def _process_queue(self, organization_id: str) -> None:
        """Process queued jobs for organization"""
        try:
            # Get queued jobs
            queued_jobs = await self.repo.list_jobs(
                organization_id=organization_id,
                status=JobStatus.QUEUED,
                limit=10
            )
            
            # Try to start each job
            for job in queued_jobs:
                await self._try_allocate_and_start(job)
                
        except Exception as e:
            logger.error(f"Error processing queue for org {organization_id}: {str(e)}")
