"""
Utility functions for catalog management and hashing.
"""
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any


def get_catalog_hash(catalog_path: str = "src/knowledge/products.json") -> str:
    """
    Calculate SHA256 hash of product catalog.
    Used to detect catalog changes.
    
    Args:
        catalog_path: Path to products.json
    
    Returns:
        SHA256 hash as hex string
    """
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Calculate hash
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return hash_obj.hexdigest()
    
    except FileNotFoundError:
        return ""


def load_product_catalog(catalog_path: str = "src/knowledge/products.json") -> List[Dict[str, Any]]:
    """
    Load product catalog from JSON file.
    
    Args:
        catalog_path: Path to products.json
    
    Returns:
        List of product dictionaries
    """
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def has_catalog_changed(
    current_hash: str,
    catalog_path: str = "src/knowledge/products.json"
) -> bool:
    """
    Check if catalog has changed since last analysis.
    
    Args:
        current_hash: Previously stored catalog hash
        catalog_path: Path to products.json
    
    Returns:
        True if catalog has changed, False otherwise
    """
    latest_hash = get_catalog_hash(catalog_path)
    return latest_hash != current_hash
