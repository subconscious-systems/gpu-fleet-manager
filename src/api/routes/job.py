from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from src.core.dependencies import get_db
from src.models.domain import JobResponse, JobCreate, JobStatus
from src.services.job import JobService

router = APIRouter(prefix="/job", tags=["Jobs"])

@router.post("/{organization_id}", response_model=JobResponse)
async def create_job(
    organization_id: str,
    job: JobCreate,
    db=Depends(get_db)
):
    """Create a new job and attempt GPU allocation"""
    service = JobService(db)
    try:
        job_dict = job.model_dump()
        job_dict['organization_id'] = organization_id
        created = await service.create_job(job_dict)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{organization_id}", response_model=List[JobResponse])
async def list_jobs(
    organization_id: str,
    status: Optional[JobStatus] = None,
    db=Depends(get_db)
):
    """List jobs for an organization"""
    service = JobService(db)
    try:
        jobs = await service.list_organization_jobs(organization_id, status)
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{organization_id}/{job_id}", response_model=JobResponse)
async def get_job(
    organization_id: str,
    job_id: str,
    db=Depends(get_db)
):
    """Get job details"""
    service = JobService(db)
    try:
        job = await service.get(job_id)
        if not job or job['organization_id'] != organization_id:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{organization_id}/{job_id}/complete")
async def complete_job(
    organization_id: str,
    job_id: str,
    db=Depends(get_db)
):
    """Mark a job as completed (demo purposes)"""
    service = JobService(db)
    try:
        job = await service.get(job_id)
        if not job or job['organization_id'] != organization_id:
            raise HTTPException(status_code=404, detail="Job not found")
        
        updated = await service.complete_job(job_id, {'demo': 'result'})
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
