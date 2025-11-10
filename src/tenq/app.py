"""
FastAPI application for 10-Q Analysis Microservice.
Standalone service that can be deployed separately from the 10-K application.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio

from .dag import analyze_10q
from ..utils.logging import setup_logger

logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="10-Q Analysis API",
    description="Microservice for analyzing quarterly reports (10-Q) and generating sales insights",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request model for 10-Q analysis."""
    company_name: str


class PainPointResponse(BaseModel):
    """Response model for a pain point."""
    category: str
    description: str
    severity: str
    evidence: str
    quarter: str


class SolutionResponse(BaseModel):
    """Response model for a matched solution."""
    solution_name: str
    solution_category: str
    value_proposition: str
    relevance_score: float
    matching_rationale: str


class InsightResponse(BaseModel):
    """Response model for a sales insight."""
    company_name: str
    quarter: str
    pain_point_summary: str
    recommended_solution: str
    value_proposition: str
    engagement_strategy: str
    priority: str
    relevance_score: Optional[float] = None


class AnalysisResponse(BaseModel):
    """Response model for complete 10-Q analysis."""
    company_name: str
    cik: Optional[str] = None
    filing_date: Optional[str] = None
    reporting_date: Optional[str] = None
    pain_points: List[PainPointResponse]
    matched_solutions: List[SolutionResponse]
    insights: List[InsightResponse]
    error: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "10-Q Analysis API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_company(request: AnalysisRequest):
    """
    Analyze a company's latest 10-Q filing and generate sales insights.
    
    Args:
        request: Analysis request with company name
        
    Returns:
        Complete analysis with pain points, matched solutions, and insights
    """
    try:
        logger.info(f"Received analysis request for: {request.company_name}")
        
        # Run the analysis
        result = await analyze_10q(request.company_name)
        
        # Check for errors
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Extract metadata
        filing_metadata = result.get("filing_metadata", {})
        
        # Format pain points
        pain_points = []
        for pp in result.get("pain_points", []):
            pain_points.append(PainPointResponse(
                category=pp.get("category", ""),
                description=pp.get("description", ""),
                severity=pp.get("severity", ""),
                evidence=pp.get("evidence", ""),
                quarter=pp.get("quarter", "")
            ))
        
        # Format matched solutions
        matched_solutions = []
        for match in result.get("matched_solutions", []):
            solution = match.get("solution", {})
            matched_solutions.append(SolutionResponse(
                solution_name=solution.get("name", ""),
                solution_category=solution.get("category", ""),
                value_proposition=solution.get("value_proposition", ""),
                relevance_score=match.get("relevance_score", 0.0),
                matching_rationale=match.get("matching_rationale", "")
            ))
        
        # Format insights
        insights = []
        for insight in result.get("insights", []):
            insights.append(InsightResponse(
                company_name=insight.get("company_name", ""),
                quarter=insight.get("quarter", ""),
                pain_point_summary=insight.get("pain_point_summary", ""),
                recommended_solution=insight.get("recommended_solution", ""),
                value_proposition=insight.get("value_proposition", ""),
                engagement_strategy=insight.get("engagement_strategy", ""),
                priority=insight.get("priority", ""),
                relevance_score=insight.get("relevance_score")
            ))
        
        return AnalysisResponse(
            company_name=request.company_name,
            cik=result.get("cik"),
            filing_date=filing_metadata.get("file_date"),
            reporting_date=filing_metadata.get("reporting_date"),
            pain_points=pain_points,
            matched_solutions=matched_solutions,
            insights=insights
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
