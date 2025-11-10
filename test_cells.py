"""Debug exact cell values"""
import requests
from bs4 import BeautifulSoup

cik = "320193"
acc_no_raw = "000032019325000073"
acc_no_with_dashes = "0000320193-25-000073"

base_archives_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_raw}/"
index_url = base_archives_url + f"{acc_no_with_dashes}-index.htm"

session = requests.Session()
session.headers.update({"User-Agent": "10Q Test Agent test@test.com"})

index_response = session.get(index_url)
soup = BeautifulSoup(index_response.text, 'html.parser')

table = soup.find('table', {'class': 'tableFile'})
if table:
    rows = table.find_all('tr')[1:]  # Skip header
    
    # Check first row in detail
    first_row = rows[0]
    cells = first_row.find_all('td')
    
    print(f"Number of cells: {len(cells)}\n")
    
    for i, cell in enumerate(cells):
        print(f"Cell {i}: '{cell.text.strip()}'")
        print(f"  Raw: {repr(cell.text)}\n")
