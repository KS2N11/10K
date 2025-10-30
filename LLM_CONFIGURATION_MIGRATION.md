# LLM Configuration Migration Guide

## Summary of Changes

**Previous Behavior**: The system would automatically detect which API keys were present and switch providers accordingly (Azure OpenAI > OpenAI > Groq).

**New Behavior**: The system uses **explicit configuration** through a centralized LLM factory. You must specify which provider to use via `PRIMARY_LLM_PROVIDER`.

---

## What Changed?

### 1. **Centralized Configuration** (`src/utils/llm_factory.py`)

All LLM and embedding initialization now goes through a single factory class:
- ✅ Single source of truth for provider configuration
- ✅ Consistent initialization across the application
- ✅ Easier testing and debugging
- ✅ No more auto-detection surprises

### 2. **Explicit Provider Selection**

Instead of auto-detecting based on API keys, you now explicitly configure:

```bash
# .env file
PRIMARY_LLM_PROVIDER=groq  # Options: groq, openai, azure
PRIMARY_EMBEDDING_PROVIDER=sentence-transformers
```

### 3. **Removed Auto-Detection Logic**

The following auto-detection logic was removed from `multi_llm.py`:
- ❌ No more automatic switching to OpenAI when `OPENAI_API_KEY` is present
- ❌ No more automatic switching to Azure when Azure credentials are present
- ❌ No more priority hierarchy (Azure > OpenAI > Groq)

---

## Migration Steps

### If You Were Using Groq (Default)

**No changes needed!** The default is still Groq. Just make sure your `.env` has:

```bash
GROQ_API_KEY=your-groq-key-here
PRIMARY_LLM_PROVIDER=groq  # This is the default
```

### If You Were Using OpenAI

Previously, the system would auto-detect `OPENAI_API_KEY` and switch to OpenAI. Now you must explicitly configure it:

**Before** (auto-detected):
```bash
GROQ_API_KEY=...
OPENAI_API_KEY=...  # System would switch to OpenAI automatically
```

**After** (explicit):
```bash
GROQ_API_KEY=...
OPENAI_API_KEY=...
PRIMARY_LLM_PROVIDER=openai  # Explicitly use OpenAI
```

### If You Were Using Azure OpenAI

**Before** (auto-detected):
```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
# System would auto-detect and switch to Azure
```

**After** (explicit):
```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview
PRIMARY_LLM_PROVIDER=azure  # Explicitly use Azure
```

---

## Benefits of Centralized Configuration

### Before (Scattered Configuration)

```python
# In routes.py
config["openai_api_key"] = os.getenv("OPENAI_API_KEY")
llm_manager = create_llm_manager(config)

# In multi_llm.py
if azure_key and azure_endpoint:
    logger.info("Switching to Azure OpenAI...")
    self.primary_provider = "azure"
elif openai_key:
    logger.info("Switching to OpenAI...")
    self.primary_provider = "openai"
```

### After (Centralized Factory)

```python
# Anywhere in the application
from src.utils.llm_factory import get_factory

factory = get_factory()
llm_manager = factory.create_llm_manager()
embedder = factory.create_embedder()
config = factory.get_config()
```

**Advantages**:
- ✅ Single point of configuration
- ✅ Predictable behavior
- ✅ Easier to test with specific providers
- ✅ No surprises from auto-detection
- ✅ Clear separation of concerns

---

## Configuration Reference

### Environment Variables (.env)

```bash
# Provider Selection (Required)
PRIMARY_LLM_PROVIDER=groq              # Options: groq, openai, azure
PRIMARY_EMBEDDING_PROVIDER=sentence-transformers  # Options: sentence-transformers, openai, cohere

# API Keys (Provide only what you need)
GROQ_API_KEY=your-groq-key-here
OPENAI_API_KEY=your-openai-key-here    # Optional
COHERE_API_KEY=your-cohere-key-here    # Optional

# Azure OpenAI (if using Azure)
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Required for SEC API
SEC_USER_AGENT=YourApp/1.0 (your@email.com)
```

### Settings File (settings.yaml)

```yaml
# Advanced: Fallback providers
llm:
  primary_provider: "groq"
  fallback_providers: ["openai"]  # Optional fallbacks
  groq:
    model_name: "moonshotai/kimi-k2-instruct-0905"
    temperature: 0.7
    max_tokens: 4096
  openai:
    model_name: "gpt-4o-mini"
    temperature: 0.7
    max_tokens: 4096

embedding:
  primary_provider: "sentence-transformers"
  fallback_providers: []
  sentence_transformers:
    model_name: "all-mpnet-base-v2"
    device: "cpu"
```

---

## Troubleshooting

### Issue: "OPENAI_API_KEY detected - switching to OpenAI" logs are gone

**This is expected!** The system no longer auto-detects and logs provider switches. Check your `PRIMARY_LLM_PROVIDER` setting to see which provider is being used.

### Issue: Getting warnings about missing API keys

Example: `⚠️ PRIMARY_LLM_PROVIDER set to 'openai' but OPENAI_API_KEY not found`

**Solution**: Either add the API key for your configured provider, or change `PRIMARY_LLM_PROVIDER` to a provider you have keys for.

### Issue: Want to test different providers without changing .env

Use `settings.yaml` and create different config files:

```bash
# settings.groq.yaml
llm:
  primary_provider: "groq"

# settings.openai.yaml  
llm:
  primary_provider: "openai"
```

Then specify which config to use when initializing the factory.

---

## Code Examples

### Using the Factory in Your Code

```python
from src.utils.llm_factory import get_factory

# Get the factory (singleton)
factory = get_factory()

# Create LLM manager
llm_manager = factory.create_llm_manager()

# Create embedder
embedder = factory.create_embedder()

# Get full configuration
config = factory.get_config()

# Use the LLM
response = await llm_manager.ainvoke("What is the capital of France?")
```

### Testing with Specific Providers

```python
from src.utils.llm_factory import LLMFactory
from pathlib import Path

# Create factory with custom config
factory = LLMFactory(config_path=Path("test_settings.yaml"))
llm_manager = factory.create_llm_manager()

# Now you know exactly which provider is being used
```

---

## Questions?

If you have questions about the migration or encounter issues, please:
1. Check that `PRIMARY_LLM_PROVIDER` is set correctly in `.env`
2. Verify your API key environment variables are set
3. Review the logs for any warnings about missing keys
4. See `src/utils/llm_factory.py` for the full implementation

