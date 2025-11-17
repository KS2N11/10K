"""
Central LLM and Embedding Factory.

This module provides a single point of configuration for all LLM and embedding
providers. Instead of having provider-specific logic scattered across the codebase,
all provider initialization and configuration is centralized here.

Usage:
    from src.utils.llm_factory import LLMFactory
    
    factory = LLMFactory()
    llm_manager = factory.create_llm_manager()
    embedder = factory.create_embedder()
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

from .multi_llm import MultiProviderLLM
from .multi_embeddings import MultiProviderEmbeddings
from .logging import setup_logger

logger = setup_logger(__name__)


class LLMFactory:
    """
    Central factory for creating LLM and embedding instances.
    
    This factory handles:
    - Loading configuration from .env and settings.yaml
    - Provider selection based on explicit configuration (not auto-detection)
    - Consistent initialization across the application
    - Single source of truth for LLM/embedding configuration
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the LLM factory.
        
        Args:
            config_path: Path to settings.yaml (defaults to src/configs/settings.yaml)
        """
        # Load environment variables first
        load_dotenv()
        
        # Load configuration
        self.config_path = config_path or Path("src/configs/settings.yaml")
        self.config = self._load_config()
        
        logger.info("🏭 LLM Factory initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from settings.yaml and merge with environment variables.
        
        Priority order:
        1. Environment variables (.env)
        2. settings.yaml
        3. Built-in defaults
        """
        # Start with defaults
        config = self._get_default_config()
        
        # Override with settings.yaml if it exists
        if self.config_path.exists():
            logger.info(f"📄 Loading config from {self.config_path}")
            with open(self.config_path, "r") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    config.update(yaml_config)
        else:
            logger.warning(f"⚠️  Config file not found at {self.config_path}, using defaults")
        
        # Override with environment variables (highest priority)
        config = self._merge_env_variables(config)
        
        # Validate required configuration
        self._validate_config(config)
        
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "vector_store_dir": "src/stores/vector",
            "catalog_store_dir": "src/stores/catalog",
            "your_company_name": "Atidan",
            "your_company_tagline": "a global technology services and consulting firm specializing in AI, cloud, and digital transformation",
            "embedding": {
                "primary_provider": "azure",
                "fallback_providers": ["sentence-transformers"],
                "sentence_transformers": {
                    "model_name": "all-mpnet-base-v2",
                    "device": "cpu"
                },
                "azure": {
                    "deployment": "text-embedding-3-large",
                    "api_version": "2024-02-01"
                },
                "openai": {
                    "model_name": "text-embedding-3-large"
                },
                "cohere": {
                    "model_name": "embed-english-v3.0",
                    "input_type": "search_document"
                }
            },
            "llm": {
                "primary_provider": "groq",
                "fallback_providers": [],
                "groq": {
                    "model_name": "moonshotai/kimi-k2-instruct-0905",
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                "openai": {
                    "model_name": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                "azure": {
                    "model_name": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            },
            "rate_limits": {
                "groq": {"rpm": 30, "tpm": 7000},
                "openai": {"rpm": 3500, "tpm": 90000},
                "azure": {"rpm": 3500, "tpm": 90000}
            },
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "top_k_chunks": 10,
            "top_k_products": 6,
            "max_iterations": 3,
            "min_confidence": 0.6,
            "log_level": "INFO"
        }
    
    def _merge_env_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge environment variables into config.
        
        Environment variables take highest priority.
        """
        # API Keys
        if os.getenv("OPENAI_API_KEY"):
            config["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        
        if os.getenv("GROQ_API_KEY"):
            config["groq_api_key"] = os.getenv("GROQ_API_KEY")
        
        if os.getenv("COHERE_API_KEY"):
            config["cohere_api_key"] = os.getenv("COHERE_API_KEY")
        
        # Azure OpenAI
        if os.getenv("AZURE_OPENAI_API_KEY"):
            config["azure_api_key"] = os.getenv("AZURE_OPENAI_API_KEY")
        
        if os.getenv("AZURE_OPENAI_ENDPOINT"):
            config["azure_endpoint"] = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if os.getenv("AZURE_OPENAI_DEPLOYMENT"):
            config["azure_deployment"] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        if os.getenv("AZURE_OPENAI_API_VERSION"):
            config["azure_api_version"] = os.getenv("AZURE_OPENAI_API_VERSION")
        
        # SEC Configuration
        if os.getenv("SEC_USER_AGENT"):
            config["sec_user_agent"] = os.getenv("SEC_USER_AGENT")
        
        # Provider Selection
        if os.getenv("PRIMARY_EMBEDDING_PROVIDER"):
            logger.info(f"🔧 Setting primary embedding provider from env: {os.getenv('PRIMARY_EMBEDDING_PROVIDER')}")
            config["embedding"]["primary_provider"] = os.getenv("PRIMARY_EMBEDDING_PROVIDER")
        else:
            logger.info(f"⚠️ PRIMARY_EMBEDDING_PROVIDER not set, using config default: {config['embedding']['primary_provider']}")
        
        if os.getenv("PRIMARY_LLM_PROVIDER"):
            config["llm"]["primary_provider"] = os.getenv("PRIMARY_LLM_PROVIDER")
        
        # Azure Embedding Configuration
        if os.getenv("AZURE_EMBEDDING_DEPLOYMENT"):
            if "azure" not in config["embedding"]:
                config["embedding"]["azure"] = {}
            config["embedding"]["azure"]["deployment"] = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
        
        if os.getenv("AZURE_EMBEDDING_API_VERSION"):
            if "azure" not in config["embedding"]:
                config["embedding"]["azure"] = {}
            config["embedding"]["azure"]["api_version"] = os.getenv("AZURE_EMBEDDING_API_VERSION")
        
        # Storage Paths
        if os.getenv("VECTOR_STORE_DIR"):
            config["vector_store_dir"] = os.getenv("VECTOR_STORE_DIR")
        
        if os.getenv("CATALOG_STORE_DIR"):
            config["catalog_store_dir"] = os.getenv("CATALOG_STORE_DIR")
        
        # Company Information
        if os.getenv("YOUR_COMPANY_NAME"):
            config["your_company_name"] = os.getenv("YOUR_COMPANY_NAME")
        
        if os.getenv("YOUR_COMPANY_TAGLINE"):
            config["your_company_tagline"] = os.getenv("YOUR_COMPANY_TAGLINE")
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration has required fields.
        
        Raises:
            ValueError: If required configuration is missing
        """
        # Validate primary LLM provider has API key
        llm_provider = config.get("llm", {}).get("primary_provider")
        
        if llm_provider == "openai" and not config.get("openai_api_key"):
            logger.warning("⚠️  PRIMARY_LLM_PROVIDER set to 'openai' but OPENAI_API_KEY not found")
        
        if llm_provider == "groq" and not config.get("groq_api_key"):
            logger.warning("⚠️  PRIMARY_LLM_PROVIDER set to 'groq' but GROQ_API_KEY not found")
        
        if llm_provider == "azure":
            if not config.get("azure_api_key") or not config.get("azure_endpoint"):
                logger.warning("⚠️  PRIMARY_LLM_PROVIDER set to 'azure' but Azure credentials not found")
        
        # Validate embedding provider
        emb_provider = config.get("embedding", {}).get("primary_provider")
        
        if emb_provider == "azure":
            if not config.get("azure_api_key") or not config.get("azure_endpoint"):
                logger.warning("⚠️  PRIMARY_EMBEDDING_PROVIDER set to 'azure' but Azure credentials not found")
        
        if emb_provider == "openai" and not config.get("openai_api_key"):
            logger.warning("⚠️  PRIMARY_EMBEDDING_PROVIDER set to 'openai' but OPENAI_API_KEY not found")
        
        if emb_provider == "cohere" and not config.get("cohere_api_key"):
            logger.warning("⚠️  PRIMARY_EMBEDDING_PROVIDER set to 'cohere' but COHERE_API_KEY not found")
        
        # Validate SEC user agent
        if not config.get("sec_user_agent"):
            logger.warning("⚠️  SEC_USER_AGENT not configured - SEC API calls will fail")
    
    def create_llm_manager(self) -> MultiProviderLLM:
        """
        Create a multi-provider LLM manager.
        
        Returns:
            MultiProviderLLM instance configured based on settings
        """
        llm_config = self.config.get("llm", {})
        
        logger.info(f"🤖 Creating LLM manager with primary provider: {llm_config.get('primary_provider')}")
        
        return MultiProviderLLM(
            primary_provider=llm_config.get("primary_provider", "groq"),
            fallback_providers=llm_config.get("fallback_providers", []),
            config=self.config,
            rate_limits=self.config.get("rate_limits", {}),
        )
    
    def create_embedder(self) -> MultiProviderEmbeddings:
        """
        Create a multi-provider embeddings manager.
        
        Returns:
            MultiProviderEmbeddings instance configured based on settings
        """
        emb_config = self.config.get("embedding", {})
        
        logger.info(f"📊 Creating embeddings manager with primary provider: {emb_config.get('primary_provider')}")
        
        return MultiProviderEmbeddings(
            primary_provider=emb_config.get("primary_provider", "azure"),
            fallback_providers=emb_config.get("fallback_providers", ["sentence-transformers"]),
            config=emb_config,
        )
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Full configuration dictionary
        """
        return self.config


# Global singleton instance
_factory: Optional[LLMFactory] = None


def get_factory(config_path: Optional[Path] = None) -> LLMFactory:
    """
    Get or create the global LLM factory singleton.
    
    Args:
        config_path: Optional path to settings.yaml
    
    Returns:
        LLMFactory instance
    """
    global _factory
    
    if _factory is None:
        _factory = LLMFactory(config_path)
    
    return _factory


def reset_factory() -> None:
    """Reset the global factory instance (useful for testing)."""
    global _factory
    _factory = None
