# GPU Metrics Collection

This document describes the GPU metrics collection system implemented in the GPU Fleet Manager.

## Overview

The GPU Fleet Manager uses NVIDIA Management Library (NVML) via the `nvidia-ml-py3` Python bindings to collect real-time metrics from NVIDIA GPUs. These metrics are exposed through a REST API endpoint and can be used for monitoring, alerting, and resource allocation decisions.

## Installation Requirements

### Dependencies

The GPU metrics collection requires the following dependencies:

- `nvidia-ml-py3` - Python bindings for NVML
- NVIDIA drivers installed on the host system

### Installation on Different Environments

#### Linux

1. Install NVIDIA drivers for your GPU:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install nvidia-driver-xxx  # Replace xxx with the appropriate version

   # CentOS/RHEL
   sudo yum install nvidia-driver-xxx
   ```

2. Verify driver installation:
   ```bash
   nvidia-smi
   ```

3. Install the Python package:
   ```bash
   pip install nvidia-ml-py3==7.352.0
   ```

#### Windows

1. Download and install the latest NVIDIA drivers from [NVIDIA's website](https://www.nvidia.com/Download/index.aspx)

2. Verify driver installation:
   ```bash
   nvidia-smi
   ```

3. Install the Python package:
   ```bash
   pip install nvidia-ml-py3==7.352.0
   ```

#### Docker Containers

When using GPU Fleet Manager in Docker containers, make sure to:

1. Use the NVIDIA Container Toolkit:
   ```bash
   # Install the toolkit
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   ```

2. Run containers with GPU access:
   ```bash
   docker run --gpus all ...
   ```

## Available Metrics

The GPU metrics collection system provides the following metrics for each GPU:

- **Basic Information**:
  - GPU ID and Name
  - UUID

- **Utilization**:
  - GPU Utilization (percentage)
  - Memory Utilization (percentage)

- **Memory**:
  - Total Memory (MB)
  - Used Memory (MB)
  - Free Memory (MB)

- **Temperature**:
  - GPU Temperature (Celsius)

- **Power**:
  - Power Usage (Watts)

- **Clock Speeds**:
  - Graphics Clock (MHz)
  - Memory Clock (MHz)

## API Endpoint

### GPU Metrics Endpoint

```
GET /api/v1/monitoring/gpu-metrics
```

#### Response Format

```json
{
  "timestamp": "2025-03-04T23:02:50.123456",
  "gpus": [
    {
      "id": "gpu-0",
      "name": "NVIDIA GeForce RTX 3080",
      "uuid": "GPU-05a9ed06-0ddb-1882-ccba-3e5f36943994",
      "utilization": 75,
      "memory": {
        "total": 10240,
        "used": 8192,
        "free": 2048
      },
      "temperature": 65,
      "power_usage": 220.5,
      "clock_speeds": {
        "graphics": 1800,
        "memory": 8000
      }
    }
  ]
}
```

## Background Collection

The GPU Fleet Manager collects metrics in the background at regular intervals (default: 30 seconds). This reduces the overhead of collecting metrics on each API request and provides a more consistent experience.

## Error Handling

The system is designed to gracefully handle various error conditions:

- If NVML is not available (e.g., NVIDIA drivers not installed), it will fall back to providing placeholder data.
- If a specific GPU metric cannot be collected, it will return a default/zero value for that metric.
- All errors are logged for troubleshooting.

## Testing

The GPU metrics system includes comprehensive tests:

- **Unit Tests**: Mock the NVML library to test functionality without requiring actual GPU hardware.
- **Integration Tests**: Test the API endpoints with mocked GPU metrics.

To run the tests:

```bash
# Run unit tests
pytest tests/unit/test_gpu_metrics.py

# Run integration tests
pytest tests/integration/test_monitoring_api.py
```

## Troubleshooting

Common issues and solutions:

1. **Metrics show zeros or placeholder data**:
   - Verify NVIDIA drivers are installed: `nvidia-smi`
   - Check application logs for NVML initialization errors

2. **Permissions issues**:
   - Ensure the application has sufficient permissions to access GPU devices
   - In Docker, ensure the container has access to GPUs

3. **Performance concerns**:
   - If metrics collection is causing performance issues, adjust the collection interval
