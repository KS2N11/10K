"""
API routes for autonomous scheduler management.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from src.services.autonomous_scheduler import get_autonomous_scheduler
from src.database.database import get_db_session
from src.database.scheduler_models import SchedulerRun, SchedulerDecision, CompanyPriority
from src.utils.logging import get_logger
from src.api.routes import load_config
from sqlalchemy.orm import Session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


# Request/Response Models
class SchedulerConfigUpdate(BaseModel):
    """Request model for updating scheduler config."""
    cron_schedule: Optional[str] = None
    is_active: Optional[bool] = None
    continuous_mode: Optional[bool] = None
    continuous_delay_minutes: Optional[int] = None
    market_cap_priority: Optional[List[str]] = None
    batch_size: Optional[int] = None
    analysis_interval_days: Optional[int] = None
    use_llm_agent: Optional[bool] = None
    max_companies_per_run: Optional[int] = None
    prioritize_industries: Optional[List[str]] = None
    exclude_industries: Optional[List[str]] = None


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""
    is_running: bool
    is_active: bool
    cron_schedule: Optional[str]
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    total_runs: Optional[int] = 0
    successful_runs: Optional[int] = 0
    failed_runs: Optional[int] = 0
    current_job_id: Optional[str]
    config: Dict[str, Any]
    recent_runs: List[Dict[str, Any]]


class TriggerRunResponse(BaseModel):
    """Response model for manual trigger."""
    run_id: str
    message: str


# Endpoints
@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """
    Get current status of the autonomous scheduler.
    
    Returns:
        Scheduler status with config and recent runs
    """
    try:
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        status = scheduler.get_status()
        
        return SchedulerStatusResponse(**status)
    
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler():
    """
    Start the autonomous scheduler.
    
    Returns:
        Success message
    """
    try:
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        
        await scheduler.start()
        
        return {
            "success": True,
            "message": "Scheduler started successfully"
        }
    
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """
    Stop the autonomous scheduler.
    
    Returns:
        Success message
    """
    try:
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        
        await scheduler.stop()
        
        return {
            "success": True,
            "message": "Scheduler stopped successfully"
        }
    
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger", response_model=TriggerRunResponse)
async def trigger_immediate_run():
    """
    Trigger an immediate analysis run (bypass schedule).
    
    Returns:
        Run ID for tracking
    """
    try:
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        
        run_id = await scheduler.trigger_now(manual=True)
        
        return TriggerRunResponse(
            run_id=run_id,
            message=f"Immediate run triggered. Track progress at /api/scheduler/runs/{run_id}"
        )
    
    except Exception as e:
        logger.error(f"Error triggering run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_scheduler_config(request: SchedulerConfigUpdate):
    """
    Update scheduler configuration.
    
    Args:
        request: Configuration update
    
    Returns:
        Success message
    """
    try:
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        
        await scheduler.update_config(
            cron_schedule=request.cron_schedule,
            is_active=request.is_active,
            continuous_mode=request.continuous_mode,
            continuous_delay_minutes=request.continuous_delay_minutes,
            market_cap_priority=request.market_cap_priority,
            batch_size=request.batch_size,
            analysis_interval_days=request.analysis_interval_days,
            use_llm_agent=request.use_llm_agent,
            max_companies_per_run=request.max_companies_per_run,
            prioritize_industries=request.prioritize_industries,
            exclude_industries=request.exclude_industries
        )
        
        return {
            "success": True,
            "message": "Scheduler configuration updated successfully"
        }
    
    except Exception as e:
        logger.error(f"Error updating scheduler config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
def get_scheduler_runs(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db_session)
):
    """
    Get history of scheduler runs.
    
    Args:
        limit: Max results
        offset: Pagination offset
        db: Database session
    
    Returns:
        List of scheduler runs
    """
    try:
        runs = db.query(SchedulerRun).order_by(
            SchedulerRun.trigger_time.desc()
        ).limit(limit).offset(offset).all()
        
        return {
            "runs": [
                {
                    "run_id": run.run_id,
                    "trigger_time": run.trigger_time.isoformat(),
                    "triggered_by": run.triggered_by,
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "total_companies_considered": run.total_companies_considered,
                    "companies_analyzed": run.companies_analyzed,
                    "companies_skipped": run.companies_skipped,
                    "companies_failed": run.companies_failed,
                    "total_tokens_used": run.total_tokens_used,
                    "total_time_seconds": run.total_time_seconds,
                    "job_id": run.job_id,
                    "error_message": run.error_message,
                    "llm_reasoning": run.llm_reasoning
                }
                for run in runs
            ],
            "count": len(runs)
        }
    
    except Exception as e:
        logger.error(f"Error getting scheduler runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}")
def get_scheduler_run_details(
    run_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Get detailed information about a specific scheduler run.
    
    Args:
        run_id: Scheduler run ID
        db: Database session
    
    Returns:
        Run details with company selections and decisions
    """
    try:
        run = db.query(SchedulerRun).filter(
            SchedulerRun.run_id == run_id
        ).first()
        
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        # Get decisions for this run
        decisions = db.query(SchedulerDecision).filter(
            SchedulerDecision.run_id == run_id
        ).order_by(SchedulerDecision.created_at).all()
        
        return {
            "run_id": run.run_id,
            "trigger_time": run.trigger_time.isoformat(),
            "triggered_by": run.triggered_by,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "total_companies_considered": run.total_companies_considered,
            "companies_selected": run.companies_selected,
            "companies_analyzed": run.companies_analyzed,
            "companies_skipped": run.companies_skipped,
            "companies_failed": run.companies_failed,
            "total_tokens_used": run.total_tokens_used,
            "total_time_seconds": run.total_time_seconds,
            "job_id": run.job_id,
            "error_message": run.error_message,
            "llm_reasoning": run.llm_reasoning,
            "decisions": [
                {
                    "company_cik": decision.company_cik,
                    "company_name": decision.company_name,
                    "decision": decision.decision,
                    "reason": decision.reason.value if decision.reason else None,
                    "reasoning": decision.reasoning,
                    "confidence": decision.confidence,
                    "market_cap": decision.market_cap.value if decision.market_cap else None,
                    "days_since_last_analysis": decision.days_since_last_analysis,
                    "previous_analysis_count": decision.previous_analysis_count,
                    "previous_avg_match_score": decision.previous_avg_match_score
                }
                for decision in decisions
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scheduler run details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/priorities")
def get_company_priorities(
    limit: int = 100,
    offset: int = 0,
    market_cap: Optional[str] = None,
    min_priority_score: float = 0.0,
    db: Session = Depends(get_db_session)
):
    """
    Get company priorities (scheduler's memory of companies).
    
    Args:
        limit: Max results
        offset: Pagination offset
        market_cap: Filter by market cap
        min_priority_score: Minimum priority score
        db: Database session
    
    Returns:
        List of company priorities
    """
    try:
        query = db.query(CompanyPriority).filter(
            CompanyPriority.priority_score >= min_priority_score
        )
        
        if market_cap:
            from src.database.models import MarketCap
            query = query.filter(CompanyPriority.market_cap == MarketCap(market_cap))
        
        priorities = query.order_by(
            CompanyPriority.priority_score.desc()
        ).limit(limit).offset(offset).all()
        
        return {
            "priorities": [
                {
                    "cik": p.cik,
                    "company_name": p.company_name,
                    "market_cap": p.market_cap.value if p.market_cap else None,
                    "industry": p.industry,
                    "sector": p.sector,
                    "times_analyzed": p.times_analyzed,
                    "last_analyzed_at": p.last_analyzed_at.isoformat() if p.last_analyzed_at else None,
                    "next_scheduled_at": p.next_scheduled_at.isoformat() if p.next_scheduled_at else None,
                    "priority_score": p.priority_score,
                    "priority_reason": p.priority_reason.value if p.priority_reason else None,
                    "avg_product_match_score": p.avg_product_match_score,
                    "total_pain_points_found": p.total_pain_points_found,
                    "has_high_value_matches": p.has_high_value_matches,
                    "last_priority_update": p.last_priority_update.isoformat() if p.last_priority_update else None
                }
                for p in priorities
            ],
            "count": len(priorities)
        }
    
    except Exception as e:
        logger.error(f"Error getting company priorities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/priorities/update")
async def update_company_priorities_endpoint(
    analysis_interval_days: int = 90
):
    """
    Manually trigger update of company priorities.
    
    Args:
        analysis_interval_days: Days between re-analysis
    
    Returns:
        Success message
    """
    try:
        config = load_config()
        scheduler = await get_autonomous_scheduler(config)
        
        from src.database.database import get_db
        with get_db() as db:
            await scheduler.scheduler_agent.update_company_priorities(
                db,
                analysis_interval_days
            )
        
        return {
            "success": True,
            "message": "Company priorities updated successfully"
        }
    
    except Exception as e:
        logger.error(f"Error updating company priorities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions")
def get_scheduler_decisions(
    limit: int = 100,
    offset: int = 0,
    company_cik: Optional[str] = None,
    decision: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    Get history of scheduler decisions (LLM reasoning).
    
    Args:
        limit: Max results
        offset: Pagination offset
        company_cik: Filter by company CIK
        decision: Filter by decision type ("analyze", "skip", "defer")
        db: Database session
    
    Returns:
        List of scheduler decisions
    """
    try:
        query = db.query(SchedulerDecision)
        
        if company_cik:
            query = query.filter(SchedulerDecision.company_cik == company_cik)
        
        if decision:
            query = query.filter(SchedulerDecision.decision == decision)
        
        decisions = query.order_by(
            SchedulerDecision.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return {
            "decisions": [
                {
                    "id": d.id,
                    "run_id": d.run_id,
                    "company_cik": d.company_cik,
                    "company_name": d.company_name,
                    "decision": d.decision,
                    "reason": d.reason.value if d.reason else None,
                    "reasoning": d.reasoning,
                    "confidence": d.confidence,
                    "market_cap": d.market_cap.value if d.market_cap else None,
                    "days_since_last_analysis": d.days_since_last_analysis,
                    "previous_analysis_count": d.previous_analysis_count,
                    "previous_avg_match_score": d.previous_avg_match_score,
                    "created_at": d.created_at.isoformat()
                }
                for d in decisions
            ],
            "count": len(decisions)
        }
    
    except Exception as e:
        logger.error(f"Error getting scheduler decisions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
