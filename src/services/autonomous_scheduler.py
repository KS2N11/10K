"""
Autonomous scheduler service that runs continuously and manages batch analysis jobs.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from src.database.database import get_db
from src.database.scheduler_models import (
    SchedulerConfig, SchedulerRun, ScheduleStatus, SchedulerJob
)
from src.database.repository import AnalysisJobRepository
from src.services.scheduler_agent import SchedulerAgent
from src.services.batch_analysis import BatchAnalysisService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AutonomousScheduler:
    """
    Autonomous scheduler that runs continuously in the background.
    
    Features:
    - Cron-based scheduling (e.g., daily at 2 AM)
    - LLM-powered company selection (intelligent decisions)
    - Memory of past analyses (avoid duplicates)
    - Market cap prioritization (small -> mid -> large -> mega)
    - Automatic error recovery
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize autonomous scheduler.
        
        Args: 
            config: Configuration dict with API keys, settings
        """
        self.config = config
        # Configure scheduler with safe defaults to avoid missed runs
        # - coalesce: collapse multiple pending runs into one
        # - max_instances: prevent overlapping job instances
        # - misfire_grace_time: tolerate short delays without dropping the run
        self.scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 600,  # 10 minutes
            }
        )
        self.llm_manager = None
        self.embedder = None
        self.scheduler_agent = None
        self.batch_service = None
        self.is_running = False
        self._current_job_id = None
        self._continuous_task = None  # Background task for continuous mode
    
    async def start(self):
        """Start the autonomous scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("🚀 Starting autonomous scheduler...")
        
        # Initialize providers
        await self._init_providers()
        
        # Load or create scheduler config
        with get_db() as db:
            scheduler_config = db.query(SchedulerConfig).first()
            
            if not scheduler_config:
                # Create default config
                logger.info("Creating default scheduler configuration...")
                scheduler_config = SchedulerConfig(
                    cron_schedule="*/15 * * * *",  # Every 15 minutes
                    is_active=True,  # Start active
                    market_cap_priority=["SMALL", "MID", "LARGE", "MEGA"],
                    batch_size=10,
                    analysis_interval_days=90,
                    use_llm_agent=True,
                    max_companies_per_run=50
                )
                db.add(scheduler_config)
                db.commit()
                db.refresh(scheduler_config)
            
            # Store config as dict to avoid session issues
            self.scheduler_config_data = {
                "cron_schedule": scheduler_config.cron_schedule,
                "is_active": scheduler_config.is_active,
                "continuous_mode": getattr(scheduler_config, 'continuous_mode', False),
                "continuous_delay_minutes": getattr(scheduler_config, 'continuous_delay_minutes', 5),
                "market_cap_priority": scheduler_config.market_cap_priority,
                "batch_size": scheduler_config.batch_size,
                "analysis_interval_days": scheduler_config.analysis_interval_days,
                "use_llm_agent": scheduler_config.use_llm_agent,
                "max_companies_per_run": scheduler_config.max_companies_per_run,
                "prioritize_industries": scheduler_config.prioritize_industries,
                "exclude_industries": scheduler_config.exclude_industries
            }
        
        # Choose mode: continuous or cron-based
        if self.scheduler_config_data["is_active"]:
            if self.scheduler_config_data.get("continuous_mode", False):
                # Continuous mode: run one after another with delay
                logger.info(f"🔄 Starting in CONTINUOUS mode (delay: {self.scheduler_config_data['continuous_delay_minutes']}min between runs)")
                self._continuous_task = asyncio.create_task(self._continuous_loop())
            else:
                # Cron mode: scheduled at specific times
                self._add_cron_job()
                logger.info(f"⏰ Starting in CRON mode: {self.scheduler_config_data['cron_schedule']}")
        else:
            logger.info("⏸️  Scheduler is paused (set is_active=True to enable)")
        
        # Start APScheduler (needed for cron mode)
        self.scheduler.start()
        self.is_running = True
        
        # Sync database state with APScheduler after startup (must be after scheduler.start())
        if self.scheduler_config_data["is_active"] and not self.scheduler_config_data.get("continuous_mode", False):
            self._sync_job_state_to_db()
        
        logger.info("✅ Autonomous scheduler started successfully")
    
    async def stop(self):
        """Stop the autonomous scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping autonomous scheduler...")
        
        # Stop continuous loop if running
        if self._continuous_task and not self._continuous_task.done():
            self._continuous_task.cancel()
            try:
                await self._continuous_task
            except asyncio.CancelledError:
                logger.info("Continuous loop cancelled")
        
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        
        logger.info("✅ Autonomous scheduler stopped")
    
    async def trigger_now(self, manual: bool = True) -> str:
        """
        Trigger an immediate analysis run.
        
        Args:
            manual: Whether this is a manual trigger (vs scheduled)
        
        Returns:
            Run ID
        """
        if self._current_job_id:
            logger.warning("A job is already running")
            return self._current_job_id
        
        logger.info("🎯 Triggering immediate analysis run...")
        
        run_id = str(uuid.uuid4())
        
        # Execute in background
        asyncio.create_task(self._execute_scheduled_run(
            run_id,
            triggered_by="manual" if manual else "immediate"
        ))
        
        return run_id
    
    async def update_config(
        self,
        cron_schedule: Optional[str] = None,
        is_active: Optional[bool] = None,
        continuous_mode: Optional[bool] = None,
        continuous_delay_minutes: Optional[int] = None,
        market_cap_priority: Optional[list] = None,
        batch_size: Optional[int] = None,
        analysis_interval_days: Optional[int] = None,
        use_llm_agent: Optional[bool] = None,
        max_companies_per_run: Optional[int] = None,
        prioritize_industries: Optional[list] = None,
        exclude_industries: Optional[list] = None
    ):
        """Update scheduler configuration."""
        with get_db() as db:
            scheduler_config = db.query(SchedulerConfig).first()
            
            if not scheduler_config:
                raise ValueError("Scheduler config not found")
            
            # Update fields
            if cron_schedule is not None:
                scheduler_config.cron_schedule = cron_schedule
            if is_active is not None:
                scheduler_config.is_active = is_active
            if continuous_mode is not None:
                scheduler_config.continuous_mode = continuous_mode
            if continuous_delay_minutes is not None:
                scheduler_config.continuous_delay_minutes = continuous_delay_minutes
            if market_cap_priority is not None:
                scheduler_config.market_cap_priority = market_cap_priority
            if batch_size is not None:
                scheduler_config.batch_size = batch_size
            if analysis_interval_days is not None:
                scheduler_config.analysis_interval_days = analysis_interval_days
            if use_llm_agent is not None:
                scheduler_config.use_llm_agent = use_llm_agent
            if max_companies_per_run is not None:
                scheduler_config.max_companies_per_run = max_companies_per_run
            if prioritize_industries is not None:
                scheduler_config.prioritize_industries = prioritize_industries
            if exclude_industries is not None:
                scheduler_config.exclude_industries = exclude_industries
            
            db.commit()
            
            # Update cached config (read values before session closes)
            self.scheduler_config_data = {
                "cron_schedule": scheduler_config.cron_schedule,
                "is_active": scheduler_config.is_active,
                "continuous_mode": getattr(scheduler_config, 'continuous_mode', False),
                "continuous_delay_minutes": getattr(scheduler_config, 'continuous_delay_minutes', 5),
                "market_cap_priority": scheduler_config.market_cap_priority,
                "batch_size": scheduler_config.batch_size,
                "analysis_interval_days": scheduler_config.analysis_interval_days,
                "use_llm_agent": scheduler_config.use_llm_agent,
                "max_companies_per_run": scheduler_config.max_companies_per_run,
                "prioritize_industries": scheduler_config.prioritize_industries,
                "exclude_industries": scheduler_config.exclude_industries
            }
        
        # Re-schedule based on mode (outside database session)
        mode_changed = continuous_mode is not None or is_active is not None or cron_schedule is not None
        
        if mode_changed:
            # Stop current mode
            self._remove_cron_job()
            if self._continuous_task and not self._continuous_task.done():
                self._continuous_task.cancel()
                try:
                    await self._continuous_task
                except asyncio.CancelledError:
                    pass
            
            # Start new mode if active
            if self.scheduler_config_data["is_active"]:
                if self.scheduler_config_data.get("continuous_mode", False):
                    logger.info(f"🔄 Switched to CONTINUOUS mode (delay: {self.scheduler_config_data['continuous_delay_minutes']}min)")
                    self._continuous_task = asyncio.create_task(self._continuous_loop())
                else:
                    self._add_cron_job()
                    logger.info(f"⏰ Switched to CRON mode: {self.scheduler_config_data['cron_schedule']}")
            else:
                logger.info("⏸️  Scheduler paused")
        
        logger.info("✅ Scheduler configuration updated")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        with get_db() as db:
            scheduler_config = db.query(SchedulerConfig).first()
            scheduler_job = db.query(SchedulerJob).filter(
                SchedulerJob.job_id == "main_cron_job"
            ).first()
            
            # Get recent runs
            recent_runs = db.query(SchedulerRun).order_by(
                SchedulerRun.trigger_time.desc()
            ).limit(5).all()
            
            # Build response from database objects (convert to dict before leaving session)
            config_data = {}
            if scheduler_config:
                config_data = {
                    "is_active": scheduler_config.is_active,
                    "cron_schedule": scheduler_config.cron_schedule,
                    "market_cap_priority": scheduler_config.market_cap_priority,
                    "batch_size": scheduler_config.batch_size,
                    "analysis_interval_days": scheduler_config.analysis_interval_days,
                    "use_llm_agent": scheduler_config.use_llm_agent,
                    "max_companies_per_run": scheduler_config.max_companies_per_run,
                    "prioritize_industries": scheduler_config.prioritize_industries,
                    "exclude_industries": scheduler_config.exclude_industries
                }
            
            # Get job state from persistent table
            job_data = {}
            if scheduler_job:
                job_data = {
                    "last_run_at": scheduler_job.last_run_time.isoformat() if scheduler_job.last_run_time else None,
                    "next_run_at": scheduler_job.next_run_time.isoformat() if scheduler_job.next_run_time else None,
                    "total_runs": scheduler_job.total_runs,
                    "successful_runs": scheduler_job.successful_runs,
                    "failed_runs": scheduler_job.failed_runs
                }
            
            recent_runs_data = [
                {
                    "run_id": run.run_id,
                    "trigger_time": run.trigger_time.isoformat(),
                    "triggered_by": run.triggered_by,
                    "status": run.status,
                    "companies_analyzed": run.companies_analyzed,
                    "companies_skipped": run.companies_skipped,
                    "companies_failed": run.companies_failed,
                    "total_companies": len(run.companies_selected) if run.companies_selected else 0
                }
                for run in recent_runs
            ]
            
            return {
                "is_running": self.is_running,
                "is_active": config_data.get("is_active", False),
                "cron_schedule": config_data.get("cron_schedule"),
                "last_run_at": job_data.get("last_run_at"),
                "next_run_at": job_data.get("next_run_at"),
                "total_runs": job_data.get("total_runs", 0),
                "successful_runs": job_data.get("successful_runs", 0),
                "failed_runs": job_data.get("failed_runs", 0),
                "current_job_id": self._current_job_id,
                "config": {
                    "market_cap_priority": config_data.get("market_cap_priority", []),
                    "batch_size": config_data.get("batch_size", 10),
                    "analysis_interval_days": config_data.get("analysis_interval_days", 90),
                    "use_llm_agent": config_data.get("use_llm_agent", True),
                    "max_companies_per_run": config_data.get("max_companies_per_run", 50),
                    "prioritize_industries": config_data.get("prioritize_industries"),
                    "exclude_industries": config_data.get("exclude_industries")
                },
                "recent_runs": recent_runs_data
            }
    
    async def _continuous_loop(self):
        """
        Continuous mode: Run analysis jobs one after another with delay.
        
        This ensures:
        - No overlapping jobs
        - No wasted time waiting for cron schedule
        - Continuous processing when there's work to do
        """
        try:
            logger.info("🔄 Continuous loop started")
            
            while self.is_running:
                try:
                    # Check if already running a job
                    if self._current_job_id:
                        logger.debug("Job already running, waiting...")
                        await asyncio.sleep(10)  # Check again in 10 seconds
                        continue
                    
                    # Trigger a new run
                    logger.info("🔄 Continuous mode: Starting new analysis run...")
                    run_id = str(uuid.uuid4())
                    await self._execute_scheduled_run(run_id, triggered_by="continuous")
                    
                    # Wait before next run
                    delay_minutes = self.scheduler_config_data.get("continuous_delay_minutes", 5)
                    logger.info(f"⏳ Continuous mode: Waiting {delay_minutes} minutes before next run...")
                    await asyncio.sleep(delay_minutes * 60)
                    
                except asyncio.CancelledError:
                    logger.info("Continuous loop cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Error in continuous loop: {e}")
                    # Wait a bit before retrying on error
                    await asyncio.sleep(60)
        
        except asyncio.CancelledError:
            logger.info("Continuous loop stopped")
        except Exception as e:
            logger.error(f"Fatal error in continuous loop: {e}")
            self.is_running = False

    async def _init_providers(self):
        """Initialize LLM and embedding providers."""
        from src.utils.llm_factory import get_factory
        
        # Use centralized factory for LLM and embeddings
        factory = get_factory()
        
        if not self.llm_manager:
            self.llm_manager = factory.create_llm_manager()
        
        if not self.embedder:
            self.embedder = factory.create_embedder()
        
        if not self.scheduler_agent:
            self.scheduler_agent = SchedulerAgent(self.llm_manager, factory.get_config())
        
        if not self.batch_service:
            self.batch_service = BatchAnalysisService(factory.get_config())
    
    def _add_cron_job(self):
        """Add cron job to scheduler."""
        try:
            # Remove existing job if present
            self._remove_cron_job()
            
            # Parse cron schedule
            parts = self.scheduler_config_data["cron_schedule"].split()
            if len(parts) != 5:
                logger.error(f"Invalid cron schedule: {self.scheduler_config_data['cron_schedule']}")
                return
            
            minute, hour, day, month, day_of_week = parts
            
            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            # Add job
            self.scheduler.add_job(
                self._scheduled_trigger,
                trigger=trigger,
                id="main_cron_job",
                name="Autonomous Analysis Scheduler",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=600,
            )
            
            # Calculate next run time from APScheduler
            next_job = self.scheduler.get_job("main_cron_job")
            if next_job:
                next_run = next_job.next_run_time if hasattr(next_job, 'next_run_time') else None
            else:
                next_run = None
            
            # Persist to database
            with get_db() as db:
                scheduler_job = db.query(SchedulerJob).filter(
                    SchedulerJob.job_id == "main_cron_job"
                ).first()
                
                if not scheduler_job:
                    # Create new job record
                    scheduler_job = SchedulerJob(
                        job_id="main_cron_job",
                        job_name="Autonomous Analysis Scheduler",
                        job_type="cron",
                        cron_schedule=self.scheduler_config_data["cron_schedule"],
                        is_active=True,
                        next_run_time=next_run
                    )
                    db.add(scheduler_job)
                else:
                    # Update existing job record
                    scheduler_job.cron_schedule = self.scheduler_config_data["cron_schedule"]
                    scheduler_job.is_active = True
                    scheduler_job.next_run_time = next_run
                    scheduler_job.updated_at = datetime.utcnow()
                
                db.commit()
            
            logger.info(f"✅ Cron job scheduled: {self.scheduler_config_data['cron_schedule']} (next run: {next_run})")
        
        except Exception as e:
            logger.error(f"Error adding cron job: {e}")
    
    def _remove_cron_job(self):
        """Remove cron job from scheduler."""
        try:
            if self.scheduler.get_job("main_cron_job"):
                self.scheduler.remove_job("main_cron_job")
                logger.info("Removed existing cron job")
        except Exception as e:
            logger.debug(f"No cron job to remove: {e}")
    
    def _sync_job_state_to_db(self):
        """
        Sync APScheduler job state to database.
        
        This is called after startup to ensure the database reflects the actual
        next_run_time calculated by APScheduler, preventing stale data issues.
        """
        try:
            next_job = self.scheduler.get_job("main_cron_job")
            if not next_job:
                logger.warning("No cron job found to sync")
                return
            
            next_run = next_job.next_run_time if hasattr(next_job, 'next_run_time') else None
            
            with get_db() as db:
                scheduler_job = db.query(SchedulerJob).filter(
                    SchedulerJob.job_id == "main_cron_job"
                ).first()
                
                if scheduler_job:
                    scheduler_job.next_run_time = next_run
                    scheduler_job.updated_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"✅ Synced job state to database: next_run_time = {next_run}")
                else:
                    logger.warning("No scheduler job found in database to sync")
        
        except Exception as e:
            logger.error(f"Error syncing job state to database: {e}")
    
    async def _scheduled_trigger(self):
        """Triggered by cron schedule."""
        logger.info("⏰ Scheduled trigger activated")
        
        # Check minimum time between runs
        with get_db() as db:
            scheduler_config = db.query(SchedulerConfig).first()
            
            if scheduler_config.last_run_at:
                time_since_last_run = (datetime.utcnow() - scheduler_config.last_run_at).total_seconds() / 60
                if time_since_last_run < scheduler_config.min_time_between_runs_minutes:
                    logger.warning(f"Skipping run - last run was {time_since_last_run:.1f} minutes ago (min: {scheduler_config.min_time_between_runs_minutes})")
                    return
        
        run_id = str(uuid.uuid4())
        await self._execute_scheduled_run(run_id, triggered_by="scheduler")
    
    async def _execute_scheduled_run(self, run_id: str, triggered_by: str = "scheduler"):
        """Execute a scheduled analysis run."""
        try:
            logger.info(f"🚀 Starting scheduled run {run_id}")
            self._current_job_id = run_id
            
            # Create run record
            with get_db() as db:
                run_record = SchedulerRun(
                    run_id=run_id,
                    triggered_by=triggered_by,
                    trigger_time=datetime.utcnow(),
                    status="pending",
                    companies_selected=[]
                )
                db.add(run_record)
                db.commit()
            
            # Get scheduler config (fresh from DB)
            with get_db() as db:
                scheduler_config = db.query(SchedulerConfig).first()
                
                # Store config values we need
                config_values = {
                    "market_cap_priority": scheduler_config.market_cap_priority,
                    "batch_size": scheduler_config.batch_size,
                    "analysis_interval_days": scheduler_config.analysis_interval_days,
                    "prioritize_industries": scheduler_config.prioritize_industries,
                    "exclude_industries": scheduler_config.exclude_industries,
                    "max_companies_per_run": scheduler_config.max_companies_per_run,
                    "use_llm_agent": scheduler_config.use_llm_agent
                }
            
            # Update company priorities
            logger.info("Updating company priorities...")
            await self.scheduler_agent.update_company_priorities(
                config_values["analysis_interval_days"]
            )
            
            # Use LLM agent to decide which companies to analyze
            if config_values["use_llm_agent"]:
                logger.info("🤖 Using LLM agent for company selection...")
                companies_to_analyze = await self.scheduler_agent.decide_companies_to_analyze(
                    run_id,
                    config_values["market_cap_priority"],
                    config_values["batch_size"],
                    config_values["analysis_interval_days"],
                    config_values["prioritize_industries"],
                    config_values["exclude_industries"],
                    config_values["max_companies_per_run"]
                )
            else:
                # Fallback: simple rule-based selection
                logger.info("Using rule-based company selection...")
                # Pass raw config dict to fallback selection
                companies_to_analyze = await self._rule_based_selection(config_values)
            
            if not companies_to_analyze:
                logger.warning("No companies selected for analysis")
                with get_db() as db:
                    run_record = db.query(SchedulerRun).filter(
                        SchedulerRun.run_id == run_id
                    ).first()
                    run_record.status = "completed"
                    run_record.completed_at = datetime.utcnow()
                    db.commit()
                
                self._current_job_id = None
                return
            
            # Update run record with selected companies
            with get_db() as db:
                run_record = db.query(SchedulerRun).filter(
                    SchedulerRun.run_id == run_id
                ).first()
                run_record.companies_selected = companies_to_analyze
                run_record.total_companies_considered = len(companies_to_analyze)
                run_record.status = "running"
                run_record.started_at = datetime.utcnow()
                db.commit()
            
            # Start batch analysis
            logger.info(f"Starting batch analysis for {len(companies_to_analyze)} companies...")
            job_id = await self.batch_service.start_batch_job(
                company_names=[c["name"] for c in companies_to_analyze],
                force_reanalyze=False
            )
            
            # Update run record with job ID
            with get_db() as db:
                run_record = db.query(SchedulerRun).filter(
                    SchedulerRun.run_id == run_id
                ).first()
                run_record.job_id = job_id
                db.commit()
            
            # Wait for batch job to complete (with timeout)
            timeout = 3600  # 1 hour timeout
            start_time = datetime.utcnow()
            
            while True:
                job_status = await self.batch_service.get_job_status(job_id)
                
                if not job_status:
                    break
                
                if job_status["status"] in ["completed", "failed"]:
                    # Update run record with results
                    with get_db() as db:
                        run_record = db.query(SchedulerRun).filter(
                            SchedulerRun.run_id == run_id
                        ).first()
                        run_record.status = "completed" if job_status["status"] == "completed" else "failed"
                        run_record.completed_at = datetime.utcnow()
                        run_record.companies_analyzed = job_status.get("completed", 0)
                        run_record.companies_skipped = job_status.get("skipped", 0)
                        run_record.companies_failed = job_status.get("failed", 0)
                        run_record.total_tokens_used = job_status.get("total_tokens", 0)
                        run_record.total_time_seconds = (run_record.completed_at - run_record.started_at).total_seconds()
                        db.commit()
                    
                    logger.info(f"✅ Scheduled run {run_id} completed: {job_status['completed']} analyzed, {job_status['skipped']} skipped, {job_status['failed']} failed")
                    break
                
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    logger.error(f"Scheduled run {run_id} timed out after {timeout}s")
                    with get_db() as db:
                        run_record = db.query(SchedulerRun).filter(
                            SchedulerRun.run_id == run_id
                        ).first()
                        run_record.status = "failed"
                        run_record.error_message = f"Timed out after {timeout}s"
                        run_record.completed_at = datetime.utcnow()
                        db.commit()
                    break
                
                # Wait before checking again
                await asyncio.sleep(10)
            
            # Update scheduler job state
            with get_db() as db:
                scheduler_job = db.query(SchedulerJob).filter(
                    SchedulerJob.job_id == "main_cron_job"
                ).first()
                
                if scheduler_job:
                    scheduler_job.last_run_time = datetime.utcnow()
                    scheduler_job.total_runs += 1
                    
                    # Update success/failure counters
                    run_record = db.query(SchedulerRun).filter(
                        SchedulerRun.run_id == run_id
                    ).first()
                    if run_record and run_record.status == "completed":
                        scheduler_job.successful_runs += 1
                    elif run_record and run_record.status == "failed":
                        scheduler_job.failed_runs += 1
                    
                    # Calculate next run time from APScheduler
                    next_job = self.scheduler.get_job("main_cron_job")
                    if next_job:
                        scheduler_job.next_run_time = next_job.next_run_time
                    
                    scheduler_job.updated_at = datetime.utcnow()
                    db.commit()
        
        except Exception as e:
            logger.error(f"Error in scheduled run {run_id}: {e}")
            
            # Update run record with error
            with get_db() as db:
                run_record = db.query(SchedulerRun).filter(
                    SchedulerRun.run_id == run_id
                ).first()
                if run_record:
                    run_record.status = "failed"
                    run_record.error_message = str(e)
                    run_record.completed_at = datetime.utcnow()
                    db.commit()
        
        finally:
            self._current_job_id = None
    
    async def _rule_based_selection(
        self,
        config_dict
    ) -> list:
        """Fallback rule-based company selection."""
        from src.utils.sec_filter import SECCompanyFilter
        from src.database.repository import CompanyRepository, AnalysisRepository

        companies = []
        sec_filter = SECCompanyFilter(self.config.get("sec_user_agent"))

        # Get values from config dict (supports both object and dict)
        market_cap_priority = getattr(config_dict, 'market_cap_priority', config_dict.get('market_cap_priority', []))
        batch_size = getattr(config_dict, 'batch_size', config_dict.get('batch_size', 10))
        max_companies_per_run = getattr(config_dict, 'max_companies_per_run', config_dict.get('max_companies_per_run', 50))
        analysis_interval_days = getattr(config_dict, 'analysis_interval_days', config_dict.get('analysis_interval_days', 90))
        
        # Select companies by market cap priority
        for market_cap in market_cap_priority:
            cap_companies = await sec_filter.search_companies(
                market_cap=[market_cap],
                limit=batch_size,
                use_realtime_lookup=False
            )
            
            for c in cap_companies:
                if len(companies) >= max_companies_per_run:
                    break

                # Skip companies analyzed too recently
                from src.database.database import get_db
                with get_db() as db:
                    db_company = CompanyRepository.get_by_cik(db, c.get("cik"))
                    if db_company:
                        latest = AnalysisRepository.get_latest_for_company(db, db_company.id)
                        if latest and latest.completed_at:
                            days_since = (datetime.utcnow() - latest.completed_at).days
                            if days_since < analysis_interval_days:
                                # Too recent; skip this company in fallback selection
                                continue

                companies.append({
                    "cik": c["cik"],
                    "name": c["name"],
                    "ticker": c.get("ticker"),
                    "market_cap": market_cap,
                    "reason": "periodic_refresh",
                    "reasoning": "Rule-based selection by market cap priority and freshness"
                })
            
            if len(companies) >= max_companies_per_run:
                break
        
        return companies


# Global scheduler instance
_autonomous_scheduler: Optional[AutonomousScheduler] = None


async def get_autonomous_scheduler(config: Dict[str, Any]) -> AutonomousScheduler:
    """Get or create the global autonomous scheduler."""
    global _autonomous_scheduler
    
    if _autonomous_scheduler is None:
        _autonomous_scheduler = AutonomousScheduler(config)
        await _autonomous_scheduler.start()
    
    return _autonomous_scheduler
