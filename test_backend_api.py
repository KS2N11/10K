"""Quick test to verify backend API is working"""
import requests
import json

url = "http://127.0.0.1:8000/api/v2/companies/search-sec"
params = {"use_realtime": "true"}
payload = {
    "market_cap": ["LARGE"],
    "sector": ["Technology"],
    "limit": 50
}

print(f"Testing: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(url, params=params, json=payload, timeout=180)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Found {data.get('count', 0)} companies")
        print(f"Source: {data.get('source')}")
        print(f"Method: {data.get('lookup_method')}\n")
        
        if data.get('companies'):
            print("First 10 companies:")
            for company in data.get('companies', [])[:10]:
                ticker = company.get('ticker', 'N/A')
                name = company.get('name', 'Unknown')
                print(f"  - {ticker:6s}: {name}")
        else:
            print("⚠️  No companies found!")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
