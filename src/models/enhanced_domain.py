"""
Enhanced domain models for the GPU Fleet Manager

This module contains enhanced Pydantic models that match our database schema upgrade
and provide strong typing for our application code.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, EmailStr, Json
from datetime import datetime
from enum import Enum
from decimal import Decimal

# Re-export existing enums and models
from src.models.domain import (
    JobStatus, GPUStatus, OrganizationRole,
    JobBase, JobCreate, JobUpdate, JobResponse,
    GPUBase, GPUCreate, GPUUpdate, GPUResponse,
    OrganizationBase, OrganizationCreate, OrganizationResponse,
    OrganizationMemberBase, OrganizationMemberCreate, OrganizationMemberResponse,
    APIKeyBase, APIKeyCreate, APIKeyResponse
)

# New enums
class WebhookStatus(str, Enum):
    """Webhook status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"

class WebhookType(str, Enum):
    """Webhook type enum"""
    JOB_STATUS = "job_status"
    GPU_STATUS = "gpu_status"
    SYSTEM = "system"

class WebhookEventType(str, Enum):
    """Webhook event type enum"""
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    GPU_ADDED = "gpu.added"
    GPU_REMOVED = "gpu.removed"
    GPU_ALLOCATED = "gpu.allocated"
    GPU_RELEASED = "gpu.released"

# Enhanced GPU Resource Models
class GPUResourceBase(BaseModel):
    """Base GPU resource model with enhanced fields"""
    name: str = Field(..., description="GPU name")
    gpu_type: str = Field(..., description="Type of GPU (e.g., NVIDIA A100)")
    provider: str = Field(..., description="Cloud provider or 'on-premise'")
    provider_id: Optional[str] = Field(None, description="Provider-specific resource ID")
    organization_id: str = Field(..., description="Organization ID")
    memory_total: int = Field(..., description="Total GPU memory in MB")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="GPU capabilities")
    cost_per_hour: Optional[Decimal] = Field(None, description="Cost per hour in USD")
    is_spot: bool = Field(default=False, description="Whether this is a spot instance")
    
    class Config:
        from_attributes = True

class GPUResourceCreate(GPUResourceBase):
    """GPU resource creation model"""
    pass

class GPUResourceUpdate(BaseModel):
    """GPU resource update model"""
    name: Optional[str] = None
    status: Optional[str] = None
    memory_allocated: Optional[int] = None
    in_use: Optional[bool] = None
    cost_per_hour: Optional[Decimal] = None
    termination_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    last_active: Optional[datetime] = None

    class Config:
        from_attributes = True

class GPUResourceResponse(GPUResourceBase):
    """GPU resource response model"""
    id: str = Field(..., description="GPU resource ID")
    status: str = Field("available", description="Current GPU status")
    memory_allocated: int = Field(0, description="Currently allocated memory in MB")
    in_use: bool = Field(False, description="Whether the GPU is currently in use")
    spot_request_id: Optional[str] = Field(None, description="Spot request ID if applicable")
    termination_time: Optional[datetime] = Field(None, description="Spot instance termination time")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    last_active: datetime = Field(..., description="Last activity timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")

    class Config:
        from_attributes = True

# GPU Metrics Models
class GPUMetricBase(BaseModel):
    """Base GPU metric model"""
    gpu_id: str = Field(..., description="GPU ID")
    memory_used: int = Field(..., description="Used GPU memory in MB")
    memory_total: int = Field(..., description="Total GPU memory in MB")
    gpu_utilization: Optional[float] = Field(None, description="GPU utilization (0-100)")
    power_usage: Optional[float] = Field(None, description="Power usage in watts")
    temperature: Optional[float] = Field(None, description="GPU temperature in Celsius")
    
    class Config:
        from_attributes = True

class GPUMetricCreate(GPUMetricBase):
    """GPU metric creation model"""
    pass

class GPUMetricResponse(GPUMetricBase):
    """GPU metric response model"""
    id: str = Field(..., description="Metric ID")
    timestamp: datetime = Field(..., description="Metric timestamp")

    class Config:
        from_attributes = True

# Enhanced Job Models
class EnhancedJobBase(JobBase):
    """Enhanced job base model"""
    model_name: str = Field(..., description="Name of the model to run")
    memory: Optional[int] = Field(None, description="Memory required in MB")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    
    class Config:
        from_attributes = True

class EnhancedJobCreate(EnhancedJobBase):
    """Enhanced job creation model"""
    pass

