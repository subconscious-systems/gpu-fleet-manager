from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
import asyncio
from contextlib import asynccontextmanager

from src.api import jobs, gpus, monitoring
from src.utils.monitoring import setup_monitoring
from dotenv import load_dotenv
from src.config import get_settings
from src.config.utils import configure_logging, get_api_cors_origins, build_api_url, is_development_mode

# Load environment variables
load_dotenv()

# Initialize settings
settings = get_settings()

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start monitoring in the background if enabled
    if settings.monitoring.enable_prometheus:
        monitoring_task = asyncio.create_task(
            setup_monitoring(metrics_port=settings.monitoring.prometheus_port)
        )
        logger.info(f"Prometheus metrics enabled on port {settings.monitoring.prometheus_port}")
    else:
        monitoring_task = None
        logger.info("Prometheus metrics disabled")
    
    yield
    
    # Cancel monitoring on shutdown if it was started
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

# Initialize FastAPI app
app = FastAPI(
    title=settings.project_name,
    description="API for managing GPU jobs and resources",
    version=settings.api_version,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_api_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# API prefix based on configuration
api_prefix = f"/api/{settings.api_version}"

# Include routers
app.include_router(
    jobs.router,
    prefix=api_prefix,
    tags=["jobs"]
)

app.include_router(
    gpus.router,
    prefix=api_prefix,
    tags=["gpus"]
)

app.include_router(
    monitoring.router,
    prefix=api_prefix,
    tags=["monitoring"]
)

# Root endpoint to serve the demo UI
@app.get("/")
async def root():
    """Serve the demo UI"""
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(static_dir, "index.html"))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": settings.api_version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host=settings.api.host, 
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers
    )
