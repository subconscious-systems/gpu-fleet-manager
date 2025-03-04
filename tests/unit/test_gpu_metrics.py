"""
Unit tests for GPU metrics module.

These tests can run without actual GPU hardware by mocking the NVML library.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime

# Create mock for pynvml module
class MockPynvml:
    NVML_TEMPERATURE_GPU = 0
    NVML_CLOCK_GRAPHICS = 0
    NVML_CLOCK_MEM = 1
    
    @staticmethod
    def nvmlInit():
        return None
    
    @staticmethod
    def nvmlShutdown():
        return None
    
    @staticmethod
    def nvmlDeviceGetCount():
        return 2
    
    @staticmethod
    def nvmlDeviceGetHandleByIndex(index):
        return f"handle-{index}"
    
    @staticmethod
    def nvmlDeviceGetName(handle):
        return b"NVIDIA GeForce RTX 3080"
    
    @staticmethod
    def nvmlDeviceGetUUID(handle):
        index = int(handle.split("-")[1])
        return f"GPU-{index}".encode('utf-8')
    
    class MockUtilization:
        def __init__(self):
            self.gpu = 80
            self.memory = 75
    
    @staticmethod
    def nvmlDeviceGetUtilizationRates(handle):
        return MockPynvml.MockUtilization()
    
    class MockMemory:
        def __init__(self):
            self.total = 10737418240  # 10 GB in bytes
            self.used = 4294967296    # 4 GB in bytes
            self.free = 6442450944    # 6 GB in bytes
    
    @staticmethod
    def nvmlDeviceGetMemoryInfo(handle):
        return MockPynvml.MockMemory()
    
    @staticmethod
    def nvmlDeviceGetTemperature(handle, sensor_type):
        return 70
    
    @staticmethod
    def nvmlDeviceGetPowerUsage(handle):
        return 200000  # 200 watts in milliwatts
    
    @staticmethod
    def nvmlDeviceGetClockInfo(handle, clock_type):
        if clock_type == MockPynvml.NVML_CLOCK_GRAPHICS:
            return 1500
        else:
            return 7000

# Add the mock to sys.modules
sys.modules['pynvml'] = MockPynvml()

# Now import the module to be tested
from src.utils.gpu_metrics import (
    initialize_nvml, shutdown_nvml, get_gpu_count, get_gpu_handle,
    get_gpu_name, get_gpu_uuid, get_gpu_utilization, get_gpu_memory,
    get_gpu_temperature, get_gpu_power_usage, get_gpu_clock_speeds,
    get_all_gpu_metrics, get_formatted_gpu_metrics
)

class TestGpuMetrics:
    """Test suite for GPU metrics module."""
    
    def test_initialize_nvml(self):
        """Test NVML initialization."""
        assert initialize_nvml() is True
    
    def test_shutdown_nvml(self):
        """Test NVML shutdown."""
        assert shutdown_nvml() is True
    
    def test_get_gpu_count(self):
        """Test getting GPU count."""
        assert get_gpu_count() == 2
    
    def test_get_gpu_handle(self):
        """Test getting GPU handle."""
        handle = get_gpu_handle(0)
        assert handle == "handle-0"
    
    def test_get_gpu_name(self):
        """Test getting GPU name."""
        handle = get_gpu_handle(0)
        assert get_gpu_name(handle) == "NVIDIA GeForce RTX 3080"
    
    def test_get_gpu_uuid(self):
        """Test getting GPU UUID."""
        handle = get_gpu_handle(0)
        assert get_gpu_uuid(handle) == "GPU-0"
    
    def test_get_gpu_utilization(self):
        """Test getting GPU utilization."""
        handle = get_gpu_handle(0)
        utilization = get_gpu_utilization(handle)
        assert utilization["gpu"] == 80
        assert utilization["memory"] == 75
    
    def test_get_gpu_memory(self):
        """Test getting GPU memory."""
        handle = get_gpu_handle(0)
        memory = get_gpu_memory(handle)
        assert memory["total"] == 10240  # 10 GB in MB
        assert memory["used"] == 4096    # 4 GB in MB
        assert memory["free"] == 6144    # 6 GB in MB
    
    def test_get_gpu_temperature(self):
        """Test getting GPU temperature."""
        handle = get_gpu_handle(0)
        assert get_gpu_temperature(handle) == 70
    
    def test_get_gpu_power_usage(self):
        """Test getting GPU power usage."""
        handle = get_gpu_handle(0)
        assert get_gpu_power_usage(handle) == 200.0
    
    def test_get_gpu_clock_speeds(self):
        """Test getting GPU clock speeds."""
        handle = get_gpu_handle(0)
        clock_speeds = get_gpu_clock_speeds(handle)
        assert clock_speeds["graphics"] == 1500
        assert clock_speeds["memory"] == 7000
    
    def test_get_all_gpu_metrics(self):
        """Test getting metrics for all GPUs."""
        metrics = get_all_gpu_metrics()
        assert len(metrics) == 2
        assert metrics[0]["id"] == "gpu-0"
        assert metrics[0]["name"] == "NVIDIA GeForce RTX 3080"
        assert metrics[0]["utilization"] == 80
        assert metrics[0]["temperature"] == 70
        assert metrics[0]["power_usage"] == 200.0
    
    def test_get_formatted_gpu_metrics(self):
        """Test getting formatted GPU metrics."""
        metrics = get_formatted_gpu_metrics()
        assert "timestamp" in metrics
        assert "gpus" in metrics
        assert len(metrics["gpus"]) == 2
    
    def test_error_handling(self):
        """Test error handling when NVML functions fail."""
        with patch('pynvml.nvmlDeviceGetCount', side_effect=Exception("Test error")):
            assert get_gpu_count() == 0
        
        with patch('pynvml.nvmlDeviceGetHandleByIndex', side_effect=Exception("Test error")):
            assert get_gpu_handle(0) is None
        
        handle = get_gpu_handle(0)
        with patch('pynvml.nvmlDeviceGetName', side_effect=Exception("Test error")):
            assert get_gpu_name(handle) == "Unknown"
        
        with patch('pynvml.nvmlDeviceGetMemoryInfo', side_effect=Exception("Test error")):
            memory = get_gpu_memory(handle)
            assert memory == {"total": 0, "used": 0, "free": 0}

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