class EnhancedJobUpdate(JobUpdate):
    """Enhanced job update model"""
    compute_status: Optional[str] = None
    compute_logs: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EnhancedJobResponse(EnhancedJobBase):
    """Enhanced job response model"""
    id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Current job status")
    gpu_id: Optional[str] = Field(None, description="ID of GPU running the job")
    compute_id: Optional[str] = Field(None, description="Compute provider job ID")
    compute_status: Optional[str] = Field(None, description="Status from compute provider")
    compute_logs: Optional[Dict[str, Any]] = Field(None, description="Logs from compute provider")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

# Cost Tracking Models
class CostTrackingBase(BaseModel):
    """Base cost tracking model"""
    organization_id: str = Field(..., description="Organization ID")
    gpu_id: str = Field(..., description="GPU ID")
    job_id: str = Field(..., description="Job ID")
    start_time: datetime = Field(..., description="Start time")
    cost_per_hour: Decimal = Field(..., description="Cost per hour in USD")
    
    class Config:
        from_attributes = True

class CostTrackingCreate(CostTrackingBase):
    """Cost tracking creation model"""
    pass

class CostTrackingUpdate(BaseModel):
    """Cost tracking update model"""
    end_time: Optional[datetime] = None
    total_cost: Optional[Decimal] = None

    class Config:
        from_attributes = True

class CostTrackingResponse(CostTrackingBase):
    """Cost tracking response model"""
    id: str = Field(..., description="Cost tracking ID")
    end_time: Optional[datetime] = Field(None, description="End time")
    total_cost: Optional[Decimal] = Field(None, description="Total cost in USD")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True

# Webhook Models
class WebhookBase(BaseModel):
    """Base webhook model"""
    organization_id: str = Field(..., description="Organization ID")
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Events to subscribe to")
    type: WebhookType = Field(WebhookType.JOB_STATUS, description="Webhook type")
    signing_secret: str = Field(..., description="Signing secret for webhook")
    
    class Config:
        from_attributes = True

class WebhookCreate(WebhookBase):
    """Webhook creation model"""
    pass

class WebhookUpdate(BaseModel):
    """Webhook update model"""
    url: Optional[str] = None
    events: Optional[List[str]] = None
    status: Optional[WebhookStatus] = None
    is_active: Optional[bool] = None
    signing_secret: Optional[str] = None

    class Config:
        from_attributes = True

class WebhookResponse(WebhookBase):
    """Webhook response model"""
    id: str = Field(..., description="Webhook ID")
    status: WebhookStatus = Field(WebhookStatus.ACTIVE, description="Webhook status")
    error_rate: float = Field(0.0, description="Recent error rate (0-1)")
    is_active: bool = Field(True, description="Whether webhook is active")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")

    class Config:
        from_attributes = True

# Webhook Delivery Models
class WebhookDeliveryBase(BaseModel):
    """Base webhook delivery model"""
    webhook_id: str = Field(..., description="Webhook ID")
    event_type: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    
    class Config:
        from_attributes = True

class WebhookDeliveryCreate(WebhookDeliveryBase):
    """Webhook delivery creation model"""
    pass

class WebhookDeliveryResponse(WebhookDeliveryBase):
    """Webhook delivery response model"""
    id: str = Field(..., description="Delivery ID")
    response_status: Optional[int] = Field(None, description="HTTP response status")
    response_body: Optional[str] = Field(None, description="Response body")
    error_message: Optional[str] = Field(None, description="Error message if delivery failed")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True

# Prediction Models
class PredictionBase(BaseModel):
    """Base prediction model"""
    organization_id: str = Field(..., description="Organization ID")
    model: str = Field(..., description="Model name")
    type: str = Field("text", description="Prediction type (text, image, etc.)")
    version: Optional[str] = Field(None, description="Model version")
    input: str = Field(..., description="Input text")
    webhook_id: Optional[str] = Field(None, description="Webhook ID")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    
    class Config:
        from_attributes = True

class PredictionCreate(PredictionBase):
    """Prediction creation model"""
    pass

class PredictionUpdate(BaseModel):
    """Prediction update model"""
    status: Optional[str] = None
    output: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PredictionResponse(PredictionBase):
    """Prediction response model"""
    id: str = Field(..., description="Prediction ID")
    status: str = Field("queued", description="Prediction status")
    output: Optional[str] = Field(None, description="Output text")
    processing_started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")

    class Config:
        from_attributes = True
