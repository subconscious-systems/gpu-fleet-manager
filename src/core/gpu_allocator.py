from typing import Optional, List, Dict
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from sqlalchemy import func

from ..models.gpu import GPU, GPUStatus
from ..models.job import Job, JobStatus, JobPriority, ComputeStatus
from ..utils.spot_manager import SpotManager
from ..utils.monitoring import monitor
from ..utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class GPUAllocator:
    def __init__(self, db: Session, spot_manager: SpotManager, cost_tracker: CostTracker):
        self.db = db
        self.spot_manager = spot_manager
        self.cost_tracker = cost_tracker
        self.model_requirements = {
            # LLM Models
            "phi-2": {
                "min_memory": 16000,  # MB
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
            # Stable Diffusion Models
            "stable-diffusion-xl": {
                "min_memory": 12000,
                "preferred_memory": 16000,
                "capabilities": {"compute_capability": "7.5"},
                "max_batch_size": 4,
                "cost_per_hour": 0.45
            }
        }

    @monitor
    async def allocate_for_job(self, job: Job) -> Optional[GPU]:
        """Find and allocate the best GPU for a job"""
        model_reqs = self.model_requirements.get(job.model_name, {
            "min_memory": 8000,
            "preferred_memory": 12000,
            "capabilities": {},
            "max_batch_size": 1,
            "cost_per_hour": 0.30
        })

        # First try to find an available GPU in the same organization
        gpu = await self._find_available_gpu(
            job.organization_id,
            model_reqs["min_memory"],
            model_reqs["capabilities"]
        )

        if gpu:
            await self._allocate_gpu(gpu, job)
            return gpu

        # If no GPU available, try to request a spot instance
        if self.spot_manager:
            gpu = await self._request_spot_gpu(
                job.organization_id,
                model_reqs["preferred_memory"],
                model_reqs["capabilities"],
                model_reqs["cost_per_hour"]
            )
            if gpu:
                await self._allocate_gpu(gpu, job)
                return gpu

        return None

    async def _find_available_gpu(
        self,
        organization_id: str,
        min_memory: int,
        required_capabilities: Dict
    ) -> Optional[GPU]:
        """Find an available GPU that meets the requirements"""
        query = self.db.query(GPU).filter(
            and_(
                GPU.organization_id == organization_id,
                GPU.status == GPUStatus.AVAILABLE,
                GPU.available_memory >= min_memory
            )
        )

        # Filter by capabilities if specified
        for cap_name, cap_value in required_capabilities.items():
            query = query.filter(GPU.capabilities[cap_name].astext == str(cap_value))

        # Order by available memory (descending) and cost (ascending)
        gpu = query.order_by(
            desc(GPU.available_memory),
            GPU.cost_per_hour
        ).first()

        return gpu

    async def _request_spot_gpu(
        self,
        organization_id: str,
        preferred_memory: int,
        required_capabilities: Dict,
        max_cost_per_hour: float
    ) -> Optional[GPU]:
        """Request a spot GPU instance"""
        try:
            spot_request = await self.spot_manager.request_spot_instance(
                organization_id=organization_id,
                memory_size=preferred_memory,
                capabilities=required_capabilities,
                max_price=max_cost_per_hour
            )

            if spot_request:
                gpu = GPU(
                    organization_id=organization_id,
                    provider="spot",
                    provider_id=spot_request["instance_id"],
                    spot_request_id=spot_request["request_id"],
                    name=f"spot-{spot_request['instance_type']}",
                    status=GPUStatus.INITIALIZING,
                    total_memory=preferred_memory,
                    available_memory=preferred_memory,
                    capabilities=required_capabilities,
                    cost_per_hour=spot_request["price"],
                    termination_time=datetime.utcnow() + timedelta(hours=1)
                )
                self.db.add(gpu)
                self.db.commit()
                return gpu

        except Exception as e:
            logger.error(f"Failed to request spot instance: {e}")
            return None

    async def _allocate_gpu(self, gpu: GPU, job: Job):
        """Allocate a GPU to a job and start cost tracking"""
        gpu.status = GPUStatus.IN_USE
        gpu.available_memory -= job.memory_required
        job.gpu_id = gpu.id
        job.compute_status = ComputeStatus.ALLOCATED

        # Start cost tracking
        await self.cost_tracker.start_tracking(
            organization_id=job.organization_id,
            gpu_id=gpu.id,
            job_id=job.id,
            cost_per_hour=gpu.cost_per_hour
        )

        self.db.commit()

    async def release_gpu(self, gpu: GPU, job: Job):
        """Release a GPU from a job and update cost tracking"""
        gpu.status = GPUStatus.AVAILABLE
        gpu.available_memory += job.memory_required
        job.gpu_id = None
        job.compute_status = None

        # Stop cost tracking
        await self.cost_tracker.stop_tracking(
            organization_id=job.organization_id,
            gpu_id=gpu.id,
            job_id=job.id
        )

        self.db.commit()

        # If this is a spot instance and it's past termination time, release it
        if gpu.provider == "spot" and gpu.termination_time and datetime.utcnow() >= gpu.termination_time:
            await self._terminate_spot_gpu(gpu)

    async def _terminate_spot_gpu(self, gpu: GPU):
        """Terminate a spot GPU instance"""
        try:
            if self.spot_manager and gpu.provider_id:
                await self.spot_manager.terminate_instance(gpu.provider_id)
            
            self.db.delete(gpu)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to terminate spot instance {gpu.provider_id}: {e}")
