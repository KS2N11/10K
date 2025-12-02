"""Simple test script to see what get_status() returns."""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.autonomous_scheduler import get_autonomous_scheduler
from src.api.routes import load_config

async def test():
    config = load_config()
    scheduler = await get_autonomous_scheduler(config)
    status = scheduler.get_status()
    
    print("Status returned by get_status():")
    print(f"  next_run_at: {status.get('next_run_at')}")
    print(f"  total_runs: {status.get('total_runs')}")
    print(f"  successful_runs: {status.get('successful_runs')}")
    print(f"  failed_runs: {status.get('failed_runs')}")

if __name__ == "__main__":
    asyncio.run(test())
