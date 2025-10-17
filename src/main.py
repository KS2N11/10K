"""
FastAPI application entry point for 10K Insight Agent.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api.routes import router
from .api.routes_v2 import router as router_v2
from .database.database import init_db
from .utils.logging import setup_logger

# Initialize logger
logger = setup_logger(__name__, level="INFO")

# Create FastAPI app
app = FastAPI(
    title="10K Insight Agent",
    description="Analyze SEC 10-K filings and match to product catalog using AI agents",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="", tags=["analysis"])
app.include_router(router_v2, tags=["batch"])

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("10K Insight Agent v2.0 starting up...")
    logger.info("Initializing database...")
    init_db()
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
