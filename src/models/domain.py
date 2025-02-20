from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    """Job status enum"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GPUStatus(str, Enum):
    """GPU status enum"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class JobBase(BaseModel):
    """Base job model"""
    model_type: str = Field(..., description="Type of model to run")
    prompt: str = Field(..., description="Input prompt for the model")
    organization_id: str = Field(..., description="Organization ID")
    priority: int = Field(default=1, description="Job priority (1-10)")
    
    class Config:
        from_attributes = True

class JobCreate(JobBase):
    """Job creation model"""
    pass

class JobUpdate(BaseModel):
    """Job update model"""
    status: Optional[JobStatus] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    gpu_id: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobResponse(JobBase):
    """Job response model"""
    id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if job failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Job results")
    gpu_id: Optional[str] = Field(None, description="ID of GPU running the job")

    class Config:
        from_attributes = True

class GPUBase(BaseModel):
    """Base GPU model"""
    name: str = Field(..., description="GPU name")
    organization_id: str = Field(..., description="Organization ID")
    memory_total: int = Field(..., description="Total GPU memory in MB")
    memory_used: int = Field(default=0, description="Used GPU memory in MB")
    
    class Config:
        from_attributes = True

class GPUCreate(GPUBase):
    """GPU creation model"""
    pass

class GPUUpdate(BaseModel):
    """GPU update model"""
    status: Optional[GPUStatus] = None
    memory_used: Optional[int] = None
    current_job_id: Optional[str] = None

    class Config:
        from_attributes = True

class GPUResponse(GPUBase):
    """GPU response model"""
    id: str = Field(..., description="GPU ID")
    status: GPUStatus = Field(..., description="Current GPU status")
    current_job_id: Optional[str] = Field(None, description="ID of currently running job")
    created_at: datetime = Field(..., description="GPU registration timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class OrganizationRole(str, Enum):
    """Organization role enum"""
    ADMIN = "admin"
    MEMBER = "member"

class OrganizationBase(BaseModel):
    """Base organization model"""
    name: str = Field(..., description="Organization name")
    
    class Config:
        from_attributes = True

class OrganizationCreate(OrganizationBase):
    """Organization creation model"""
    admin_email: EmailStr = Field(..., description="Email of the organization admin")

class OrganizationResponse(OrganizationBase):
    """Organization response model"""
    id: str = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Organization creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class OrganizationMemberBase(BaseModel):
    """Base organization member model"""
    user_id: str = Field(..., description="User ID")
    role: OrganizationRole = Field(..., description="Member role in the organization")
    
    class Config:
        from_attributes = True

class OrganizationMemberCreate(OrganizationMemberBase):
    """Organization member creation model"""
    organization_id: str = Field(..., description="Organization ID")
    email: EmailStr = Field(..., description="Member email")

class OrganizationMemberResponse(OrganizationMemberBase):
    """Organization member response model"""
    id: str = Field(..., description="Member ID")
    organization_id: str = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Member creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class APIKeyBase(BaseModel):
    """Base API key model"""
    name: str = Field(..., description="API key name")
    organization_id: str = Field(..., description="Organization ID")
    
    class Config:
        from_attributes = True

class APIKeyCreate(APIKeyBase):
    """API key creation model"""
    pass

class APIKeyResponse(APIKeyBase):
    """API key response model"""
    id: str = Field(..., description="API key ID")
    key: str = Field(..., description="API key (only shown on creation)")
    created_at: datetime = Field(..., description="Key creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    class Config:
        from_attributes = True
