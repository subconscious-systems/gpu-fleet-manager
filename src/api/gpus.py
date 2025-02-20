from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.domain import (
    GPUCreate, GPUUpdate, GPUResponse,
    GPUStatus
)
from src.core.dependencies import get_db_dependency

router = APIRouter()

@router.get("/gpus", response_model=List[GPUResponse])
async def list_gpus(
    organization_id: str,
    status: Optional[GPUStatus] = None,
    db=Depends(get_db_dependency)
) -> List[GPUResponse]:
    """List GPUs for an organization"""
    try:
        params = {
            'select': '*',
            'organization_id': f'eq.{organization_id}'
        }
        
        if status:
            params['status'] = f'eq.{status}'
        
        response = await db.client.get('/rest/v1/gpu_resources', params=params)
        response.raise_for_status()
        result = response.json()
        
        return [GPUResponse(**gpu) for gpu in result]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list GPUs: {str(e)}"
        )

@router.post("/gpus", response_model=GPUResponse)
async def create_gpu(
    gpu: GPUCreate,
    db=Depends(get_db_dependency)
) -> GPUResponse:
    """Register a new GPU"""
    try:
        gpu_data = {
            **gpu.model_dump(),
            "status": GPUStatus.AVAILABLE,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = await db.client.post(
            '/rest/v1/gpu_resources',
            json=gpu_data
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create GPU resource"
            )
        
        return GPUResponse(**result[0])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create GPU: {str(e)}"
        )

@router.get("/gpus/{gpu_id}", response_model=GPUResponse)
async def get_gpu(
    gpu_id: str,
    db=Depends(get_db_dependency)
) -> GPUResponse:
    """Get GPU details"""
    try:
        response = await db.client.get(
            '/rest/v1/gpu_resources',
            params={'id': f'eq.{gpu_id}', 'select': '*'}
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="GPU not found"
            )
        
        return GPUResponse(**result[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GPU: {str(e)}"
        )

@router.patch("/gpus/{gpu_id}", response_model=GPUResponse)
async def update_gpu(
    gpu_id: str,
    gpu_update: GPUUpdate,
    db=Depends(get_db_dependency)
) -> GPUResponse:
    """Update GPU details"""
    try:
        # Check if GPU exists
        gpu = await get_gpu(gpu_id, db)
        
        update_data = {
            **gpu_update.model_dump(exclude_unset=True),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = await db.client.patch(
            '/rest/v1/gpu_resources',
            params={'id': f'eq.{gpu_id}'},
            json=update_data
        )
        response.raise_for_status()
        result = response.json()
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to update GPU"
            )
        
        return GPUResponse(**result[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update GPU: {str(e)}"
        )
