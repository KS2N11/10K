"""
State definitions and schemas for 10-Q analysis pipeline.
"""
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TenQState(TypedDict):
    """State for the 10-Q analysis workflow."""
    company_name: str
    cik: Optional[str]
    filing_metadata: Optional[Dict[str, Any]]
    filing_content: Optional[str]
    parsed_sections: Optional[Dict[str, str]]
    embeddings: Optional[List[Any]]
    pain_points: Optional[List[Dict[str, Any]]]
    matched_solutions: Optional[List[Dict[str, Any]]]
    insights: Optional[List[Dict[str, Any]]]
    error: Optional[str]


class PainPoint(BaseModel):
    """Represents a business pain point extracted from 10-Q."""
    category: str = Field(description="Category of pain point (e.g., 'revenue_decline', 'operational_challenges', 'market_risks')")
    description: str = Field(description="Detailed description of the pain point")
    severity: str = Field(description="Severity level: low, medium, high, critical")
    evidence: str = Field(description="Direct quote or evidence from 10-Q")
    quarter: str = Field(description="Fiscal quarter this pain point relates to")


class Solution(BaseModel):
    """Represents a product/service solution from catalog."""
    id: str = Field(description="Unique solution ID")
    name: str = Field(description="Solution name")
    category: str = Field(description="Solution category")
    description: str = Field(description="Detailed description of the solution")
    pain_points_addressed: List[str] = Field(description="List of pain point categories this solution addresses")
    value_proposition: str = Field(description="Key value proposition")


class MatchedSolution(BaseModel):
    """Represents a solution matched to a pain point."""
    pain_point: PainPoint
    solution: Solution
    relevance_score: float = Field(description="Relevance score (0-1)")
    matching_rationale: str = Field(description="Why this solution matches the pain point")


class Insight(BaseModel):
    """Represents a sales insight generated from matched solutions."""
    company_name: str
    quarter: str
    pain_point_summary: str
    recommended_solution: str
    value_proposition: str
    engagement_strategy: str = Field(description="Suggested approach for sales engagement")
    priority: str = Field(description="Priority level: low, medium, high, urgent")
    estimated_opportunity: Optional[str] = Field(default=None, description="Estimated opportunity size if available")
