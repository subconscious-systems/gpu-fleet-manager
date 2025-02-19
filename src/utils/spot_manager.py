from typing import Optional, Dict, List
import logging
import asyncio
from datetime import datetime, timedelta
import aiohttp
from sqlalchemy.orm import Session
import boto3
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.gpu import GPU, GPUStatus, GPUProvider
from .monitoring import monitor

logger = logging.getLogger(__name__)

class SpotManager:
    def __init__(self, db: Session, config: Dict):
        self.db = db
        self.config = config
        self.providers = {
            "sfcompute": SFComputeProvider(config.get("sfcompute", {})),
            "vast": VastAIProvider(config.get("vast", {})),
            "aws": AWSProvider(config.get("aws", {}))
        }
        
        # Configuration
        self.max_spot_instances = config.get("max_spot_instances", 5)
        self.price_threshold = config.get("spot_price_threshold", 2.0)
        self.min_instance_lifetime = config.get("min_instance_lifetime", 3600)  # 1 hour

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
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url", "https://api.sfcompute.com/v1")
        self.session = aiohttp.ClientSession()

    async def get_spot_offers(self, min_memory: int, capabilities: Dict) -> List[Dict]:
        """Get available spot instances from SFCompute"""
        async with self.session.get(
            f"{self.api_url}/spot/offers",
            params={
                "min_memory": min_memory,
                "capabilities": capabilities
            },
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as response:
            data = await response.json()
            return data["offers"]

    async def provision_instance(self, instance_type: str) -> Dict:
        """Provision a spot instance"""
        async with self.session.post(
            f"{self.api_url}/spot/provision",
            json={"instance_type": instance_type},
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as response:
            return await response.json()

    async def check_instance_status(self, instance_id: str) -> Dict:
        """Check instance status"""
        async with self.session.get(
            f"{self.api_url}/instances/{instance_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as response:
            return await response.json()

    async def terminate_instance(self, instance_id: str):
        """Terminate a spot instance"""
        async with self.session.post(
            f"{self.api_url}/spot/terminate/{instance_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as response:
            return await response.json()

class VastAIProvider:
    """Vast.ai API integration"""
    def __init__(self, config: Dict):
        self.api_key = config.get("api_key")
        # Similar methods as SFComputeProvider...

class AWSProvider:
    """AWS EC2 GPU spot instances"""
    def __init__(self, config: Dict):
        self.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            region_name=config.get("region", "us-east-1")
        )
        # Similar methods as other providers...
