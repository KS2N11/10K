"""Test to see what companies are prioritized first"""
import asyncio
from src.utils.sec_company_fetcher import SECCompanyFetcher
from src.utils.market_cap_lookup import MarketCapLookup
import random

async def check_first_prioritized():
    # Fetch companies
    fetcher = SECCompanyFetcher()
    all_companies = await fetcher.fetch_all_companies()
    print(f"Total companies: {len(all_companies)}")
    
    # Apply same prioritization as sec_filter.py
    companies_with_ticker = [c for c in all_companies if c.get("ticker")]
    companies_without_ticker = [c for c in all_companies if not c.get("ticker")]
    
    companies_with_ticker.sort(key=lambda x: x.get("cik", ""))
    random.shuffle(companies_without_ticker)
    
    prioritized = companies_with_ticker + companies_without_ticker
    print(f"Companies with tickers: {len(companies_with_ticker)}")
    print(f"Companies without tickers: {len(companies_without_ticker)}")
    print("\n=== First 20 prioritized companies ===")
    
    # Check first 20
    lookup = MarketCapLookup()
    first_20 = prioritized[:20]
    
    for i, company in enumerate(first_20, 1):
        cik = company.get("cik")
        ticker = company.get("ticker", "NO_TICKER")
        info = await lookup.get_company_info(cik, ticker)
        
        if info:
            cap = info.get("market_cap_billions", 0)
            tier = lookup.categorize_market_cap(cap)
            sector = info.get("sector", "Unknown")
            print(f"{i}. {ticker:8s} | {tier.value:5s} | ${cap:6.1f}B | {sector}")
        else:
            print(f"{i}. {ticker:8s} | ERROR")
        
        # Small delay
        await asyncio.sleep(0.1)
    
    # Check if Microsoft/Apple are in first 500
    print("\n=== Checking for known MEGA tech companies in first 500 ===")
    first_500_tickers = [c.get("ticker", "").upper() for c in prioritized[:500]]
    
    known_mega_tech = ["MSFT", "AAPL", "NVDA", "GOOGL", "META", "TSLA", "AVGO"]
    for ticker in known_mega_tech:
        if ticker in first_500_tickers:
            pos = first_500_tickers.index(ticker) + 1
            print(f"✓ {ticker} found at position {pos}")
        else:
            print(f"✗ {ticker} NOT in first 500")

if __name__ == "__main__":
    asyncio.run(check_first_prioritized())
