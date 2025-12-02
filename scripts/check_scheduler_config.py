"""Quick script to check scheduler_config table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import get_db
from src.database.scheduler_models import SchedulerConfig
from datetime import datetime

with get_db() as db:
    config = db.query(SchedulerConfig).first()
    
    if config:
        print(f"Cron Schedule: {config.cron_schedule}")
        print(f"Is Active: {config.is_active}")
        print(f"Next Run At: {config.next_run_at}")
        print(f"Last Run At: {config.last_run_at}")
        print(f"Updated At: {config.updated_at}")
        print(f"\nCurrent Time: {datetime.utcnow()}")
    else:
        print("No scheduler config found!")
