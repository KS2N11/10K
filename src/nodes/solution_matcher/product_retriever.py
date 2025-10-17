"""
Product Retriever node - retrieves candidate products from catalog.
"""
from typing import Dict, Any, List
from pathlib import Path
import json
import chromadb
from chromadb.config import Settings

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


async def product_retriever_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve candidate products from catalog based on identified pains.
    
    Args:
        state: Graph state with pains and embedder
    
    Returns:
        Updated state with candidate_products
    """
    pains = state.get("pains", [])
    config = state.get("config", {})
    embedder = state.get("embedder")
    
    # Create embedder from config if not in state (for hashability)
    if not embedder:
        from ...utils.multi_embeddings import MultiProviderEmbeddings
        embedder = MultiProviderEmbeddings(config=config)
    
    logger.info(f"Retrieving products for {len(pains)} pain points")
    
    try:
        # Load product catalog
        catalog_path = Path("src/knowledge/products.json")
        if not catalog_path.exists():
            logger.warning("Product catalog not found, using empty catalog")
            products = []
        else:
            with open(catalog_path, "r") as f:
                products = json.load(f)
        
        logger.info(f"Loaded {len(products)} products from catalog")
        
        # If we have pains, use vector search to find relevant products
        if pains and products and embedder:
            catalog_store_dir = Path(config.get("catalog_store_dir", "src/stores/catalog"))
            catalog_store_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize Chroma client
            client = chromadb.PersistentClient(
                path=str(catalog_store_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            
            # Check if catalog collection exists
            try:
                catalog_collection = client.get_collection("catalog")
                logger.info("Using existing catalog embeddings")
            except:
                logger.info("Creating catalog embeddings...")
                
                # Create catalog embeddings
                catalog_texts = []
                catalog_metadatas = []
                catalog_ids = []
                
                for product in products:
                    # Combine product info for embedding
                    text = f"{product.get('name', '')} - {product.get('description', '')} - Solves: {', '.join(product.get('solves', []))}"
                    catalog_texts.append(text)
                    catalog_metadatas.append({
                        "product_id": product.get("product_id", ""),
                        "name": product.get("name", ""),
                    })
                    catalog_ids.append(product.get("product_id", f"product_{len(catalog_ids)}"))
                
                # Embed catalog
                catalog_embeddings = await embedder.embed_documents(catalog_texts)
                
                # Create collection
                catalog_collection = client.create_collection(
                    name="catalog",
                    metadata={"hnsw:space": "cosine"},
                )
                
                catalog_collection.add(
                    documents=catalog_texts,
                    embeddings=catalog_embeddings,
                    metadatas=catalog_metadatas,
                    ids=catalog_ids,
                )
                
                logger.info(f"✅ Created catalog with {len(products)} products")
            
            # Query catalog for each pain
            top_k = config.get("top_k_products", 6)
            relevant_product_ids = set()
            
            for pain in pains:
                query = f"{pain.get('theme', '')} {pain.get('rationale', '')}"
                
                # Embed query
                query_embedding = await embedder.embed_query(query)
                
                # Search
                results = catalog_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, len(products))
                )
                
                # Extract product IDs
                metadatas = results.get("metadatas", [[]])[0]
                for metadata in metadatas:
                    product_id = metadata.get("product_id")
                    if product_id:
                        relevant_product_ids.add(product_id)
            
            # Filter products to relevant ones
            candidate_products = [
                p for p in products
                if p.get("product_id") in relevant_product_ids
            ]
            
            # If no matches, return all products
            if not candidate_products:
                candidate_products = products[:top_k]
        
        else:
            # No pains identified, return top products
            candidate_products = products[:config.get("top_k_products", 6)]
        
        # Log trace event
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ProductRetriever",
            "retrieve_products",
            f"Retrieved {len(candidate_products)} candidate products",
            {"products": [p.get("product_id") for p in candidate_products]}
        ).to_dict())
        
        return {
            **state,
            "candidate_products": candidate_products,
            "trace": trace
        }
    
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ProductRetriever",
            "error",
            f"Failed to retrieve products: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "candidate_products": [],
            "trace": trace
        }
