"""
SEC 10-Q filing fetcher using data.sec.gov API.
Standalone fetcher for the 10-Q microservice.
"""
import os
import sys
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# SEC API endpoints
SEC_COMPANY_SEARCH = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "10Q Insight Agent contact@example.com")


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
    acc_no: str  # Without dashes
    acc_no_raw: str  # With dashes (original format)
    document_url: str
    
    @classmethod
    def from_submission(cls, company: str, cik: str, filing: Dict[str, Any]) -> "Filing":
        """Create a Filing instance from a submission entry."""
        acc_no_raw = filing.get("accessionNumber", "")
        acc_no = acc_no_raw.replace("-", "")
        
        # Remove leading zeros from CIK for the URL
        cik_num = str(int(cik))
        
        # Build the primary document URL (the main 10-Q HTML file)
        # Format: https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{acc_no_raw}-index.htm
        # But we want the primary document which is typically the first file
        # For now, we'll construct a generic filing documents page
        base_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={acc_no_raw}&xbrl_type=v"
        
        # Store the accession number for later document fetching
        filing_data = filing.copy()
        filing_data["acc_no"] = acc_no
        filing_data["acc_no_raw"] = acc_no_raw
        filing_data["cik_num"] = cik_num
        
        return cls(
            cik=cik,
            company=company,
            form_type=filing.get("form", ""),
            file_date=filing.get("filingDate", ""),
            reporting_date=filing.get("reportDate", ""),
            acc_no=acc_no,
            acc_no_raw=acc_no_raw,
            document_url=base_url
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
