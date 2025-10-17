"""
Objection Handler node - predicts objections and provides rebuttals.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


async def objection_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict likely objections and provide grounded rebuttals.
    
    Args:
        state: Graph state with matches, pains, and llm_manager
    
    Returns:
        Updated state with objections list
    """
    matches = state.get("matches", [])
    pains = state.get("pains", [])
    candidate_products = state.get("candidate_products", [])
    config = state.get("config", {})
    llm_manager = state.get("llm_manager")
    
    # Create llm_manager from config if not in state (for hashability)
    if not llm_manager:
        from ...utils.multi_llm import MultiProviderLLM
        llm_manager = MultiProviderLLM(config=config)
    
    if not matches:
        logger.warning("No matches to handle objections for")
        return {**state, "objections": []}
    
    if not llm_manager:
        logger.error("No LLM manager in state")
        return {**state, "objections": []}
    
    logger.info(f"Handling objections for {len(matches)} matches")
    
    # Get top matches
    top_matches = matches[:3]
    
    objection_prompt = """You are an expert sales strategist. Predict the top 3-5 objections a prospect might have for these product recommendations.

Context:
Company Pain Points: {pains_summary}

Recommended Solutions: {matches_summary}

For each objection, provide:
1. objection: The likely objection
2. rebuttal: A data-backed rebuttal using product proof points
3. evidence: Specific evidence from the product catalog

Format as JSON:
{{
  "objections": [
    {{
      "objection": "This seems too expensive for our budget",
      "rebuttal": "While there is an upfront cost, our customers see average ROI of...",
      "evidence": ["Avg 18% cost savings in 90 days", "3-month payback period"]
    }}
  ]
}}

Provide your analysis in valid JSON format:"""
    
    # Format context
    pains_summary = "; ".join([p.get("theme", "") for p in pains[:5]])
    
    matches_summary = "\n".join([
        f"- {m.get('product_id')}: {m.get('why', '')[:150]} (Score: {m.get('score')})"
        for m in top_matches
    ])
    
    # Create messages
    system_message = SystemMessage(content="You are a helpful assistant that provides structured objection analysis. Always respond with valid JSON.")
    user_message = HumanMessage(content=objection_prompt.format(
        pains_summary=pains_summary,
        matches_summary=matches_summary
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
        objections = result.get("objections", [])
        
        # Create citations for objections
        citations = state.get("citations", [])
        for i, objection in enumerate(objections):
            citations.append({
                "source": "CATALOG",
                "id": f"objection_{i}",
                "objection": objection.get("objection"),
                "evidence": objection.get("evidence", [])
            })
        
        # Log trace event
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ObjectionHandler",
            "handle_objections",
            f"Identified {len(objections)} potential objections with rebuttals",
            {"objections_count": len(objections)}
        ).to_dict())
        
        return {
            **state,
            "objections": objections,
            "citations": citations,
            "trace": trace
        }
    
    except Exception as e:
        logger.error(f"Error handling objections: {str(e)}")
        logger.debug(f"Raw response: {response}")
        
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ObjectionHandler",
            "error",
            f"Failed to handle objections: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "objections": [],
            "trace": trace
        }
