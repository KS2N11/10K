"""Test SEC document fetching"""
import requests
from bs4 import BeautifulSoup

# Apple Inc 10-Q
cik = "320193"
acc_no = "000032019325000073"
acc_no_with_dashes = "0000320193-25-000073"

# Get the filing index
index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{acc_no_with_dashes}-index.htm"
print(f"Fetching index: {index_url}\n")

response = requests.get(index_url, headers={"User-Agent": "10Q Test Agent test@test.com"})
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all document links in the filing
    print("Documents in this filing:")
    print("=" * 60)
    
    table = soup.find('table', {'class': 'tableFile'})
    if table:
        rows = table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                seq = cells[0].text.strip()
                desc = cells[1].text.strip()
                doc = cells[2].text.strip()
                doc_type = cells[3].text.strip()
                
                print(f"{seq}. {doc_type:20} | {doc:40} | {desc}")
                
                # Get the first .htm document (usually the primary filing)
                if doc.endswith('.htm') and seq == "1":
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{doc}"
                    print(f"\n✅ Primary document URL: {doc_url}\n")
                    
                    # Fetch a preview
                    doc_response = requests.get(doc_url, headers={"User-Agent": "10Q Test Agent test@test.com"})
                    if doc_response.status_code == 200:
                        print(f"Document size: {len(doc_response.text)} characters")
                        print(f"Preview (first 500 chars):\n{doc_response.text[:500]}")
