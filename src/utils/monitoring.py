import time
from typing import Dict, List, Any, Callable, TypeVar, ParamSpec
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import psutil
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# System Metrics
cpu_utilization = Gauge('cpu_utilization_percent', 'CPU utilization percentage')
ram_utilization = Gauge('ram_utilization_percent', 'RAM utilization percentage')

# GPU Metrics
gpu_memory_used = Gauge('gpu_memory_used_bytes', 'GPU memory used in bytes', ['device'])
gpu_memory_total = Gauge('gpu_memory_total_bytes', 'Total GPU memory in bytes', ['device'])
gpu_utilization = Gauge('gpu_utilization_percent', 'GPU utilization percentage', ['device'])

# Job Metrics
gpu_jobs_queued = Gauge('gpu_jobs_queued_total', 'Total number of jobs in queued state')
gpu_jobs_running = Gauge('gpu_jobs_running_total', 'Total number of jobs in running state')
gpu_jobs_completed = Counter('gpu_jobs_completed_total', 'Total number of completed jobs', ['model_name'])
gpu_jobs_failed = Counter('gpu_jobs_failed_total', 'Total number of failed jobs', ['model_name'])

class GPUMetricsCollector:
    """Collects system and GPU metrics"""
    
    def __init__(self):
        """Initialize the metrics collector"""
        self.last_collection_time = time.time()
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics"""
        try:
            # Collect system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Update Prometheus metrics
            cpu_utilization.set(cpu_percent)
            ram_utilization.set(memory.percent)
            
            # Simulate GPU metrics for now
            gpu_data = self._simulate_gpu_metrics()
            for gpu in gpu_data["gpus"]:
                device = gpu["id"]
                gpu_memory_used.labels(device=device).set(gpu["memory"]["used"])
                gpu_memory_total.labels(device=device).set(gpu["memory"]["total"])
                gpu_utilization.labels(device=device).set(gpu["utilization"])
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent
                    }
                },
                "gpus": gpu_data["gpus"]
            }
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def _simulate_gpu_metrics(self) -> Dict[str, Any]:
        """Simulate GPU metrics for testing"""
        return {
            "gpus": [
                {
                    "id": "gpu-0",
                    "name": "NVIDIA A100",
                    "memory": {
                        "total": 40960,  # 40GB
                        "used": 20480,   # 20GB
                        "free": 20480    # 20GB
                    },
                    "utilization": 75.5,
                    "temperature": 65.0,
                    "power_draw": 250.0
                }
            ]
        }

# Type variables for decorator
P = ParamSpec('P')
T = TypeVar('T')

def monitor(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to monitor function execution and update metrics"""
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Extract model name if present in args/kwargs
        model_name = "unknown"
        for arg in args + tuple(kwargs.values()):
            if hasattr(arg, 'model_name'):
                model_name = arg.model_name
                break

        try:
            result = await func(*args, **kwargs)
            
            # Update success metrics
            if func.__name__ == '_run_job':
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
        logger.info(f"Started metrics server on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {str(e)}")
        raise

# Global metrics collector instance
metrics = GPUMetricsCollector()

def setup_monitoring(metrics_port: int = 9400):
    """Setup monitoring system"""
    try:
        # Start Prometheus metrics server
        start_metrics_server(metrics_port)
        
        # Initialize metrics collector
        global metrics
        metrics = GPUMetricsCollector()
        
        logger.info("Monitoring system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to setup monitoring: {str(e)}")
        raise
