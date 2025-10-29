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
    # Prefer external prompt template for consistency
    try:
        from pathlib import Path
        prompt_path = Path("src/knowledge/prompts/extract_pains.txt")
        if prompt_path.exists():
            extraction_prompt = prompt_path.read_text(encoding="utf-8")
        else:
            extraction_prompt = (
                "You are an expert business analyst extracting pain points from SEC 10-K filings.\n"
                "Return valid JSON only with a 'pains' array.\n"
            )
    except Exception:
        extraction_prompt = (
            "You are an expert business analyst extracting pain points from SEC 10-K filings.\n"
            "Return valid JSON only with a 'pains' array.\n"
        )

    extraction_prompt += "\n\n10-K Excerpts:"
    
    # Add chunks to prompt
    for i, chunk in enumerate(top_chunks[:8]):  # Limit context
        section = chunk['metadata'].get('section', 'Unknown')
        content = chunk['content'][:500] + "..." if len(chunk['content']) > 500 else chunk['content']
        extraction_prompt += f"\n\n[Section: {section}]\n{content}"
    
    extraction_prompt += "\n\nProvide your analysis in valid JSON format:"
    
    # Call LLM
    messages = [
        SystemMessage(content="You are a helpful assistant that extracts structured business insights. You MUST respond with ONLY valid JSON. Do not include any text before or after the JSON. Do not wrap JSON in code blocks."),
        HumanMessage(content=extraction_prompt)
    ]
    
    response = await llm_manager.ainvoke(messages, temperature=0.2, max_tokens=1500)
    
    # Parse response
    try:
        # Extract JSON from response (robust)
        response_text = response.strip()
        logger.debug(f"Raw LLM response (first 300 chars): {response_text[:300]}")

        response_data = None

        # Method 1: JSON inside markdown code fences (```json or ```)
        if "```" in response_text:
            for block in response_text.split("```"):
                bt = block.strip()
                # Remove language identifier if present (json, JSON, etc.)
                if bt.startswith("json"):
                    bt = bt[4:].strip()
                elif bt.startswith("JSON"):
                    bt = bt[4:].strip()
                
                if bt.startswith(("{", "[")):
                    try:
                        response_data = json.loads(bt)
                        logger.info("✅ Successfully parsed JSON from code fence")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to parse code fence block: {e}")
                        continue

        # Method 2: substring from first { to last }
        if response_data is None:
            try:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    response_data = json.loads(json_str)
                    logger.info("✅ Successfully parsed JSON by finding braces")
            except Exception as e:
                logger.debug(f"Failed to parse by finding braces: {e}")
                response_data = None

        # Method 3: parse entire text as JSON
        if response_data is None:
            try:
                response_data = json.loads(response_text)
                logger.info("✅ Successfully parsed entire response as JSON")
            except Exception as e:
                logger.debug(f"Failed to parse entire response: {e}")
                response_data = None
        
        # Check if we successfully got JSON
        if response_data is None:
            raise json.JSONDecodeError("Could not extract valid JSON from response", response_text, 0)

        # Normalize and extract pains
        result = response_data if isinstance(response_data, dict) else {"pains": response_data}
        pains = result.get("pains", [])
        if not pains:
            pains = result.get("pain_points") or result.get("issues") or []
        
        # Validate pain point structure
        validated_pains = []
        for pain in pains:
            if isinstance(pain, dict):
                # Ensure all required fields exist with defaults
                validated_pain = {
                    "theme": pain.get("theme", "Unknown Pain Point"),
                    "rationale": pain.get("rationale", "No rationale provided"),
                    "quotes": pain.get("quotes", []),
                    "section": pain.get("section", "Unknown"),
                    "confidence": float(pain.get("confidence", 0.5))
                }
                validated_pains.append(validated_pain)
            else:
                logger.warning(f"Skipping invalid pain point structure: {pain}")
        
        if not validated_pains:
            logger.warning("No valid pain points found after parsing")
            # Create a minimal pain point rather than failing completely
            validated_pains = [{
                "theme": "Insufficient Data",
                "rationale": "LLM response contained no valid pain point structures",
                "quotes": [],
                "section": "N/A",
                "confidence": 0.4
            }]
        
        logger.info(f"✅ Validated {len(validated_pains)} pain points")
        
        # Add citations
        citations = []
        for pain in validated_pains:
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
            f"Extracted {len(validated_pains)} pain points from {len(top_chunks)} chunks",
            {
                "pain_count": len(validated_pains),
                "chunk_count": len(top_chunks),
                "citations": len(citations)
            }
        ).to_dict())
        
        return {
            **state,
            "pains": validated_pains,
            "citations": citations,
            "trace": trace
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response was (first 1000 chars): {response[:1000]}")
        
        # Fallback: create basic pain points with more context
        pains = [{
            "theme": "Analysis Error - JSON Parse Failed",
            "rationale": f"Could not parse structured pain points from filing. The LLM returned malformed JSON. Error: {str(e)[:100]}",
            "quotes": ["[Unable to extract quotes due to parsing error]"],
            "section": "N/A",
            "confidence": 0.3
        }]
        
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "ProblemMiner",
            "error",
            f"JSON parsing failed: {str(e)}. Response preview: {response[:200]}",
            {"error": str(e), "response_preview": response[:200]}
        ).to_dict())
        
        return {
            **state,
            "pains": pains,
            "citations": [],
            "trace": trace,
            "error": f"JSON parsing failed: {str(e)}"
        }
