import time
from typing import Dict, List, Any, Callable, TypeVar, ParamSpec
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import psutil
from functools import wraps
from datetime import datetime, timedelta
import httpx
from ..core.rune_config import RuneSettings
import asyncio

logger = logging.getLogger(__name__)

# System Metrics
cpu_utilization = Gauge('cpu_utilization_percent', 'CPU utilization percentage')
ram_utilization = Gauge('ram_utilization_percent', 'RAM utilization percentage')

# GPU Metrics from RUNE
gpu_online_status = Gauge('gpu_online_status', 'GPU online status (1=online, 0=offline)', ['hostname'])
gpu_last_heartbeat = Gauge('gpu_last_heartbeat', 'Last GPU heartbeat timestamp', ['hostname'])
rune_api_status = Gauge('rune_api_status', 'RUNE API status (1=up, 0=down)', ['error_type'])
rune_api_last_check = Gauge('rune_api_last_check', 'Last time the RUNE API was checked')

# Job Metrics
gpu_jobs_queued = Gauge('gpu_jobs_queued_total', 'Total number of jobs in queued state')
gpu_jobs_running = Gauge('gpu_jobs_running_total', 'Total number of jobs in running state')
gpu_jobs_completed = Counter('gpu_jobs_completed_total', 'Total number of completed jobs', ['model_name'])
gpu_jobs_failed = Counter('gpu_jobs_failed_total', 'Total number of failed jobs', ['model_name'])

class GPUMetricsCollector:
    """Collects system and GPU metrics from RUNE API"""
    
    def __init__(self, rune_settings: RuneSettings):
        """Initialize the metrics collector"""
        self.rune_settings = rune_settings
        self.http_client = httpx.AsyncClient(
            base_url=rune_settings.RUNE_API_BASE_URL,
            headers={"x-api-key": rune_settings.RUNE_API_KEY}
        )
        self.last_collection_time = time.time()

    async def collect_rune_metrics(self) -> Dict[str, Any]:
        """Collect metrics from RUNE API"""
        try:
            # Update last check timestamp
            rune_api_last_check.set(time.time())
            
            # Reset error status
            rune_api_status.labels(error_type='maintenance').set(0)
            rune_api_status.labels(error_type='auth').set(0)
            rune_api_status.labels(error_type='connection').set(0)
            rune_api_status.labels(error_type='unknown').set(0)
            
            # Get GPU status from RUNE API
            endpoint = f"/customer-status/{self.rune_settings.RUNE_CLUSTER_ID}"
            response = await self.http_client.get(endpoint)
            
            if response.status_code == 200:
                data = response.json()
                # Update Prometheus metrics
                gpu_online_status.labels(hostname=data["hostname"]).set(1 if data["status_online"] else 0)
                
                # Convert UTC timestamp to seconds since epoch
                last_heartbeat = datetime.fromisoformat(data["last_heartbeat"].replace('Z', '+00:00'))
                gpu_last_heartbeat.labels(hostname=data["hostname"]).set(last_heartbeat.timestamp())
                
                logger.info(f"Successfully collected metrics from RUNE API for GPU {data['hostname']}")
                return data
            elif response.status_code == 401:
                logger.error("Unauthorized access to RUNE API. Please check your API key.")
                rune_api_status.labels(error_type='auth').set(1)
                return {}
            elif response.status_code == 404:
                logger.error(f"GPU cluster {self.rune_settings.RUNE_CLUSTER_ID} not found.")
                rune_api_status.labels(error_type='maintenance').set(1)
                return {}
            else:
                logger.error(f"Failed to collect RUNE metrics: {response.status_code} - {response.text}")
                rune_api_status.labels(error_type='unknown').set(1)
                return {}
        except httpx.ConnectError:
            logger.error("Failed to connect to RUNE API. Service might be down.")
            rune_api_status.labels(error_type='connection').set(1)
            return {}
        except Exception as e:
            logger.error(f"Error collecting RUNE metrics: {str(e)}")
            rune_api_status.labels(error_type='unknown').set(1)
            return {}
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics"""
        try:
            # Collect system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Update Prometheus metrics
            cpu_utilization.set(cpu_percent)
            ram_utilization.set(memory.percent)
            
            # Collect RUNE GPU metrics
            gpu_data = await self.collect_rune_metrics()
            
            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent
                },
                "gpu": gpu_data
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            return {}

# Type variables for decorator
P = ParamSpec('P')
T = TypeVar('T')

def monitor(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to monitor function execution and update metrics"""
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Update success metrics
            if hasattr(func, '__name__'):
                model_name = kwargs.get('model_name', 'unknown')
                gpu_jobs_completed.labels(model_name=model_name).inc()
            
            return result
        except Exception as e:
            # Update failure metrics
            if hasattr(func, '__name__'):
                model_name = kwargs.get('model_name', 'unknown')
                gpu_jobs_failed.labels(model_name=model_name).inc()
            raise
    return wrapper

def start_metrics_server(port: int = 9400):
    """Start the Prometheus metrics server"""
    try:
        start_http_server(port)
        logger.info(f"Started metrics server on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {str(e)}")
        raise

async def setup_monitoring(metrics_port: int = 9400):
    """Setup monitoring system"""
    try:
        # Start Prometheus metrics server
        start_metrics_server(metrics_port)
        
        # Initialize metrics collector
        rune_settings = RuneSettings()
        metrics = GPUMetricsCollector(rune_settings)
        
        # Start periodic collection
        while True:
            await metrics.collect_metrics()
            await asyncio.sleep(15)  # Collect every 15 seconds
            
    except Exception as e:
        logger.error(f"Error in monitoring setup: {str(e)}")
        raise

# Global metrics collector instance
rune_settings = RuneSettings()
metrics = GPUMetricsCollector(rune_settings)
