from __future__ import annotations

"""
SEC 10-K filing fetcher using data.sec.gov API.
Retrieves the latest 10-K filing for any given company name.

Usage:
    python fetch_tenq.py "Company Name"

Environment variables:
    SEC_USER_AGENT: Set this to "Your Company Name your.email@example.com"
"""

import os
import sys
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Sequence
from dotenv import load_dotenv   
load_dotenv()



import requests

# SEC API endpoints
SEC_COMPANY_SEARCH = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "Sample Company Name test@example.com")

def create_session() -> requests.Session:
    """Create a session with proper headers for SEC API."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": SEC_USER_AGENT,
        "Accept": "application/json",
    })
    return session

@dataclass
class Filing:
    """Represents a SEC filing with relevant metadata."""
    cik: str
    company: str
    form_type: str
    file_date: str
    reporting_date: str
    acc_no: str
    document_url: str
    
    @classmethod
    def from_submission(cls, company: str, cik: str, filing: Dict[str, Any]) -> "Filing":
        """Create a Filing instance from a submission entry."""
        acc_no_raw = filing.get("accessionNumber", "")
        acc_no = acc_no_raw.replace("-", "")
        # Remove leading zeros from CIK for the URL
        cik_num = str(int(cik))
        # Format: https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION-NO-NODASHES}/{PRIMARY-DOCUMENT}.htm
        # We'll use the -index.htm file which lists all documents
        document_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={acc_no_raw}"
        return cls(
            cik=cik,
            company=company,
            form_type=filing.get("form", ""),
            file_date=filing.get("filingDate", ""),
            reporting_date=filing.get("reportDate", ""),
            acc_no=acc_no,
            document_url=document_url
        )

def find_company_cik(company_name: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """Find a company's CIK number by searching the company name."""
    sess = session or create_session()
    try:
        resp = sess.get(SEC_COMPANY_SEARCH)
        resp.raise_for_status()
        companies = resp.json()
        
        # Normalize search term
        search = company_name.lower().strip()
        
        # Search through companies
        for entry in companies.values():
            if (search in str(entry.get("title", "")).lower() or 
                search in str(entry.get("ticker", "")).lower()):
                return str(entry.get("cik_str")).zfill(10)
        
        return None
    
    except requests.RequestException as e:
        print(f"Error searching for company: {e}", file=sys.stderr)
        return None

def get_latest_10q_filing(cik: str, session: Optional[requests.Session] = None) -> Optional[Filing]:
    """Get the latest 10-Q filing for a given CIK."""
    sess = session or create_session()
    
    try:
        # Get all submissions for the CIK
        url = SEC_SUBMISSIONS_BASE.format(cik=cik)
        resp = sess.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        # Find the latest 10-Q
        company_name = data.get("name", "")
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        report_dates = filings.get("reportDate", [])
        accession_numbers = filings.get("accessionNumber", [])
        
        # Find latest 10-Q
        for i, form in enumerate(forms):
            if form == "10-Q":
                return Filing.from_submission(
                    company=company_name,
                    cik=cik,
                    filing={
                        "form": form,
                        "filingDate": dates[i] if i < len(dates) else "",
                        "reportDate": report_dates[i] if i < len(report_dates) else "",
                        "accessionNumber": accession_numbers[i] if i < len(accession_numbers) else ""
                    }
                )
        
        return None
        
    except requests.RequestException as e:
        print(f"Error fetching filings: {e}", file=sys.stderr)
        return None

def get_latest_10q(company_name: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest 10-Q filing for a given company name.
    Returns None if no filing is found or if there's an error.
    """
    session = create_session()
    
    # Step 1: Find the company's CIK
    cik = find_company_cik(company_name, session)
    if not cik:
        print(f"Could not find CIK for company: {company_name}", file=sys.stderr)
        return None
        
    # Step 2: Get the latest 10-Q filing
    filing = get_latest_10q_filing(cik, session)
    if not filing:
        print(f"No 10-Q filing found for {company_name} (CIK: {cik})", file=sys.stderr)
        return None
        
    # Convert to dict for JSON serialization
    return asdict(filing)

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line interface for fetching latest 10-Q filings."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch latest 10-Q filing for a company",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_tenq.py "Apple Inc"
  python fetch_tenq.py "Microsoft Corporation"
  python fetch_tenq.py "Tesla, Inc."
        """.strip()
    )
    
    parser.add_argument(
        "company",
        nargs="?",
        help="Company name to search for (required)",
    )
    
    args = parser.parse_args(argv)
    
    if not args.company:
        parser.print_help()
        return 1
    
    if not SEC_USER_AGENT or SEC_USER_AGENT == "Sample Company Name test@example.com":
        print("WARNING: Using default SEC_USER_AGENT. For reliable results, set your own:", file=sys.stderr)
        print('  set SEC_USER_AGENT="Your Company Name your.email@example.com"', file=sys.stderr)
        print()
    
    try:
        result = get_latest_10q(args.company)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        return 1
        
    except KeyboardInterrupt:
        print("\nCancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())