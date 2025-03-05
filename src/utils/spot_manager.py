from typing import Optional, Dict, List
import logging
import asyncio
from datetime import datetime, timedelta
import aiohttp
from sqlalchemy.orm import Session
import boto3
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.gpu import GPU, GPUStatus, GPUProvider
from ..config import get_settings
from ..config.utils import get_gpu_provider_config
from .monitoring import monitor

logger = logging.getLogger(__name__)

class SpotManager:
    def __init__(self, db: Session, config: Optional[Dict] = None):
        """
        Initialize the spot instance manager
        
        Args:
            db: Database session for persisting GPU information
            config: Optional configuration override. If not provided,
                   configuration is loaded from central settings.
        """
        self.db = db
        
        # Get configuration from central settings if not provided
        if config is None:
            settings = get_settings()
            self.config = settings.spot_instances.dict()
        else:
            self.config = config
            
        # Get provider configs
        provider_config = get_gpu_provider_config()
        
        # Initialize providers
        self.providers = {
            "sfcompute": SFComputeProvider(self.config.get("sfcompute", {})),
            "vast": VastAIProvider(self.config.get("vast", {})),
            "aws": AWSProvider(provider_config if provider_config["provider_type"] == "aws" else self.config.get("aws", {}))
        }
        
        # Configuration
        self.max_spot_instances = self.config.get("max_spot_instances", 5)
        self.price_threshold = self.config.get("spot_price_threshold", 2.0)
        self.min_instance_lifetime = self.config.get("min_instance_lifetime", 3600)  # 1 hour

    @monitor
    async def provision_gpu(
        self,
        min_memory: int,
        capabilities: Dict,
        max_price: Optional[float] = None
    ) -> Optional[GPU]:
        """Provision a new spot GPU instance"""
        
        # Check if we're at capacity
        current_spots = self.db.query(GPU).filter(
            GPU.provider == GPUProvider.SPOT
        ).count()
        
        if current_spots >= self.max_spot_instances:
            logger.warning("Maximum spot instances reached")
            return None

        # Get best price across providers
        best_offer = await self._find_best_spot_offer(
            min_memory=min_memory,
            capabilities=capabilities,
            max_price=max_price or self.price_threshold
        )
        
        if not best_offer:
            logger.warning("No suitable spot instances available")
            return None

        try:
            # Provision the instance
            provider = self.providers[best_offer["provider"]]
            instance_info = await provider.provision_instance(best_offer["instance_type"])
            
            # Create GPU record
            gpu = GPU(
                provider=GPUProvider.SPOT,
                provider_id=instance_info["instance_id"],
                name=instance_info["gpu_name"],
                status=GPUStatus.PROVISIONING,
                total_memory=instance_info["total_memory"],
                available_memory=instance_info["total_memory"],
                capabilities=instance_info["capabilities"],
                cost_per_hour=best_offer["price"],
                spot_request_id=instance_info.get("spot_request_id"),
                current_jobs=[]
            )
            
            self.db.add(gpu)
            self.db.commit()
            
            # Wait for instance to be ready
            await self._wait_for_instance(gpu)
            return gpu
            
        except Exception as e:
            logger.error(f"Failed to provision spot instance: {e}")
            return None

    async def _find_best_spot_offer(
        self,
        min_memory: int,
        capabilities: Dict,
        max_price: float
    ) -> Optional[Dict]:
        """Find the best spot instance offer across providers"""
        offers = []
        
        # Gather offers from all providers
        for provider_name, provider in self.providers.items():
            try:
                provider_offers = await provider.get_spot_offers(
                    min_memory=min_memory,
                    capabilities=capabilities
                )
                
                for offer in provider_offers:
                    if offer["price"] <= max_price:
                        offers.append({
                            "provider": provider_name,
                            **offer
                        })
                        
            except Exception as e:
                logger.error(f"Error getting offers from {provider_name}: {e}")
                
        if not offers:
            return None
            
        # Return cheapest suitable offer
        return min(offers, key=lambda x: x["price"])

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=30)
    )
    async def _wait_for_instance(self, gpu: GPU) -> bool:
        """Wait for spot instance to be ready"""
        provider = self.providers[gpu.provider]
        
        while True:
            status = await provider.check_instance_status(gpu.provider_id)
            
            if status["state"] == "ready":
                gpu.status = GPUStatus.AVAILABLE
                self.db.commit()
                return True
                
            elif status["state"] == "failed":
                gpu.status = GPUStatus.OFFLINE
                self.db.commit()
                raise Exception(f"Instance failed to start: {status.get('error')}")
                
            await asyncio.sleep(10)

    async def terminate_gpu(self, gpu: GPU):
        """Terminate a spot instance"""
        if gpu.provider != GPUProvider.SPOT:
            return
            
        try:
            provider = self.providers[gpu.provider]
            await provider.terminate_instance(gpu.provider_id)
            
            gpu.status = GPUStatus.TERMINATING
            gpu.termination_time = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error terminating spot instance {gpu.id}: {e}")

    async def monitor_spot_instances(self):
        """Monitor spot instances for termination notices and health"""
        while True:
            try:
                spot_gpus = self.db.query(GPU).filter(
                    GPU.provider == GPUProvider.SPOT,
                    GPU.status.in_([GPUStatus.AVAILABLE, GPUStatus.BUSY])
                ).all()
                
                for gpu in spot_gpus:
                    provider = self.providers[gpu.provider]
                    status = await provider.check_instance_status(gpu.provider_id)
                    
                    if status.get("termination_notice"):
                        logger.warning(f"Spot instance {gpu.id} scheduled for termination")
                        # Handle graceful shutdown
                        await self._handle_termination_notice(gpu)
                        
                    elif status["state"] == "failed":
                        logger.error(f"Spot instance {gpu.id} failed")
                        await self._handle_instance_failure(gpu)
                        
            except Exception as e:
                logger.error(f"Error monitoring spot instances: {e}")
                
            await asyncio.sleep(60)  # Check every minute

    async def _handle_termination_notice(self, gpu: GPU):
        """Handle spot instance termination notice"""
        # Mark GPU as terminating
        gpu.status = GPUStatus.TERMINATING
        gpu.termination_time = datetime.utcnow()
        self.db.commit()
        
        # Notify job manager to migrate jobs if needed
        # This would be implemented based on your job migration strategy

    async def _handle_instance_failure(self, gpu: GPU):
        """Handle spot instance failure"""
        gpu.status = GPUStatus.OFFLINE
        self.db.commit()
        
        # Attempt to provision replacement if needed
        if len(gpu.current_jobs) > 0:
            await self.provision_gpu(
                min_memory=gpu.total_memory,
                capabilities=gpu.capabilities
            )

