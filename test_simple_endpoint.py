"""Test simple endpoint"""
import requests
import json

try:
    # Test health endpoint
    response = requests.get("http://127.0.0.1:8000/api/v2/health", timeout=5)
    print(f"Health check: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}\n")
    
    # Test search-by-name (simpler endpoint)
    response = requests.get(
        "http://127.0.0.1:8000/api/v2/companies/search-by-name",
        params={"query": "Microsoft", "limit": 5},
        timeout=30
    )
    print(f"Search by name: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data.get('count', 0)} companies\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
