"""Test JUST the first 10 prioritized companies to see if AMD is there"""
import asyncio
import aiohttp
from src.utils.market_cap_lookup import MarketCapLookup

async def test_first_10():
    # Fetch all companies
    async with aiohttp.ClientSession() as session:
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": "Test test@test.com"}
        async with session.get(url, headers=headers) as response:
            data = await response.json()
    
    # Convert to list
    all_companies = []
    for company in data.values():
        all_companies.append({
            "cik": str(company.get("cik_str", "")).zfill(10),
            "ticker": company.get("ticker", ""),
            "name": company.get("title", "")
        })
    
    # Apply MEGA/LARGE prioritization
    companies_with_ticker = [c for c in all_companies if c.get("ticker")]
    companies_with_ticker.sort(key=lambda x: x.get("cik", ""))
    
    print(f"Total companies with tickers: {len(companies_with_ticker)}\n")
    print("=== First 10 prioritized companies ===")
    
    # Check first 10
    lookup = MarketCapLookup()
    for i, company in enumerate(companies_with_ticker[:10], 1):
        cik = company.get("cik")
        ticker = company.get("ticker")
        name = company.get("name")
        
        info = await lookup.get_company_info(cik, ticker, enrich_sector=True)
        
        if info:
            cap = info.get("market_cap_billions", 0)
            tier = lookup.categorize_market_cap(cap).value if lookup.categorize_market_cap(cap) else "Unknown"
            sector = info.get("sector", "Unknown")
            industry = info.get("industry", "Unknown")
            
            # Highlight MEGA + Technology matches
            is_match = (tier == "MEGA" and sector == "Technology")
            prefix = ">>> " if is_match else "    "
            
            print(f"{prefix}{i}. {ticker:8s} | {tier:5s} | ${cap:6.1f}B | {sector} | {name}")
        else:
            print(f"    {i}. {ticker:8s} | ERROR | {name}")
        
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(test_first_10())
