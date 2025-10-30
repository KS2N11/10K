"""
Extended API routes for batch processing and database operations.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
from pathlib import Path
import json

from src.database.database import get_db_session
from src.database.repository import (
    CompanyRepository, AnalysisRepository, ProductMatchRepository,
    PitchRepository, MetricsRepository
)
from src.database.models import MarketCap
from src.services.batch_analysis import BatchAnalysisService
from src.utils.logging import get_logger
from src.api.routes import load_config
from src.utils.catalog_parser import parse_product_catalog, save_product_catalog, merge_product_catalogs
from src.utils.multi_llm import MultiProviderLLM

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2", tags=["v2"])

# Global batch service
_batch_service = None


def get_batch_service() -> BatchAnalysisService:
    """Get or create batch analysis service."""
    global _batch_service
    if _batch_service is None:
        config = load_config()
        _batch_service = BatchAnalysisService(config)
    return _batch_service


# Request/Response Models
class BatchAnalysisRequest(BaseModel):
    """Request model for batch analysis."""
    company_names: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 50
    force_reanalyze: bool = False  # Force re-analysis even if company already analyzed
    selected_companies: Optional[List[Dict[str, str]]] = None  # List of {cik, ticker, name} dicts


class BatchAnalysisResponse(BaseModel):
    """Response model for batch analysis."""
    job_id: str
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    total_companies: int
    completed: int
    failed: int
    skipped: int
    current_company: Optional[str]
    current_step: Optional[str]
    estimated_time_remaining: Optional[float]
    total_tokens: int
    started_at: Optional[str]
    completed_at: Optional[str]


class CompanySearchRequest(BaseModel):
    """Request model for company search."""
    query: Optional[str] = None
    market_cap: Optional[List[str]] = None
    industry: Optional[List[str]] = None
    sector: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0


# Endpoints
@router.post("/analysis/batch", response_model=BatchAnalysisResponse)
async def start_batch_analysis(
    request: BatchAnalysisRequest,
    service: BatchAnalysisService = Depends(get_batch_service)
):
    """
    Start a batch analysis job for multiple companies.
    
    Args:
        request: Batch analysis request with company names, filters, or selected companies
    
    Returns:
        Job ID for tracking progress
    """
    logger.info(f"🎯 BATCH ANALYSIS REQUEST RECEIVED: {request}")
    print(f"🎯 BATCH ANALYSIS REQUEST RECEIVED: {request}")
    
    try:
        # If selected_companies provided, extract names
        company_names = request.company_names
        if request.selected_companies:
            company_names = [c.get("name") or c.get("ticker") for c in request.selected_companies]
            logger.info(f"Analyzing {len(company_names)} selected companies: {company_names}")
        
        job_id = await service.start_batch_job(
            company_names=company_names,
            filters=request.filters,
            limit=request.limit,
            force_reanalyze=request.force_reanalyze
        )
        
        return BatchAnalysisResponse(
            job_id=job_id,
            message=f"Batch job started successfully. Track progress at /api/v2/analysis/status/{job_id}"
        )
    
    except Exception as e:
        logger.error(f"Error starting batch analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    service: BatchAnalysisService = Depends(get_batch_service)
):
    """
    Get status of a batch analysis job.
    
    Args:
        job_id: Job UUID
    
    Returns:
        Job status with progress information
    """
    try:
        status = await service.get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return JobStatusResponse(**status)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/jobs")
def get_all_jobs(
    limit: int = Query(20, description="Number of jobs to return"),
    include_completed: bool = Query(False, description="Include completed jobs"),
    db: Session = Depends(get_db_session)
):
    """
    Get all recent analysis jobs (active and optionally completed).
    
    Args:
        limit: Maximum number of jobs to return
        include_completed: Whether to include completed jobs
        db: Database session
    
    Returns:
        List of job IDs and their status
    """
    try:
        from src.database.models import AnalysisJob, AnalysisStatus
        from datetime import datetime, timedelta
        
        query = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc())
        
        if not include_completed:
            # Only return active jobs (QUEUED or IN_PROGRESS)
            query = query.filter(AnalysisJob.status.in_([
                AnalysisStatus.QUEUED,
                AnalysisStatus.IN_PROGRESS
            ]))
        else:
            # Return jobs from last 24 hours
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            query = query.filter(AnalysisJob.created_at >= one_day_ago)
        
        jobs = query.limit(limit).all()
        
        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "total_companies": job.total_companies,
                    "completed": job.completed_count,
                    "failed": job.failed_count,
                    "skipped": job.skipped_count,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                }
                for job in jobs
            ],
            "count": len(jobs)
        }
    
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companies/search")
def search_companies(
    request: CompanySearchRequest,
    db: Session = Depends(get_db_session)
):
    """
    Search companies in database with filters.
    
    Args:
        request: Search request with filters
        db: Database session
    
    Returns:
        List of matching companies
    """
    try:
        # Convert string market caps to enum (case-insensitive)
        market_cap_enum = None
        if request.market_cap:
            market_cap_enum = [MarketCap(mc.upper()) for mc in request.market_cap]
        
        companies = CompanyRepository.search(
            db,
            query=request.query,
            market_cap=market_cap_enum,
            industry=request.industry,
            sector=request.sector,
            limit=request.limit,
            offset=request.offset
        )
        
        return {
            "companies": [
                {
                    "id": c.id,
                    "cik": c.cik,
                    "name": c.name,
                    "ticker": c.ticker,
                    "industry": c.industry,
                    "sector": c.sector,
                    "market_cap": c.market_cap.value if c.market_cap else None
                }
                for c in companies
            ],
            "count": len(companies)
        }
    
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companies/search-sec")
async def search_sec_companies(
    request: CompanySearchRequest,
    use_realtime: bool = Query(False, description="Use real-time market cap lookup (slower, covers all 14k+ companies)")
):
    """
    Search companies from SEC EDGAR database with filters.
    This searches the SEC's live database, not our local database.
    
    Args:
        request: Search request with market cap, industry, sector filters
        use_realtime: If true, uses Yahoo Finance API for ALL 14k+ companies (slower).
                     If false, uses static mapping of ~100 companies (faster).
    
    Returns:
        List of companies from SEC matching the criteria
    
    Note: Real-time lookup can take 1-3 minutes depending on the number of companies.
    """
    try:
        from src.utils.sec_filter import SECCompanyFilter
        config = load_config()
        
        # Initialize SEC filter
        sec_filter = SECCompanyFilter(config.get("sec_user_agent"))
        
        # Limit to prevent timeouts
        actual_limit = min(request.limit or 100, 100)
        
        # OPTIMIZATION: For small queries, suggest static mode
        if use_realtime and actual_limit <= 20:
            logger.info(f"Small query ({actual_limit} companies) with real-time - suggesting static mode")
        
        logger.info(f"Searching SEC companies: market_cap={request.market_cap}, limit={actual_limit}, realtime={use_realtime}")
        
        # Search SEC database
        companies = await sec_filter.search_companies(
            market_cap=request.market_cap,
            industry=request.industry,
            sector=request.sector,
            limit=actual_limit,
            use_realtime_lookup=use_realtime
        )
        
        logger.info(f"Found {len(companies)} companies")
        
        return {
            "companies": companies,
            "count": len(companies),
            "source": "SEC EDGAR",
            "lookup_method": "real-time" if use_realtime else "static (~100 companies)",
            "note": "For queries under 20 companies, static mode is faster" if use_realtime and actual_limit <= 20 else None
        }
    
    except Exception as e:
        logger.error(f"Error searching SEC companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/search-by-name")
async def search_company_by_name(
    query: str = Query(..., description="Company name or ticker to search"),
    limit: int = Query(20, description="Maximum number of results")
):
    """
    Search for companies by name or ticker in SEC database.
    Returns all companies matching the query.
    
    Args:
        query: Company name or ticker to search (e.g., "Apple", "AAPL")
        limit: Maximum number of results to return
    
    Returns:
        List of matching companies with cik, ticker, name
    """
    try:
        from src.utils.sec_filter import SECCompanyFilter
        config = load_config()
        
        # Initialize SEC filter
        sec_filter = SECCompanyFilter(config.get("sec_user_agent"))
        
        # Search by name/ticker
        companies = await sec_filter.search_company_by_name(query, limit)
        
        return {
            "companies": companies,
            "count": len(companies),
            "query": query,
            "source": "SEC EDGAR"
        }
    
    except Exception as e:
        logger.error(f"Error searching company by name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/analysis")
def get_company_analysis(
    company_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Get latest analysis for a company.
    
    Args:
        company_id: Company database ID
        db: Database session
    
    Returns:
        Analysis details with pain points and matches
    """
    try:
        # Get latest analysis
        analysis = AnalysisRepository.get_latest_for_company(db, company_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"No analysis found for company {company_id}")
        
        # Get related data
        pain_points = [
            {
                "id": p.id,
                "theme": p.theme,
                "rationale": p.rationale,
                "confidence": p.confidence,
                "quotes": p.quotes,
                "category": p.category
            }
            for p in analysis.pain_points
        ]
        
        product_matches = [
            {
                "id": m.id,
                "product_id": m.product_id,
                "product_name": m.product_name,
                "fit_score": m.fit_score,
                "why_fits": m.why_fits,
                "evidence": m.evidence
            }
            for m in analysis.product_matches
        ]
        
        pitches = [
            {
                "id": p.id,
                "persona": p.persona,
                "subject": p.subject,
                "body": p.body,
                "overall_score": p.overall_score
            }
            for p in analysis.pitches
        ]
        
        return {
            "analysis": {
                "id": analysis.id,
                "company_id": analysis.company_id,
                "company_name": analysis.company.name,
                "filing_date": analysis.filing_date.isoformat(),
                "accession_number": analysis.accession_number,
                "filing_path": analysis.filing_path,  # Add filing path for document viewing
                "status": analysis.status.value,
                "time_taken_seconds": analysis.time_taken_seconds,
                "total_tokens_used": analysis.total_tokens_used,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
            },
            "pain_points": pain_points,
            "product_matches": product_matches,
            "pitches": pitches
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyses/all")
def get_all_analyses(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session)
):
    """
    Get all completed analyses.
    
    Args:
        limit: Max results
        offset: Pagination offset
        db: Database session
    
    Returns:
        List of analyses with company info
    """
    try:
        analyses = AnalysisRepository.get_all_completed(db, limit=limit, offset=offset)
        
        return {
            "analyses": [
                {
                    "id": a.id,
                    "company_id": a.company_id,
                    "company_name": a.company.name,
                    "company_ticker": a.company.ticker,
                    "company_cik": a.company.cik,
                    "filing_date": a.filing_date.isoformat(),
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "pain_points_count": len(a.pain_points),
                    "matches_count": len(a.product_matches),
                    "top_match_score": max((m.fit_score for m in a.product_matches), default=0)
                }
                for a in analyses
            ],
            "count": len(analyses)
        }
    
    except Exception as e:
        logger.error(f"Error getting analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pitches/top")
