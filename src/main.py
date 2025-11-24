"""
FastAPI application entry point for 10K Insight Agent.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from .api.routes import router, load_config
from .api.routes_v2 import router as router_v2
from .api.scheduler_routes import router as scheduler_router
from .database.database import init_db
from .utils.logging import setup_logger
from .services.autonomous_scheduler import get_autonomous_scheduler

# Initialize logger
logger = setup_logger(__name__, level="INFO")

# Create FastAPI app
app = FastAPI(
    title="10K Insight Agent",
    description="Analyze SEC 10-K filings and match to product catalog using AI agents",
    version="3.0.0 - Autonomous Scheduler",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS from environment variable or default to permissive for development
cors_origins = os.getenv("CORS_ORIGINS", "*")
if cors_origins == "*":
    allow_origins = ["*"]
    logger.warning("CORS configured to allow all origins (*). Set CORS_ORIGINS env var for production.")
else:
    allow_origins = [origin.strip() for origin in cors_origins.split(",")]
    logger.info(f"CORS configured for origins: {allow_origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="", tags=["analysis"])
app.include_router(router_v2, tags=["batch"])
app.include_router(scheduler_router, tags=["scheduler"])

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("10K Insight Agent v3.0 (Autonomous) starting up...")
    logger.info("Initializing database...")
    init_db()
    
    # Start autonomous scheduler
    try:
        logger.info("Starting autonomous scheduler...")
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        logger.info("✅ Autonomous scheduler started")
    except Exception as e:
        logger.error(f"Failed to start autonomous scheduler: {e}")
        logger.warning("Scheduler can be started manually via API")
    
    logger.info("✅ FastAPI application ready")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("10K Insight Agent shutting down...")


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        timeout_keep_alive=300  # 5 minutes timeout for long-running requests
    )
