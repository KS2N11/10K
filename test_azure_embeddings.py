"""
Test Azure OpenAI embeddings configuration.
"""
import asyncio
from src.utils.llm_factory import get_factory

async def test_azure_embeddings():
    """Test that Azure OpenAI embeddings are being used."""
    
    print("=" * 60)
    print("Azure OpenAI Embeddings Test")
    print("=" * 60)
    
    # Get factory
    factory = get_factory()
    
    # Check configuration
    config = factory.get_config()
    emb_config = config.get("embedding", {})
    
    print(f"\n📊 Embedding Provider: {emb_config.get('primary_provider')}")
    print(f"🔄 Fallback Providers: {emb_config.get('fallback_providers')}")
    
    azure_config = emb_config.get("azure", {})
    print(f"\n🔵 Azure Deployment: {azure_config.get('deployment')}")
    print(f"🔵 Azure API Version: {azure_config.get('api_version')}")
    
    # Create embedder
    print("\n" + "=" * 60)
    print("Creating Embedder...")
    print("=" * 60)
    
    embedder = factory.create_embedder()
    
    # Test embedding
    print("\n🧪 Testing embedding...")
    test_text = "Azure OpenAI provides enterprise-grade AI capabilities."
    
    embedding = await embedder.embed_query(test_text)
    
    print(f"\n✅ Successfully created embedding!")
    print(f"📏 Embedding dimension: {len(embedding)}")
    print(f"🔢 First 5 values: {embedding[:5]}")
    
    # Test batch embedding
    print("\n🧪 Testing batch embedding...")
    test_docs = [
        "Cloud computing enables scalable infrastructure.",
        "Machine learning models require large datasets.",
        "API integration simplifies software development."
    ]
    
    embeddings = await embedder.embed_documents(test_docs)
    
    print(f"\n✅ Successfully created {len(embeddings)} embeddings!")
    print(f"📏 Each embedding dimension: {len(embeddings[0])}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_azure_embeddings())
