# GPU Fleet Manager

A high-performance GPU resource management system with intelligent job scheduling and multi-tenant support.

## Quick Demo Setup

1. **Environment Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Create or update `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=your_url
   SUPABASE_KEY=your_key
   ```

3. **Database Setup**:
   - Run the initial schema migration in Supabase SQL Editor:
     ```sql
     -- Copy contents of migrations/001_initial_schema.sql
     ```
   - Create a demo organization and GPU:
     ```sql
     INSERT INTO organizations (id, name) 
     VALUES ('demo-org', 'Demo Organization');
     
     INSERT INTO gpu_resources (id, name, organization_id, memory_total, status) 
     VALUES 
       ('gpu-1', 'NVIDIA A100', 'demo-org', 81920, 'available'),
       ('gpu-2', 'NVIDIA A100', 'demo-org', 81920, 'available');
     ```

4. **Run the Demo**:
   ```bash
   python -m uvicorn src.main:app --reload
   ```

5. **Access the Demo UI**:
   Open [http://localhost:8000](http://localhost:8000) in your browser

The demo interface allows you to:
- View available GPU resources
- Submit new jobs
- Monitor job status in real-time
- See GPU allocation changes

## Table of Contents
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Database Layer](#database-layer)
- [Job Lifecycle](#job-lifecycle)
- [Getting Started](#getting-started)
- [Demo System](#demo-system)
- [Production Deployment](#production-deployment)

## System Architecture

The system is built with a focus on reliability, scalability, and security:

```mermaid
graph TD
    A[Job Submission] --> B[GPU Requirements Check]
    B --> C{GPU Available?}
    C -->|Yes| D[Allocate GPU]
    C -->|No| E[Queue Job]
    D --> F[Update Job Status]
    E --> G[Monitor Queue]
    G --> C
    F --> H[Job Execution]
    H --> I[Release GPU]
```

## Core Components

### 1. Database Client (`src/db/supabase_client.py`)
High-performance Supabase client with advanced features:
```python
class SupabaseClient:
    """Singleton client with connection pooling and retry logic"""
    def __init__(self, config: SupabaseConfig):
        self.client = httpx.AsyncClient(
            base_url=config.url,
            timeout=config.timeout,
            limits=httpx.Limits(max_connections=config.max_connections)
        )
```
- Connection pooling
- Automatic retries with exponential backoff
- Thread-safe singleton pattern
- Comprehensive error handling

### 2. Repository Layer (`src/db/repository.py`)
Clean abstraction over database operations:
```python
class Repository:
    """Repository pattern for database operations"""
    @requires_db
    async def allocate_gpu(self, gpu_id: str, job_id: str, org_id: str):
        """Atomic GPU allocation with optimistic locking"""
        return await self.client.update(
            "gpus",
            {"status": "allocated", "job_id": job_id},
            filters={"id": f"eq.{gpu_id}", "status": "eq.available"}
        )
```
- Atomic operations
- Organization-level isolation
- Optimistic locking
- Type-safe interfaces

### 3. Job Lifecycle Management (`src/demo/job_lifecycle.py`)
Complete job management system:
```python
class JobLifecycleDemo:
    """Demonstrates complete job lifecycle"""
    async def submit_test_jobs(self, org_id: str):
        """Submit jobs with different GPU requirements"""
        
    async def allocate_gpus(self, org_id: str, jobs: List[Dict]):
        """Match and allocate GPUs to jobs"""
        
    async def monitor_jobs(self, org_id: str, jobs: List[Dict]):
        """Real-time job status monitoring"""
```

## Database Layer

### Key Features
1. **Connection Management**:
   - Pooled connections (default: 10)
   - Automatic connection recovery
   - Connection timeouts

2. **Data Operations**:
   - Atomic transactions
   - Optimistic locking
   - Bulk operations support

3. **Security**:
   - Multi-tenant isolation
   - API key authentication
   - SQL injection prevention

## Job Lifecycle

### 1. Job Submission
```python
job_data = {
    "name": "Text Generation",
    "model_type": "text",
    "gpu_requirements": {
        "min_memory": 8,
        "gpu_type": "NVIDIA A100"
    }
}
job = await repository.create_gpu_job(org_id, job_data)
```

### 2. GPU Allocation
```python
# Find matching GPU
gpus = await repository.get_available_gpus(
    org_id,
    min_memory=job["gpu_requirements"]["min_memory"],
    gpu_type=job["gpu_requirements"]["gpu_type"]
)

# Atomic allocation
allocated_gpu = await repository.allocate_gpu(
    gpu["id"], 
    job["id"], 
    org_id
)
```

### 3. Job Monitoring
```python
# Real-time status updates
current_jobs = await repository.get_gpu_jobs(org_id)
for job in current_jobs:
    print(f"Job {job['id']}: {job['status']}")
```

## Getting Started

1. **Environment Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Create `.env` file:
   ```
   SUPABASE_URL=your_url
   SUPABASE_KEY=your_key
   ```

3. **Database Setup**:
   - Create required tables in Supabase
   - Set up organization and GPU records

## Demo System

Run the complete demo:
```bash
./start_demo.sh
```

The demo will:
1. Start the FastAPI server
2. Submit test jobs
3. Allocate GPUs
4. Monitor job status
5. Clean up resources

### Demo Features
- Real-time job status dashboard
- GPU allocation visualization
- Error handling demonstration
- Resource cleanup

### Monitoring Output
```
┌──────────┬──────────────┬──────────┬──────────┬────────────┐
│ Job ID   │ Name         │ Status   │ GPU      │ Updated At │
├──────────┼──────────────┼──────────┼──────────┼────────────┤
│ job-123  │ Text Gen     │ running  │ gpu-456  │ 2025-02-19 │
│ job-124  │ Image Gen    │ waiting  │ N/A      │ 2025-02-19 │
└──────────┴──────────────┴──────────┴──────────┴────────────┘
```

## Error Handling

The system implements comprehensive error handling:
```python
try:
    await repository.allocate_gpu(gpu_id, job_id, org_id)
except HTTPException as e:
    if e.status_code == 409:  # Conflict
        await handle_allocation_conflict(job_id)
    else:
        await mark_job_failed(job_id)
finally:
    await cleanup_resources()
```

## Best Practices

1. **Resource Management**:
   - Always use context managers
   - Implement proper cleanup
   - Monitor resource usage

2. **Error Handling**:
   - Use specific exceptions
   - Implement retries
   - Log errors properly

3. **Security**:
   - Validate all inputs
   - Use proper authentication
   - Implement rate limiting

4. **Performance**:
   - Use connection pooling
   - Implement caching
   - Optimize queries

## Production Deployment

### Prerequisites
1. A domain name pointing to your server
2. Auth0 account and application set up
3. Docker and Docker Compose installed on your server

### Setup Instructions

1. Clone this repository to your server:
   ```bash
   git clone https://github.com/your-org/gpu-fleet-manager.git
   cd gpu-fleet-manager
   ```

2. Copy the production environment template:
   ```bash
   cp .env.production .env
   ```

3. Edit the `.env` file with your configuration:
   - Set a secure `GRAFANA_ADMIN_PASSWORD`
   - Configure Auth0 credentials (`AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`)
   - Set your `ACME_EMAIL` for Let's Encrypt notifications
   - Update `DOMAIN` to your domain name

4. Configure Auth0:
   - Create a new Application in Auth0
   - Set the allowed callback URLs:
     ```
     https://your-domain.com/grafana/login/generic_oauth
     ```
   - Set the allowed logout URLs:
     ```
     https://your-domain.com/grafana
     ```
   - Add the following rules to map roles:
     ```javascript
     function (user, context, callback) {
       const namespace = 'https://your-domain.com';
       if (context.authorization && context.authorization.roles) {
         context.idToken[namespace + '/roles'] = context.authorization.roles;
         context.accessToken[namespace + '/roles'] = context.authorization.roles;
       }
       callback(null, user, context);
     }
     ```

5. Update the domain in docker-compose.yml:
   - Replace all instances of `your-domain.com` with your actual domain

6. Start the services:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

7. Access your dashboard:
   - Go to `https://your-domain.com/grafana`
   - Log in with your organization credentials via Auth0

### Security Notes
- All traffic is encrypted via HTTPS
- Authentication is handled by Auth0
- Users are automatically assigned roles based on their Auth0 groups
- The admin interface is only accessible to users with the admin role

### Monitoring Stack
- **Traefik**: Handles routing and SSL termination
- **Grafana**: Visualization and dashboards
- **Prometheus**: Metrics collection and storage

### Adding Users
1. Users should be managed through Auth0
2. Assign users to groups in Auth0:
   - `admin`: Full access
   - `editor`: Can edit dashboards
   - `viewer`: Can only view dashboards

### Backup
The following volumes should be backed up regularly:
- `prometheus_data`: Contains historical metrics
- `grafana_data`: Contains dashboard configurations
- `letsencrypt`: Contains SSL certificates

### Troubleshooting
- Check container logs: `docker-compose logs -f [service]`
- Verify Auth0 configuration
- Check Traefik logs for routing issues
- Ensure all environment variables are properly set
