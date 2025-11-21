"""
Fit Scorer node - maps pain points to products with explainable scores.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


def categorize_product(product_name: str, capabilities: List[str]) -> str:
    """
    Categorize a product based on its name and capabilities.
    
    Args:
        product_name: Name of the product
        capabilities: List of product capabilities
    
    Returns:
        Product category string
    """
    name_lower = product_name.lower()
    caps_text = " ".join(capabilities).lower()
    
    # Security & Compliance
    if any(word in name_lower for word in ['security', 'cybersecurity', 'compliance']):
        return "Security & Compliance"
    if any(word in caps_text for word in ['threat', 'encryption', 'compliance', 'security']):
        return "Security & Compliance"
    
    # AI & Machine Learning
    if any(word in name_lower for word in ['ai', 'machine learning', 'ml', 'innovation']):
        return "AI & Machine Learning"
    if any(word in caps_text for word in ['predictive analytics', 'nlp', 'computer vision', 'ai']):
        return "AI & Machine Learning"
    
    # Cloud & Infrastructure
    if any(word in name_lower for word in ['cloud', 'infrastructure', 'modernization']):
        return "Infrastructure & Cloud"
    if any(word in caps_text for word in ['cloud', 'migration', 'devops', 'infrastructure']):
        return "Infrastructure & Cloud"
    
    # Data & Analytics
    if any(word in name_lower for word in ['data', 'analytics', 'bi']):
        return "Data & Analytics"
    if any(word in caps_text for word in ['data warehouse', 'analytics', 'dashboard', 'etl']):
        return "Data & Analytics"
    
    # Digital Transformation
    if any(word in name_lower for word in ['digital', 'transformation']):
        return "Consulting & Strategy"
    if any(word in caps_text for word in ['digitization', 'workflow automation', 'modernization']):
        return "Consulting & Strategy"
    
    # Customer Experience
    if any(word in name_lower for word in ['customer', 'experience', 'engagement']):
        return "Customer Experience"
    if any(word in caps_text for word in ['customer', 'crm', 'personalization']):
        return "Customer Experience"
    
    # Supply Chain
    if any(word in name_lower for word in ['supply', 'chain', 'logistics']):
        return "Supply Chain & Logistics"
    
    # HR & Talent
    if any(word in name_lower for word in ['talent', 'hr', 'human']):
        return "Human Resources"
    
    # Finance
    if any(word in name_lower for word in ['financial', 'finance', 'accounting']):
        return "Finance & Accounting"
    
    # Default
    return "Consulting & Strategy"


async def fit_scorer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score product-pain fit with explanations and evidence.
    
    Args:
        state: Graph state with pains, candidate_products, and llm_manager
    
    Returns:
        Updated state with matches (scored pain-product pairs)
    """
    pains = state.get("pains", [])
    candidate_products = state.get("candidate_products", [])
    config = state.get("config", {})
    llm_manager = state.get("llm_manager")
    
    # Create llm_manager from config if not in state (for hashability)
    if not llm_manager:
        from ...utils.multi_llm import MultiProviderLLM
        llm_manager = MultiProviderLLM(config=config)
    
    if not pains or not candidate_products:
        logger.warning("No pains or products to score")
        return {**state, "matches": []}
    
    if not llm_manager:
        logger.error("No LLM manager in state")
        return {**state, "error": "No LLM manager available"}
    
    logger.info(f"Scoring fit between {len(pains)} pains and {len(candidate_products)} products")
    
    scoring_prompt = """You are an expert solutions architect. Score how well each product addresses each pain point.

Pain Points:
{pains_text}

Products:
{products_text}

For each pain-product pair with good fit (score >= 60), provide:
1. pain_theme: The pain point theme
2. product_id: The product identifier
3. score: Fit score from 0-100
4. why: Detailed explanation of why this product fits
5. evidence: Specific capabilities or proof points that address the pain

Format as JSON:
{{
  "matches": [
    {{
      "pain_theme": "Supply Chain Disruption",
      "product_id": "supply-optimizer",
      "score": 85,
      "why": "This product directly addresses supply chain visibility...",
      "evidence": ["Real-time tracking", "Predictive analytics"]
    }}
  ]
}}

Provide your analysis in valid JSON format:"""
    
    # Format pains and products
    pains_text = "\n".join([
        f"- {p.get('theme')}: {p.get('rationale', '')[:200]}"
        for p in pains
    ])
    
    products_text = "\n".join([
        f"- {p.get('product_id')} ({p.get('title')}): {p.get('summary', '')}\n  Capabilities: {', '.join(p.get('capabilities', []))}"
        for p in candidate_products
    ])
    
    # Create system and user messages
    system_message = SystemMessage(content="You are a helpful assistant that provides structured product-fit analysis. Always respond with valid JSON.")
    user_message = HumanMessage(content=scoring_prompt.format(
        pains_text=pains_text,
        products_text=products_text
    ))
    
    # Call LLM
    response = await llm_manager.ainvoke([system_message, user_message])
    
    try:
        # Extract JSON from response (response is already a string from MultiProviderLLM)
        content = response.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content)
        matches = result.get("matches", [])
        
        # Enrich matches with product names and categories from candidate_products
        candidate_products = state.get("candidate_products", [])
        product_lookup = {p.get("product_id"): {
            "name": p.get("title", p.get("product_id")),
            "capabilities": p.get("capabilities", [])
        } for p in candidate_products}
        
        for match in matches:
            product_id = match.get("product_id")
            if product_id and product_id in product_lookup:
                product_info = product_lookup[product_id]
                # Add product_name field using title from catalog
                match["product_name"] = product_info["name"]
                # Determine and add category based on product name and capabilities
                match["product_category"] = categorize_product(product_info["name"], product_info["capabilities"])
        
        # Sort by score
        matches.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Create citations for matches
        citations = state.get("citations", [])
        for i, match in enumerate(matches):
            citations.append({
                "source": "CATALOG",
                "id": f"match_{i}",
                "product_id": match.get("product_id"),
                "evidence": match.get("evidence", [])
            })
        
        # Log trace event
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "FitScorer",
            "score_fit",
            f"Scored {len(matches)} product-pain matches",
            {
                "matches_count": len(matches),
                "top_score": matches[0].get("score") if matches else 0,
                "top_match": matches[0].get("product_id") if matches else None
            }
        ).to_dict())
        
        return {
            **state,
            "matches": matches,
            "citations": citations,
            "trace": trace
        }
    
    except Exception as e:
        logger.error(f"Error scoring fit: {str(e)}")
        logger.debug(f"Raw response: {response}")
        
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "FitScorer",
            "error",
            f"Failed to score fit: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "matches": [],
            "trace": trace
        }
