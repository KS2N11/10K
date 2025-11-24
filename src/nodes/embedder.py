"""
Embedder node - processes filing text and creates vector embeddings.
"""
from typing import Dict, Any
from pathlib import Path

from ..utils.text_utils import TextProcessor
from ..utils.logging import setup_logger, log_trace_event
from ..utils.chromadb_utils import create_chromadb_client

logger = setup_logger(__name__)


async def embedder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process 10-K filing: parse, chunk, and embed.
    
    Args:
        state: Graph state with file_path
    
    Returns:
        Updated state with vector_store, chunks count
    """
    file_path = state.get("file_path")
    config = state.get("config", {})
    company = state.get("company", "Unknown")
    embedder = state.get("embedder")
    
    # Create embedder from config if not in state (for hashability)
    if not embedder:
        from ..utils.multi_embeddings import MultiProviderEmbeddings
        emb_config = config.get("embedding", {})
        embedder = MultiProviderEmbeddings(
            primary_provider=emb_config.get("primary_provider", "azure"),
            fallback_providers=emb_config.get("fallback_providers", ["sentence-transformers"]),
            config=emb_config
        )
    
    if not file_path:
        logger.error("No file path provided to embedder")
        return {
            **state,
            "error": "No file path available for embedding"
        }
    
    logger.info(f"Processing and embedding filing: {file_path}")
    
    try:
        # Create vector store directory
        vector_store_dir = Path(config.get("vector_store_dir", "src/stores/vector"))
        vector_store_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma client
        # Sanitize company name for ChromaDB collection name
        # ChromaDB requires: 3-512 chars, [a-zA-Z0-9._-], must start/end with alphanumeric
        safe_company = company.replace(" ", "_").replace(".", "").replace(",", "").lower()
        safe_company = "".join(c for c in safe_company if c.isalnum() or c in "_-")
        collection_name = f"filing_{safe_company}"
        
        # Initialize ChromaDB client with automatic corruption recovery
        client = create_chromadb_client(vector_store_dir, auto_recover=True, max_retries=2)
        
        # Check if collection already exists and is up to date
        use_cached_embeddings = False
        try:
            existing_collection = client.get_collection(collection_name)
            
            # Check metadata to see if this is the same filing
            collection_meta = existing_collection.metadata or {}
            cached_accession = collection_meta.get("accession")
            cached_filing_date = collection_meta.get("filing_date")
            current_accession = state.get("accession")
            current_filing_date = state.get("filing_date")
            
            # Get file modification time
            file_mtime = Path(file_path).stat().st_mtime
            cached_file_mtime = collection_meta.get("file_mtime")
            
            # Use cached if same filing and file hasn't changed
            if (cached_accession == current_accession and 
                cached_filing_date == current_filing_date and
                cached_file_mtime == file_mtime):
                use_cached_embeddings = True
                collection = existing_collection
                chunk_count = existing_collection.count()
                logger.info(f"✅ Using cached embeddings ({chunk_count} chunks) - filing unchanged")
            else:
                logger.info(f"📥 Filing changed or new - re-embedding")
                client.delete_collection(collection_name)
        except Exception:
            # Collection doesn't exist or error reading it
            logger.info(f"📥 No cached embeddings found - creating new")
        
        # Process and embed if needed
        if not use_cached_embeddings:
            # Process filing into chunks
            processor = TextProcessor()
            chunks = processor.process_filing(
                Path(file_path),
                chunk_size=config.get("chunk_size", 1000),
                chunk_overlap=config.get("chunk_overlap", 200)
            )
            
            # Create new collection with metadata
            collection = client.create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "accession": state.get("accession", ""),
                    "filing_date": state.get("filing_date", ""),
                    "file_mtime": str(Path(file_path).stat().st_mtime),
                    "company": company
                },
            )
            
            # Prepare documents for embedding
            # TextProcessor returns chunks with "text" key and nested "metadata"
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [
                {
                    "section": chunk.get("metadata", {}).get("section", "unknown"),
                    "chunk_index": chunk.get("metadata", {}).get("chunk_index", i),
                    "char_count": chunk.get("metadata", {}).get("char_count", len(chunk["text"])),
                    "company": company,
                }
                for i, chunk in enumerate(chunks)
            ]
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            
            # Embed documents using multi-provider embedder
            logger.info(f"Embedding {len(texts)} chunks...")
            embeddings = await embedder.embed_documents(texts)
            
            # Add to collection
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            
            chunk_count = len(chunks)
            logger.info(f"✅ Created vector store with {chunk_count} chunks")
        else:
            chunk_count = collection.count()
        
        # Log trace event
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "Embedder",
            "create_embeddings",
            f"{'Used cached' if use_cached_embeddings else 'Created'} {chunk_count} chunks {'from' if use_cached_embeddings else 'and embedded into'} vector store",
            {
                "chunks": chunk_count,
                "collection_name": collection_name,
                "vector_store_dir": str(vector_store_dir),
                "cached": use_cached_embeddings
            }
        ).to_dict())
        
        return {
            **state,
            "vector_store": collection,
            "chunks": chunk_count,
            "collection_name": collection_name,
            "trace": trace
        }
    
    except Exception as e:
        logger.error(f"Error embedding filing: {str(e)}")
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "Embedder",
            "error",
            f"Failed to embed filing: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "error": f"Failed to embed filing: {str(e)}",
            "trace": trace
        }
