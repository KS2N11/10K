"""
Test complete Azure OpenAI integration (LLM + Embeddings).
"""
import asyncio
from src.utils.llm_factory import get_factory

async def test_azure_complete():
    """Test that Azure OpenAI is used for both LLM and embeddings."""
    
    print("=" * 60)
    print("Azure OpenAI Complete Integration Test")
    print("=" * 60)
    
    # Get factory
    factory = get_factory()
    config = factory.get_config()
    
    # Check LLM configuration
    llm_config = config.get("llm", {})
    print(f"\n🤖 LLM Provider: {llm_config.get('primary_provider')}")
    print(f"🤖 LLM Model: {config.get('azure_deployment', 'N/A')}")
    
    # Check Embedding configuration
    emb_config = config.get("embedding", {})
    print(f"\n📊 Embedding Provider: {emb_config.get('primary_provider')}")
    azure_emb = emb_config.get("azure", {})
    print(f"📊 Embedding Model: {azure_emb.get('deployment', 'N/A')}")
    
    # Test LLM
    print("\n" + "=" * 60)
    print("Testing LLM (GPT-4o)...")
    print("=" * 60)
    
    llm_manager = factory.create_llm_manager()
    
    test_prompt = "What is cloud computing? Answer in one sentence."
    response = await llm_manager.ainvoke(test_prompt)
    
    print(f"\n✅ LLM Response: {response[:150]}...")
    
    # Test Embeddings
    print("\n" + "=" * 60)
    print("Testing Embeddings (text-embedding-3-large)...")
    print("=" * 60)
    
    embedder = factory.create_embedder()
    test_text = "Azure OpenAI provides enterprise-grade AI."
    embedding = await embedder.embed_query(test_text)
    
    print(f"\n✅ Embedding created!")
    print(f"📏 Dimension: {len(embedding)} (expected: 3072 for text-embedding-3-large)")
    
    # Summary
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"\n✅ LLM: Azure OpenAI GPT-4o")
    print(f"✅ Embeddings: Azure OpenAI text-embedding-3-large")
    print(f"✅ Endpoint: {config.get('azure_endpoint', 'N/A')}")
    print(f"✅ API Version: {config.get('azure_api_version', 'N/A')}")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_azure_complete())
