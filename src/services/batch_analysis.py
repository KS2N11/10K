"""
Batch analysis service for processing multiple companies.
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.repository import (
    CompanyRepository, AnalysisRepository, PainPointRepository,
    ProductMatchRepository, PitchRepository, AnalysisJobRepository
)
from src.database.models import AnalysisStatus, MarketCap, PainPoint
from src.utils.catalog import get_catalog_hash
from src.utils.sec_filter import get_companies_by_names, SECCompanyFilter
from src.utils.logging import get_logger
from src.graph.dag import create_dag
from src.utils.multi_llm import MultiProviderLLM
from src.utils.multi_embeddings import MultiProviderEmbeddings

logger = get_logger(__name__)


class BatchAnalysisService:
    """Service for batch processing multiple company analyses."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize batch analysis service.
        
        Args:
            config: Configuration dict with API keys, settings
        """
        self.config = config
        self.llm_manager = None
        self.embedder = None
    
    async def _init_providers(self):
        """Initialize LLM and embedding providers if not already done."""
        if not self.llm_manager:
            self.llm_manager = MultiProviderLLM(config=self.config)
        
        if not self.embedder:
            self.embedder = MultiProviderEmbeddings(config=self.config)
    
    async def start_batch_job(
        self,
        company_names: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        force_reanalyze: bool = False
    ) -> str:
        """
        Start a batch analysis job.
        
        Args:
            company_names: List of specific company names to analyze
            filters: Dict with market_cap, industry, sector filters
            limit: Max number of companies to analyze
            force_reanalyze: Force re-analysis even if company already analyzed
        
        Returns:
            Job ID (UUID string)
        """
        job_id = str(uuid.uuid4())
        
        with get_db() as db:
            # Get companies to analyze
            companies_to_process = []
            
            if company_names:
                # Search by specific names
                logger.info(f"Searching for {len(company_names)} companies by name")
                companies_to_process = await get_companies_by_names(
                    company_names,
                    self.config.get("sec_user_agent")
                )
            
            elif filters:
                # Search by filters
                logger.info(f"Searching companies with filters: {filters}")
                sec_filter = SECCompanyFilter(self.config.get("sec_user_agent"))
                companies_to_process = await sec_filter.search_companies(
                    market_cap=filters.get("market_cap"),
                    industry=filters.get("industry"),
                    sector=filters.get("sector"),
                    limit=limit
                )
            
            # Create job record
            job = AnalysisJobRepository.create(
                db,
                job_id=job_id,
                filters=filters,
                company_names=company_names,
                total_companies=len(companies_to_process),
                status=AnalysisStatus.QUEUED
            )
            
            logger.info(f"Created batch job {job_id} with {len(companies_to_process)} companies")
        
        # Start async processing (don't await - run in background)
        asyncio.create_task(self._process_batch(job_id, companies_to_process, force_reanalyze))
        
        return job_id
    
    async def _process_batch(
        self,
        job_id: str,
        companies: List[Dict[str, str]],
        force_reanalyze: bool = False
    ):
        """
        Process batch of companies (runs in background).
        
        Args:
            job_id: Job UUID
            companies: List of company dicts with cik, name, ticker
            force_reanalyze: Force re-analysis even if company already analyzed
        """
        await self._init_providers()
        
        with get_db() as db:
            # Update job status
            AnalysisJobRepository.update_progress(
                db,
                job_id,
                status=AnalysisStatus.IN_PROGRESS,
                started_at=datetime.utcnow()
            )
        
        completed = 0
        failed = 0
        skipped = 0
        total_tokens = 0
        start_time = datetime.utcnow()
        
        for i, company_data in enumerate(companies):
            try:
                # Update job progress first
                with get_db() as db:
                    remaining = len(companies) - i
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    avg_time = elapsed / max(i, 1)
                    eta = avg_time * remaining
                    
                    AnalysisJobRepository.update_progress(
                        db,
                        job_id,
                        current_company=company_data.get("name"),
                        current_step="Initializing",
                        estimated_time_remaining=eta
                    )
                
                # Get or create company and check if analysis needed
                company_id = None
                should_analyze = True
                
                with get_db() as db:
                    # Get or create company
                    company = CompanyRepository.get_or_create(
                        db,
                        cik=company_data.get("cik"),
                        name=company_data.get("name"),
                        ticker=company_data.get("ticker")
                    )
                    company_id = company.id
                    
                    # Check if analysis needed (caching logic)
                    catalog_hash = get_catalog_hash()
                    
                    # Check if company was already analyzed (unless force_reanalyze is True)
                    if not force_reanalyze:
                        latest_analysis = AnalysisRepository.get_latest_for_company(db, company.id)
                        if latest_analysis and latest_analysis.status == AnalysisStatus.COMPLETED:
                            # Check if re-analysis is needed
                            # Only skip if analysis exists for same catalog AND has actual data
                            if latest_analysis.catalog_hash == catalog_hash:
                                # Check if analysis has actual pain points (not empty)
                                pain_count = db.query(PainPoint).filter(
                                    PainPoint.analysis_id == latest_analysis.id
                                ).count()
                                
                                if pain_count > 0:
                                    logger.info(f"⏭️  Skipping {company.name} - already analyzed with current catalog ({pain_count} pain points)")
                                    skipped += 1
                                    should_analyze = False
                                else:
                                    logger.warning(f"🔄 Re-analyzing {company.name} - previous analysis had no pain points")
                    else:
                        logger.info(f"🔄 Force re-analyzing {company.name}")
                
                # Update progress
                with get_db() as db:
                    AnalysisJobRepository.update_progress(
                        db,
                        job_id,
                        completed_count=completed,
                        failed_count=failed,
                        skipped_count=skipped,
                        total_tokens_used=total_tokens
                    )
                
                if not should_analyze:
                    continue
                    
                # Run analysis (this is the long-running part)
                result = await self._analyze_company(
                    job_id,
                    company_id,
                    company_data.get("cik"),
                    company_data.get("name"),
                    catalog_hash
                )
                
                if result["status"] == "completed":
                    completed += 1
                    total_tokens += result.get("tokens_used", 0)
                elif result["status"] == "skipped":
                    skipped += 1
                else:
                    failed += 1
                
                # Update job progress
                with get_db() as db:
                    AnalysisJobRepository.update_progress(
                        db,
                        job_id,
                        completed_count=completed,
                        failed_count=failed,
                        skipped_count=skipped,
                        total_tokens_used=total_tokens
                    )
            
            except Exception as e:
                logger.error(f"Error processing company {company_data.get('name')}: {e}")
                failed += 1
        
        # Mark job as completed
        with get_db() as db:
            total_time = (datetime.utcnow() - start_time).total_seconds()
            AnalysisJobRepository.update_progress(
                db,
                job_id,
                status=AnalysisStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                total_time_seconds=total_time,
                current_company=None,
                current_step="Completed"
            )
        
        logger.info(f"Batch job {job_id} completed: {completed} succeeded, {failed} failed, {skipped} skipped")
    
    async def _analyze_company(
        self,
        job_id: str,
        company_id: int,
        cik: str,
        company_name: str,
        catalog_hash: str
    ) -> Dict[str, Any]:
        """
        Analyze a single company.
        
        Args:
            job_id: Parent job ID
            company_id: Company database ID
            cik: Company CIK
            company_name: Company name
            catalog_hash: Current catalog hash
        
        Returns:
            Result dict with status, tokens_used, etc.
        """
        try:
            # Track analysis start time
            analysis_start_time = datetime.utcnow()
            
            # Update job current step
            with get_db() as db:
                AnalysisJobRepository.update_progress(
                    db,
                    job_id,
                    current_step="Fetching 10-K"
                )
            
            # Build DAG
            dag_app = create_dag()
            
            # Prepare initial state
            # NOTE: Not passing llm_manager/embedder as they're not hashable
            # Nodes will create them from config instead
            initial_state = {
                "user_query": f"Analyze {company_name}'s latest 10-K and map to our catalog",
                "config": self.config,
                "company": company_name,
                "cik": cik,
                "trace": []
            }
            
            # Check if re-analysis needed
            # This will be handled by the enhanced sec_fetcher and embedder nodes
            
            # Run DAG
            logger.info(f"Starting analysis for {company_name}")
            try:
                result = await dag_app.ainvoke(initial_state)
            except Exception as dag_error:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"DAG execution failed for {company_name}: {error_details}")
                raise Exception(f"DAG execution error: {str(dag_error)}\n{error_details}")
            
            # Check if DAG returned an error state
            if "error" in result and result["error"]:
                error_msg = result["error"]
                logger.error(f"DAG returned error for {company_name}: {error_msg}")
                raise Exception(f"DAG execution error: {error_msg}")
            
            # Extract results
            filing_date_str = result.get("filing_date")
            filing_date = datetime.fromisoformat(filing_date_str) if filing_date_str else datetime.utcnow()
            accession = result.get("accession", "")
            # DAG returns "file_path", map to "filing_path" for database
            filing_path = result.get("filing_path") or result.get("file_path", "")
            
            # Check if skipped due to cache
            was_cached = result.get("used_cache", False)
            
            if was_cached:
                logger.info(f"Using cached analysis for {company_name}")
                return {"status": "skipped", "reason": "cached"}
            
            # Create analysis record
            analysis_id = None
            with get_db() as db:
                analysis = AnalysisRepository.create(
                    db,
                    company_id=company_id,
                    filing_date=filing_date,
                    accession_number=accession,
                    filing_path=filing_path,
                    status=AnalysisStatus.IN_PROGRESS,
                    started_at=analysis_start_time,  # Explicit start time
                    catalog_hash=catalog_hash,
                    used_cached_filing=result.get("cached_filing", False),
                    used_cached_embeddings=result.get("cached_embeddings", False)
                )
                analysis_id = analysis.id
            
            # Save pain points
            pains = result.get("pains", [])
            pain_objs = []
            if pains:
                with get_db() as db:
                    pain_data = [
                        {
                            "theme": p.get("theme", ""),
                            "rationale": p.get("rationale", ""),
                            "confidence": p.get("confidence", 0.0),
                            "quotes": p.get("quotes", [])
                        }
                        for p in pains
                    ]
                    pain_objs = PainPointRepository.create_bulk(db, analysis_id, pain_data)
            
            # Save product matches
            matches = result.get("matches", [])
            match_objs = []
            if matches:
                with get_db() as db:
                    # Create a mapping from pain theme to pain point ID
                    pain_theme_to_id = {p.theme: p.id for p in pain_objs} if pain_objs else {}
                    
                    match_data = []
                    for m in matches:
                        # Try to find matching pain point by theme
                        pain_theme = m.get("pain_theme", "")
                        pain_point_id = pain_theme_to_id.get(pain_theme)
                        
                        # Fallback to first pain point if theme not found
                        if not pain_point_id and pain_objs:
                            pain_point_id = pain_objs[0].id
                        
                        match_data.append({
                            "pain_point_id": pain_point_id,
                            "product_id": m.get("product_id", ""),
                            "product_name": m.get("product_name", m.get("product_id", "")),  # Use product_name if available
                            "fit_score": m.get("score", 0),
                            "why_fits": m.get("why", ""),
                            "evidence": m.get("evidence", []),
                            "potential_objections": m.get("objections", [])
                        })
                    
                    match_objs = ProductMatchRepository.create_bulk(db, analysis_id, match_data)
            
            # Save pitch
            pitch = result.get("pitch", {})
            if pitch and match_objs:
                with get_db() as db:
                    pitch_data = [
                        {
                            "analysis_id": analysis_id,
                            "product_match_id": match_objs[0].id,  # Top match
                            "persona": pitch.get("persona", "Executive"),
                            "subject": pitch.get("subject", ""),
                            "body": pitch.get("body", ""),
                            "key_quotes": pitch.get("key_quotes", []),
                            "overall_score": match_objs[0].fit_score
                        }
                    ]
                    PitchRepository.create_bulk(db, pitch_data)
            
            # Calculate time taken
            analysis_end_time = datetime.utcnow()
            time_taken = (analysis_end_time - analysis_start_time).total_seconds()
            
            # Validate that analysis actually produced results
            if not pains or len(pains) == 0:
                error_msg = f"Analysis completed but no pain points found for {company_name}. Filing may be malformed or LLM failed to extract data."
                logger.error(error_msg)
                
                # Mark as FAILED if no data extracted
                with get_db() as db:
                    AnalysisRepository.update_status(
                        db,
                        analysis_id,
                        AnalysisStatus.FAILED,
                        error_message=error_msg
                    )
                
                return {
                    "status": "failed",
                    "error": error_msg,
                    "analysis_id": analysis_id
                }
            
            # Calculate tokens (from trace or estimate)
            # Try to get tokens from trace events metadata/artifacts
            total_tokens = 0
            trace_events = result.get("trace", [])
            for event in trace_events:
                # Check metadata dict first
                if isinstance(event, dict):
                    total_tokens += event.get("metadata", {}).get("tokens", 0)
                    total_tokens += event.get("artifacts", {}).get("tokens", 0)
            
            # If no tokens tracked, estimate based on content length
            # Rough estimate: 1 token ≈ 4 characters
            if total_tokens == 0:
                # Estimate from pain points and matches text
                pains_text = str(result.get("pains", []))
                matches_text = str(result.get("matches", []))
                pitch_text = str(result.get("pitch", {}))
                total_chars = len(pains_text) + len(matches_text) + len(pitch_text)
                total_tokens = total_chars // 4
                logger.info(f"Estimated {total_tokens} tokens for {company_name} (no usage data from LLM)")
            
            # Update analysis as completed with metrics
            # Note: time_taken_seconds is calculated automatically by update_status
            # based on started_at and completed_at, but we can also set it explicitly
            with get_db() as db:
                AnalysisRepository.update_status(
                    db,
                    analysis_id,
                    AnalysisStatus.COMPLETED,
                    total_tokens_used=total_tokens
                )
            
            logger.info(f"✅ Completed analysis for {company_name} in {time_taken:.2f}s using {total_tokens} tokens - {len(pains)} pain points, {len(matches)} matches")
            
            return {
                "status": "completed",
                "tokens_used": total_tokens,
                "time_taken": time_taken,
                "analysis_id": analysis_id
            }
        
        except Exception as e:
            logger.error(f"Error analyzing {company_name}: {e}")
            
            # Create failed analysis record
            with get_db() as db:
                analysis = AnalysisRepository.create(
                    db,
                    company_id=company_id,
                    filing_date=datetime.utcnow(),
                    accession_number="",
                    status=AnalysisStatus.FAILED,
                    error_message=str(e),
                    catalog_hash=catalog_hash
                )
            
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a batch job.
        
        Args:
            job_id: Job UUID
        
        Returns:
            Job status dict or None if not found
        """
        with get_db() as db:
            job = AnalysisJobRepository.get_by_job_id(db, job_id)
            
            if not job:
                return None
            
            # Get recent errors from failed analyses in this job
            from src.database.models import Analysis
            recent_errors = db.query(Analysis).filter(
                Analysis.status == AnalysisStatus.FAILED,
                Analysis.created_at >= job.created_at
            ).order_by(Analysis.created_at.desc()).limit(5).all()
            
            error_details = []
            for analysis in recent_errors:
                if analysis.error_message:
                    # Get company name
                    company = CompanyRepository.get_by_id(db, analysis.company_id)
                    error_details.append({
                        "company": company.name if company else "Unknown",
                        "error": analysis.error_message[:200]  # Truncate long errors
                    })
            
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "total_companies": job.total_companies,
                "completed": job.completed_count,
                "failed": job.failed_count,
                "skipped": job.skipped_count,
                "current_company": job.current_company,
                "current_step": job.current_step,
                "estimated_time_remaining": job.estimated_time_remaining,
                "total_tokens": job.total_tokens_used,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "errors": error_details  # Add error details
            }
