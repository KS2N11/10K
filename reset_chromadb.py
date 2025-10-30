"""
CLI tool to reset corrupted ChromaDB vector stores.

Usage:
    python reset_chromadb.py            # Reset all vector stores
    python reset_chromadb.py --vector   # Reset only vector store
    python reset_chromadb.py --catalog  # Reset only catalog store
"""
import argparse
from pathlib import Path

from src.utils.chromadb_utils import reset_vector_store, reset_all_vector_stores


def main():
    parser = argparse.ArgumentParser(
        description="Reset corrupted ChromaDB vector stores"
    )
    parser.add_argument(
        "--vector",
        action="store_true",
        help="Reset only the vector store"
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Reset only the catalog store"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset all stores (default)"
    )
    
    args = parser.parse_args()
    
    # Default to all if no specific store selected
    if not args.vector and not args.catalog:
        args.all = True
    
    base_dir = Path("src/stores")
    
    if args.all:
        print("🗑️  Resetting ALL vector stores...")
        reset_all_vector_stores(base_dir)
        print("✅ All vector stores have been reset!")
    else:
        if args.vector:
            print("🗑️  Resetting vector store...")
            reset_vector_store(base_dir / "vector")
            print("✅ Vector store has been reset!")
        
        if args.catalog:
            print("🗑️  Resetting catalog store...")
            reset_vector_store(base_dir / "catalog")
            print("✅ Catalog store has been reset!")
    
    print("\n📝 Note: Embeddings will be automatically recreated on next analysis.")


if __name__ == "__main__":
    main()
