"""
Initialize database tables for 10K Insight Agent v2.0
Run this script to create all required database tables.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import all models to ensure they're registered with Base
from src.database.models import Base, Company, Analysis, PainPoint, ProductMatch, Pitch, AnalysisJob
from src.database.scheduler_models import SchedulerConfig, SchedulerRun, CompanyPriority, SchedulerMemory, SchedulerDecision
from src.database.database import init_db

if __name__ == "__main__":
    print("🔧 Initializing database...")
    print("📍 DATABASE_URL:", os.getenv("DATABASE_URL", "Not set!"))
    
    try:
        init_db()
        print("\n✅ Database initialized successfully!")
        print("\nCreated tables:")
        print("  - companies")
        print("  - analyses")
        print("  - pain_points")
        print("  - product_matches")
        print("  - pitches")
        print("  - analysis_jobs")
        print("  - system_metrics")
        print("  - scheduler_config")
        print("  - scheduler_runs")
        print("  - company_priorities")
        print("  - scheduler_memory")
        print("  - scheduler_decisions")
        print("\n🎉 You can now start the API server and Streamlit app!")
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running: docker-compose ps postgres")
        print("2. Check DATABASE_URL in .env file")
        print("3. Verify connection: docker exec -it tenk_insight_postgres psql -U postgres -d tenk_insight")
        sys.exit(1)
