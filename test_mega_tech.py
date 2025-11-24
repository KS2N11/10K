"""
Test MEGA cap Technology filtering
"""
import asyncio
from src.utils.market_cap_lookup import MarketCapLookup

async def test_known_mega_tech():
    """Test with known MEGA cap tech companies"""
    lookup = MarketCapLookup()
    
    # Test with Microsoft (known MEGA cap tech)
    test_companies = [
        {"cik": "0000789019", "ticker": "MSFT", "name": "Microsoft"},
        {"cik": "0000320193", "ticker": "AAPL", "name": "Apple"},
        {"cik": "0001018724", "ticker": "AMZN", "name": "Amazon"},
        {"cik": "0001652044", "ticker": "GOOGL", "name": "Alphabet"},
        {"cik": "0001045810", "ticker": "NVDA", "name": "NVIDIA"},
    ]
    
    print("Testing known MEGA cap tech companies:\n")
    
    for company in test_companies:
        info = await lookup.get_company_info(
            company["cik"], 
            company["ticker"], 
            enrich_sector=True
        )
        
        if info:
            tier = lookup.categorize_market_cap(info.get("market_cap_billions"))
            print(f"{company['name']} ({company['ticker']})")
            print(f"  CIK: {company['cik']}")
            print(f"  Market Cap: ${info.get('market_cap_billions', 0):.1f}B")
            print(f"  Tier: {tier.value if tier else 'None'}")
            print(f"  Sector: {info.get('sector', 'Unknown')}")
            print(f"  Industry: {info.get('industry', 'Unknown')}")
            print(f"  Has SEC data: {info.get('has_sec_data', False)}")
            print()
        else:
            print(f"{company['name']} - NO DATA\n")

if __name__ == "__main__":
    asyncio.run(test_known_mega_tech())
