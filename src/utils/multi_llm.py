"""
Multi-provider LLM manager with fallback and rate limiting.
"""
import asyncio
from typing import Optional, Dict, Any, List, Literal, Union
import time
import os

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

from ..utils.logging import setup_logger

logger = setup_logger(__name__)

ProviderType = Literal["openai", "groq", "azure"]


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, rpm: int, tpm: int):
        """
        Initialize rate limiter.
        
        Args:
            rpm: Requests per minute
            tpm: Tokens per minute
        """
        self.rpm = rpm
        self.tpm = tpm
        self.request_times: List[float] = []
        self.token_counts: List[tuple[float, int]] = []
    
    def _clean_old_entries(self):
        """Remove entries older than 1 minute."""
        cutoff = time.time() - 60
        self.request_times = [t for t in self.request_times if t > cutoff]
        self.token_counts = [(t, c) for t, c in self.token_counts if t > cutoff]
    
    async def wait_if_needed(self, estimated_tokens: int = 1000):
        """Wait if rate limits would be exceeded."""
        self._clean_old_entries()
        
        # Check request rate
        if len(self.request_times) >= self.rpm:
            wait_time = 60 - (time.time() - self.request_times[0])
            if wait_time > 0:
                logger.info(f"⏳ Rate limit: waiting {wait_time:.1f}s (request limit)")
                await asyncio.sleep(wait_time)
                self._clean_old_entries()
        
        # Check token rate
        total_tokens = sum(c for _, c in self.token_counts)
        if total_tokens + estimated_tokens > self.tpm:
            wait_time = 60 - (time.time() - self.token_counts[0][0])
            if wait_time > 0:
                logger.info(f"⏳ Token limit: waiting {wait_time:.1f}s (token limit)")
                await asyncio.sleep(wait_time)
                self._clean_old_entries()
        
        # Record this request
        self.request_times.append(time.time())
        self.token_counts.append((time.time(), estimated_tokens))


