"""
FastAPI routes for the 10K Insight Agent API.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pathlib import Path

from ..graph.dag import dag_app
from ..utils.logging import setup_logger
from ..utils.llm_factory import get_factory

logger = setup_logger(__name__)

router = APIRouter()

# Global factory instance (initialized once)
_factory = None


def get_llm_factory():
    """Get or create the global LLM factory singleton."""
    global _factory
    if _factory is None:
        logger.info("🏭 Initializing LLM Factory...")
        _factory = get_factory()
    return _factory


def load_config() -> Dict[str, Any]:
    """Load configuration via the LLM factory."""
    factory = get_llm_factory()
    return factory.get_config()


def get_llm_manager():
    """Get or create LLM manager from the factory."""
    factory = get_llm_factory()
    return factory.create_llm_manager()


def get_embedder():
    """Get or create embedder from the factory."""
    factory = get_llm_factory()
    return factory.create_embedder()


@router.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "10K Insight Agent",
        "version": "0.1.0",
        "status": "running"
    }


@router.get("/analyze")
async def analyze_company(
    query: str = Query(..., description="Analysis query with company name"),
    company: Optional[str] = Query(None, description="Specific company name (for disambiguation)")
) -> Dict[str, Any]:
    """
    Analyze a company's 10-K and match to product catalog.
    
    Args:
        query: User query (e.g., "Analyze Microsoft's 10-K risks")
        company: Optional specific company name if disambiguation needed
    
    Returns:
        Analysis results with insights, matches, and pitch
    """
    logger.info(f"Received analysis request: {query}")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize multi-provider managers
        llm_manager = get_llm_manager(config)
        embedder = get_embedder(config)
        
        # Validate required config
        if not config.get("sec_user_agent"):
            raise HTTPException(
                status_code=500,
                detail="SEC User-Agent not configured"
            )
        
        # Initialize state
        initial_state = {
            "user_query": query,
            "config": config,
            "llm_manager": llm_manager,
            "embedder": embedder,
            "trace": []
        }
        
        # If specific company provided, add to state
        if company:
            initial_state["user_query"] = f"{company} {query}"
        
        # Run the DAG
        logger.info("Invoking DAG workflow")
        result = await dag_app.ainvoke(initial_state)
        
        # Check for disambiguation
        if result.get("status") == "disambiguation_required":
            return {
                "status": "disambiguation_required",
                "message": "Multiple companies found. Please specify which one:",
                "candidates": result.get("candidates", []),
                "trace": result.get("trace", [])
            }
        
        # Check for errors
        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error")
            )
        
        # Format successful response
        response = {
            "status": "success",
            "company": result.get("company"),
            "ticker": result.get("ticker"),
            "filing_url": result.get("filing_url"),
            "filing_date": result.get("filing_date"),
            "embedding_chunks": result.get("chunks"),
            "insights": {
                "pain_points": result.get("pains", []),
                "product_matches": result.get("matches", []),
                "objections": result.get("objections", []),
                "draft_pitch": result.get("pitch")
            },
            "citations": result.get("citations", []),
            "trace": result.get("trace", [])
        }
        
        logger.info(f"Analysis completed for {result.get('company')}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Detailed health check."""
    config_path = Path("src/configs/settings.yaml")
    catalog_path = Path("src/knowledge/products.json")
    
    return {
        "status": "healthy",
        "config_exists": config_path.exists(),
        "catalog_exists": catalog_path.exists(),
        "components": {
            "dag": "operational",
            "nodes": "loaded"
        }
    }
