"""
Database migration script to add autonomous scheduler tables.

Run this script to create the new scheduler tables in your existing database.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database import engine, init_db
from src.database.scheduler_models import (
    SchedulerConfig, SchedulerRun, CompanyPriority,
    SchedulerMemory, SchedulerDecision
)
from sqlalchemy import inspect

def check_existing_tables():
    """Check which scheduler tables already exist."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    scheduler_tables = [
        'scheduler_config',
        'scheduler_runs',
        'company_priorities',
        'scheduler_memory',
        'scheduler_decisions'
    ]
    
    print("\n📊 Checking existing tables...")
    for table in scheduler_tables:
        status = "✅ EXISTS" if table in existing_tables else "❌ MISSING"
        print(f"  {status}: {table}")
    
    missing_tables = [t for t in scheduler_tables if t not in existing_tables]
    return missing_tables


def create_scheduler_tables():
    """Create scheduler tables."""
    print("\n🔨 Creating scheduler tables...")
    
    # Import Base from scheduler_models (which includes all models)
    from src.database.scheduler_models import Base as SchedulerBase
    
    # Create all scheduler tables
    SchedulerBase.metadata.create_all(bind=engine)
    
    print("✅ Scheduler tables created successfully")


def initialize_default_config():
    """Create default scheduler configuration."""
    from src.database.database import get_db
    
    print("\n⚙️  Initializing default scheduler configuration...")
    
    with get_db() as db:
        # Check if config already exists
        existing_config = db.query(SchedulerConfig).first()
        
        if existing_config:
            print("  ℹ️  Scheduler config already exists, skipping...")
            return
        
        # Create default config
        config = SchedulerConfig(
            cron_schedule="0 2 * * *",  # Daily at 2 AM
            is_active=False,  # Start paused
            market_cap_priority=["SMALL", "MID", "LARGE", "MEGA"],
            batch_size=10,
            analysis_interval_days=90,
            use_llm_agent=True,
            llm_temperature=0.3,
            max_companies_per_run=50,
            min_time_between_runs_minutes=60,
            max_concurrent_analyses=5
        )
        
        db.add(config)
        db.commit()
        
        print("✅ Default scheduler configuration created")
        print(f"  📅 Cron schedule: {config.cron_schedule}")
        print(f"  ⏸️  Active: {config.is_active}")
        print(f"  🎯 Market cap priority: {config.market_cap_priority}")
        print(f"  📦 Batch size: {config.batch_size}")
        print(f"  📆 Analysis interval: {config.analysis_interval_days} days")


def migrate_existing_companies():
    """Migrate existing companies to company_priorities table."""
    from src.database.database import get_db
    from src.database.models import Company, Analysis
    from datetime import datetime
    
    print("\n🔄 Migrating existing companies to priority system...")
    
    with get_db() as db:
        # Get all companies
        companies = db.query(Company).all()
        
        if not companies:
            print("  ℹ️  No companies found, skipping migration...")
            return
        
        migrated = 0
        skipped = 0
        
        for company in companies:
            # Check if priority record already exists
            existing_priority = db.query(CompanyPriority).filter(
                CompanyPriority.cik == company.cik
            ).first()
            
            if existing_priority:
                skipped += 1
                continue
            
            # Get latest analysis
            latest_analysis = db.query(Analysis).filter(
                Analysis.company_id == company.id
            ).order_by(Analysis.completed_at.desc()).first()
            
            # Create priority record
            priority = CompanyPriority(
                cik=company.cik,
                company_name=company.name,
                market_cap=company.market_cap,
                industry=company.industry,
                sector=company.sector,
                times_analyzed=db.query(Analysis).filter(
                    Analysis.company_id == company.id
                ).count(),
                last_analyzed_at=latest_analysis.completed_at if latest_analysis else None,
                priority_score=50.0  # Default score
            )
            
            db.add(priority)
            migrated += 1
        
        db.commit()
        
        print(f"✅ Migration complete: {migrated} companies migrated, {skipped} skipped")


def main():
    """Run migration."""
    print("=" * 70)
    print("🚀 AUTONOMOUS SCHEDULER MIGRATION")
    print("=" * 70)
    
    try:
        # Check existing tables
        missing_tables = check_existing_tables()
        
        if not missing_tables:
            print("\n✅ All scheduler tables already exist!")
        else:
            print(f"\n📝 Need to create {len(missing_tables)} tables")
            
            # Create tables
            create_scheduler_tables()
        
        # Initialize default config
        initialize_default_config()
        
        # Migrate existing companies
        migrate_existing_companies()
        
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\n📚 Next steps:")
        print("  1. Review AUTONOMOUS_SCHEDULER.md for documentation")
        print("  2. Start the application: uvicorn src.main:app --reload")
        print("  3. Check scheduler status: GET /api/scheduler/status")
        print("  4. Enable scheduler: PUT /api/scheduler/config (set is_active=true)")
        print("  5. Trigger test run: POST /api/scheduler/trigger")
        print("\n🎉 Ready for autonomous operation!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
