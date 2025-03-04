from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import psutil
import logging
from datetime import datetime
from src.utils.gpu_metrics import get_formatted_gpu_metrics, initialize_nvml, shutdown_nvml, start_metrics_collection

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Service is unhealthy"
        )

@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )

@router.get("/gpu-metrics", response_model=Dict[str, Any])
async def get_gpu_metrics():
    """Get GPU metrics using NVML"""
    try:
        # Get GPU metrics using our new module
        metrics = get_formatted_gpu_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get GPU metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GPU metrics: {str(e)}"
        )

# Initialize NVML when the module is loaded
try:
    initialize_nvml()
    # Start collecting metrics in the background every 30 seconds
    start_metrics_collection(interval_seconds=30)
    logger.info("NVML initialized and background metrics collection started")
except Exception as e:
    logger.error(f"Failed to initialize NVML: {str(e)}")

# Ensure NVML is properly shut down when the application exits
import atexit
atexit.register(shutdown_nvml)
