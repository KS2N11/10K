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
    
    # Get your company name from config
    your_company_name = config.get("your_company_name", "[Your Company]")
    your_company_tagline = config.get("your_company_tagline", "")
    
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
    
    # Build company intro line
    company_intro = f"We're {your_company_name}"
    if your_company_tagline:
        company_intro += f", {your_company_tagline}"
    company_intro += "."
    
    pitch_prompt = """You are an expert sales professional writing for {your_company}. Write a compelling, personalized email pitch for {target_company}.

Context:
Your Company: {your_company}
Target Company: {target_company}

THEIR PAIN POINTS (from their 10-K filing):
{pains_text}

YOUR SOLUTIONS (with proof points):
{solutions_text}

Requirements:
1. Start with a compelling subject line that references their specific challenge
2. Open with a DIRECT QUOTE from their 10-K filing showing you understand their challenge
3. Introduce {your_company} naturally in the first paragraph
4. Present 1-2 specific solutions from the list above with:
   - The exact product/service title
   - How it addresses their specific pain point
   - A concrete proof point with metrics (use the exact proof points provided)
5. CRITICAL: Use ONLY the proof points provided above - DO NOT invent company names, metrics, or case studies
6. Reference specific capabilities that solve their documented challenges
7. Keep it professional, concise (200-250 words), and value-focused
8. End with a clear, low-pressure call-to-action
9. Target persona: C-suite executive (CEO, CFO, CTO, or COO)

Format as JSON:
{{
  "subject": "Email subject line referencing their 10-K challenge",
  "body": "Full email body with specific 10-K quotes in quotation marks and real proof points",
  "persona": "CEO" or "CFO" or "CTO" or "COO",
  "key_quotes": ["Exact quote from their 10-K", "Another quote if relevant"],
  "products_mentioned": ["product-id-1", "product-id-2"]
}}

Write a professional, value-focused pitch using ONLY the information provided:"""
    
    # Format context with RICH product details
    pains_text = "\n".join([
        f"• {p.get('theme')}\n  Challenge: \"{p.get('quotes', [''])[0][:200] if p.get('quotes') else p.get('rationale', '')[:200]}...\"\n  Confidence: {p.get('confidence', 0):.0%}"
        for p in pains[:3]
    ])
    
    # Build detailed solutions text with full product info
    solutions_parts = []
    for m in matches[:2]:
        product_info = m.get('product', {})
        solution_text = f"""
• {m.get('product_name', m.get('product_id'))} (Match Score: {m.get('score', 0):.0%})
  Summary: {product_info.get('summary', 'N/A')}
  Key Capabilities: {', '.join(product_info.get('capabilities', [])[:4])}
  Proof Points:
    {chr(10).join(['- ' + pp for pp in product_info.get('proof_points', [])[:2]])}
  Why This Fits: {m.get('why', '')[:250]}"""
        solutions_parts.append(solution_text)
    
    solutions_text = "\n".join(solutions_parts)
    
    # Create messages
    system_message = SystemMessage(content=f"You are a sales professional representing {your_company_name}. Write compelling pitches that reference the company's actual products and proof points. Never invent company names.")
    user_message = HumanMessage(content=pitch_prompt.format(
        your_company=your_company_name,
        target_company=company,
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
