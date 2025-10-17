"""
Main DAG orchestration for the 10K Insight Agent.
"""
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END

from ..nodes.company_resolver import company_resolver_node
from ..nodes.sec_fetcher import sec_fetcher_node
from ..nodes.embedder import embedder_node
from ..nodes.solution_matcher.subgraph import solution_matcher_node
from ..utils.logging import setup_logger

logger = setup_logger(__name__)


class AgentState(TypedDict):
    """State shared across all nodes in the DAG."""
    # Input
    user_query: str
    config: Dict[str, Any]
    
    # AI Providers (injected from routes)
    llm_manager: Any  # MultiProviderLLM instance
    embedder: Any  # MultiProviderEmbeddings instance
    
    # Company resolution
    company: str
    cik: str
    ticker: str
    candidates: list
    status: str
    
    # SEC filing
    filing_url: str
    file_path: str
    filing_date: str
    accession: str
    
    # Embedding
    vector_store: Any
    chunks: int
    collection_name: str
    
    # Solution matcher results
    pains: list
    candidate_products: list
    matches: list
    objections: list
    pitch: Dict[str, Any]
    citations: list
    
    # Metadata
    trace: list
    error: str


def should_continue_after_resolver(state: Dict[str, Any]) -> str:
    """
    Determine next step after company resolver.
    
    Returns:
        - "fetch" if company resolved
        - "end" if disambiguation required or error
    """
    if state.get("status") == "disambiguation_required":
        logger.info("Disambiguation required, ending workflow")
        return "end"
    
    if state.get("error"):
        logger.error(f"Error in company resolver: {state.get('error')}")
        return "end"
    
    if state.get("company") and state.get("cik"):
        logger.info("Company resolved, continuing to fetch")
        return "fetch"
    
    logger.warning("Unexpected state in company resolver")
    return "end"


def should_continue_after_fetcher(state: Dict[str, Any]) -> str:
    """Determine next step after SEC fetcher."""
    if state.get("error"):
        return "end"
    if state.get("file_path"):
        return "embed"
    return "end"


def should_continue_after_embedder(state: Dict[str, Any]) -> str:
    """Determine next step after embedder."""
    if state.get("error"):
        return "end"
    if state.get("vector_store"):
        return "match"
    return "end"


def create_dag() -> StateGraph:
    """
    Create the main DAG workflow.
    
    Flow:
    user_query -> company_resolver -> sec_fetcher -> embedder -> solution_matcher -> END
    
    Returns:
        Compiled StateGraph
    """
    # Define the graph
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("company_resolver", company_resolver_node)
    workflow.add_node("sec_fetcher", sec_fetcher_node)
    workflow.add_node("embedder", embedder_node)
    workflow.add_node("solution_matcher", solution_matcher_node)
    
    # Set entry point
    workflow.set_entry_point("company_resolver")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "company_resolver",
        should_continue_after_resolver,
        {
            "fetch": "sec_fetcher",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "sec_fetcher",
        should_continue_after_fetcher,
        {
            "embed": "embedder",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "embedder",
        should_continue_after_embedder,
        {
            "match": "solution_matcher",
            "end": END
        }
    )
    
    # Final edge to END
    workflow.add_edge("solution_matcher", END)
    
    # Compile
    app = workflow.compile()
    
    logger.info("Main DAG workflow compiled successfully")
    return app


# Create singleton instance
dag_app = create_dag()
