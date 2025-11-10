"""
Multi-provider embedding manager with fallback support.
"""
import asyncio
from typing import List, Optional, Dict, Any, Literal
import os

# Import only what we need, lazily to avoid blocking
from langchain_core.embeddings import Embeddings

from ..utils.logging import setup_logger

logger = setup_logger(__name__)

ProviderType = Literal["openai", "sentence-transformers", "cohere", "azure"]


class MultiProviderEmbeddings:
    """Embedding manager with multiple providers and fallback support."""
    
    def __init__(
        self,
        primary_provider: ProviderType = "sentence-transformers",
        fallback_providers: Optional[List[ProviderType]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize multi-provider embeddings.
        
        Args:
            primary_provider: Primary embedding provider to use
            fallback_providers: List of fallback providers if primary fails
            config: Configuration dict for each provider
        """
        self.primary_provider = primary_provider
        self.fallback_providers = fallback_providers or []
        self.config = config or {}
        
        self._embedders: Dict[str, Embeddings] = {}
        # Don't initialize embedders here - do it lazily on first use
    
    def _ensure_embedder(self, provider: str) -> Embeddings:
        """Ensure an embedder is initialized (lazy initialization)."""
        if provider not in self._embedders:
            try:
                if provider == "sentence-transformers":
                    self._embedders[provider] = self._init_sentence_transformers()
                elif provider == "openai":
                    self._embedders[provider] = self._init_openai()
                elif provider == "azure":
                    self._embedders[provider] = self._init_azure()
                elif provider == "cohere":
                    self._embedders[provider] = self._init_cohere()
                
                logger.info(f"✅ Initialized {provider} embeddings")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize {provider}: {e}")
                raise
        
        return self._embedders[provider]
    
    def _init_sentence_transformers(self) -> Embeddings:
        """Initialize local Sentence Transformers."""
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        st_config = self.config.get("sentence_transformers", {})
        model_name = st_config.get("model_name", "all-mpnet-base-v2")
        device = st_config.get("device", "cpu")
        
        logger.info(f"Loading Sentence Transformers model: {model_name} on {device}")
        
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
    
    def _init_openai(self) -> Embeddings:
        """Initialize OpenAI embeddings."""
        from langchain_openai import OpenAIEmbeddings
        
        openai_config = self.config.get("openai", {})
        model_name = openai_config.get("model_name", "text-embedding-3-large")
        
        # Check if API key is available
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        return OpenAIEmbeddings(
            model=model_name,
            # API key loaded from environment
        )
    
    def _init_azure(self) -> Embeddings:
        """Initialize Azure OpenAI embeddings."""
        from langchain_openai import AzureOpenAIEmbeddings
        
        azure_config = self.config.get("azure", {})
        
        # Get Azure configuration from environment
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = azure_config.get("deployment") or os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        api_version = azure_config.get("api_version") or os.getenv("AZURE_EMBEDDING_API_VERSION", "2024-02-01")
        
        if not api_key or not endpoint:
            raise ValueError("AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT required for Azure embeddings")
        
        logger.info(f"🔵 Initializing Azure OpenAI Embeddings: {deployment}")
        
        return AzureOpenAIEmbeddings(
            azure_deployment=deployment,
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key,
        )
    
    def _init_cohere(self) -> Embeddings:
        """Initialize Cohere embeddings."""
        from langchain_community.embeddings import CohereEmbeddings
        
        cohere_config = self.config.get("cohere", {})
        model_name = cohere_config.get("model_name", "embed-english-v3.0")
        
        # Check if API key is available
        if not os.getenv("COHERE_API_KEY"):
            raise ValueError("COHERE_API_KEY not found in environment")
        
        return CohereEmbeddings(
            model=model_name,
            # API key loaded from environment
        )
    
    async def embed_documents(
        self,
        texts: List[str],
        provider: Optional[ProviderType] = None,
    ) -> List[List[float]]:
        """
        Embed documents with fallback support.
        
        Args:
            texts: List of text documents to embed
            provider: Specific provider to use (defaults to primary)
        
        Returns:
            List of embedding vectors
        """
        provider = provider or self.primary_provider
        providers_to_try = [provider] + [p for p in self.fallback_providers if p != provider]
        
        for prov in providers_to_try:
            try:
                # Lazy initialization
                embedder = self._ensure_embedder(prov)
                
                logger.info(f"🔄 Embedding {len(texts)} documents with {prov}")
                
                # Run in executor for CPU-bound tasks (Sentence Transformers)
                if prov == "sentence-transformers":
                    loop = asyncio.get_event_loop()
                    embeddings = await loop.run_in_executor(
                        None, embedder.embed_documents, texts
                    )
                else:
                    # Azure, OpenAI, Cohere all support async
                    embeddings = await embedder.aembed_documents(texts)
                
                logger.info(f"✅ Successfully embedded with {prov}")
                return embeddings
                
            except Exception as e:
                logger.warning(f"⚠️  {prov} embedding failed: {e}")
                continue
        
        raise RuntimeError("All embedding providers failed")
    
    async def embed_query(
        self,
        text: str,
        provider: Optional[ProviderType] = None,
    ) -> List[float]:
        """
        Embed query with fallback support.
        
        Args:
            text: Query text to embed
            provider: Specific provider to use (defaults to primary)
        
        Returns:
            Embedding vector
        """
        provider = provider or self.primary_provider
        providers_to_try = [provider] + [p for p in self.fallback_providers if p != provider]
        
        for prov in providers_to_try:
            try:
                # Lazy initialization
                embedder = self._ensure_embedder(prov)
                
                if prov == "sentence-transformers":
                    loop = asyncio.get_event_loop()
                    embedding = await loop.run_in_executor(
                        None, embedder.embed_query, text
                    )
                else:
                    embedding = await embedder.aembed_query(text)
                
                return embedding
                
            except Exception as e:
                logger.warning(f"⚠️  {prov} query embedding failed: {e}")
                continue
        
        raise RuntimeError("All embedding providers failed")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        # Return dimension based on primary provider
        if self.primary_provider == "sentence-transformers":
            model_name = self.config.get("sentence_transformers", {}).get("model_name", "all-mpnet-base-v2")
            if "mpnet" in model_name:
                return 768
            elif "MiniLM" in model_name:
                return 384
            return 768  # default
        elif self.primary_provider == "azure":
            # Azure uses same models as OpenAI
            deployment = self.config.get("azure", {}).get("deployment", "text-embedding-3-large")
            if "large" in deployment:
                return 3072
            elif "small" in deployment:
                return 1536
            return 3072  # default for text-embedding-3-large
        elif self.primary_provider == "openai":
            model_name = self.config.get("openai", {}).get("model_name", "text-embedding-3-large")
            if "large" in model_name:
                return 3072
            elif "small" in model_name:
                return 1536
            return 1536  # default
        elif self.primary_provider == "cohere":
            return 1024  # Cohere embed-english-v3.0
        return 768  # default
