"""
Solution Matcher Subgraph - orchestrates the agentic matching workflow.
"""
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator

from .problem_miner import problem_miner_node
from .product_retriever import product_retriever_node
from .fit_scorer import fit_scorer_node
from .objection_handler import objection_handler_node
from .pitch_writer import pitch_writer_node
from ...utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


class SolutionMatcherState(TypedDict):
    """State for solution matcher subgraph."""
    # Input
    vector_store: Any
    user_query: str
    company: str
    config: Dict[str, Any]
    
    # Intermediate results
    pains: list
    candidate_products: list
    matches: list
    objections: list
    pitch: Dict[str, Any]
    
    # Metadata
    citations: list
    trace: list
    error: str
    
    # Referee control
    iteration: int
    needs_revision: bool
    revision_feedback: str


def referee_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Referee guard that validates outputs and enforces quality standards.
    
    Checks:
    - Minimum confidence on pains
    - Citations present
    - At least one match found
    - Pitch references 10-K quotes
    
    Args:
        state: Current state
    
    Returns:
        Updated state with validation results
    """
    config = state.get("config", {})
    iteration = state.get("iteration", 0)
    max_iterations = config.get("max_iterations", 3)
    min_confidence = config.get("min_confidence", 0.6)
    
    logger.info(f"Referee validating iteration {iteration}")
    
    # Check if we've exceeded max iterations
    if iteration >= max_iterations:
        logger.warning("Max iterations reached, accepting current state")
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "Referee",
            "max_iterations",
            "Maximum iterations reached, completing workflow",
            {"iteration": iteration}
        ).to_dict())
        
        return {
            **state,
            "needs_revision": False,
            "trace": trace
        }
    
    # Validation checks
    issues = []
    
    # Check pains have sufficient confidence
    pains = state.get("pains", [])
    if pains:
        low_conf_pains = [p for p in pains if p.get("confidence", 0) < min_confidence]
        if len(low_conf_pains) == len(pains):
            issues.append("All pain points have low confidence")
    else:
        issues.append("No pain points identified")
    
    # Check citations exist
    citations = state.get("citations", [])
    if not citations:
        issues.append("No citations provided")
    
    # Check matches exist
    matches = state.get("matches", [])
    if not matches:
        issues.append("No product matches found")
    
    # Check pitch has 10-K quotes
    pitch = state.get("pitch")
    if pitch:
        key_quotes = pitch.get("key_quotes", [])
        if not key_quotes:
            issues.append("Pitch does not reference 10-K quotes")
    
    # Determine if revision needed
    if issues:
        logger.warning(f"Referee found {len(issues)} issues: {issues}")
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "Referee",
            "validation_failed",
            f"Found {len(issues)} issues, requesting revision",
            {"issues": issues, "iteration": iteration}
        ).to_dict())
        
        return {
            **state,
            "needs_revision": True,
            "revision_feedback": "; ".join(issues),
            "iteration": iteration + 1,
            "trace": trace
        }
    
    # All checks passed
    logger.info("Referee validation passed")
    trace = state.get("trace", [])
    trace.append(log_trace_event(
        logger,
        "Referee",
        "validation_passed",
        "All quality checks passed",
        {"iteration": iteration}
    ).to_dict())
    
    return {
        **state,
        "needs_revision": False,
        "trace": trace
    }


def should_revise(state: Dict[str, Any]) -> str:
    """Decide if revision is needed."""
    if state.get("needs_revision", False):
        return "revise"
    return "end"


def create_solution_matcher_subgraph() -> StateGraph:
    """
    Create the solution matcher subgraph workflow.
    
    Returns:
        Compiled StateGraph
    """
    # Define the graph
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("problem_miner", problem_miner_node)
    workflow.add_node("product_retriever", product_retriever_node)
    workflow.add_node("fit_scorer", fit_scorer_node)
    workflow.add_node("objection_handler", objection_handler_node)
    workflow.add_node("pitch_writer", pitch_writer_node)
    workflow.add_node("referee", referee_node)
    
    # Define edges
    workflow.set_entry_point("problem_miner")
    workflow.add_edge("problem_miner", "product_retriever")
    workflow.add_edge("product_retriever", "fit_scorer")
    workflow.add_edge("fit_scorer", "objection_handler")
    workflow.add_edge("objection_handler", "pitch_writer")
    workflow.add_edge("pitch_writer", "referee")
    
    # Conditional edge from referee
    workflow.add_conditional_edges(
        "referee",
        should_revise,
        {
            "revise": "problem_miner",  # Loop back for revision
            "end": END
        }
    )
    
    # Compile
    app = workflow.compile()
    
    logger.info("Solution matcher subgraph compiled")
    return app


# Wrapper function for use in main DAG
async def solution_matcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the full solution matcher subgraph.
    
    Args:
        state: Graph state with vector_store
    
    Returns:
        Updated state with all solution matcher results
    """
    logger.info("Starting solution matcher subgraph")
    
    # Initialize iteration counter
    subgraph_state = {
        **state,
        "iteration": 0,
        "needs_revision": False,
        "revision_feedback": ""
    }
    
    # Create and run subgraph
    subgraph = create_solution_matcher_subgraph()
    
    # Run the subgraph
    result = await subgraph.ainvoke(subgraph_state)
    
    logger.info("Solution matcher subgraph completed")
    
    return result
