from typing import Optional, List, Dict
import logging
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..models.job import Job, JobStatus, JobPriority, ComputeStatus
from ..models.gpu import GPU, GPUStatus
from .gpu_allocator import GPUAllocator
from ..utils.monitoring import monitor
from ..utils.model_runner import ModelRunner
from ..utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(
        self,
        db: Session,
        gpu_allocator: GPUAllocator,
        model_runner: ModelRunner,
        cost_tracker: CostTracker
    ):
        self.db = db
        self.gpu_allocator = gpu_allocator
        self.model_runner = model_runner
        self.cost_tracker = cost_tracker
        self.is_running = False
        self._queue_processor_task = None

    async def submit_job(self, job_data: Dict) -> Job:
        """Submit a new job to the queue"""
        # Calculate memory requirements based on model and batch size
        memory_required = self._calculate_memory_required(
            job_data["model_name"],
            job_data.get("batch_size", 1)
        )

        job = Job(
            name=job_data.get("name", f"job-{datetime.utcnow().isoformat()}"),
            model_type=job_data["model_type"],
            model_name=job_data["model_name"],
            priority=job_data.get("priority", JobPriority.NORMAL),
            organization_id=job_data["organization_id"],
            user_id=job_data["user_id"],
            input_data=job_data["parameters"],
            memory_required=memory_required,
            timeout_seconds=job_data.get("timeout_seconds", 3600),
            status=JobStatus.QUEUED,
            compute_status=None  # No compute assigned yet
        )
        
        self.db.add(job)
        self.db.commit()
        
        # Start queue processor if not running
        await self.ensure_queue_processor_running()
        
        return job

    def _calculate_memory_required(self, model_name: str, batch_size: int) -> int:
        """Calculate memory requirements for a model"""
        base_memory = self.gpu_allocator.model_requirements.get(model_name, {
            "min_memory": 8000
        })["min_memory"]
        
        # Scale memory by batch size with some overhead
        return int(base_memory * batch_size * 1.2)  # 20% overhead

    @monitor
    async def process_queue(self):
        """Process the job queue continuously"""
        while self.is_running:
            try:
                # Get next batch of jobs, ordered by priority and creation time
                pending_jobs = self.db.query(Job).filter(
                    and_(
                        Job.status == JobStatus.QUEUED,
                        Job.compute_status.is_(None)
                    )
                ).order_by(
                    desc(Job.priority),
                    Job.created_at
                ).limit(10).all()

                for job in pending_jobs:
                    try:
                        # Try to allocate GPU
                        gpu = await self.gpu_allocator.allocate_for_job(job)
                        
                        if gpu:
                            # Run the job
                            job.status = JobStatus.RUNNING
                            self.db.commit()
                            
                            try:
                                result = await self.model_runner.run_job(job, gpu)
                                job.output_data = result
                                job.status = JobStatus.COMPLETED
                            except Exception as e:
                                logger.error(f"Job {job.id} failed: {e}")
                                job.error_message = str(e)
                                job.status = JobStatus.FAILED
                            finally:
                                # Always release the GPU
                                await self.gpu_allocator.release_gpu(gpu, job)
                        else:
                            # No GPU available, keep job queued
                            continue

                    except Exception as e:
                        logger.error(f"Error processing job {job.id}: {e}")
                        job.error_message = str(e)
                        job.status = JobStatus.FAILED
                    finally:
                        self.db.commit()

            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
            
            # Wait before next batch
            await asyncio.sleep(5)

    async def ensure_queue_processor_running(self):
        """Ensure the queue processor is running"""
        if not self.is_running:
            self.is_running = True
            self._queue_processor_task = asyncio.create_task(self.process_queue())

    async def stop_queue_processor(self):
        """Stop the queue processor"""
        self.is_running = False
        if self._queue_processor_task:
            await self._queue_processor_task
            self._queue_processor_task = None

    async def get_job_status(self, job_id: str, organization_id: str) -> Optional[Job]:
        """Get the status of a specific job"""
        return self.db.query(Job).filter(
            and_(
                Job.id == job_id,
                Job.organization_id == organization_id
            )
        ).first()

    async def cancel_job(self, job_id: str, organization_id: str) -> bool:
        """Cancel a job if it hasn't started"""
        job = await self.get_job_status(job_id, organization_id)
        
        if not job or job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
            return False

        if job.status == JobStatus.RUNNING and job.gpu_id:
            gpu = self.db.query(GPU).get(job.gpu_id)
            if gpu:
                await self.gpu_allocator.release_gpu(gpu, job)

        job.status = JobStatus.CANCELLED
        self.db.commit()
        return True

    async def get_organization_jobs(
        self,
        organization_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """Get jobs for an organization"""
        query = self.db.query(Job).filter(Job.organization_id == organization_id)
        
        if status:
            query = query.filter(Job.status == status)
            
        return query.order_by(desc(Job.created_at)).offset(offset).limit(limit).all()
