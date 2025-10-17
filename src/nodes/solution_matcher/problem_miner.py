"""
Problem Miner node - extracts pain points and objectives from 10-K with citations.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


async def problem_miner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mine pain points and business objectives from 10-K filing.
    
    Args:
        state: Graph state with vector_store
    
    Returns:
        Updated state with pains and citations
    """
    vector_store = state.get("vector_store")
    config = state.get("config", {})
    embedder = state.get("embedder")
    llm_manager = state.get("llm_manager")
    user_query = state.get("user_query", "")
    
    # Create providers from config if not in state (for hashability)
    if not embedder:
        from ...utils.multi_embeddings import MultiProviderEmbeddings
        embedder = MultiProviderEmbeddings(config=config)
    if not llm_manager:
        from ...utils.multi_llm import MultiProviderLLM
        llm_manager = MultiProviderLLM(config=config)
    
    if not vector_store:
        logger.error("No vector store available for problem mining")
        return {**state, "error": "No vector store available"}
    
    logger.info("Mining pain points from 10-K")
    
    # Query vector store for relevant sections
    top_k = config.get("top_k_chunks", 10)
    
    # Focus on risk factors and MD&A
    queries = [
        "business risks challenges obstacles",
        "financial risks operational difficulties",
        "competitive pressures market challenges",
        user_query
    ]
    
    all_chunks = []
    seen_content = set()
    
    for query_text in queries:
        # Embed query
        query_embedding = await embedder.embed_query(query_text)
        
        # Search vector store
        results = vector_store.query(
            query_embeddings=[query_embedding],
            n_results=top_k // len(queries)
        )
        
        # Process results
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        for i, doc in enumerate(docs):
            if doc not in seen_content:
                all_chunks.append({
                    "content": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "score": float(distances[i]) if i < len(distances) else 0.0
                })
                seen_content.add(doc)
    
    # Sort by score and take top chunks
    all_chunks.sort(key=lambda x: x["score"])
    top_chunks = all_chunks[:top_k]
    
    # Use LLM to extract structured pain points
    extraction_prompt = """You are an expert business analyst. Analyze the following excerpts from a company's 10-K filing and extract the top 3-5 pain points or business challenges.

For each pain point, provide:
1. A concise theme (2-5 words)
2. A detailed rationale explaining the pain
3. Direct quotes from the text as evidence
4. A confidence score (0.0-1.0)

Format your response as JSON:
{
  "pains": [
    {
      "theme": "Supply Chain Disruption",
      "rationale": "The company faces significant supply chain challenges...",
      "quotes": ["exact quote from text", "another quote"],
      "section": "Item 1A",
      "confidence": 0.85
    }
  ]
}

10-K Excerpts:
"""
    
    # Add chunks to prompt
    for i, chunk in enumerate(top_chunks[:8]):  # Limit context
        section = chunk['metadata'].get('section', 'Unknown')
        content = chunk['content'][:500] + "..." if len(chunk['content']) > 500 else chunk['content']
        extraction_prompt += f"\n\n[Section: {section}]\n{content}"
    
    extraction_prompt += "\n\nProvide your analysis in valid JSON format:"
    
    # Call LLM
    messages = [
        SystemMessage(content="You are a helpful assistant that extracts structured business insights. Always respond with valid JSON."),
        HumanMessage(content=extraction_prompt)
    ]
    
    response = await llm_manager.ainvoke(messages)
    
    # Parse response
    try:
        # Extract JSON from response (handle markdown code blocks)
        response_text = response.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        pains = result.get("pains", [])
        
        # Add citations
        citations = []
        for pain in pains:
            for quote in pain.get("quotes", []):
                # Find source chunk
                for chunk in top_chunks:
                    if quote.lower() in chunk["content"].lower():
                        citations.append({
                            "quote": quote,
                            "section": chunk["metadata"].get("section", "Unknown"),
                            "context": chunk["content"][:200]
                        })
                        break
        
        # Log trace
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ProblemMiner",
            "extract_pains",
            f"Extracted {len(pains)} pain points from {len(top_chunks)} chunks",
            {
                "pain_count": len(pains),
                "chunk_count": len(top_chunks),
                "citations": len(citations)
            }
        ).to_dict())
        
        return {
            **state,
            "pains": pains,
            "citations": citations,
            "trace": trace
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Response was: {response[:500]}")
        
        # Fallback: create basic pain points
        pains = [{
            "theme": "Analysis Error",
            "rationale": "Could not parse structured pain points from filing",
            "quotes": [],
            "section": "N/A",
            "confidence": 0.3
        }]
        
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ProblemMiner",
            "error",
            f"JSON parsing failed: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "pains": pains,
            "citations": [],
            "trace": trace
        }
