"""
Fit Scorer node - maps pain points to products with explainable scores.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


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
        
        # Enrich matches with product names from candidate_products
        candidate_products = state.get("candidate_products", [])
        product_lookup = {p.get("product_id"): p.get("title", p.get("product_id")) for p in candidate_products}
        
        for match in matches:
            product_id = match.get("product_id")
            if product_id and product_id not in match:
                # Add product_name field using title from catalog
                match["product_name"] = product_lookup.get(product_id, product_id)
        
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
