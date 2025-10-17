"""
SEC EDGAR API utilities for fetching company information and 10-K filings.
"""
import aiohttp
import asyncio
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import json
import re
from datetime import datetime

from ..utils.logging import setup_logger

logger = setup_logger(__name__)


class SECAPIError(Exception):
    """Custom exception for SEC API errors."""
    pass


class SECAPI:
    """Client for interacting with SEC EDGAR API."""
    
    BASE_URL = "https://www.sec.gov"
    DATA_URL = "https://data.sec.gov"
    EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    
    def __init__(self, user_agent: str):
        """
        Initialize SEC API client.
        
        Args:
            user_agent: Required User-Agent string (must include email)
        """
        if not user_agent or "@" not in user_agent:
            raise ValueError(
                "SEC requires a valid User-Agent with email: "
                "AppName/Version (email@example.com)"
            )
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json"
        }
    
    async def search_company(self, company_name: str) -> List[Dict[str, str]]:
        """
        Search for companies by name.
        
        Args:
            company_name: Company name to search for
        
        Returns:
            List of matching companies with name, ticker, and CIK
        """
        # Clean company name
        clean_name = company_name.strip().upper()
        
        # Try to get company tickers JSON
        url = f"{self.BASE_URL}/files/company_tickers.json"
        
        # Retry logic for SEC API
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            data = await response.json()
                            break
                        elif response.status == 429:  # Rate limit
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt  # Exponential backoff
                                logger.warning(f"SEC API rate limit hit, retrying in {wait_time}s...")
                                await asyncio.sleep(wait_time)
                                continue
                        else:
                            error_text = await response.text()
                            logger.error(f"SEC API error {response.status}: {error_text}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)
                                continue
                            raise SECAPIError(f"Failed to fetch company tickers: {response.status}")
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"SEC API timeout, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)
                    continue
                raise SECAPIError("SEC API request timed out after multiple retries")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"SEC API error: {str(e)}, retrying...")
                    await asyncio.sleep(1)
                    continue
                raise SECAPIError(f"SEC API error: {str(e)}")
        else:
            raise SECAPIError("Failed to fetch company data after multiple retries")
        
        # Search for matching companies
        candidates = []
        for item in data.values():
            title = item.get("title", "").upper()
            ticker = item.get("ticker", "")
            cik = str(item.get("cik_str", "")).zfill(10)
            
            # Fuzzy matching
            if clean_name in title or title in clean_name:
                candidates.append({
                    "name": item.get("title", ""),
                    "ticker": ticker,
                    "cik": cik
                })
        
        logger.info(f"Found {len(candidates)} candidate(s) for '{company_name}'")
        return candidates
    
    async def get_cik(self, company_identifier: str) -> str:
        """
        Get CIK for a company by name or ticker.
        
        Args:
            company_identifier: Company name or ticker symbol
        
        Returns:
            10-digit CIK string
        
        Raises:
            SECAPIError: If company not found or multiple matches
        """
        candidates = await self.search_company(company_identifier)
        
        if len(candidates) == 0:
            raise SECAPIError(f"No company found for: {company_identifier}")
        
        if len(candidates) > 1:
            # Return the first exact match if available
            for c in candidates:
                if c["name"].upper() == company_identifier.upper():
                    return c["cik"]
            
            raise SECAPIError(
                f"Multiple companies found for '{company_identifier}': "
                f"{[c['name'] for c in candidates]}"
            )
        
        return candidates[0]["cik"]
    
    async def get_latest_10k(self, cik: str) -> Tuple[str, str, str]:
        """
        Get the latest 10-K filing for a company.
        
        Args:
            cik: 10-digit CIK string
        
        Returns:
            Tuple of (filing_url, accession_number, filing_date)
        
        Raises:
            SECAPIError: If no 10-K found
        """
        # Get company submissions
        url = f"{self.DATA_URL}/submissions/CIK{cik}.json"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    raise SECAPIError(f"Failed to fetch submissions for CIK {cik}: {response.status}")
                
                data = await response.json()
        
        # Find latest 10-K
        recent_filings = data.get("filings", {}).get("recent", {})
        forms = recent_filings.get("form", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        filing_dates = recent_filings.get("filingDate", [])
        primary_documents = recent_filings.get("primaryDocument", [])
        
        for i, form in enumerate(forms):
            if form == "10-K":
                accession = accession_numbers[i].replace("-", "")
                filing_date = filing_dates[i]
                primary_doc = primary_documents[i]
                
                # Build document URL
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik}/{accession}/{primary_doc}"
                )
                
                logger.info(f"Found 10-K for CIK {cik}: {filing_url} (filed: {filing_date})")
                return filing_url, accession_numbers[i], filing_date
        
        raise SECAPIError(f"No 10-K filing found for CIK {cik}")
    
    async def download_filing(
        self,
        filing_url: str,
        output_path: Path
    ) -> Path:
        """
        Download a filing document.
        
        Args:
            filing_url: URL of the filing document
            output_path: Path where the file should be saved
        
        Returns:
            Path to the downloaded file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(filing_url, headers=self.headers) as response:
                if response.status != 200:
                    raise SECAPIError(f"Failed to download filing: {response.status}")
                
                content = await response.text()
                
                # Save to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
        
        logger.info(f"Downloaded filing to {output_path}")
        return output_path


async def fetch_company_10k(
    company_name: str,
    user_agent: str,
    output_dir: Path
) -> Dict[str, str]:
    """
    Fetch the latest 10-K for a company.
    
    Args:
        company_name: Company name or ticker
        user_agent: SEC User-Agent string
        output_dir: Directory to save the filing
    
    Returns:
        Dict with company, cik, filing_url, file_path, filing_date
    """
    api = SECAPI(user_agent)
    
    # Get CIK
    cik = await api.get_cik(company_name)
    
    # Get latest 10-K
    filing_url, accession, filing_date = await api.get_latest_10k(cik)
    
    # Download filing
    safe_name = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
    output_path = output_dir / f"{safe_name}_10K.html"
    file_path = await api.download_filing(filing_url, output_path)
    
    return {
        "company": company_name,
        "cik": cik,
        "filing_url": filing_url,
        "file_path": str(file_path),
        "filing_date": filing_date,
        "accession": accession
    }
