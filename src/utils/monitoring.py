import time
from typing import Dict, List
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import torch
import psutil
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Existing GPU Metrics (compatible with server-experimentation)
gpu_memory_used = Gauge('gpu_memory_used_bytes', 'GPU memory used in bytes', ['device'])
gpu_memory_total = Gauge('gpu_memory_total_bytes', 'Total GPU memory in bytes', ['device'])
gpu_utilization = Gauge('gpu_utilization_percent', 'GPU utilization percentage', ['device'])
cpu_utilization = Gauge('cpu_utilization_percent', 'CPU utilization percentage')
ram_utilization = Gauge('ram_utilization_percent', 'RAM utilization percentage')

# New Fleet Manager Metrics
gpu_jobs_queued = Gauge('gpu_jobs_queued_total', 'Total number of jobs in queued state')
gpu_jobs_running = Gauge('gpu_jobs_running_total', 'Total number of jobs in running state')
gpu_jobs_completed = Counter('gpu_jobs_completed_total', 'Total number of completed jobs', ['model_name'])
gpu_jobs_failed = Counter('gpu_jobs_failed_total', 'Total number of failed jobs', ['model_name'])

gpu_allocation_time = Histogram(
    'gpu_allocation_seconds',
    'Time taken to allocate GPU for job',
    ['model_name'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

model_load_time = Histogram(
    'model_load_seconds',
    'Time taken to load model into GPU',
    ['model_name'],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

spot_instance_count = Gauge('spot_instances_total', 'Total number of spot instances', ['provider'])
spot_instance_cost = Gauge('spot_instance_cost_hourly', 'Hourly cost of spot instances', ['provider'])

# Cost Optimization Metrics
gpu_cost_per_job = Histogram(
    'gpu_cost_per_job_dollars',
    'Cost per job execution',
    ['model_name', 'provider'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0)
)

gpu_idle_time = Gauge(
    'gpu_idle_seconds_total',
    'Total time GPU spent idle',
    ['device_id', 'provider']
)

gpu_efficiency = Gauge(
    'gpu_efficiency_percent',
    'GPU efficiency score based on utilization and cost',
    ['device_id', 'provider']
)

cost_savings = Counter(
    'cost_savings_dollars_total',
    'Total cost savings from optimization strategies',
    ['strategy']
)

batch_efficiency = Histogram(
    'batch_efficiency_ratio',
    'Ratio of actual vs optimal batch size',
    ['model_name'],
    buckets=(0.1, 0.3, 0.5, 0.7, 0.9, 1.0)
)

class GPUMetricsCollector:
    def __init__(self, db_session):
        self.db = db_session
        self.diagnostics = GPUDiagnostics()
        self.last_collection_time = time.time()
        self.base_costs = {
            'A100': 3.0,  # Cost per hour
            'A6000': 2.0,
            'V100': 1.5,
            'T4': 0.5
        }
        self.model_requirements = {}

    async def collect_basic_metrics(self):
        """Collect basic system and GPU metrics (compatible with existing exporter)"""
        # CPU metrics
        cpu_utilization.set(psutil.cpu_percent())
        
        # RAM metrics
        ram = psutil.virtual_memory()
        ram_utilization.set(ram.percent)
        
        # GPU metrics
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                # Get GPU memory information
                memory_allocated = torch.cuda.memory_allocated(i)
                total_memory = torch.cuda.get_device_properties(i).total_memory
                
                # Update metrics (compatible with existing format)
                gpu_memory_used.labels(device=f'gpu{i}').set(memory_allocated)
                gpu_memory_total.labels(device=f'gpu{i}').set(total_memory)
                utilization = (memory_allocated / total_memory) * 100
                gpu_utilization.labels(device=f'gpu{i}').set(utilization)

    async def collect_fleet_metrics(self):
        """Collect GPU fleet-specific metrics"""
        from ..models.job import Job, JobStatus
        from ..models.gpu import GPU, GPUProvider

        # Job metrics
        queued = self.db.query(Job).filter(Job.status == JobStatus.QUEUED).count()
        running = self.db.query(Job).filter(Job.status == JobStatus.RUNNING).count()
        gpu_jobs_queued.set(queued)
        gpu_jobs_running.set(running)

        # Spot instance metrics
        for provider in ['sfcompute', 'vast', 'aws']:
            count = self.db.query(GPU).filter(
                GPU.provider == GPUProvider.SPOT,
                GPU.provider_id.like(f"{provider}%")
            ).count()
            spot_instance_count.labels(provider=provider).set(count)

            # Calculate total hourly cost for this provider
            total_cost = sum(
                gpu.cost_per_hour for gpu in 
                self.db.query(GPU).filter(
                    GPU.provider == GPUProvider.SPOT,
                    GPU.provider_id.like(f"{provider}%")
                ).all()
            )
            spot_instance_cost.labels(provider=provider).set(total_cost)

    async def collect_cost_metrics(self):
        """Collect cost optimization metrics"""
        from ..models.job import Job, JobStatus
        from ..models.gpu import GPU, GPUProvider
        current_time = time.time()
        
        # Calculate idle time and efficiency for each GPU
        gpus = self.db.query(GPU).all()
        for gpu in gpus:
            # Calculate idle time
            if not gpu.current_jobs:
                idle_time = current_time - gpu.last_job_end_time if gpu.last_job_end_time else 0
                gpu_idle_time.labels(
                    device_id=gpu.id,
                    provider=gpu.provider
                ).set(idle_time)
            
            # Calculate GPU efficiency score (0-100)
            # Based on: utilization %, cost efficiency, and job throughput
            utilization_score = len(gpu.current_jobs) / gpu.max_jobs if gpu.max_jobs > 0 else 0
            cost_score = self._calculate_cost_efficiency(gpu)
            throughput_score = self._calculate_throughput_score(gpu)
            
            efficiency_score = (
                utilization_score * 0.4 +
                cost_score * 0.3 +
                throughput_score * 0.3
            ) * 100
            
            gpu_efficiency.labels(
                device_id=gpu.id,
                provider=gpu.provider
            ).set(efficiency_score)

        # Calculate cost savings from different strategies
        self._track_spot_savings()
        self._track_batching_savings()
        self._track_autoscaling_savings()

    def _calculate_cost_efficiency(self, gpu: GPU) -> float:
        """Calculate cost efficiency score (0-1) for a GPU"""
        # Get base cost for this GPU type
        base_cost = self.base_costs.get(gpu.model, 1.0)
        
        # Calculate actual cost per compute unit
        actual_cost = gpu.cost_per_hour
        if actual_cost == 0:
            return 1.0  # Avoid division by zero
            
        # Score is ratio of base to actual cost, normalized to 0-1
        # Lower actual cost = higher score
        score = base_cost / actual_cost
        return min(score, 1.0)  # Cap at 1.0

    def _calculate_throughput_score(self, gpu: GPU) -> float:
        """Calculate job throughput efficiency score (0-1)"""
        # Get completed jobs in last hour
        completed_jobs = self.db.query(Job).filter(
            Job.compute_id == gpu.id,
            Job.status == JobStatus.COMPLETED,
            Job.completed_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        # Calculate throughput score based on GPU capability
        expected_throughput = gpu.max_jobs * 0.8  # Expected 80% of max
        if expected_throughput == 0:
            return 0.0
            
        score = completed_jobs / expected_throughput
        return min(score, 1.0)  # Cap at 1.0

    def _track_spot_savings(self):
        """Track cost savings from spot instance usage"""
        spot_gpus = self.db.query(GPU).filter(
            GPU.provider == GPUProvider.SPOT
        ).all()
        
        total_savings = 0
        for gpu in spot_gpus:
            # Calculate difference between spot and on-demand price
            base_cost = self.base_costs.get(gpu.model, 1.0)
            savings_per_hour = base_cost - gpu.cost_per_hour
            
            # Accumulate savings
            if savings_per_hour > 0:
                # Convert to savings since last collection
                hours_since_last = (time.time() - self.last_collection_time) / 3600
                total_savings += savings_per_hour * hours_since_last
        
        if total_savings > 0:
            cost_savings.labels(strategy='spot_instances').inc(total_savings)

    def _track_batching_savings(self):
        """Track cost savings from efficient batching"""
        # Get all running jobs
        running_jobs = self.db.query(Job).filter(
            Job.status == JobStatus.RUNNING
        ).all()
        
        for job in running_jobs:
            if not job.batch_size or not job.model_name:
                continue
                
            # Get optimal batch size for this model
            optimal_batch = self.model_requirements.get(
                job.model_name, {}
            ).get('max_batch_size', 1)
            
            # Calculate batch efficiency
            if optimal_batch > 0:
                efficiency = job.batch_size / optimal_batch
                batch_efficiency.labels(
                    model_name=job.model_name
                ).observe(efficiency)
                
                # Calculate cost savings from batching
                if job.batch_size > 1:
                    # Assume linear cost savings from batching
                    base_cost = self.base_costs.get(job.gpu_model, 1.0)
                    savings = base_cost * (job.batch_size - 1) / job.batch_size
                    cost_savings.labels(strategy='batching').inc(savings)

    def _track_autoscaling_savings(self):
        """Track cost savings from autoscaling"""
        # Calculate savings from shutting down idle GPUs
        terminated_gpus = self.db.query(GPU).filter(
            GPU.status == GPUStatus.TERMINATED,
            GPU.terminated_at >= datetime.utcnow() - timedelta(hours=1)
        ).all()
        
        total_savings = 0
        for gpu in terminated_gpus:
            # Calculate savings as cost avoided during idle time
            idle_duration = (gpu.terminated_at - gpu.last_job_end_time).total_seconds() / 3600
            savings = gpu.cost_per_hour * idle_duration
            total_savings += savings
        
        if total_savings > 0:
            cost_savings.labels(strategy='autoscaling').inc(total_savings)

    async def collect_all_metrics(self):
        """Collect all metrics"""
        await self.collect_basic_metrics()
        await self.collect_fleet_metrics()
        await self.collect_cost_metrics()
        self.last_collection_time = time.time()

def monitor(func):
    """Decorator to monitor function execution and update metrics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract model name if present in args/kwargs
        model_name = "unknown"
        for arg in args + tuple(kwargs.values()):
            if hasattr(arg, 'model_name'):
                model_name = arg.model_name
                break

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            
            # Update success metrics
            if func.__name__ == 'allocate_for_job':
                gpu_allocation_time.labels(model_name=model_name).observe(
                    time.time() - start_time
                )
            elif func.__name__ == '_run_job':
                gpu_jobs_completed.labels(model_name=model_name).inc()
            
            return result
            
        except Exception as e:
            # Update error metrics
            if func.__name__ == '_run_job':
                gpu_jobs_failed.labels(model_name=model_name).inc()
            raise e
            
    return wrapper

def start_metrics_server(port: int = 9400):
    """Start the Prometheus metrics server"""
    try:
        start_http_server(port)
        logger.info(f"GPU metrics exporter started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise
