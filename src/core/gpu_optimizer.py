from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.job import Job, JobStatus, JobPriority
from ..models.gpu import GPU, GPUStatus
from ..utils.monitoring import monitor

logger = logging.getLogger(__name__)

class GPUOptimizer:
    def __init__(self, db: Session):
        self.db = db
        # Model-specific batching configurations
        self.model_configs = {
            "phi-2": {
                "max_batch_size": 4,
                "max_sequence_length": 2048,
                "memory_per_token": 0.5,  # MB per token
                "base_memory": 16000,     # Base model memory in MB
                "supports_batching": True,
                "batch_padding_penalty": 0.1  # Performance penalty for uneven batches
            },
            "deepseek-coder": {
                "max_batch_size": 2,
                "max_sequence_length": 4096,
                "memory_per_token": 1.0,
                "base_memory": 24000,
                "supports_batching": True,
                "batch_padding_penalty": 0.15
            },
            "stable-diffusion-xl": {
                "max_batch_size": 4,
                "memory_per_image": 3000,  # MB per image
                "base_memory": 12000,
                "supports_batching": True,
                "batch_padding_penalty": 0.05
            }
        }

    @monitor
    async def optimize_gpu_allocation(self, gpu: GPU) -> List[Job]:
        """Find optimal batch of jobs for a GPU"""
        available_memory = gpu.available_memory
        queued_jobs = self._get_candidate_jobs()
        
        if not queued_jobs:
            return []

        # Group jobs by model type
        model_groups = self._group_jobs_by_model(queued_jobs)
        best_batch = []
        best_score = 0

        for model_name, jobs in model_groups.items():
            if not jobs:
                continue

            config = self.model_configs.get(model_name, {})
            if not config:
                continue

            # Try different batch combinations
            batch, score = self._find_optimal_batch(
                jobs=jobs,
                available_memory=available_memory,
                config=config
            )

            if score > best_score:
                best_batch = batch
                best_score = score

        return best_batch

    def _get_candidate_jobs(self) -> List[Job]:
        """Get jobs that could be batched together"""
        return self.db.query(Job).filter(
            and_(
                Job.status == JobStatus.QUEUED,
                or_(
                    *[Job.model_name == model 
                      for model in self.model_configs.keys()]
                )
            )
        ).order_by(
            Job.priority.desc(),
            Job.created_at.asc()
        ).all()

    def _group_jobs_by_model(self, jobs: List[Job]) -> Dict[str, List[Job]]:
        """Group jobs by model type for potential batching"""
        groups = {}
        for job in jobs:
            if job.model_name not in groups:
                groups[job.model_name] = []
            groups[job.model_name].append(job)
        return groups

    def _find_optimal_batch(
        self,
        jobs: List[Job],
        available_memory: int,
        config: Dict
    ) -> Tuple[List[Job], float]:
        """Find optimal batch of jobs that maximizes GPU utilization"""
        if not config["supports_batching"]:
            # If batching not supported, return highest priority job
            return ([jobs[0]], self._calculate_job_score(jobs[0]))

        best_batch = []
        best_score = 0
        max_batch_size = config["max_batch_size"]

        # Try different batch sizes
        for batch_size in range(1, min(len(jobs) + 1, max_batch_size + 1)):
            for i in range(len(jobs) - batch_size + 1):
                batch = jobs[i:i + batch_size]
                memory_required = self._calculate_batch_memory(batch, config)
                
                if memory_required <= available_memory:
                    score = self._calculate_batch_score(batch, config)
                    if score > best_score:
                        best_batch = batch
                        best_score = score

        return best_batch, best_score

    def _calculate_batch_memory(self, jobs: List[Job], config: Dict) -> int:
        """Calculate memory required for a batch of jobs"""
        if not jobs:
            return 0

        base_memory = config["base_memory"]
        
        if jobs[0].model_name.startswith("stable-diffusion"):
            # For image generation, each job adds significant memory
            return base_memory + sum(
                config["memory_per_image"]
                for job in jobs
            )
        else:
            # For text models, calculate based on token length
            max_tokens = max(
                len(job.parameters.get("prompt", "")) * 1.5  # Estimate tokens
                for job in jobs
            )
            return base_memory + (max_tokens * config["memory_per_token"] * len(jobs))

    def _calculate_batch_score(self, jobs: List[Job], config: Dict) -> float:
        """Calculate optimization score for a batch of jobs"""
        if not jobs:
            return 0

        # Base score from priority and age
        priority_scores = [
            job.priority * (1 + (datetime.utcnow() - job.created_at).total_seconds() / 3600)
            for job in jobs
        ]
        
        # Efficiency bonus for optimal batch sizes
        batch_size = len(jobs)
        efficiency = batch_size / config["max_batch_size"]
        
        # Penalty for uneven batches (e.g., different sequence lengths)
        if jobs[0].model_name.startswith("stable-diffusion"):
            uniformity = 1.0  # Image generation is uniform
        else:
            # Calculate variance in sequence lengths
            lengths = [len(job.parameters.get("prompt", "")) for job in jobs]
            uniformity = 1.0 - (np.std(lengths) / np.mean(lengths) if lengths else 0)

        # Combined score
        batch_score = (
            sum(priority_scores) *           # Priority and age
            (1.0 + efficiency) *             # Batch efficiency bonus
            (1.0 - config["batch_padding_penalty"] * (1 - uniformity))  # Uniformity
        )

        return batch_score

    def _calculate_job_score(self, job: Job) -> float:
        """Calculate score for a single job"""
        age_hours = (datetime.utcnow() - job.created_at).total_seconds() / 3600
        return job.priority * (1 + age_hours)

    @monitor
    async def rebalance_gpus(self):
        """Rebalance jobs across GPUs for optimal utilization"""
        available_gpus = self.db.query(GPU).filter(
            GPU.status.in_([GPUStatus.AVAILABLE, GPUStatus.BUSY])
        ).all()

        # Calculate current utilization
        for gpu in available_gpus:
            current_jobs = self.db.query(Job).filter(
                Job.gpu_assigned == gpu.id,
                Job.status == JobStatus.RUNNING
            ).all()

            # Check if GPU is underutilized
            if self._is_gpu_underutilized(gpu, current_jobs):
                # Try to find more jobs to add to this GPU
                new_jobs = await self.optimize_gpu_allocation(gpu)
                if new_jobs:
                    await self._migrate_jobs_to_gpu(new_jobs, gpu)

    def _is_gpu_underutilized(self, gpu: GPU, current_jobs: List[Job]) -> bool:
        """Check if a GPU is significantly underutilized"""
        if not current_jobs:
            return True

        # Get model config for current jobs
        model_name = current_jobs[0].model_name
        config = self.model_configs.get(model_name, {})
        if not config:
            return False

        # Check batch utilization
        batch_utilization = len(current_jobs) / config["max_batch_size"]
        memory_utilization = (gpu.total_memory - gpu.available_memory) / gpu.total_memory

        return batch_utilization < 0.5 or memory_utilization < 0.4

    async def _migrate_jobs_to_gpu(self, jobs: List[Job], target_gpu: GPU):
        """Migrate jobs to a specific GPU"""
        for job in jobs:
            job.gpu_assigned = target_gpu.id
            job.status = JobStatus.PENDING
        self.db.commit()
