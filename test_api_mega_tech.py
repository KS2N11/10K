"""Test API with MEGA + Technology after server restart"""
import asyncio
import aiohttp
import json

async def test_mega_tech_api():
    url = "http://127.0.0.1:8000/api/v2/companies/search-sec"
    
    payload = {
        "market_cap": ["MEGA"],
        "sector": ["Technology"],
        "limit": 5
    }
    
    print(f"Testing: {url}?use_realtime=true")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    print("This will take ~2 minutes with yfinance enrichment...\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{url}?use_realtime=true",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                print(f"Status: {response.status}\n")
                data = await response.json()
                
                print(f"✅ Found {data.get('count', 0)} companies")
                print(f"Source: {data.get('source')}")
                print(f"Method: {data.get('lookup_method')}\n")
                
                print("Companies:")
                for company in data.get('companies', []):
                    ticker = company.get('ticker', 'N/A')
                    name = company.get('name', 'Unknown')
                    print(f"  - {ticker:6s}: {name}")
                    
    except asyncio.TimeoutError:
        print("❌ Request timed out after 3 minutes")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mega_tech_api())
