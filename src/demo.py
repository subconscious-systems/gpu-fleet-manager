import asyncio
import logging
from datetime import datetime
from src.core.job_manager import JobManager
from src.db.repository import Repository
from src.db.supabase_client import SupabaseClient, SupabaseConfig
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_job_submission(job_manager: JobManager, organization_id: str):
    """Submit demo jobs to test the system"""
    
    # Demo Text Generation Job
    text_job = {
        "name": "demo-text-job",
        "model_type": "text-generation",
        "model_name": "phi-2",
        "organization_id": organization_id,
        "user_id": "demo-user",
        "parameters": {
            "prompt": "Write a Python function to calculate fibonacci numbers"
        },
        "priority": "normal",
        "batch_size": 1
    }
    
    # Demo Image Generation Job
    image_job = {
        "name": "demo-image-job",
        "model_type": "image-generation",
        "model_name": "stable-diffusion-xl",
        "organization_id": organization_id,
        "user_id": "demo-user",
        "parameters": {
            "prompt": "A beautiful sunset over a mountain lake, photorealistic",
            "negative_prompt": "blurry, low quality"
        },
        "priority": "high",
        "batch_size": 1
    }
    
    # Submit jobs
    logger.info("Submitting demo jobs...")
    text_job_result = await job_manager.submit_job(text_job)
    image_job_result = await job_manager.submit_job(image_job)
    
    return text_job_result.id, image_job_result.id

async def monitor_jobs(job_manager: JobManager, job_ids: list, organization_id: str):
    """Monitor job status until completion"""
    completed = set()
    
    while len(completed) < len(job_ids):
        for job_id in job_ids:
            if job_id in completed:
                continue
                
            status = await job_manager.get_job_status(job_id, organization_id)
            logger.info(f"Job {job_id}: {status.status}")
            
            if status.status in ["COMPLETED", "FAILED", "CANCELLED"]:
                completed.add(job_id)
                if status.status == "COMPLETED":
                    logger.info(f"Job {job_id} completed successfully!")
                    if hasattr(status, 'output_data'):
                        logger.info(f"Output: {status.output_data}")
                else:
                    logger.error(f"Job {job_id} {status.status}: {status.error_message}")
        
        await asyncio.sleep(5)

async def main():
    """Main demo function"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize database client
        config = SupabaseConfig(
            url="your_supabase_url",
            key="your_supabase_key"
        )
        client = await SupabaseClient.get_instance(config)
        repo = Repository(client)
        
        # Initialize job manager
        job_manager = JobManager(repo)
        
        # Demo organization
        organization_id = "demo-org-123"
        
        logger.info("Starting GPU Fleet Manager Demo")
        logger.info("=================================")
        
        # Submit demo jobs
        job_ids = await demo_job_submission(job_manager, organization_id)
        
        # Monitor jobs until completion
        await monitor_jobs(job_manager, job_ids, organization_id)
        
        # Display final stats
        jobs = await job_manager.get_organization_jobs(organization_id)
        logger.info("\nFinal Job Statistics:")
        logger.info("=====================")
        for job in jobs:
            logger.info(f"Job {job.id}:")
            logger.info(f"  Status: {job.status}")
            logger.info(f"  Model: {job.model_name}")
            logger.info(f"  Created: {job.created_at}")
            if job.completed_at:
                duration = (job.completed_at - job.created_at).total_seconds()
                logger.info(f"  Duration: {duration:.2f} seconds")
            logger.info("---------------------")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        # Cleanup
        await job_manager.stop_queue_processor()
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
