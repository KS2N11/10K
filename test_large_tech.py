"""Test search-sec with realtime and sector"""
import requests
import json
import time

url = "http://127.0.0.1:8000/api/v2/companies/search-sec"

print("Testing: LARGE cap + Technology sector, real-time lookup")
print("This will take ~30-60 seconds...\n")

start = time.time()

response = requests.post(
    url,
    params={"use_realtime": "true"},
    json={
        "market_cap": ["LARGE"],
        "sector": ["Technology"],
        "limit": 10
    },
    timeout=180
)

elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.1f}s\n")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Found {data.get('count', 0)} companies")
    print(f"Source: {data.get('source')}")
    print(f"Method: {data.get('lookup_method')}\n")
    
    if data.get('companies'):
        print("Companies found:")
        for company in data.get('companies', []):
            ticker = company.get('ticker', 'N/A')
            name = company.get('name', 'Unknown')
            print(f"  - {ticker:6s}: {name}")
    else:
        print("⚠️  No companies matched the filters!")
else:
    print(f"❌ Error {response.status_code}: {response.text}")
