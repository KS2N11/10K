"""
LangGraph DAG for 10-Q analysis pipeline.
"""
from langgraph.graph import StateGraph, END
from .schemas import TenQState
from .nodes import (
    fetch_10q_node,
    parse_10q_node,
    embed_content_node,
    extract_pain_points_node,
    match_solutions_node,
    generate_insights_node
)
from ..utils.logging import setup_logger

logger = setup_logger(__name__)


def should_continue(state: TenQState) -> str:
    """Determine if pipeline should continue or end."""
    if state.get("error"):
        logger.error(f"Pipeline error: {state['error']}")
        return END
    return "continue"


def create_10q_workflow() -> StateGraph:
    """Create the 10-Q analysis workflow."""
    workflow = StateGraph(TenQState)
    
    # Add nodes
    workflow.add_node("fetch_10q", fetch_10q_node)
    workflow.add_node("parse_10q", parse_10q_node)
    workflow.add_node("embed_content", embed_content_node)
    workflow.add_node("extract_pain_points", extract_pain_points_node)
    workflow.add_node("match_solutions", match_solutions_node)
    workflow.add_node("generate_insights", generate_insights_node)
    
    # Define edges
    workflow.set_entry_point("fetch_10q")
    
    workflow.add_edge("fetch_10q", "parse_10q")
    workflow.add_edge("parse_10q", "embed_content")
    workflow.add_edge("embed_content", "extract_pain_points")
    workflow.add_edge("extract_pain_points", "match_solutions")
    workflow.add_edge("match_solutions", "generate_insights")
    workflow.add_edge("generate_insights", END)
    
    return workflow.compile()


async def analyze_10q(company_name: str) -> TenQState:
    """
    Run complete 10-Q analysis for a company.
    
    Args:
        company_name: Name of the company to analyze
        
    Returns:
        Final state with insights
    """
    logger.info(f"🚀 Starting 10-Q analysis for {company_name}")
    
    # Create initial state
    initial_state: TenQState = {
        "company_name": company_name,
        "cik": None,
        "filing_metadata": None,
        "filing_content": None,
        "parsed_sections": None,
        "embeddings": None,
        "pain_points": None,
        "matched_solutions": None,
        "insights": None,
        "error": None
    }
    
    # Create and run workflow
    workflow = create_10q_workflow()
    
    final_state = await workflow.ainvoke(initial_state)
    
    logger.info(f"✅ 10-Q analysis complete for {company_name}")
    
    return final_state
