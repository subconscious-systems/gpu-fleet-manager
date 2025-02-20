from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from src.models.domain import (
    JobCreate, JobUpdate, JobResponse,
    JobStatus
)
from src.core.dependencies import get_db_dependency

router = APIRouter()

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job: JobCreate,
    db=Depends(get_db_dependency)
) -> JobResponse:
    """Create a new job"""
    try:
        job_data = {
            **job.model_dump(),
            "status": JobStatus.QUEUED,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = await db.client.post(
            '/rest/v1/jobs',
            json=job_data
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create job")
            
        return JobResponse(**result[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    organization_id: str,
    status: Optional[JobStatus] = Query(None, description="Filter jobs by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of jobs to return"),
    db=Depends(get_db_dependency)
) -> List[JobResponse]:
    """List jobs for an organization"""
    try:
        params = {
            'select': '*',
            'organization_id': f'eq.{organization_id}',
            'limit': limit
        }
        
        if status:
            params['status'] = f'eq.{status}'
            
        response = await db.client.get('/rest/v1/jobs', params=params)
        response.raise_for_status()
        result = response.json()
        
        return [JobResponse(**item) for item in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db=Depends(get_db_dependency)
) -> JobResponse:
    """Get job details"""
    try:
        response = await db.client.get(
            '/rest/v1/jobs',
            params={'id': f'eq.{job_id}', 'select': '*'}
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return JobResponse(**result[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    db=Depends(get_db_dependency)
) -> JobResponse:
    """Update job details"""
    try:
        # First check if job exists
        job = await get_job(job_id, db)
        
        # Update job
        response = await db.client.patch(
            '/rest/v1/jobs',
            params={'id': f'eq.{job_id}'},
            json=job_update.model_dump(exclude_unset=True)
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update job")
            
        return JobResponse(**result[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db=Depends(get_db_dependency)
) -> JobResponse:
    """Cancel a job"""
    try:
        # Get current job
        job = await get_job(job_id, db)
        
        # Can only cancel queued or running jobs
        if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job in {job.status} state"
            )
        
        # Update job status
        response = await db.client.patch(
            '/rest/v1/jobs',
            params={'id': f'eq.{job_id}'},
            json={
                "status": JobStatus.CANCELLED,
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to cancel job")
            
        return JobResponse(**result[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
