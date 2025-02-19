from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from rich.console import Console
from rich.table import Table

from src.db.repository import Repository
from src.db.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.model_runner import BaseModelRunner

# Configure rich console for beautiful output
console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobLifecycleDemo:
    def __init__(self, app: FastAPI, supabase_config: SupabaseConfig):
        self.app = app
        self.supabase_config = supabase_config
        self.db: Repository | None = None
        self.model_runner = BaseModelRunner()
        
    async def initialize(self):
        """Initialize database connection and repository."""
        client = await SupabaseClient.get_instance(self.supabase_config)
        self.db = Repository(client)
        logger.info("✅ Database connection initialized")

    async def submit_test_jobs(self, org_id: str) -> List[Dict]:
        """Submit a batch of test jobs with different configurations."""
        jobs = []
        test_configs = [
            {
                "name": "Text Generation",
                "model_type": "text",
                "gpu_requirements": {"min_memory": 8, "gpu_type": "NVIDIA A100"},
                "params": {"prompt": "Write a story about AI", "max_length": 100}
            },
            {
                "name": "Image Generation",
                "model_type": "image",
                "gpu_requirements": {"min_memory": 16, "gpu_type": "NVIDIA A100"},
                "params": {"prompt": "A beautiful sunset", "size": "1024x1024"}
            }
        ]
        
        for config in test_configs:
            try:
                job = await self.db.create_gpu_job(org_id, config)
                jobs.append(job)
                console.print(f"✅ Submitted job: {config['name']}", style="green")
            except Exception as e:
                console.print(f"❌ Failed to submit job: {config['name']}", style="red")
                console.print(f"Error: {str(e)}", style="red")
        
        return jobs

    async def allocate_gpus(self, org_id: str, jobs: List[Dict]) -> None:
        """Attempt to allocate GPUs for submitted jobs."""
        for job in jobs:
            try:
                # Find available GPU matching requirements
                gpus = await self.db.get_available_gpus(
                    org_id,
                    min_memory=job["gpu_requirements"]["min_memory"],
                    gpu_type=job["gpu_requirements"]["gpu_type"]
                )
                
                if not gpus:
                    await self.db.update_gpu_job(
                        job["id"], org_id, {"status": "waiting_for_gpu"}
                    )
                    console.print(f"⏳ Job {job['name']}: Waiting for GPU", style="yellow")
                    continue
                
                # Allocate first available GPU
                gpu = gpus[0]
                allocated_gpu = await self.db.allocate_gpu(gpu["id"], job["id"], org_id)
                
                # Update job status
                await self.db.update_gpu_job(
                    job["id"], org_id, {"status": "running", "gpu_id": gpu["id"]}
                )
                
                console.print(
                    f"✅ Job {job['name']}: Allocated GPU {gpu['id']}", 
                    style="green"
                )
                
            except Exception as e:
                console.print(f"❌ Failed to allocate GPU for job: {job['name']}", style="red")
                console.print(f"Error: {str(e)}", style="red")

    async def monitor_jobs(self, org_id: str, jobs: List[Dict]) -> None:
        """Monitor and display job status updates."""
        while True:
            table = Table(title="Job Status Dashboard")
            table.add_column("Job ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("GPU", style="yellow")
            table.add_column("Updated At", style="blue")
            
            current_jobs = await self.db.get_gpu_jobs(org_id)
            
            for job in current_jobs:
                table.add_row(
                    str(job["id"]),
                    job["name"],
                    job["status"],
                    job.get("gpu_id", "N/A"),
                    job.get("updated_at", "N/A")
                )
            
            console.clear()
            console.print(table)
            
            # Check if all jobs are completed
            if all(job["status"] in ["completed", "failed"] for job in current_jobs):
                break
                
            await asyncio.sleep(2)

    async def cleanup(self, org_id: str) -> None:
        """Release all GPUs and clean up resources."""
        try:
            # Get all allocated GPUs
            allocated_gpus = await self.db.get_gpu_jobs(org_id, status="running")
            
            for job in allocated_gpus:
                if "gpu_id" in job:
                    await self.db.release_gpu(job["gpu_id"], org_id)
                    console.print(f"✅ Released GPU: {job['gpu_id']}", style="green")
            
            if self.db and hasattr(self.db.client, 'close'):
                await self.db.client.close()
                console.print("✅ Cleaned up database connections", style="green")
                
        except Exception as e:
            console.print("❌ Error during cleanup", style="red")
            console.print(f"Error: {str(e)}", style="red")

async def run_demo():
    """Run the complete job lifecycle demo."""
    # Load configuration
    config = SupabaseConfig(
        url="YOUR_SUPABASE_URL",
        key="YOUR_SUPABASE_KEY",
        timeout=10.0,
        max_connections=10
    )
    
    app = FastAPI()
    demo = JobLifecycleDemo(app, config)
    
    try:
        # Initialize
        await demo.initialize()
        
        # Use a test organization ID
        org_id = "test-org-123"
        
        # Submit test jobs
        console.print("\n📝 Submitting test jobs...", style="bold blue")
        jobs = await demo.submit_test_jobs(org_id)
        
        # Allocate GPUs
        console.print("\n🔄 Allocating GPUs...", style="bold blue")
        await demo.allocate_gpus(org_id, jobs)
        
        # Monitor jobs
        console.print("\n📊 Monitoring job status...", style="bold blue")
        await demo.monitor_jobs(org_id, jobs)
        
    except Exception as e:
        console.print("❌ Demo failed with error:", style="bold red")
        console.print(str(e), style="red")
        
    finally:
        # Cleanup
        console.print("\n🧹 Cleaning up resources...", style="bold blue")
        await demo.cleanup(org_id)

if __name__ == "__main__":
    asyncio.run(run_demo())
