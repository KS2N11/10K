"""Test search-sec endpoint without sector filter"""
import requests
import json

url = "http://127.0.0.1:8000/api/v2/companies/search-sec"

# Test 1: No filters (should return quick)
print("Test 1: No filters, use_realtime=false")
response = requests.post(
    url,
    params={"use_realtime": "false"},
    json={"limit": 10},
    timeout=30
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {data.get('count', 0)} companies\n")
else:
    print(f"Error: {response.text}\n")

# Test 2: Just LARGE cap, no sector
print("Test 2: LARGE cap only, use_realtime=false")
response = requests.post(
    url,
    params={"use_realtime": "false"},
    json={"market_cap": ["LARGE"], "limit": 10},
    timeout=30
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {data.get('count', 0)} companies\n")
else:
    print(f"Error: {response.text}\n")
