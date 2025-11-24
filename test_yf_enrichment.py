"""Test Yahoo Finance enrichment"""
import asyncio
from src.utils.market_cap_lookup import MarketCapLookup

async def test_enrichment():
    lookup = MarketCapLookup()
    
    # Clear cache to force fresh lookups
    lookup.cache.clear()
    
    # Test with known MEGA tech stocks
    test_cases = [
        ("0000789019", "MSFT"),  # Microsoft
        ("0000320193", "AAPL"),  # Apple
        ("0000002488", "AMD"),   # AMD
    ]
    
    for cik, ticker in test_cases:
        print(f"\n=== Testing {ticker} ===")
        info = await lookup.get_company_info(cik, ticker, enrich_sector=True)
        if info:
            print(f"Market Cap: ${info.get('market_cap_billions', 0):.1f}B")
            print(f"Sector: {info.get('sector', 'N/A')}")
            print(f"Industry: {info.get('industry', 'N/A')}")
            print(f"Has SEC data: {info.get('has_sec_data', False)}")
        else:
            print("No info returned")

if __name__ == "__main__":
    asyncio.run(test_enrichment())