class SFComputeProvider:
    """SFCompute.com API integration"""
    
    def __init__(self, config: Dict):
        """
        Initialize SFCompute provider
        
        Args:
            config: Provider-specific configuration
        """
        settings = get_settings()
        
        # Get credentials from config or central settings
        self.api_key = config.get("api_key") or settings.cloud_providers.sfcompute_api_key.get_secret_value()
        self.api_url = config.get("api_url") or settings.cloud_providers.sfcompute_api_url
        self.session = aiohttp.ClientSession()
        
    async def get_spot_offers(self, min_memory: int, capabilities: Dict) -> List[Dict]:
        """
        Get available spot instances from SFCompute
        
        Args:
            min_memory: Minimum GPU memory in GB
            capabilities: Required GPU capabilities
            
        Returns:
            List of spot instance offers
        """
        # Implementation details...
        pass
        
    async def provision_instance(self, instance_type: str) -> Dict:
        """
        Provision a spot instance
        
        Args:
            instance_type: Type of instance to provision
            
        Returns:
            Instance information
        """
        # Implementation details...
        pass
        
    async def check_instance_status(self, instance_id: str) -> Dict:
        """
        Check instance status
        
        Args:
            instance_id: ID of the instance to check
            
        Returns:
            Status information
        """
        # Implementation details...
        pass
        
    async def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate a spot instance
        
        Args:
            instance_id: ID of the instance to terminate
            
        Returns:
            True if terminated successfully
        """
        # Implementation details...
        pass


class VastAIProvider:
    """Vast.ai API integration"""
    
    def __init__(self, config: Dict):
        """
        Initialize Vast.ai provider
        
        Args:
            config: Provider-specific configuration
        """
        settings = get_settings()
        
        # Get credentials from config or central settings
        self.api_key = config.get("api_key") or settings.cloud_providers.vast_api_key.get_secret_value()
        self.api_url = config.get("api_url") or settings.cloud_providers.vast_api_url
        # Similar methods as SFComputeProvider...


class AWSProvider:
    """AWS EC2 GPU spot instances"""
    
    def __init__(self, config: Dict):
        """
        Initialize AWS provider
        
        Args:
            config: Provider-specific configuration
        """
        settings = get_settings()
        
        # Get AWS credentials from config or settings
        aws_access_key = config.get("aws_access_key_id") or (
            settings.gpu_provider.aws_access_key.get_secret_value() 
            if settings.gpu_provider.aws_access_key else None
        )
        
        aws_secret_key = config.get("aws_secret_access_key") or (
            settings.gpu_provider.aws_secret_key.get_secret_value()
            if settings.gpu_provider.aws_secret_key else None
        )
        
        region = config.get("region") or settings.gpu_provider.aws_region or "us-east-1"
        
        # Initialize boto3 client
        self.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        # Similar methods as other providers...
