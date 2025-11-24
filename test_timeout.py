"""Test MEGA + Technology filtering with 2-minute timeout"""
import asyncio
from src.utils.sec_filter import SECCompanyFilter

async def test_with_timeout():
    filter = SECCompanyFilter(user_agent="Test test@test.com")
    
    print("Testing MEGA cap + Technology (limit=5, 2-minute timeout)\n")
    
    try:
        companies = await asyncio.wait_for(
            filter.search_companies(
                market_cap=["MEGA"],
                sector=["Technology"],
                limit=5,
                use_realtime_lookup=True
            ),
            timeout=120  # 2 minutes
        )
        
        print(f"\n=== SUCCESS! Found {len(companies)} companies ===")
        for company in companies:
            ticker = company.get("ticker", "NO_TICKER")
            name = company.get("name", "Unknown")
            print(f"  {ticker}: {name}")
            
    except asyncio.TimeoutError:
        print("\n=== TIMEOUT after 2 minutes ===")
        print("The filtering is too slow. Need further optimization.")

if __name__ == "__main__":
    asyncio.run(test_with_timeout())
