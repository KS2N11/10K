"""Test if server is responding at all"""
import requests

try:
    response = requests.get("http://127.0.0.1:8000/docs", timeout=5)
    print(f"Server status: {response.status_code}")
    print("✅ Server is responding!")
except Exception as e:
    print(f"❌ Server not responding: {e}")