class MultiProviderLLM:
    """LLM manager with multiple providers and fallback support."""
    
    def __init__(
        self,
        primary_provider: ProviderType = "groq",
        fallback_providers: Optional[List[ProviderType]] = None,
        config: Optional[Dict[str, Any]] = None,
        rate_limits: Optional[Dict[str, Dict[str, int]]] = None,
    ):
        """
        Initialize multi-provider LLM.
        
        Args:
            primary_provider: Primary LLM provider to use
            fallback_providers: List of fallback providers if primary fails
            config: Configuration dict for each provider
            rate_limits: Rate limit config for each provider
        """
        self.primary_provider = primary_provider
        self.fallback_providers = fallback_providers or []
        self.config = config or {}
        self.rate_limits = rate_limits or {}
        
        self._llms: Dict[str, BaseChatModel] = {}
        self._limiters: Dict[str, RateLimiter] = {}
        self._initialize_llms()
    
    def _initialize_llms(self):
        """Initialize all configured LLM providers."""
        # Initialize providers based on explicit configuration
        # No auto-detection - use the primary_provider and fallback_providers as configured
        providers_to_init = [self.primary_provider] + self.fallback_providers
        
        for provider in providers_to_init:
            try:
                if provider == "groq":
                    groq_key = self.config.get("groq_api_key") or os.getenv("GROQ_API_KEY")
                    if not groq_key:
                        logger.warning(f"⚠️  Skipping {provider} - API key not found")
                        continue
                    self._llms[provider] = self._init_groq()
                elif provider == "openai":
                    openai_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
                    if not openai_key:
                        logger.warning(f"⚠️  Skipping {provider} - API key not found")
                        continue
                    self._llms[provider] = self._init_openai()
                elif provider == "azure":
                    azure_key = self.config.get("azure_api_key") or os.getenv("AZURE_OPENAI_API_KEY")
                    azure_endpoint = self.config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
                    if not azure_key or not azure_endpoint:
                        logger.warning(f"⚠️  Skipping {provider} - API key or endpoint not found")
                        continue
                    self._llms[provider] = self._init_azure()
                
                # Initialize rate limiter
                limits = self.rate_limits.get(provider, {"rpm": 60, "tpm": 10000})
                self._limiters[provider] = RateLimiter(
                    rpm=limits["rpm"],
                    tpm=limits["tpm"],
                )
                
                logger.info(f"✅ Initialized {provider} LLM")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize {provider}: {e}")
    
    def _init_groq(self) -> ChatGroq:
        """Initialize Groq LLM."""
        groq_config = self.config.get("groq", {})
        
        # Check if API key is available (from config or environment)
        api_key = self.config.get("groq_api_key") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in config or environment")
        
        return ChatGroq(
            api_key=api_key,
            model=groq_config.get("model_name", "moonshotai/kimi-k2-instruct-0905"),
            temperature=groq_config.get("temperature", 0.7),
            max_tokens=groq_config.get("max_tokens", 4096),
        )
    
    def _init_openai(self) -> ChatOpenAI:
        """Initialize OpenAI LLM."""
        openai_config = self.config.get("openai", {})
        
        # Check if API key is available (from config or environment)
        api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in config or environment")
        
        return ChatOpenAI(
            api_key=api_key,
            model=openai_config.get("model_name", "gpt-4o-mini"),
            temperature=openai_config.get("temperature", 0.7),
            max_tokens=openai_config.get("max_tokens", 4096),
        )
    
    def _init_azure(self) -> AzureChatOpenAI:
        """Initialize Azure OpenAI LLM."""
        azure_config = self.config.get("azure", {})
        
        # Check if API key and endpoint are available
        api_key = self.config.get("azure_api_key") or os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = self.config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not api_key or not endpoint:
            raise ValueError("AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT required")
        
        # Azure deployment name (defaults to model name)
        deployment_name = (
            self.config.get("azure_deployment") or 
            os.getenv("AZURE_OPENAI_DEPLOYMENT") or 
            azure_config.get("model_name", "gpt-4o-mini")
        )
        
        # API version
        api_version = (
            self.config.get("azure_api_version") or 
            os.getenv("AZURE_OPENAI_API_VERSION") or 
            "2024-12-01-preview"
        )
        return AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            azure_deployment=deployment_name,
            temperature=azure_config.get("temperature", 0.7)
        )
       
    
    async def ainvoke(
        self,
        messages: Union[List[BaseMessage], str],
        provider: Optional[ProviderType] = None,
        **kwargs,
    ) -> str:
        """
        Invoke LLM with fallback support.
        
        Args:
            messages: List of messages or single prompt string
            provider: Specific provider to use (defaults to primary)
            **kwargs: Additional arguments to pass to LLM
        
        Returns:
            Response text from LLM
        """
        # Convert string to messages if needed
        if isinstance(messages, str):
            messages = [HumanMessage(content=messages)]
        
        provider = provider or self.primary_provider
        providers_to_try = [provider] + [p for p in self.fallback_providers if p != provider]
        
        for prov in providers_to_try:
            llm = self._llms.get(prov)
            limiter = self._limiters.get(prov)
            
            if not llm or not limiter:
                continue
            
            try:
                # Wait if needed for rate limits
                await limiter.wait_if_needed()
                
                # Log more details about the call
                logger.info(f"🔄 Calling {prov} LLM (primary={self.primary_provider}, fallbacks={self.fallback_providers})")
                if isinstance(messages[0], HumanMessage):
                    logger.info(f"Query: {messages[0].content[:100]}...")
                
                # Call LLM
                response = await llm.ainvoke(messages, **kwargs)
                
                logger.info(f"✅ Successfully got response from {prov} (request complete)")
                return response.content
                
            except Exception as e:
                import traceback
                logger.warning(f"⚠️  {prov} LLM failed: {e}")
                logger.warning(f"⚠️  {prov} LLM error details:\n{traceback.format_exc()}")
                logger.warning(f"⚠️  Falling back from {prov} to next provider (if available)")
                continue
        
        raise RuntimeError("All LLM providers failed")
    
    async def astream(
        self,
        messages: Union[List[BaseMessage], str],
        provider: Optional[ProviderType] = None,
        **kwargs,
    ):
        """
        Stream LLM response with fallback support.
        
        Args:
            messages: List of messages or single prompt string
            provider: Specific provider to use (defaults to primary)
            **kwargs: Additional arguments to pass to LLM
        
        Yields:
            Response chunks from LLM
        """
        # Convert string to messages if needed
        if isinstance(messages, str):
            messages = [HumanMessage(content=messages)]
        
        provider = provider or self.primary_provider
        providers_to_try = [provider] + [p for p in self.fallback_providers if p != provider]
        
        for prov in providers_to_try:
            llm = self._llms.get(prov)
            limiter = self._limiters.get(prov)
            
            if not llm or not limiter:
                continue
            
            try:
                # Wait if needed for rate limits
                await limiter.wait_if_needed()
                
                logger.info(f"🔄 Streaming from {prov} LLM")
                
                # Stream response
                async for chunk in llm.astream(messages, **kwargs):
                    yield chunk.content
                
                logger.info(f"✅ Successfully streamed from {prov}")
                return
                
            except Exception as e:
                logger.warning(f"⚠️  {prov} LLM streaming failed: {e}")
                continue
        
        raise RuntimeError("All LLM providers failed")


def create_llm_manager(settings: Dict[str, Any]) -> MultiProviderLLM:
    """Create LLM manager from settings."""
    llm_config = settings.get("llm", {})
    
    return MultiProviderLLM(
        primary_provider=llm_config.get("primary_provider", "groq"),
        fallback_providers=llm_config.get("fallback_providers", []),
        config=llm_config,
        rate_limits=settings.get("rate_limits", {}),
    )


def create_embedder(settings: Dict[str, Any]):
    """Create embedding manager from settings."""
    from .multi_embeddings import MultiProviderEmbeddings
    
    emb_config = settings.get("embedding", {})
    
    return MultiProviderEmbeddings(
        primary_provider=emb_config.get("primary_provider", "sentence-transformers"),
        fallback_providers=emb_config.get("fallback_providers", []),
        config=emb_config,
    )
