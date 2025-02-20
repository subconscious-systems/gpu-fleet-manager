from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.core.dependencies import get_db
from src.models.domain import GPUResponse, GPUCreate
from src.services.gpu import GPUService

router = APIRouter(prefix="/gpu", tags=["GPU Resources"])

@router.get("/{organization_id}", response_model=List[GPUResponse])
async def list_gpus(
    organization_id: str,
    memory_required: int = None,
    db=Depends(get_db)
):
    """List available GPUs for an organization"""
    service = GPUService(db)
    try:
        if memory_required is not None:
            gpus = await service.list_available(organization_id, memory_required)
        else:
            gpus = await service.list({'organization_id': organization_id})
        return gpus
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{organization_id}", response_model=GPUResponse)
async def register_gpu(
    organization_id: str,
    gpu: GPUCreate,
    db=Depends(get_db)
):
    """Register a new GPU for an organization"""
    service = GPUService(db)
    try:
        gpu_dict = gpu.model_dump()
        gpu_dict['organization_id'] = organization_id
        created = await service.create(gpu_dict)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
