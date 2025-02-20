from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from src.core.dependencies import SupabaseClient
from src.models.domain import GPUStatus, JobStatus
from .base import BaseService

class GPUService(BaseService):
    """Service for managing GPU resources"""
    
    def __init__(self, db: SupabaseClient):
        super().__init__(db, 'gpu_resources')
        self._locks = {}  # In-memory locks for GPU allocation
    
    async def list_available(self, organization_id: str, memory_required: int) -> List[Dict[str, Any]]:
        """List available GPUs for the given organization with sufficient memory"""
        response = await self.db.client.get(
            '/rest/v1/gpu_resources',
            params={
                'select': '*',
                'organization_id': f'eq.{organization_id}',
                'status': 'eq.available',
                'memory_total-memory_allocated': f'gte.{memory_required}'
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def allocate_for_job(self, job_id: str, organization_id: str, memory_required: int) -> Optional[Dict[str, Any]]:
        """Attempt to allocate a GPU for a job"""
        # Get available GPUs
        available_gpus = await self.list_available(organization_id, memory_required)
        if not available_gpus:
            return None
        
        # Sort by available memory (ascending) to optimize resource usage
        available_gpus.sort(key=lambda g: g['memory_total'] - g['memory_allocated'])
        
        # Try to allocate the first available GPU
        for gpu in available_gpus:
            gpu_id = gpu['id']
            
            # Use in-memory lock to prevent race conditions
            if gpu_id not in self._locks:
                self._locks[gpu_id] = asyncio.Lock()
            
            async with self._locks[gpu_id]:
                # Double-check GPU is still available
                current = await self.get(gpu_id)
                if (current['status'] == GPUStatus.AVAILABLE.value and 
                    current['memory_total'] - current['memory_allocated'] >= memory_required):
                    
                    # Update GPU status and memory allocation
                    updated = await self.update(gpu_id, {
                        'status': GPUStatus.IN_USE.value,
                        'memory_allocated': current['memory_allocated'] + memory_required,
                        'current_job_id': job_id
                    })
                    
                    # Update job with GPU assignment
                    await self.db.client.patch(
                        '/rest/v1/jobs',
                        params={'id': f'eq.{job_id}'},
                        json={
                            'status': JobStatus.RUNNING.value,
                            'gpu_id': gpu_id,
                            'started_at': datetime.utcnow().isoformat()
                        }
                    )
                    
                    return updated
        
        return None
    
    async def release_gpu(self, gpu_id: str, job_id: str, memory_to_free: int) -> Dict[str, Any]:
        """Release a GPU from a job"""
        if gpu_id not in self._locks:
            self._locks[gpu_id] = asyncio.Lock()
        
        async with self._locks[gpu_id]:
            current = await self.get(gpu_id)
            if not current or current['current_job_id'] != job_id:
                raise ValueError(f"GPU {gpu_id} is not allocated to job {job_id}")
            
            # Update GPU status and memory allocation
            updated = await self.update(gpu_id, {
                'status': GPUStatus.AVAILABLE.value,
                'memory_allocated': max(0, current['memory_allocated'] - memory_to_free),
                'current_job_id': None
            })
            
            return updated
