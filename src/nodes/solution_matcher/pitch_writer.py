"""
Pitch Writer node - generates persona-aware pitch with 10-K citations.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


async def pitch_writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a personalized pitch that references specific 10-K insights.
    
    Args:
        state: Graph state with all analysis results and llm_manager
    
    Returns:
        Updated state with pitch object
    """
    pains = state.get("pains", [])
    matches = state.get("matches", [])
    objections = state.get("objections", [])
    company = state.get("company", "the company")
    config = state.get("config", {})
    llm_manager = state.get("llm_manager")
    
    # Create llm_manager from config if not in state (for hashability)
    if not llm_manager:
        from ...utils.multi_llm import MultiProviderLLM
        llm_manager = MultiProviderLLM(config=config)
    
    if not matches:
        logger.warning("No matches to create pitch for")
        return {**state, "pitch": None}
    
    if not llm_manager:
        logger.error("No LLM manager in state")
        return {**state, "pitch": None}
    
    logger.info("Generating personalized pitch")
    
    pitch_prompt = """You are an expert sales professional. Write a compelling, personalized email pitch for {company}.

Context:
Company: {company}
Pain Points from 10-K: {pains_text}
Recommended Solutions: {solutions_text}

Requirements:
1. Start with a compelling subject line
2. Open with a specific reference to their 10-K filing (quote a specific challenge)
3. Position 1-2 products as solutions to their documented pains
4. Include concrete proof points
5. End with a clear call-to-action
6. Keep it concise (under 250 words)
7. Target persona: CFO or VP of Operations

Format as JSON:
{{
  "subject": "Email subject line",
  "body": "Full email body with specific 10-K quotes in quotation marks",
  "persona": "CFO",
  "key_quotes": ["Specific quote from 10-K", "Another quote"],
  "products_mentioned": ["product-id-1", "product-id-2"]
}}

Write a professional, value-focused pitch in valid JSON format:"""
    
    # Format context
    pains_text = "\n".join([
        f"- {p.get('theme')}: \"{p.get('quotes', [''])[0][:150] if p.get('quotes') else p.get('rationale', '')[:150]}...\""
        for p in pains[:3]
    ])
    
    solutions_text = "\n".join([
        f"- {m.get('product_id')} (Score: {m.get('score')}): {m.get('why', '')[:200]}"
        for m in matches[:2]
    ])
    
    # Create messages
    system_message = SystemMessage(content="You are a helpful assistant that writes compelling sales pitches. Always respond with valid JSON.")
    user_message = HumanMessage(content=pitch_prompt.format(
        company=company,
        pains_text=pains_text,
        solutions_text=solutions_text
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
        
        pitch = json.loads(content)
        
        # Create citations for pitch
        citations = state.get("citations", [])
        citations.append({
            "source": "PITCH",
            "id": "pitch_output",
            "subject": pitch.get("subject"),
            "quotes_used": pitch.get("key_quotes", [])
        })
        
        # Log trace event
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "PitchWriter",
            "generate_pitch",
            f"Generated pitch for {pitch.get('persona', 'executive')}",
            {
                "persona": pitch.get("persona"),
                "products_count": len(pitch.get("products_mentioned", []))
            }
        ).to_dict())
        
        return {
            **state,
            "pitch": pitch,
            "citations": citations,
            "trace": trace
        }
    
    except Exception as e:
        logger.error(f"Error generating pitch: {str(e)}")
        logger.debug(f"Raw response: {response}")
        
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "PitchWriter",
            "error",
            f"Failed to generate pitch: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "pitch": None,
            "trace": trace
        }
