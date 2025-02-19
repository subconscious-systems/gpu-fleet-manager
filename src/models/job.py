from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum
from typing import Optional
from datetime import datetime

from .base import Base

class JobStatus(str, enum.Enum):
    QUEUED = "queued"         # Initial state, waiting to be processed
    RUNNING = "running"       # Currently being processed
    COMPLETED = "completed"   # Successfully finished
    FAILED = "failed"         # Error occurred
    CANCELLED = "cancelled"   # User cancelled

class ComputeStatus(str, enum.Enum):
    """Track the status of compute resources separately"""
    AVAILABLE = "available"       # Ready to accept new jobs
    LOADING = "loading"          # Loading model or preparing resources
    PROCESSING = "processing"    # Currently processing jobs
    ERROR = "error"             # Error state
    TERMINATING = "terminating"  # Being shut down

class JobPriority(int, enum.Enum):
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    model_type = Column(String(50))  # 'llm', 'stable-diffusion', etc.
    model_name = Column(String(255))  # 'phi', 'deepseek', etc.
    priority = Column(Integer, default=JobPriority.NORMAL)
    status = Column(String(50), default=JobStatus.QUEUED)
    
    # Compute tracking
    compute_id = Column(String(255), nullable=True)      # ID of assigned compute resource
    compute_status = Column(String(50), nullable=True)   # Current status of compute
    compute_logs = Column(JSON, nullable=True)           # Logs from compute processing
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    gpu_assigned = Column(String(255), nullable=True)
    error_message = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    timeout_seconds = Column(Integer, nullable=True)
    parameters = Column(JSON)
    result_url = Column(String, nullable=True)
    cost_estimate = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<Job {self.id}: {self.model_name} ({self.status})>"
