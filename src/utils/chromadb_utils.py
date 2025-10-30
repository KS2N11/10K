"""
ChromaDB utilities for handling database corruption and recovery.
"""
from pathlib import Path
import shutil
from typing import Optional
import chromadb
from chromadb.config import Settings

from .logging import setup_logger

logger = setup_logger(__name__)


def reset_vector_store(vector_store_dir: Path) -> None:
    """
    Reset a corrupted vector store by removing and recreating it.
    
    Args:
        vector_store_dir: Path to the vector store directory
    """
    try:
        if vector_store_dir.exists():
            logger.warning(f"🗑️  Removing corrupted vector store at {vector_store_dir}")
            shutil.rmtree(vector_store_dir)
        
        vector_store_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created fresh vector store directory at {vector_store_dir}")
    except Exception as e:
        logger.error(f"❌ Failed to reset vector store: {e}")
        raise


def create_chromadb_client(
    vector_store_dir: Path,
    auto_recover: bool = True,
    max_retries: int = 2
) -> chromadb.PersistentClient:
    """
    Create a ChromaDB persistent client with automatic corruption recovery.
    
    Args:
        vector_store_dir: Path to the vector store directory
        auto_recover: Whether to automatically recover from corruption
        max_retries: Maximum number of retry attempts
    
    Returns:
        ChromaDB PersistentClient instance
    
    Raises:
        RuntimeError: If client creation fails after all retries
    """
    vector_store_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"🔧 Creating ChromaDB client at {vector_store_dir} (auto_recover={auto_recover}, max_retries={max_retries})")
    
    client = None
    last_error = None
    
    for attempt in range(max_retries):
        try:
            client = chromadb.PersistentClient(
                path=str(vector_store_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            
            if attempt > 0:
                logger.info(f"✅ Successfully created ChromaDB client after {attempt + 1} attempts")
            
            return client
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Check for known corruption errors
            is_corruption = (
                "PanicException" in error_type or
                "PanicException" in error_msg or
                "range start index" in error_msg or
                "out of range" in error_msg or
                "panic" in error_msg.lower() or
                "rust" in error_msg.lower()
            )
            
            if is_corruption and auto_recover and attempt < max_retries - 1:
                logger.warning(f"⚠️  ChromaDB corruption detected ({error_type}) (attempt {attempt + 1}/{max_retries})")
                logger.warning(f"Error: {error_msg}")
                logger.info("🔧 Attempting to recover by resetting vector store...")
                
                try:
                    reset_vector_store(vector_store_dir)
                    logger.info("✅ Vector store reset, retrying...")
                except Exception as reset_error:
                    logger.error(f"❌ Failed to reset vector store: {reset_error}")
                    raise
            else:
                # Not a corruption error, or out of retries, or auto-recover disabled
                if is_corruption:
                    logger.error(f"❌ ChromaDB corruption persists after {attempt + 1} attempts")
                raise
    
    # Should not reach here, but just in case
    raise RuntimeError(f"Failed to create ChromaDB client after {max_retries} retries. Last error: {last_error}")


def is_chromadb_corruption_error(error: Exception) -> bool:
    """
    Check if an exception is a ChromaDB corruption error.
    
    Args:
        error: Exception to check
    
    Returns:
        True if error indicates ChromaDB corruption
    """
    error_msg = str(error)
    corruption_indicators = [
        "PanicException",
        "range start index",
        "out of range",
        "panic",
        "rust",
        "sqlite",
    ]
    
    return any(indicator in error_msg for indicator in corruption_indicators)


def reset_all_vector_stores(base_dir: Path = Path("src/stores")) -> None:
    """
    Reset all vector stores (nuclear option for widespread corruption).
    
    Args:
        base_dir: Base directory containing vector stores
    """
    logger.warning("🗑️  Resetting ALL vector stores...")
    
    vector_dir = base_dir / "vector"
    catalog_dir = base_dir / "catalog"
    
    for dir_path in [vector_dir, catalog_dir]:
        if dir_path.exists():
            logger.info(f"Removing {dir_path}")
            shutil.rmtree(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("✅ All vector stores reset successfully")
