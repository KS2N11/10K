"""Debug SEC document fetching"""
import requests
from bs4 import BeautifulSoup

# Apple Inc 10-Q - using the exact values from the fetcher
cik = "320193"
acc_no_raw = "000032019325000073"  # WITHOUT dashes
acc_no_with_dashes = "0000320193-25-000073"  # WITH dashes

# Build URLs
base_archives_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_raw}/"
index_url = base_archives_url + f"{acc_no_with_dashes}-index.htm"

print(f"CIK: {cik}")
print(f"Accession (no dashes): {acc_no_raw}")
print(f"Accession (with dashes): {acc_no_with_dashes}")
print(f"Base URL: {base_archives_url}")
print(f"Index URL: {index_url}\n")

session = requests.Session()
session.headers.update({"User-Agent": "10Q Test Agent test@test.com"})

print("Fetching index...")
try:
    index_response = session.get(index_url)
    print(f"Status: {index_response.status_code}\n")
    
    if index_response.status_code == 200:
        soup = BeautifulSoup(index_response.text, 'html.parser')
        
        table = soup.find('table', {'class': 'tableFile'})
        if table:
            print("✅ Found tableFile")
            rows = table.find_all('tr')[1:]  # Skip header
            print(f"Found {len(rows)} document rows\n")
            
            for row in rows[:5]:  # First 5
                cells = row.find_all('td')
                if len(cells) >= 4:
                    seq = cells[0].text.strip()
                    doc_name = cells[2].text.strip()
                    doc_type = cells[3].text.strip()
                    
                    print(f"Seq {seq}: {doc_type:15} | {doc_name:40}")
                    
                    # Check for primary document
                    if seq == "1" and doc_name.endswith('.htm') and '10-Q' in doc_type:
                        primary_url = base_archives_url + doc_name
                        print(f"\n✅ PRIMARY DOCUMENT FOUND!")
                        print(f"URL: {primary_url}\n")
                        
                        # Test fetch
                        doc_resp = session.get(primary_url)
                        print(f"Fetch status: {doc_resp.status_code}")
                        if doc_resp.status_code == 200:
                            print(f"Content length: {len(doc_resp.text)} characters")
        else:
            print("❌ No tableFile found")
            print("Available tables:")
            for table in soup.find_all('table'):
                print(f"  - {table.get('class', 'no class')}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
