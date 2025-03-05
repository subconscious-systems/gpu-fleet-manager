"""
Enhanced repository layer for GPU Fleet Manager

This module provides an enhanced repository layer that works with the updated
database schema, supporting all the new tables and relationships.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from decimal import Decimal

from src.models.enhanced_domain import (
    # Re-exported original models
    JobStatus, GPUStatus, OrganizationRole,
    JobCreate, JobUpdate, JobResponse,
    GPUCreate, GPUUpdate, GPUResponse,
    OrganizationBase, OrganizationCreate, OrganizationResponse,
    OrganizationMemberBase, OrganizationMemberCreate, OrganizationMemberResponse,
    APIKeyBase, APIKeyCreate, APIKeyResponse,
    
    # New models
    WebhookStatus, WebhookType, WebhookEventType,
    GPUResourceBase, GPUResourceCreate, GPUResourceUpdate, GPUResourceResponse,
    GPUMetricBase, GPUMetricCreate, GPUMetricResponse,
    EnhancedJobBase, EnhancedJobCreate, EnhancedJobUpdate, EnhancedJobResponse,
    CostTrackingBase, CostTrackingCreate, CostTrackingUpdate, CostTrackingResponse,
    WebhookBase, WebhookCreate, WebhookUpdate, WebhookResponse,
    WebhookDeliveryBase, WebhookDeliveryCreate, WebhookDeliveryResponse,
    PredictionBase, PredictionCreate, PredictionUpdate, PredictionResponse
)
from src.db.supabase_client import SupabaseClient

class EnhancedRepository:
    """Enhanced repository for database operations with the new schema"""
    
    def __init__(self, client: SupabaseClient):
        """Initialize repository with database client"""
        self.client = client

    #==========================================================================
    # Job Methods
    #==========================================================================
    
    async def create_job(self, job: Union[JobCreate, EnhancedJobCreate]) -> Union[JobResponse, EnhancedJobResponse]:
        """Create a new job"""
        job_data = {
            **job.model_dump(),
            "status": JobStatus.QUEUED,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("jobs").insert(job_data).execute()
        if result.error:
            raise Exception(f"Failed to create job: {result.error}")
            
        # Determine which response model to use based on input type
        if isinstance(job, EnhancedJobCreate):
            return EnhancedJobResponse(**result.data[0])
        else:
            return JobResponse(**result.data[0])

    async def get_job(self, job_id: str, enhanced: bool = True) -> Optional[Union[JobResponse, EnhancedJobResponse]]:
        """
        Get job by ID
        
        Args:
            job_id: The ID of the job to retrieve
            enhanced: Whether to return the enhanced job model
        """
        result = await self.client.table("jobs").select("*").eq("id", job_id).execute()
        if result.error:
            raise Exception(f"Failed to get job: {result.error}")
            
        if not result.data:
            return None
            
        # Return appropriate model based on enhanced flag
        if enhanced:
            return EnhancedJobResponse(**result.data[0])
        else:
            return JobResponse(**result.data[0])

    async def list_jobs(
        self,
        organization_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        enhanced: bool = True
    ) -> List[Union[JobResponse, EnhancedJobResponse]]:
        """
        List jobs for organization
        
        Args:
            organization_id: The organization ID to filter by
            status: Optional status filter
            limit: Maximum number of results to return
            enhanced: Whether to return enhanced job models
        """
        query = self.client.table("jobs").select("*").eq("organization_id", organization_id)
        
        if status:
            query = query.eq("status", status)
            
        result = await query.limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list jobs: {result.error}")
            
        # Return appropriate model based on enhanced flag
        if enhanced:
            return [EnhancedJobResponse(**item) for item in result.data]
        else:
            return [JobResponse(**item) for item in result.data]

    async def update_job(
        self, 
        job_id: str, 
        job_update: Union[JobUpdate, EnhancedJobUpdate]
    ) -> Optional[Union[JobResponse, EnhancedJobResponse]]:
        """Update job details"""
        result = await self.client.table("jobs").update(job_update.model_dump()).eq("id", job_id).execute()
        if result.error:
            raise Exception(f"Failed to update job: {result.error}")
            
        if not result.data:
            return None
            
        # Determine which response model to use based on input type
        if isinstance(job_update, EnhancedJobUpdate):
            return EnhancedJobResponse(**result.data[0])
        else:
            return JobResponse(**result.data[0])
    
    #==========================================================================
    # GPU Methods
    #==========================================================================
    
    async def create_gpu(self, gpu: Union[GPUCreate, GPUResourceCreate]) -> Union[GPUResponse, GPUResourceResponse]:
        """Create a new GPU or GPU resource"""
        gpu_data = {
            **gpu.model_dump(),
            "status": GPUStatus.AVAILABLE,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Determine which table to use
        table = "gpu_resources" if isinstance(gpu, GPUResourceCreate) else "gpus"
        
        result = await self.client.table(table).insert(gpu_data).execute()
        if result.error:
            raise Exception(f"Failed to create GPU: {result.error}")
            
        # Return appropriate model based on input type
        if isinstance(gpu, GPUResourceCreate):
            return GPUResourceResponse(**result.data[0])
        else:
            return GPUResponse(**result.data[0])

    async def get_gpu(
        self, 
        gpu_id: str, 
        enhanced: bool = True
    ) -> Optional[Union[GPUResponse, GPUResourceResponse]]:
        """
        Get GPU by ID
        
        Args:
            gpu_id: The ID of the GPU to retrieve
            enhanced: Whether to use the gpu_resources table instead of gpus
        """
        # Determine which table to use
        table = "gpu_resources" if enhanced else "gpus"
        
        result = await self.client.table(table).select("*").eq("id", gpu_id).execute()
        if result.error:
            raise Exception(f"Failed to get GPU: {result.error}")
            
        if not result.data:
            return None
            
        # Return appropriate model based on enhanced flag
        if enhanced:
            return GPUResourceResponse(**result.data[0])
        else:
            return GPUResponse(**result.data[0])

    async def list_gpus(
        self,
        organization_id: str,
        status: Optional[Union[GPUStatus, str]] = None,
        limit: int = 100,
        enhanced: bool = True
    ) -> List[Union[GPUResponse, GPUResourceResponse]]:
        """
        List GPUs for organization
        
        Args:
            organization_id: The organization ID to filter by
            status: Optional status filter
            limit: Maximum number of results to return
            enhanced: Whether to use the gpu_resources table instead of gpus
        """
        # Determine which table to use
        table = "gpu_resources" if enhanced else "gpus"
        
        query = self.client.table(table).select("*").eq("organization_id", organization_id)
        
        if status:
            query = query.eq("status", status)
            
        result = await query.limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list GPUs: {result.error}")
            
        # Return appropriate model based on enhanced flag
        if enhanced:
            return [GPUResourceResponse(**item) for item in result.data]
        else:
            return [GPUResponse(**item) for item in result.data]

    async def update_gpu(
        self, 
        gpu_id: str, 
        gpu_update: Union[GPUUpdate, GPUResourceUpdate],
        enhanced: bool = True
    ) -> Optional[Union[GPUResponse, GPUResourceResponse]]:
        """
        Update GPU details
        
        Args:
            gpu_id: The ID of the GPU to update
            gpu_update: The update data
            enhanced: Whether to use the gpu_resources table instead of gpus
        """
        # Determine which table to use
        table = "gpu_resources" if enhanced else "gpus"
        
        result = await self.client.table(table).update(gpu_update.model_dump()).eq("id", gpu_id).execute()
        if result.error:
            raise Exception(f"Failed to update GPU: {result.error}")
            
        if not result.data:
            return None
            
        # Return appropriate model based on enhanced flag
        if enhanced:
            return GPUResourceResponse(**result.data[0])
        else:
            return GPUResponse(**result.data[0])
            
    #==========================================================================
    # GPU Metrics Methods
    #==========================================================================
    
    async def create_gpu_metric(self, metric: GPUMetricCreate) -> GPUMetricResponse:
        """Create a new GPU metric"""
        metric_data = {
            **metric.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("gpu_metrics").insert(metric_data).execute()
        if result.error:
            raise Exception(f"Failed to create GPU metric: {result.error}")
            
        return GPUMetricResponse(**result.data[0])

    async def get_gpu_metrics(
        self,
        gpu_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[GPUMetricResponse]:
        """
        Get metrics for a specific GPU
        
        Args:
            gpu_id: The ID of the GPU to get metrics for
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of results to return
        """
        query = self.client.table("gpu_metrics").select("*").eq("gpu_id", gpu_id)
        
        if start_time:
            query = query.gte("timestamp", start_time.isoformat())
            
        if end_time:
            query = query.lte("timestamp", end_time.isoformat())
            
        result = await query.order("timestamp", ascending=False).limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to get GPU metrics: {result.error}")
            
        return [GPUMetricResponse(**item) for item in result.data]
            
    #==========================================================================
    # Cost Tracking Methods
    #==========================================================================
    
    async def create_cost_tracking(self, cost_tracking: CostTrackingCreate) -> CostTrackingResponse:
        """Create a new cost tracking record"""
        cost_data = {
            **cost_tracking.model_dump(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("cost_tracking").insert(cost_data).execute()
        if result.error:
            raise Exception(f"Failed to create cost tracking: {result.error}")
            
        return CostTrackingResponse(**result.data[0])

    async def get_cost_tracking(self, job_id: str) -> Optional[CostTrackingResponse]:
        """Get cost tracking for a specific job"""
        result = await self.client.table("cost_tracking").select("*").eq("job_id", job_id).execute()
        if result.error:
            raise Exception(f"Failed to get cost tracking: {result.error}")
            
        return CostTrackingResponse(**result.data[0]) if result.data else None

    async def update_cost_tracking(
        self, 
        cost_tracking_id: str, 
        update: CostTrackingUpdate
    ) -> Optional[CostTrackingResponse]:
        """Update cost tracking record"""
        result = await self.client.table("cost_tracking").update(update.model_dump()).eq("id", cost_tracking_id).execute()
        if result.error:
            raise Exception(f"Failed to update cost tracking: {result.error}")
            
        return CostTrackingResponse(**result.data[0]) if result.data else None

    async def list_organization_costs(
        self,
        organization_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CostTrackingResponse]:
        """
        List cost tracking records for an organization
        
        Args:
            organization_id: The organization ID to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of results to return
        """
        query = self.client.table("cost_tracking").select("*").eq("organization_id", organization_id)
        
        if start_time:
            query = query.gte("start_time", start_time.isoformat())
            
        if end_time:
            query = query.lte("start_time", end_time.isoformat())
            
        result = await query.order("start_time", ascending=False).limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list organization costs: {result.error}")
            
        return [CostTrackingResponse(**item) for item in result.data]
            
    #==========================================================================
    # Webhook Methods
    #==========================================================================
    
    async def create_webhook(self, webhook: WebhookCreate) -> WebhookResponse:
        """Create a new webhook"""
        webhook_data = {
            **webhook.model_dump(),
            "status": WebhookStatus.ACTIVE,
            "error_rate": 0.0,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("webhooks").insert(webhook_data).execute()
        if result.error:
            raise Exception(f"Failed to create webhook: {result.error}")
            
        return WebhookResponse(**result.data[0])

    async def get_webhook(self, webhook_id: str) -> Optional[WebhookResponse]:
        """Get webhook by ID"""
        result = await self.client.table("webhooks").select("*").eq("id", webhook_id).execute()
        if result.error:
            raise Exception(f"Failed to get webhook: {result.error}")
            
        return WebhookResponse(**result.data[0]) if result.data else None

    async def update_webhook(self, webhook_id: str, update: WebhookUpdate) -> Optional[WebhookResponse]:
        """Update webhook"""
        update_data = {
            **update.model_dump(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("webhooks").update(update_data).eq("id", webhook_id).execute()
        if result.error:
            raise Exception(f"Failed to update webhook: {result.error}")
            
        return WebhookResponse(**result.data[0]) if result.data else None

    async def list_webhooks(
        self,
        organization_id: str,
        is_active: Optional[bool] = None,
        webhook_type: Optional[WebhookType] = None,
        limit: int = 100
    ) -> List[WebhookResponse]:
        """
        List webhooks for an organization
        
        Args:
            organization_id: The organization ID to filter by
            is_active: Optional active status filter
            webhook_type: Optional webhook type filter
            limit: Maximum number of results to return
        """
        query = self.client.table("webhooks").select("*").eq("organization_id", organization_id)
        
        if is_active is not None:
            query = query.eq("is_active", is_active)
            
        if webhook_type:
            query = query.eq("type", webhook_type)
            
        result = await query.order("created_at", ascending=False).limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list webhooks: {result.error}")
            
        return [WebhookResponse(**item) for item in result.data]
    
    async def create_webhook_delivery(self, delivery: WebhookDeliveryCreate) -> WebhookDeliveryResponse:
        """Create a new webhook delivery record"""
        delivery_data = {
            **delivery.model_dump(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("webhook_deliveries").insert(delivery_data).execute()
        if result.error:
            raise Exception(f"Failed to create webhook delivery: {result.error}")
            
        return WebhookDeliveryResponse(**result.data[0])

    async def update_webhook_delivery(
        self, 
        delivery_id: str, 
        response_status: int, 
        response_body: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[WebhookDeliveryResponse]:
        """Update webhook delivery with response information"""
        update_data = {
            "response_status": response_status
        }
        
        if response_body:
            update_data["response_body"] = response_body
            
        if error_message:
            update_data["error_message"] = error_message
        
        result = await self.client.table("webhook_deliveries").update(update_data).eq("id", delivery_id).execute()
        if result.error:
            raise Exception(f"Failed to update webhook delivery: {result.error}")
            
        return WebhookDeliveryResponse(**result.data[0]) if result.data else None

    async def list_webhook_deliveries(
        self,
        webhook_id: str,
        limit: int = 100
    ) -> List[WebhookDeliveryResponse]:
        """List delivery records for a webhook"""
        result = await self.client.table("webhook_deliveries")\
            .select("*")\
            .eq("webhook_id", webhook_id)\
            .order("created_at", ascending=False)\
            .limit(limit)\
            .execute()
            
        if result.error:
            raise Exception(f"Failed to list webhook deliveries: {result.error}")
            
        return [WebhookDeliveryResponse(**item) for item in result.data]
            
    #==========================================================================
    # Prediction Methods
    #==========================================================================
    
    async def create_prediction(self, prediction: PredictionCreate) -> PredictionResponse:
        """Create a new prediction"""
        prediction_data = {
            **prediction.model_dump(),
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("predictions").insert(prediction_data).execute()
        if result.error:
            raise Exception(f"Failed to create prediction: {result.error}")
            
        return PredictionResponse(**result.data[0])

    async def get_prediction(self, prediction_id: str) -> Optional[PredictionResponse]:
        """Get prediction by ID"""
        result = await self.client.table("predictions").select("*").eq("id", prediction_id).execute()
        if result.error:
            raise Exception(f"Failed to get prediction: {result.error}")
            
        return PredictionResponse(**result.data[0]) if result.data else None

    async def update_prediction(
        self, 
        prediction_id: str, 
        update: PredictionUpdate
    ) -> Optional[PredictionResponse]:
        """Update prediction"""
        update_data = {
            **update.model_dump(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await self.client.table("predictions").update(update_data).eq("id", prediction_id).execute()
        if result.error:
            raise Exception(f"Failed to update prediction: {result.error}")
            
        return PredictionResponse(**result.data[0]) if result.data else None

    async def list_predictions(
        self,
        organization_id: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[PredictionResponse]:
        """
        List predictions for an organization
        
        Args:
            organization_id: The organization ID to filter by
            status: Optional status filter
            limit: Maximum number of results to return
        """
        query = self.client.table("predictions").select("*").eq("organization_id", organization_id)
        
        if status:
            query = query.eq("status", status)
            
        result = await query.order("created_at", ascending=False).limit(limit).execute()
        if result.error:
            raise Exception(f"Failed to list predictions: {result.error}")
            
        return [PredictionResponse(**item) for item in result.data]