def get_top_pitches(
    min_score: int = Query(75, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_session)
):
    """
    Get top-scoring pitches across all companies.
    
    Args:
        min_score: Minimum score threshold
        limit: Max results
        db: Database session
    
    Returns:
        List of top pitches
    """
    try:
        pitches = PitchRepository.get_top_pitches(db, min_score=min_score, limit=limit)
        
        return {
            "pitches": [
                {
                    "id": p.id,
                    "company_name": p.analysis.company.name,
                    "company_ticker": p.analysis.company.ticker,
                    "persona": p.persona,
                    "subject": p.subject,
                    "body": p.body,
                    "overall_score": p.overall_score,
                    "product_id": p.product_match.product_id,
                    "product_name": p.product_match.product_name,
                    "created_at": p.created_at.isoformat()
                }
                for p in pitches
            ],
            "count": len(pitches)
        }
    
    except Exception as e:
        logger.error(f"Error getting top pitches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/summary")
def get_metrics_summary(
    db: Session = Depends(get_db_session)
):
    """
    Get system-wide metrics summary.
    
    Returns:
        Metrics dashboard data
    """
    try:
        metrics = MetricsRepository.get_current_metrics(db)
        return metrics
    
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filings/{company_id}/document", response_class=HTMLResponse)
def get_filing_document(
    company_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Get the 10-K filing HTML document for a company.
    
    Args:
        company_id: Company database ID
        db: Database session
    
    Returns:
        HTML content of the 10-K filing
    """
    try:
        # Get latest analysis for company
        analysis = AnalysisRepository.get_latest_for_company(db, company_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"No analysis found for company {company_id}")
        
        if not analysis.filing_path:
            raise HTTPException(status_code=404, detail=f"No filing document available for this company")
        
        # Construct full file path
        filing_path = Path(analysis.filing_path)
        
        # Check if file exists
        if not filing_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Filing document not found at path: {analysis.filing_path}"
            )
        
        # Read and return HTML content
        with open(filing_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving filing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Product Catalog Management
class CatalogUploadRequest(BaseModel):
    """Request model for catalog text upload."""
    text_content: str
    company_name: Optional[str] = "Your Company"
    merge_with_existing: bool = False


@router.post("/catalog/upload")
async def upload_product_catalog(request: CatalogUploadRequest):
    """
    Parse and upload product catalog from text.
    
    Args:
        request: Text content describing products/services
    
    Returns:
        Parsed products and save status
    """
    try:
        # Initialize LLM
        config = load_config()
        llm_manager = MultiProviderLLM(config=config)
        
        # Parse products from text
        logger.info(f"Parsing catalog for {request.company_name}")
        products = await parse_product_catalog(
            request.text_content,
            llm_manager,
            request.company_name
        )
        
        if not products:
            raise HTTPException(
                status_code=400,
                detail="No valid products found in the provided text"
            )
        
        # Merge with existing if requested
        if request.merge_with_existing:
            catalog_path = Path("src/knowledge/products.json")
            if catalog_path.exists():
                with open(catalog_path, "r") as f:
                    existing_products = json.load(f)
                products = await merge_product_catalogs(products, existing_products)
        
        # Save to file
        saved_path = await save_product_catalog(products, backup=True)
        
        # Invalidate catalog cache (force reload)
        # Note: This will be picked up on next analysis
        logger.info("✅ Product catalog updated successfully")
        
        return {
            "success": True,
            "products_count": len(products),
            "products": products,
            "saved_to": saved_path,
            "message": f"Successfully parsed and saved {len(products)} products"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/current")
async def get_current_catalog():
    """
    Get the current product catalog.
    
    Returns:
        List of products in the catalog
    """
    try:
        catalog_path = Path("src/knowledge/products.json")
        
        if not catalog_path.exists():
            return {"products": [], "count": 0}
        
        with open(catalog_path, "r") as f:
            products = json.load(f)
        
        return {
            "products": products,
            "count": len(products)
        }
    
    except Exception as e:
        logger.error(f"Error reading catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/catalog/products/{product_id}")
async def delete_product(product_id: str):
    """
    Delete a product from the catalog.
    
    Args:
        product_id: Product ID to delete
    
    Returns:
        Success status
    """
    try:
        catalog_path = Path("src/knowledge/products.json")
        
        if not catalog_path.exists():
            raise HTTPException(status_code=404, detail="Catalog not found")
        
        with open(catalog_path, "r") as f:
            products = json.load(f)
        
        # Filter out the product
        filtered = [p for p in products if p.get("product_id") != product_id]
        
        if len(filtered) == len(products):
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        
        # Save updated catalog
        await save_product_catalog(filtered, backup=True)
        
        return {
            "success": True,
            "message": f"Product {product_id} deleted",
            "remaining_count": len(filtered)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        raise HTTPException(status_code=500, detail=str(e))
