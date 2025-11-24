"""Quick test to verify AMD is found in first batch"""
import asyncio
from src.utils.sec_filter import SECCompanyFilter

async def test_first_batch():
    filter = SECCompanyFilter(user_agent="Test test@test.com")
    
    print("Testing MEGA cap + Technology with small limit\n")
    
    companies = await filter.search_companies(
        market_cap=["MEGA"],
        sector=["Technology"],
        limit=5,  # Only get first 5 matches
        use_realtime_lookup=True
    )
    
    print(f"\n=== Results ===")
    print(f"Found {len(companies)} companies:")
    for company in companies:
        ticker = company.get("ticker", "NO_TICKER")
        name = company.get("name", "Unknown")
        print(f"  {ticker}: {name}")

if __name__ == "__main__":
    asyncio.run(test_first_batch())
