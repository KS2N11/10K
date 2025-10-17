"""
Company resolver node - extracts and disambiguates company from user query.
"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage

from ..utils.sec_api import SECAPI
from ..utils.logging import setup_logger, log_trace_event
from ..utils.multi_llm import MultiProviderLLM

logger = setup_logger(__name__)


async def company_resolver_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract company name from query and resolve to CIK.
    
    If multiple matches found, returns candidates for disambiguation.
    
    Args:
        state: Graph state with user_query
    
    Returns:
        Updated state with company/cik or candidates list
    """
    user_query = state.get("user_query", "")
    config = state.get("config", {})
    llm_manager = state.get("llm_manager")
    
    # Create llm_manager from config if not in state (for hashability)
    if not llm_manager:
        from ..utils.multi_llm import MultiProviderLLM
        llm_manager = MultiProviderLLM(config=config)
    
    logger.info(f"Resolving company from query: {user_query}")
    
    # Use multi-provider LLM to extract company name
    messages = [
        SystemMessage(content="You are a helpful assistant that extracts company names from queries. "
                   "Return ONLY the company name, nothing else. If no company is mentioned, return 'NONE'."),
        HumanMessage(content=f"Extract the company name from this query: {user_query}")
    ]
    
    company_name = await llm_manager.ainvoke(messages)
    company_name = company_name.strip()
    
    if company_name == "NONE" or not company_name:
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "CompanyResolver",
            "extract_company",
            "No company found in query",
            {"query": user_query}
        ).to_dict())
        
        return {
            **state,
            "error": "No company name found in query",
            "trace": trace
        }
    
    logger.info(f"Extracted company name: {company_name}")
    
    # Search for company in SEC database
    sec_api = SECAPI(config.get("sec_user_agent"))
    candidates = await sec_api.search_company(company_name)
    
    trace = state.get("trace", [])
    
    if len(candidates) == 0:
        trace.append(log_trace_event(
            logger,
            "CompanyResolver",
            "search_company",
            f"No company found for: {company_name}",
            {"company_name": company_name}
        ).to_dict())
        
        return {
            **state,
            "error": f"No company found for: {company_name}",
            "trace": trace
        }
    
    elif len(candidates) == 1:
        # Exact match found
        company = candidates[0]
        trace.append(log_trace_event(
            logger,
            "CompanyResolver",
            "resolve_company",
            f"Resolved to: {company['name']} (CIK: {company['cik']})",
            {"company": company}
        ).to_dict())
        
        return {
            **state,
            "company": company["name"],
            "cik": company["cik"],
            "ticker": company.get("ticker"),
            "trace": trace
        }
    
    else:
        # Multiple matches - need disambiguation
        trace.append(log_trace_event(
            logger,
            "CompanyResolver",
            "disambiguation_required",
            f"Found {len(candidates)} candidates for: {company_name}",
            {"candidates": candidates}
        ).to_dict())
        
        return {
            **state,
            "status": "disambiguation_required",
            "candidates": candidates,
            "trace": trace
        }
