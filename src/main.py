from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

# Import routers
from api import jobs, gpus, monitoring

app = FastAPI(
    title="GPU Fleet Manager",
    description="Distributed GPU management system for ML model execution",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(gpus.router, prefix="/api/v1/gpus", tags=["gpus"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
