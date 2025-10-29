"""
FastAPI routes for the 10K Insight Agent API.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import yaml
from pathlib import Path
import os
from dotenv import load_dotenv

from ..graph.dag import dag_app
from ..utils.logging import setup_logger
from ..utils.multi_llm import create_llm_manager
from ..utils.multi_embeddings import MultiProviderEmbeddings

logger = setup_logger(__name__)

router = APIRouter()

# Global managers (initialized once)
_llm_manager = None
_embedder = None


def load_config() -> Dict[str, Any]:
    """Load configuration from settings.yaml."""
    config_path = Path("src/configs/settings.yaml")
    
    # Load environment variables
    load_dotenv()
    
    if not config_path.exists():
        logger.warning("settings.yaml not found, using defaults")
        
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "groq_api_key": os.getenv("GROQ_API_KEY"),
            "cohere_api_key": os.getenv("COHERE_API_KEY"),
            "sec_user_agent": os.getenv("SEC_USER_AGENT"),
            "vector_store_dir": os.getenv("VECTOR_STORE_DIR", "src/stores/vector"),
            "catalog_store_dir": os.getenv("CATALOG_STORE_DIR", "src/stores/catalog"),
            "embedding": {
                "primary_provider": os.getenv("PRIMARY_EMBEDDING_PROVIDER", "sentence-transformers"),
                "fallback_providers": ["openai"],
                "sentence_transformers": {
                    "model_name": "all-mpnet-base-v2",
                    "device": "cpu"
                },
                "openai": {
                    "model_name": "text-embedding-3-large"
                }
            },
            "llm": {
                "primary_provider": os.getenv("PRIMARY_LLM_PROVIDER", "groq"),
                "fallback_providers": ["openai"],
                "groq": {
                    "model_name": "openai/gpt-oss-120b",
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                "openai": {
                    "model_name": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            },
            "rate_limits": {
                "groq": {"rpm": 30, "tpm": 7000},
                "openai": {"rpm": 3500, "tpm": 90000}
            },
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "top_k_chunks": 10,
            "top_k_products": 6,
            "max_iterations": 3,
            "min_confidence": 0.6,
            "log_level": "INFO"
        }
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Set API keys from environment (they override config file)
    config["openai_api_key"] = os.getenv("OPENAI_API_KEY", config.get("openai_api_key"))
    config["groq_api_key"] = os.getenv("GROQ_API_KEY", config.get("groq_api_key"))
    config["cohere_api_key"] = os.getenv("COHERE_API_KEY", config.get("cohere_api_key"))
    config["sec_user_agent"] = os.getenv("SEC_USER_AGENT", config.get("sec_user_agent"))
    
    return config


def get_llm_manager(config: Dict[str, Any]):
    """Get or create LLM manager singleton."""
    global _llm_manager
    if _llm_manager is None:
        logger.info("🚀 Initializing multi-provider LLM manager...")
        _llm_manager = create_llm_manager(config)
    return _llm_manager


def get_embedder(config: Dict[str, Any]):
    """Get or create embedder singleton."""
    global _embedder
    if _embedder is None:
        logger.info("🚀 Initializing multi-provider embeddings...")
        emb_config = config.get("embedding", {})
        _embedder = MultiProviderEmbeddings(
            primary_provider=emb_config.get("primary_provider", "sentence-transformers"),
            fallback_providers=emb_config.get("fallback_providers", []),
            config=emb_config,
        )
    return _embedder


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
