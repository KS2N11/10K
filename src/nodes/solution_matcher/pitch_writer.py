"""
Pitch Writer node - generates persona-aware pitch with 10-K citations.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


def determine_persona(matches: List[Dict[str, Any]], pains: List[Dict[str, Any]]) -> str:
    """
    Intelligently determine the target persona based on product category and pain points.
    
    Args:
        matches: List of product matches with categories
        pains: List of pain points
    
    Returns:
        Target persona (e.g., "CTO", "CFO", "CISO", "VP of Operations")
    """
    if not matches:
        return "CFO"
    
    # Get the top match's category
    top_match = matches[0]
    product_category = top_match.get('product_category', '')
    product_name = top_match.get('product_name', '').lower()
    
    # Map categories to personas
    persona_mapping = {
        "Security & Compliance": "CISO",
        "Infrastructure & Cloud": "CTO",
        "AI & Machine Learning": "CTO",
        "Data & Analytics": "CTO",
        "Automation & RPA": "VP of Operations",
        "Supply Chain & Logistics": "VP of Operations",
        "Customer Experience": "VP of Customer Success",
        "Finance & Accounting": "CFO",
        "Human Resources": "CHRO",
        "Consulting & Strategy": "CEO"
    }
    
    # Check for specific keywords in product name for more precision
    # Order matters - check more specific terms first
    if 'cybersecurity' in product_name or 'security' in product_name:
        return "CISO"
    elif 'supply' in product_name or 'logistics' in product_name or 'supply chain' in product_name:
        return "VP of Operations"
    elif 'financial' in product_name or 'finance' in product_name:
        return "CFO"
    elif 'ai' in product_name or 'machine learning' in product_name or 'ml' in product_name:
        return "CTO"
    elif 'data' in product_name or 'analytics' in product_name:
        return "CTO"
    elif 'customer' in product_name:
        return "VP of Customer Success"
    elif 'hr' in product_name or 'talent' in product_name:
        return "CHRO"
    
    # Use category mapping
    return persona_mapping.get(product_category, "CFO")


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
    
    # Determine the appropriate persona based on the product/solution category
    persona = determine_persona(matches, pains)
    logger.info(f"Determined persona: {persona}")
    
    # Build company intro line
    company_intro = f"We're {your_company_name}"
    if your_company_tagline:
        company_intro += f", {your_company_tagline}"
    company_intro += "."
    
    pitch_prompt = """You are writing a brief, direct sales email based on real examples from a successful sales team.

Context:
Your Company: {your_company}
Target Company: {target_company}
Target Persona: {persona}
Pain Points from their 10-K: {pains_text}
Your Solutions: {solutions_text}

CRITICAL STYLE REQUIREMENTS (based on proven sales emails):
- Write like a real person, NOT ChatGPT
- Keep it SHORT (150-200 words max)
- Be direct and conversational
- Use simple, natural language
- NO corporate buzzwords or fluff
- NO phrases like "I hope this finds you well" or "I'd love to connect"
- Start with a direct observation or insight
- Reference their 10-K naturally, not formally

EMAIL STRUCTURE:
1. Subject: Direct and specific (6-10 words) - mention company or specific insight
2. Opening: Quick intro + why you're reaching out (1-2 sentences)
3. Insight: Reference their 10-K challenge briefly (1-2 sentences)
4. Solution: How you help (1-2 sentences with specific value)
5. Social proof: Quick mention of results (1 sentence)
6. CTA: Simple, low-pressure ask (1 sentence)

TONE EXAMPLES (match this style):
✓ "Reaching out because..."
✓ "I went through [Company]'s 10-K and noticed..."
✓ "After reviewing [Company]'s filing, a few things stood out..."
✓ "Quick note after digging into..."
✓ "This is something your team is currently dealing with or planning around"

AVOID:
✗ "I hope this email finds you well"
✗ "I would love to schedule a call"
✗ "We are reaching out to introduce"
✗ "Our cutting-edge solution"
✗ Long paragraphs or formal language

Format as JSON:
{{
  "subject": "Short, specific subject line",
  "body": "Direct, conversational email body (150-200 words)",
  "persona": "{persona}",
  "key_quotes": ["Brief quote from 10-K"],
  "products_mentioned": ["product-id-1"]
}}

Write a natural, conversational pitch in valid JSON format:"""
    
    # Format context
    pains_text = "\n".join([
        f"- {p.get('theme')}: \"{p.get('quotes', [''])[0][:150] if p.get('quotes') else p.get('rationale', '')[:150]}...\""
        for p in pains[:3]
    ])
    
    solutions_text = "\n".join([
        f"- {m.get('product_name', m.get('product_id'))} (Fit Score: {m.get('score')}): {m.get('why', '')[:200]}"
        for m in matches[:2]
    ])
    
    # Create messages
    system_message = SystemMessage(content=f"You are a sales rep at {your_company_name}. Write brief, natural emails like the examples shown. Be conversational and direct. Avoid corporate speak.")
    user_message = HumanMessage(content=pitch_prompt.format(
        your_company=your_company_name,
        target_company=company,
        persona=persona,
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
