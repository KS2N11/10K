"""
Database migration script to add scheduler_jobs table.

This migration adds the SchedulerJob table for persistent APScheduler state tracking.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect
from src.database import database
from src.database.scheduler_models import SchedulerJob, Base
from src.utils.logging import get_logger

logger = get_logger(__name__)


def migrate():
    """Run the migration."""
    engine = database.engine
    inspector = inspect(engine)
    
    # Check if table already exists
    if "scheduler_jobs" in inspector.get_table_names():
        logger.info("✅ scheduler_jobs table already exists")
        return
    
    logger.info("Creating scheduler_jobs table...")
    
    # Create only the SchedulerJob table
    SchedulerJob.__table__.create(engine, checkfirst=True)
    
    logger.info("✅ scheduler_jobs table created successfully")
    
    # Optionally migrate existing data from SchedulerConfig
    logger.info("Migrating existing scheduler state...")
    from src.database.database import get_db
    from src.database.scheduler_models import SchedulerConfig
    from datetime import datetime
    
    with get_db() as db:
        scheduler_config = db.query(SchedulerConfig).first()
        
        if scheduler_config:
            # Check if job already exists
            existing_job = db.query(SchedulerJob).filter(
                SchedulerJob.job_id == "main_cron_job"
            ).first()
            
            if not existing_job:
                # Create initial job record from config
                scheduler_job = SchedulerJob(
                    job_id="main_cron_job",
                    job_name="Autonomous Analysis Scheduler",
                    job_type="cron",
                    cron_schedule=scheduler_config.cron_schedule,
                    is_active=scheduler_config.is_active,
                    next_run_time=scheduler_config.next_run_at,
                    last_run_time=scheduler_config.last_run_at,
                    total_runs=0,
                    successful_runs=0,
                    failed_runs=0
                )
                db.add(scheduler_job)
                db.commit()
                
                logger.info(f"✅ Migrated scheduler state: next_run_time = {scheduler_config.next_run_at}")
            else:
                logger.info("✅ Scheduler job record already exists")
        else:
            logger.warning("No scheduler config found to migrate")


if __name__ == "__main__":
    try:
        migrate()
        logger.info("🎉 Migration completed successfully!")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
