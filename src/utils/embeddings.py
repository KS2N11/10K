"""
Embedding utilities for creating and managing vector stores.
"""
from typing import List, Dict, Optional, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from ..utils.logging import setup_logger

logger = setup_logger(__name__)


class EmbeddingClient:
    """Client for creating and querying embeddings."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-large",
        persist_directory: Optional[Path] = None
    ):
        """
        Initialize embedding client.
        
        Args:
            api_key: OpenAI API key
            model_name: Name of the embedding model
            persist_directory: Directory for vector store persistence
        """
        self.api_key = api_key
        self.model_name = model_name
        self.persist_directory = persist_directory
        
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            model=model_name
        )
        
        logger.info(f"Initialized embedding client with model: {model_name}")
    
    def create_vector_store(
        self,
        chunks: List[Dict[str, Any]],
        collection_name: str = "filings"
    ) -> Chroma:
        """
        Create a vector store from text chunks.
        
        Args:
            chunks: List of chunk dicts with 'text' and 'metadata'
            collection_name: Name for the collection
        
        Returns:
            Chroma vector store instance
        """
        if not chunks:
            raise ValueError("No chunks provided for vector store creation")
        
        # Extract texts and metadata
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        logger.info(f"Creating vector store with {len(texts)} chunks")
        
        # Create Chroma vector store
        if self.persist_directory:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            vector_store = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                collection_name=collection_name,
                persist_directory=str(self.persist_directory)
            )
            
            logger.info(f"Vector store persisted to {self.persist_directory}")
        else:
            vector_store = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                collection_name=collection_name
            )
        
        logger.info(f"Vector store created with {len(texts)} documents")
        return vector_store
    
    def load_vector_store(
        self,
        collection_name: str = "filings"
    ) -> Chroma:
        """
        Load an existing vector store.
        
        Args:
            collection_name: Name of the collection to load
        
        Returns:
            Chroma vector store instance
        """
        if not self.persist_directory or not self.persist_directory.exists():
            raise ValueError(f"Vector store not found at {self.persist_directory}")
        
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory)
        )
        
        logger.info(f"Loaded vector store from {self.persist_directory}")
        return vector_store
    
    def query(
        self,
        vector_store: Chroma,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store.
        
        Args:
            vector_store: Chroma vector store instance
            query: Query string
            top_k: Number of results to return
        
        Returns:
            List of results with content and metadata
        """
        results = vector_store.similarity_search_with_score(query, k=top_k)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        
        logger.debug(f"Query returned {len(formatted_results)} results")
        return formatted_results
    
    def add_documents(
        self,
        vector_store: Chroma,
        chunks: List[Dict[str, Any]]
    ) -> None:
        """
        Add new documents to existing vector store.
        
        Args:
            vector_store: Chroma vector store instance
            chunks: List of chunk dicts to add
        """
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"Added {len(texts)} documents to vector store")


def create_catalog_embeddings(
    products: List[Dict[str, Any]],
    api_key: str,
    model_name: str,
    persist_directory: Path
) -> Chroma:
    """
    Create embeddings for product catalog.
    
    Args:
        products: List of product dicts
        api_key: OpenAI API key
        model_name: Embedding model name
        persist_directory: Where to persist the catalog
    
    Returns:
        Chroma vector store with catalog embeddings
    """
    client = EmbeddingClient(api_key, model_name, persist_directory)
    
    # Create chunks from products
    chunks = []
    for product in products:
        # Create a rich text representation
        text_parts = [
            f"Product: {product.get('title', 'Unknown')}",
            f"Summary: {product.get('summary', '')}",
            f"Capabilities: {', '.join(product.get('capabilities', []))}",
        ]
        
        if product.get('proof_points'):
            text_parts.append(f"Proof Points: {', '.join(product['proof_points'])}")
        
        text = "\n".join(text_parts)
        
        chunks.append({
            "text": text,
            "metadata": {
                "product_id": product.get("product_id", ""),
                "title": product.get("title", ""),
                "type": "product_catalog"
            }
        })
    
    vector_store = client.create_vector_store(chunks, collection_name="catalog")
    logger.info(f"Created catalog embeddings for {len(products)} products")
    
    return vector_store
