"""Quick script to check scheduler_jobs table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import get_db
from src.database.scheduler_models import SchedulerJob
from datetime import datetime

with get_db() as db:
    job = db.query(SchedulerJob).filter(
        SchedulerJob.job_id == "main_cron_job"
    ).first()
    
    if job:
        print(f"Job ID: {job.job_id}")
        print(f"Job Name: {job.job_name}")
        print(f"Cron Schedule: {job.cron_schedule}")
        print(f"Is Active: {job.is_active}")
        print(f"Next Run Time: {job.next_run_time}")
        print(f"Last Run Time: {job.last_run_time}")
        print(f"Total Runs: {job.total_runs}")
        print(f"Successful Runs: {job.successful_runs}")
        print(f"Failed Runs: {job.failed_runs}")
        print(f"Created At: {job.created_at}")
        print(f"Updated At: {job.updated_at}")
        print(f"\nCurrent Time: {datetime.utcnow()}")
    else:
        print("No scheduler job found!")
