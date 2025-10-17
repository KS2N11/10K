"""
Product Catalog Parser - Extract and format product/service information from text.
"""
from typing import List, Dict, Any
from langchain.schema import SystemMessage, HumanMessage
import json
from pathlib import Path

from src.utils.logging import get_logger
from src.utils.multi_llm import MultiProviderLLM

logger = get_logger(__name__)


async def parse_product_catalog(
    text_content: str,
    llm_manager: MultiProviderLLM,
    company_name: str = "Your Company"
) -> List[Dict[str, Any]]:
    """
    Parse product/service descriptions from unstructured text and format into catalog schema.
    
    Args:
        text_content: Raw text describing products/services
        llm_manager: LLM instance for parsing
        company_name: Name of the company (for context)
    
    Returns:
        List of products in standard catalog format
    """
    logger.info(f"Parsing product catalog for {company_name}")
    
    system_prompt = """You are an expert at extracting product and service information from unstructured text.
    
Your task is to read product/service descriptions and convert them into a structured JSON format.

For each product or service mentioned, extract:
1. **product_id**: A URL-friendly identifier (lowercase, hyphens, no spaces)
2. **title**: The official product/service name
3. **summary**: A one-sentence description (max 150 chars)
4. **capabilities**: Array of key features/capabilities (3-8 items)
5. **icp** (Ideal Customer Profile):
   - **industries**: Array of target industries
   - **min_emp**: Minimum employee count for target companies
6. **proof_points**: Array of achievements, metrics, or social proof (2-5 items)

**IMPORTANT**: 
- product_id must be lowercase with hyphens (e.g., "ai-innovation-suite")
- Extract ALL products/services mentioned in the text
- If information is missing, make reasonable inferences based on context
- Focus on extracting business value and capabilities

Return ONLY valid JSON in this exact format:
{
  "products": [
    {
      "product_id": "example-product",
      "title": "Example Product",
      "summary": "Brief one-sentence description of what it does.",
      "capabilities": ["capability1", "capability2", "capability3"],
      "icp": {
        "industries": ["Industry1", "Industry2"],
        "min_emp": 100
      },
      "proof_points": [
        "Metric or achievement 1",
        "Metric or achievement 2"
      ]
    }
  ]
}"""

    user_prompt = f"""Extract all products and services from the following text about {company_name}:

{text_content}

Return the structured JSON catalog as specified."""

    try:
        # Call LLM
        system_message = SystemMessage(content=system_prompt)
        user_message = HumanMessage(content=user_prompt)
        
        response = await llm_manager.ainvoke([system_message, user_message])
        
        # Extract JSON from response
        content = response.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content)
        products = result.get("products", [])
        
        # Validate product schema
        validated_products = []
        for p in products:
            if all(key in p for key in ["product_id", "title", "summary", "capabilities", "icp", "proof_points"]):
                validated_products.append(p)
            else:
                logger.warning(f"Skipping invalid product: {p.get('title', 'Unknown')}")
        
        logger.info(f"✅ Extracted {len(validated_products)} products from catalog")
        return validated_products
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Raw response: {response[:500]}")
        raise ValueError("Could not parse product catalog from text. Please try with clearer product descriptions.")
    
    except Exception as e:
        logger.error(f"Error parsing product catalog: {e}")
        raise


async def save_product_catalog(products: List[Dict[str, Any]], backup: bool = True) -> str:
    """
    Save product catalog to products.json file.
    
    Args:
        products: List of product dictionaries
        backup: Whether to backup existing catalog
    
    Returns:
        Path to saved catalog file
    """
    catalog_path = Path("src/knowledge/products.json")
    
    # Backup existing catalog
    if backup and catalog_path.exists():
        backup_path = Path("src/knowledge/products_backup.json")
        import shutil
        shutil.copy(catalog_path, backup_path)
        logger.info(f"📦 Backed up existing catalog to {backup_path}")
    
    # Save new catalog
    with open(catalog_path, "w") as f:
        json.dump(products, f, indent=2)
    
    logger.info(f"💾 Saved {len(products)} products to {catalog_path}")
    return str(catalog_path)


async def merge_product_catalogs(
    new_products: List[Dict[str, Any]],
    existing_products: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge new products with existing catalog, avoiding duplicates.
    
    Args:
        new_products: Newly parsed products
        existing_products: Current catalog products
    
    Returns:
        Merged product list
    """
    existing_ids = {p["product_id"] for p in existing_products}
    merged = existing_products.copy()
    
    added = 0
    for product in new_products:
        if product["product_id"] not in existing_ids:
            merged.append(product)
            added += 1
        else:
            logger.info(f"⏭️  Skipping duplicate: {product['product_id']}")
    
    logger.info(f"✅ Merged catalog: {len(existing_products)} existing + {added} new = {len(merged)} total")
    return merged
