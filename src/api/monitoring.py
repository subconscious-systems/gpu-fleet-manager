from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import psutil
import logging
from datetime import datetime

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
    """Get GPU metrics"""
    try:
        # TODO: Implement actual GPU metrics collection
        # This is a placeholder that would be replaced with actual GPU monitoring
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "gpus": [
                {
                    "id": "gpu-1",
                    "utilization": 75.5,
                    "memory": {
                        "total": 16384,
                        "used": 8192,
                        "free": 8192
                    },
                    "temperature": 65
                }
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get GPU metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GPU metrics: {str(e)}"
        )
