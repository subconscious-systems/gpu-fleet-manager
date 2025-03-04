"""
GPU Metrics Collection Module

This module uses NVIDIA Management Library (NVML) to collect real-time metrics
from NVIDIA GPUs. It provides functions to initialize the NVML library,
collect various metrics, and properly shut down the library.
"""

import logging
from typing import Dict, List, Any, Optional
import threading
import time
from datetime import datetime

# Import NVML with error handling
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    logging.warning("NVIDIA Management Library (pynvml) not available. GPU metrics will be simulated.")

# Thread-safe singleton pattern for NVML initialization
_nvml_lock = threading.Lock()
_nvml_initialized = False

logger = logging.getLogger(__name__)

def initialize_nvml() -> bool:
    """
    Initialize the NVIDIA Management Library (NVML).
    
    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    global _nvml_initialized
    
    if not NVML_AVAILABLE:
        logger.warning("NVML not available. Cannot initialize.")
        return False
    
    with _nvml_lock:
        if not _nvml_initialized:
            try:
                pynvml.nvmlInit()
                _nvml_initialized = True
                logger.info("NVML initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize NVML: {str(e)}")
                return False
        return True

def shutdown_nvml() -> bool:
    """
    Shut down the NVIDIA Management Library (NVML).
    
    Returns:
        bool: True if shutdown was successful, False otherwise.
    """
    global _nvml_initialized
    
    if not NVML_AVAILABLE:
        logger.warning("NVML not available. Nothing to shut down.")
        return False
    
    with _nvml_lock:
        if _nvml_initialized:
            try:
                pynvml.nvmlShutdown()
                _nvml_initialized = False
                logger.info("NVML shut down successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to shut down NVML: {str(e)}")
                return False
        return True

def get_gpu_count() -> int:
    """
    Get the number of NVIDIA GPUs in the system.
    
    Returns:
        int: Number of GPUs, or 0 if NVML is not available.
    """
    if not NVML_AVAILABLE or not initialize_nvml():
        return 0
    
    try:
        return pynvml.nvmlDeviceGetCount()
    except Exception as e:
        logger.error(f"Failed to get GPU count: {str(e)}")
        return 0

def get_gpu_handle(index: int) -> Optional[Any]:
    """
    Get a handle to a specific GPU.
    
    Args:
        index (int): The index of the GPU.
        
    Returns:
        Optional[Any]: GPU handle or None if the GPU is not available.
    """
    if not NVML_AVAILABLE or not initialize_nvml():
        return None
    
    try:
        return pynvml.nvmlDeviceGetHandleByIndex(index)
    except Exception as e:
        logger.error(f"Failed to get handle for GPU {index}: {str(e)}")
        return None

def get_gpu_name(handle: Any) -> str:
    """
    Get the name of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        str: Name of the GPU or "Unknown" if not available.
    """
    if not NVML_AVAILABLE or handle is None:
        return "Unknown"
    
    try:
        return pynvml.nvmlDeviceGetName(handle).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to get GPU name: {str(e)}")
        return "Unknown"

def get_gpu_uuid(handle: Any) -> str:
    """
    Get the UUID of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        str: UUID of the GPU or "Unknown" if not available.
    """
    if not NVML_AVAILABLE or handle is None:
        return "Unknown"
    
    try:
        return pynvml.nvmlDeviceGetUUID(handle).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to get GPU UUID: {str(e)}")
        return "Unknown"

def get_gpu_utilization(handle: Any) -> Dict[str, int]:
    """
    Get the utilization percentages of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        Dict[str, int]: Dictionary with GPU and memory utilization percentages.
    """
    if not NVML_AVAILABLE or handle is None:
        return {"gpu": 0, "memory": 0}
    
    try:
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return {
            "gpu": utilization.gpu,
            "memory": utilization.memory
        }
    except Exception as e:
        logger.error(f"Failed to get GPU utilization: {str(e)}")
        return {"gpu": 0, "memory": 0}

def get_gpu_memory(handle: Any) -> Dict[str, int]:
    """
    Get memory information of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        Dict[str, int]: Dictionary with total, used, and free memory in MB.
    """
    if not NVML_AVAILABLE or handle is None:
        return {"total": 0, "used": 0, "free": 0}
    
    try:
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        # Convert bytes to MB
        total = memory.total // (1024 * 1024)
        used = memory.used // (1024 * 1024)
        free = memory.free // (1024 * 1024)
        
        return {
            "total": total,
            "used": used,
            "free": free
        }
    except Exception as e:
        logger.error(f"Failed to get GPU memory: {str(e)}")
        return {"total": 0, "used": 0, "free": 0}

def get_gpu_temperature(handle: Any) -> int:
    """
    Get the temperature of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        int: Temperature in Celsius, or 0 if not available.
    """
    if not NVML_AVAILABLE or handle is None:
        return 0
    
    try:
        return pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
    except Exception as e:
        logger.error(f"Failed to get GPU temperature: {str(e)}")
        return 0

def get_gpu_power_usage(handle: Any) -> float:
    """
    Get the power usage of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        float: Power usage in watts, or 0.0 if not available.
    """
    if not NVML_AVAILABLE or handle is None:
        return 0.0
    
    try:
        # Power usage is returned in milliwatts, convert to watts
        return pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
    except Exception as e:
        logger.error(f"Failed to get GPU power usage: {str(e)}")
        return 0.0

def get_gpu_clock_speeds(handle: Any) -> Dict[str, int]:
    """
    Get the clock speeds of a GPU.
    
    Args:
        handle (Any): GPU handle obtained from get_gpu_handle.
        
    Returns:
        Dict[str, int]: Dictionary with graphics and memory clock speeds in MHz.
    """
    if not NVML_AVAILABLE or handle is None:
        return {"graphics": 0, "memory": 0}
    
    try:
        graphics_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
        memory_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
        
        return {
            "graphics": graphics_clock,
            "memory": memory_clock
        }
    except Exception as e:
        logger.error(f"Failed to get GPU clock speeds: {str(e)}")
        return {"graphics": 0, "memory": 0}

def get_all_gpu_metrics() -> List[Dict[str, Any]]:
    """
    Get metrics from all available GPUs in the system.
    
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing metrics for each GPU.
    """
    gpu_metrics = []
    gpu_count = get_gpu_count()
    
    for i in range(gpu_count):
        handle = get_gpu_handle(i)
        if handle:
            gpu_info = {
                "id": f"gpu-{i}",
                "name": get_gpu_name(handle),
                "uuid": get_gpu_uuid(handle),
                "utilization": get_gpu_utilization(handle)["gpu"],
                "memory": get_gpu_memory(handle),
                "temperature": get_gpu_temperature(handle),
                "power_usage": get_gpu_power_usage(handle),
                "clock_speeds": get_gpu_clock_speeds(handle)
            }
            gpu_metrics.append(gpu_info)
    
    # If no GPUs are available or metrics couldn't be collected, return a placeholder
    if not gpu_metrics and not NVML_AVAILABLE:
        logger.warning("No GPUs available or NVML not available. Returning placeholder data.")
        gpu_metrics = [{
            "id": "gpu-0",
            "name": "Simulated GPU",
            "uuid": "GPU-00000000-0000-0000-0000-000000000000",
            "utilization": 0,
            "memory": {"total": 16384, "used": 0, "free": 16384},
            "temperature": 0,
            "power_usage": 0.0,
            "clock_speeds": {"graphics": 0, "memory": 0}
        }]
    
    return gpu_metrics

def get_formatted_gpu_metrics() -> Dict[str, Any]:
    """
    Get formatted GPU metrics for API response.
    
    Returns:
        Dict[str, Any]: Dictionary with timestamp and GPU metrics.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "gpus": get_all_gpu_metrics()
    }

# Cleanup handler to ensure NVML is properly shut down
import atexit
atexit.register(shutdown_nvml)

# Module-level storage for periodic metrics collection
_last_metrics = None
_metrics_lock = threading.Lock()

def start_metrics_collection(interval_seconds: int = 60):
    """
    Start collecting GPU metrics in the background at specified intervals.
    
    Args:
        interval_seconds (int): Interval between collections in seconds.
    """
    global _last_metrics
    
    def collection_task():
        global _last_metrics
        while True:
            metrics = get_formatted_gpu_metrics()
            with _metrics_lock:
                _last_metrics = metrics
            time.sleep(interval_seconds)
    
    # Start the collection thread
    thread = threading.Thread(target=collection_task, daemon=True)
    thread.start()
    logger.info(f"Started background GPU metrics collection with interval of {interval_seconds} seconds")

def get_latest_metrics() -> Dict[str, Any]:
    """
    Get the latest collected metrics or collect them on demand if not available.
    
    Returns:
        Dict[str, Any]: The latest GPU metrics.
    """
    global _last_metrics
    
    with _metrics_lock:
        if _last_metrics is None:
            # If no metrics have been collected yet, collect them now
            _last_metrics = get_formatted_gpu_metrics()
        return _last_metrics
