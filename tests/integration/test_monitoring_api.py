"""
Integration tests for monitoring API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys

# Import the main FastAPI app
from src.main import app
from src.utils import gpu_metrics

client = TestClient(app)

class TestMonitoringAPI:
    """Test suite for monitoring API endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/v1/monitoring/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_system_metrics(self):
        """Test system metrics endpoint."""
        response = client.get("/api/v1/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "system" in data
        assert "cpu_percent" in data["system"]
        assert "memory" in data["system"]
        assert "disk" in data["system"]
    
    @patch('src.utils.gpu_metrics.get_formatted_gpu_metrics')
    def test_gpu_metrics(self, mock_get_gpu_metrics):
        """Test GPU metrics endpoint."""
        # Mock the GPU metrics response
        mock_metrics = {
            "timestamp": "2025-03-04T12:00:00.000000",
            "gpus": [
                {
                    "id": "gpu-0",
                    "name": "NVIDIA GeForce RTX 3080",
                    "uuid": "GPU-0",
                    "utilization": 80,
                    "memory": {
                        "total": 10240,
                        "used": 4096,
                        "free": 6144
                    },
                    "temperature": 70,
                    "power_usage": 200.0,
                    "clock_speeds": {
                        "graphics": 1500,
                        "memory": 7000
                    }
                }
            ]
        }
        mock_get_gpu_metrics.return_value = mock_metrics
        
        response = client.get("/api/v1/monitoring/gpu-metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "gpus" in data
        assert len(data["gpus"]) == 1
        gpu = data["gpus"][0]
        assert gpu["id"] == "gpu-0"
        assert gpu["name"] == "NVIDIA GeForce RTX 3080"
        assert gpu["utilization"] == 80
        assert gpu["temperature"] == 70
        assert gpu["power_usage"] == 200.0
    
    @patch('src.utils.gpu_metrics.get_formatted_gpu_metrics')
    def test_gpu_metrics_error_handling(self, mock_get_gpu_metrics):
        """Test error handling in GPU metrics endpoint."""
        # Mock an exception
        mock_get_gpu_metrics.side_effect = Exception("Test error")
        
        response = client.get("/api/v1/monitoring/gpu-metrics")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to get GPU metrics" in data["detail"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
