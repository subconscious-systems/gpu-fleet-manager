from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, select
from sqlalchemy import func
import asyncio
from contextlib import asynccontextmanager

from ..models.gpu import GPU, GPUStatus
from ..models.job import Job, JobStatus, JobPriority, ComputeStatus
from ..utils.spot_manager import SpotManager
from ..utils.monitoring import monitor
from ..utils.cost_tracker import CostTracker
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AllocationError(Exception):
    """Raised when GPU allocation fails"""
    pass

class GPUAllocator:
    def __init__(self, db: Session, spot_manager: SpotManager, cost_tracker: CostTracker):
        self.db = db
        self.spot_manager = spot_manager
        self.cost_tracker = cost_tracker
        self._load_model_requirements()
        self._allocation_lock = asyncio.Lock()
    
    def _load_model_requirements(self):
        """Load model requirements with fallback defaults"""
        self.model_requirements = {
            # LLM Models
            "phi-2": {
                "min_memory": 16000,
                "preferred_memory": 24000,
                "capabilities": {"compute_capability": "8.0"},
                "max_batch_size": 4,
                "cost_per_hour": 0.60
            },
            "deepseek-coder": {
                "min_memory": 24000,
                "preferred_memory": 32000,
                "capabilities": {"compute_capability": "8.0"},
                "max_batch_size": 2,
                "cost_per_hour": 0.90
            },
            "stable-diffusion-xl": {
                "min_memory": 12000,
                "preferred_memory": 16000,
                "capabilities": {"compute_capability": "7.5"},
                "max_batch_size": 4,
                "cost_per_hour": 0.45
            }
        }
        
        # Default fallback configuration
        self.default_requirements = {
            "min_memory": settings.DEFAULT_GPU_MEMORY,
            "preferred_memory": settings.DEFAULT_GPU_MEMORY * 1.5,
            "capabilities": {},
            "max_batch_size": 1,
            "cost_per_hour": 0.30
        }

    @monitor
    @asynccontextmanager
    async def allocation_context(self, job: Job):
        """Context manager for safe GPU allocation"""
        gpu = None
        try:
            gpu = await self.allocate_for_job(job)
            if not gpu:
                raise AllocationError(f"No suitable GPU found for job {job.id}")
            yield gpu
        except Exception as e:
            if gpu:
                await self.release_gpu(gpu, job)
            logger.error(f"Allocation failed for job {job.id}: {str(e)}", exc_info=True)
            raise
    
    @monitor
    async def allocate_for_job(self, job: Job) -> Optional[GPU]:
        """Find and allocate the best GPU for a job with proper locking"""
        async with self._allocation_lock:
            try:
                model_reqs = self.model_requirements.get(
                    job.model_name,
                    self.default_requirements
                )

                # Validate memory requirements
                if model_reqs["min_memory"] < settings.MIN_GPU_MEMORY:
                    model_reqs["min_memory"] = settings.MIN_GPU_MEMORY

                # Try to find an available GPU
                gpu = await self._find_available_gpu(
                    job.organization_id,
                    model_reqs["min_memory"],
                    model_reqs["capabilities"]
                )

                if gpu:
                    await self._allocate_gpu(gpu, job)
                    return gpu

                # If no GPU available, try spot instance
                if self.spot_manager:
                    gpu = await self._request_spot_gpu(
                        job.organization_id,
                        model_reqs["preferred_memory"],
                        model_reqs["capabilities"],
                        min(model_reqs["cost_per_hour"], settings.SPOT_INSTANCE_MAX_PRICE)
                    )
                    if gpu:
                        await self._allocate_gpu(gpu, job)
                        return gpu

                return None
                
            except Exception as e:
                logger.error(f"Error allocating GPU for job {job.id}: {str(e)}", exc_info=True)
                raise AllocationError(f"Failed to allocate GPU: {str(e)}") from e

    async def _find_available_gpu(
        self,
        organization_id: str,
        min_memory: int,
        required_capabilities: Dict[str, Any]
    ) -> Optional[GPU]:
        """Find an available GPU with optimized query"""
        try:
            # Build efficient query
            query = select(GPU).where(
                and_(
                    GPU.organization_id == organization_id,
                    GPU.status == GPUStatus.AVAILABLE,
                    GPU.available_memory >= min_memory,
                    # Ensure GPU isn't scheduled for termination
                    or_(
                        GPU.termination_time.is_(None),
                        GPU.termination_time > datetime.utcnow()
                    )
                )
            )

            # Add capability filters
            for cap_name, cap_value in required_capabilities.items():
                query = query.where(GPU.capabilities[cap_name].astext == str(cap_value))

            # Optimize ordering for best fit
            query = query.order_by(
                # Prefer GPUs with closer memory match to avoid fragmentation
                func.abs(GPU.available_memory - min_memory),
                GPU.cost_per_hour
            )

            return await self.db.execute(query).first()

        except Exception as e:
            logger.error(f"Error finding available GPU: {str(e)}", exc_info=True)
            return None

    async def _allocate_gpu(self, gpu: GPU, job: Job):
        """Allocate GPU with proper error handling and state management"""
        try:
            # Update GPU state
            gpu.status = GPUStatus.IN_USE
            gpu.available_memory -= job.memory_required
            gpu.current_job_count = (gpu.current_job_count or 0) + 1
            
            # Validate we haven't exceeded max jobs per GPU
            if gpu.current_job_count > settings.MAX_JOBS_PER_GPU:
                raise AllocationError(f"GPU {gpu.id} has exceeded maximum job limit")
            
            # Update job state
            job.gpu_id = gpu.id
            job.compute_status = ComputeStatus.ALLOCATED
            job.allocation_time = datetime.utcnow()

            # Start cost tracking
            await self.cost_tracker.start_tracking(
                organization_id=job.organization_id,
                gpu_id=gpu.id,
                job_id=job.id,
                cost_per_hour=gpu.cost_per_hour
            )

            await self.db.commit()
            
            logger.info(f"Successfully allocated GPU {gpu.id} to job {job.id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to allocate GPU {gpu.id} to job {job.id}: {str(e)}", exc_info=True)
            raise AllocationError(f"GPU allocation failed: {str(e)}") from e

    async def release_gpu(self, gpu: GPU, job: Job):
        """Release GPU with cleanup and error handling"""
        try:
            # Update GPU state
            gpu.available_memory += job.memory_required
            gpu.current_job_count = max(0, (gpu.current_job_count or 1) - 1)
            
            # Only mark as available if no other jobs are running
            if gpu.current_job_count == 0:
                gpu.status = GPUStatus.AVAILABLE
            
            # Update job state
            job.gpu_id = None
            job.compute_status = None
            job.release_time = datetime.utcnow()

            # Stop cost tracking
            await self.cost_tracker.stop_tracking(
                organization_id=job.organization_id,
                gpu_id=gpu.id,
                job_id=job.id
            )

            await self.db.commit()
            
            # Handle spot instance cleanup if needed
            if (gpu.provider == "spot" and gpu.termination_time 
                and datetime.utcnow() >= gpu.termination_time
                and gpu.current_job_count == 0):
                await self._terminate_spot_gpu(gpu)
                
            logger.info(f"Successfully released GPU {gpu.id} from job {job.id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error releasing GPU {gpu.id} from job {job.id}: {str(e)}", exc_info=True)
            raise

    async def _terminate_spot_gpu(self, gpu: GPU):
        """Terminate a spot GPU instance"""
        try:
            if self.spot_manager and gpu.provider_id:
                await self.spot_manager.terminate_instance(gpu.provider_id)
            
            self.db.delete(gpu)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to terminate spot instance {gpu.provider_id}: {e}")
