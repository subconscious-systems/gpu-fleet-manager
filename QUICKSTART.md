# GPU Fleet Manager Quick Start Guide

## Common Operations

### 1. Submit a Job

```python
from src.db.repository import Repository
from src.db.supabase_client import SupabaseClient, SupabaseConfig

# Initialize client
config = SupabaseConfig(
    url="your_supabase_url",
    key="your_supabase_key"
)
client = await SupabaseClient.get_instance(config)
repo = Repository(client)

# Submit job
job_data = {
    "name": "My ML Job",
    "model_type": "text",
    "gpu_requirements": {
        "min_memory": 8,
        "gpu_type": "NVIDIA A100"
    },
    "params": {
        "prompt": "Your prompt here",
        "max_length": 100
    }
}

job = await repo.create_gpu_job("your-org-id", job_data)
print(f"Job created with ID: {job['id']}")
```

### 2. Check Job Status

```python
# Get single job status
job = await repo.get_gpu_jobs(
    org_id="your-org-id",
    filters={"id": "eq.your-job-id"}
)

# Get all running jobs
running_jobs = await repo.get_gpu_jobs(
    org_id="your-org-id",
    status="running"
)
```

### 3. Find Available GPUs

```python
# Find GPUs matching requirements
gpus = await repo.get_available_gpus(
    org_id="your-org-id",
    min_memory=8,
    gpu_type="NVIDIA A100"
)

# Check GPU details
for gpu in gpus:
    print(f"GPU {gpu['id']}: {gpu['memory_gb']}GB {gpu['gpu_type']}")
```

### 4. Run the Demo System

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Set up environment variables
export SUPABASE_URL="your_url"
export SUPABASE_KEY="your_key"

# 3. Run the demo
./start_demo.sh
```

### 5. Monitor System

The demo provides a real-time dashboard showing:
- Job statuses
- GPU allocations
- Resource utilization
- Error states

Example output:
```
📊 Job Status Dashboard
┌──────────┬──────────────┬──────────┬──────────┬────────────┐
│ Job ID   │ Name         │ Status   │ GPU      │ Updated At │
├──────────┼──────────────┼──────────┼──────────┼────────────┤
│ job-123  │ Text Gen     │ running  │ gpu-456  │ 2025-02-19 │
└──────────┴──────────────┴──────────┴──────────┴────────────┘
```

## Troubleshooting

### Common Issues

1. **Connection Errors**
```python
# Check connection
client = await SupabaseClient.get_instance()
try:
    await client.select("organizations", limit=1)
    print("✅ Connection successful")
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
```

2. **GPU Allocation Failures**
```python
# Check GPU availability
available_gpus = await repo.get_available_gpus(org_id)
if not available_gpus:
    print("No GPUs available")
    # Check for stuck allocations
    stuck_jobs = await repo.get_gpu_jobs(org_id, status="running")
    print(f"Found {len(stuck_jobs)} potentially stuck jobs")
```

3. **Job Stuck in Queue**
```python
# Force job status update
await repo.update_gpu_job(
    job_id="stuck-job-id",
    org_id="your-org-id",
    updates={"status": "failed"}
)

# Release any allocated GPU
if job.get("gpu_id"):
    await repo.release_gpu(job["gpu_id"], "your-org-id")
```

## Best Practices

1. **Resource Cleanup**
```python
# Always use async context managers
async with SupabaseClient.get_instance(config) as client:
    repo = Repository(client)
    # ... your code here ...
```

2. **Error Handling**
```python
try:
    job = await repo.create_gpu_job(org_id, job_data)
except HTTPException as e:
    if e.status_code == 409:  # Conflict
        # Handle resource conflict
        pass
    elif e.status_code == 404:  # Not found
        # Handle missing resource
        pass
    else:
        # Log unexpected error
        logger.error(f"Unexpected error: {str(e)}")
```

3. **Performance Optimization**
```python
# Use bulk operations when possible
jobs = await repo.get_gpu_jobs(
    org_id,
    filters={"status": "in.(running,queued)"},
    limit=100
)

# Use specific column selection
gpus = await repo.get_available_gpus(
    org_id,
    columns="id,memory_gb,gpu_type"
)
```

## Need Help?

- Check the main README.md for detailed documentation
- Review the error logs in `logs/gpu_manager.log`
- Submit issues with full error details and reproduction steps
