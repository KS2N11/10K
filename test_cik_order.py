"""Quick test to check CIK numbers of MEGA cap companies"""
import asyncio
import aiohttp

async def check_ciks():
    url = "https://www.sec.gov/files/company_tickers.json"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"User-Agent": "Test test@test.com"}) as response:
            data = await response.json()
    
    # Find known MEGA tech companies
    known_mega_tech = ["MSFT", "AAPL", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "AMD"]
    
    companies = []
    for company in data.values():
        ticker = company.get("ticker", "")
        if ticker in known_mega_tech:
            cik = str(company.get("cik_str", "")).zfill(10)
            companies.append((ticker, cik, company.get("title")))
    
    # Sort by CIK
    companies.sort(key=lambda x: x[1])
    
    print("MEGA cap Tech companies sorted by CIK:")
    for ticker, cik, name in companies:
        print(f"{ticker:6s} | CIK {cik} | {name}")
    
    # Check all companies with tickers, sorted by CIK
    all_with_tickers = []
    for company in data.values():
        if company.get("ticker"):
            cik = str(company.get("cik_str", "")).zfill(10)
            ticker = company.get("ticker")
            all_with_tickers.append((cik, ticker))
    
    all_with_tickers.sort()
    
    print(f"\nTotal companies with tickers: {len(all_with_tickers)}")
    print("\nFirst 20 companies by CIK:")
    for cik, ticker in all_with_tickers[:20]:
        print(f"{ticker:8s} | CIK {cik}")
    
    # Check where MSFT appears
    msft_pos = next((i for i, (cik, t) in enumerate(all_with_tickers) if t == "MSFT"), -1)
    aapl_pos = next((i for i, (cik, t) in enumerate(all_with_tickers) if t == "AAPL"), -1)
    print(f"\nMSFT position in CIK-sorted list: {msft_pos + 1}")
    print(f"AAPL position in CIK-sorted list: {aapl_pos + 1}")

if __name__ == "__main__":
    asyncio.run(check_ciks())
