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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start monitoring in the background
    monitoring_task = asyncio.create_task(setup_monitoring(metrics_port=9402))  # Changed from 9401
    yield
    # Cancel monitoring on shutdown
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass

# Initialize FastAPI app
app = FastAPI(
    title="GPU Fleet Manager",
    description="API for managing GPU jobs and resources",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(
    jobs.router,
    prefix="/api/v1",
    tags=["jobs"]
)

app.include_router(
    gpus.router,
    prefix="/api/v1",
    tags=["gpus"]
)

app.include_router(
    monitoring.router,
    prefix="/api/v1",
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
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
