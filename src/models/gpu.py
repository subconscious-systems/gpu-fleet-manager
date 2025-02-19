from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import enum

from .base import Base

class GPUStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    PROVISIONING = "provisioning"
    TERMINATING = "terminating"

class GPUProvider(str, enum.Enum):
    BASE = "base"
    SPOT = "spot"

class GPU(Base):
    __tablename__ = "gpus"

    id = Column(UUID, primary_key=True)
    name = Column(String(255))  # e.g., "NVIDIA RTX 4090"
    provider = Column(String(50))  # 'base' or 'spot'
    provider_id = Column(String(255))  # Provider-specific ID
    
    status = Column(String(50), default=GPUStatus.AVAILABLE)
    total_memory = Column(Integer)  # in MB
    available_memory = Column(Integer)
    
    current_jobs = Column(ARRAY(UUID), default=[])
    capabilities = Column(JSON)  # GPU capabilities/features
    
    cost_per_hour = Column(Float)
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    
    # Spot instance specific fields
    spot_request_id = Column(String(255), nullable=True)
    termination_time = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<GPU {self.name}: {self.status}>"

    @property
    def utilization(self):
        """Calculate current GPU utilization percentage"""
        if not self.total_memory:
            return 0
        return ((self.total_memory - self.available_memory) / self.total_memory) * 100

    @property
    def is_spot(self):
        """Check if this is a spot instance"""
        return self.provider == GPUProvider.SPOT
