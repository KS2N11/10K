"""Test the actual API endpoint for MEGA + Technology filtering"""
import asyncio
import aiohttp

async def test_api_endpoint():
    url = "http://localhost:8000/api/companies/search"
    
    params = {
        "market_cap": "MEGA",
        "sector": "Technology",
        "limit": 5
    }
    
    print(f"Testing API: {url}")
    print(f"Parameters: {params}\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=180)) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                
                print(f"\nResponse:")
                print(f"Companies found: {len(data.get('companies', []))}")
                
                for company in data.get('companies', []):
                    ticker = company.get('ticker', 'N/A')
                    name = company.get('name', 'N/A')
                    print(f"  - {ticker}: {name}")
                    
    except asyncio.TimeoutError:
        print("\nERROR: Request timed out after 3 minutes")
    except aiohttp.ClientConnectorError:
        print("\nERROR: Cannot connect to server. Is it running on localhost:8000?")
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_endpoint())
