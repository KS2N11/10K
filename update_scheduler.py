"""
Update scheduler configuration to 60 minutes
"""
from src.database.database import get_db
from src.database.scheduler_models import SchedulerConfig

print("🔧 Updating scheduler configuration...")

with get_db() as db:
    scheduler_config = db.query(SchedulerConfig).first()
    
    if scheduler_config:
        print(f"Current cron schedule: {scheduler_config.cron_schedule}")
        print(f"Current active status: {scheduler_config.is_active}")
        
        # Update to 60 minutes (every hour at minute 0)
        scheduler_config.cron_schedule = "0 * * * *"
        scheduler_config.is_active = True
        
        db.commit()
        
        print(f"✅ Updated cron schedule to: {scheduler_config.cron_schedule}")
        print("✅ Scheduler is active")
    else:
        print("Creating new scheduler config...")
        scheduler_config = SchedulerConfig(
            cron_schedule="0 * * * *",  # Every 60 minutes
            is_active=True,
            market_cap_priority=["SMALL", "MID", "LARGE", "MEGA"],
            batch_size=10,
            analysis_interval_days=90,
            use_llm_agent=True,
            max_companies_per_run=50
        )
        db.add(scheduler_config)
        db.commit()
        print("✅ Created new scheduler config with 60-minute interval")

print("\n📝 Scheduler Configuration:")
with get_db() as db:
    config = db.query(SchedulerConfig).first()
    if config:
        print(f"  Cron Schedule: {config.cron_schedule}")
        print(f"  Active: {config.is_active}")
        print(f"  Batch Size: {config.batch_size}")
        print(f"  Analysis Interval: {config.analysis_interval_days} days")
        print(f"  Use LLM Agent: {config.use_llm_agent}")
        print(f"  Max Companies Per Run: {config.max_companies_per_run}")

print("\n✅ Done! Restart the backend for changes to take effect.")
