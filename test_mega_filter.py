"""
Debug MEGA cap Technology sector filtering
"""
import asyncio
from src.utils.sec_filter import SECCompanyFilter

async def test_mega_tech_filter():
    """Test the actual API filtering that frontend uses"""
    
    filter = SECCompanyFilter(user_agent="Test test@test.com")
    
    print("Testing MEGA cap + Technology sector filtering\n")
    print("=" * 60)
    
    # This is what the frontend sends
    companies = await filter.search_companies(
        market_cap=["MEGA"],
        sector=["Technology"],
        industry=None,
        limit=10,
        use_realtime_lookup=True
    )
    
    print(f"\nFound {len(companies)} companies")
    print("=" * 60)
    
    for c in companies:
        print(f"\n{c.get('name')} ({c.get('ticker', 'N/A')})")
        print(f"  CIK: {c.get('cik')}")
        print(f"  Market Cap: {c.get('market_cap_tier', 'N/A')}")
        print(f"  Sector: {c.get('sector', 'N/A')}")
        print(f"  Industry: {c.get('industry', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_mega_tech_filter())
