"""
SEC company search and filtering utilities.
Enhanced with real-time market cap lookup and direct company search.
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from enum import Enum

from src.utils.logging import get_logger
from src.utils.market_cap_lookup import MarketCapLookup, MarketCapTier

logger = get_logger(__name__)


class MarketCapCategory(str, Enum):
    """Market cap categories."""
    SMALL = "small"      # < $2B
    MID = "mid"          # $2B - $10B
    LARGE = "large"      # $10B - $200B
    MEGA = "mega"        # > $200B


# Industry/Sector mappings (SIC codes)
INDUSTRY_SIC_MAPPING = {
    "Technology": ["7370", "7371", "7372", "7373", "7374", "7375", "7376", "7377", "7378", "7379"],
    "Healthcare": ["8000", "8010", "8020", "8050", "8060", "8070", "8071", "8082", "8090", "8092"],
    "Finance": ["6000", "6010", "6020", "6035", "6036", "6099", "6141", "6153", "6159", "6162"],
    "Retail": ["5200", "5210", "5250", "5260", "5310", "5330", "5390", "5399", "5400", "5410"],
    "Manufacturing": ["2000", "3000", "3100", "3200", "3300", "3400", "3500", "3600", "3700"],
    "Energy": ["1300", "1310", "1311", "1381", "1382", "1389", "2911", "4900", "4911", "4922"],
    "Real Estate": ["6500", "6510", "6512", "6513", "6519", "6531", "6552", "6770"],
    "Transportation": ["4000", "4011", "4100", "4200", "4400", "4500", "4512", "4513", "4700"],
    "Telecommunications": ["4810", "4812", "4813", "4822", "4832", "4833", "4899", "4841"],
    "Consumer Goods": ["2080", "2082", "2086", "2090", "5070", "5080", "5090", "5110", "5120"],
}


class SECCompanyFilter:
    """Filter companies from SEC EDGAR based on criteria."""
    
    def __init__(self, user_agent: str):
        """
        Initialize SEC company filter.
        
        Args:
            user_agent: SEC API user agent
        """
        self.user_agent = user_agent
        self.base_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.headers = {"User-Agent": user_agent}
        self.market_cap_lookup = MarketCapLookup()
        
    async def search_company_by_name(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for companies by name or ticker in SEC database.
        
        Args:
            query: Company name or ticker to search
            limit: Maximum number of results
        
        Returns:
            List of matching companies with cik, ticker, name
        """
        try:
            # Fetch all companies
            async with aiohttp.ClientSession() as session:
                url = "https://www.sec.gov/files/company_tickers.json"
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch SEC companies: {response.status}")
                        return []
                    
                    data = await response.json()
            
            # Search by name or ticker
            query_lower = query.lower()
            matches = []
            
            for company_data in data.values():
                name = company_data.get("title", "").lower()
                ticker = company_data.get("ticker", "").lower()
                
                # Check if query matches name or ticker
                if query_lower in name or query_lower in ticker:
                    matches.append({
                        "cik": str(company_data.get("cik_str", "")).zfill(10),
                        "ticker": company_data.get("ticker", ""),
                        "name": company_data.get("title", "")
                    })
                    
                    if len(matches) >= limit:
                        break
            
            logger.info(f"Found {len(matches)} companies matching '{query}'")
            return matches
        
        except Exception as e:
            logger.error(f"Error searching for company '{query}': {e}")
            return []
    
    async def search_by_industry(
        self,
        industry: str,
        limit: int = 100
    ) -> List[Dict[str, str]]:
        """
        Search companies by industry using SIC codes.
        
        Args:
            industry: Industry name (e.g., "Technology")
            limit: Maximum number of companies to return
        
        Returns:
            List of company dicts with name, cik, ticker
        """
        sic_codes = INDUSTRY_SIC_MAPPING.get(industry, [])
        if not sic_codes:
            logger.warning(f"Unknown industry: {industry}")
            return []
        
        companies = []
        
        # Search by each SIC code
        for sic in sic_codes[:3]:  # Limit to avoid too many requests
            try:
                async with aiohttp.ClientSession() as session:
                    params = {
                        "action": "getcompany",
                        "SIC": sic,
                        "owner": "exclude",
                        "match": "",
                        "count": min(limit, 100),
                        "output": "atom"
                    }
                    
                    async with session.get(
                        self.base_url,
                        params=params,
                        headers=self.headers
                    ) as response:
                        if response.status == 200:
                            # Parse response (simplified)
                            # In production, parse the atom feed properly
                            logger.info(f"Found companies for SIC {sic}")
                        else:
                            logger.warning(f"Failed to fetch for SIC {sic}: {response.status}")
                
                await asyncio.sleep(0.1)  # Rate limiting
            
            except Exception as e:
                logger.error(f"Error searching SIC {sic}: {e}")
        
        return companies[:limit]
    
    async def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company facts including market cap from SEC API.
        
        Args:
            cik: Company CIK
        
        Returns:
            Company facts dict or None
        """
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to get facts for CIK {cik}: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Error getting facts for CIK {cik}: {e}")
            return None
    
    def categorize_market_cap(self, market_cap_value: float) -> MarketCapCategory:
        """
        Categorize market cap value.
        
        Args:
            market_cap_value: Market cap in dollars
        
        Returns:
            Market cap category
        """
        if market_cap_value < 2_000_000_000:
            return MarketCapCategory.SMALL
        elif market_cap_value < 10_000_000_000:
            return MarketCapCategory.MID
        elif market_cap_value < 200_000_000_000:
            return MarketCapCategory.LARGE
        else:
            return MarketCapCategory.MEGA
    
    async def search_companies(
        self,
        market_cap: Optional[List[str]] = None,
        industry: Optional[List[str]] = None,
        sector: Optional[List[str]] = None,
        limit: int = 50,
        use_realtime_lookup: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search companies with multiple filters.
        
        Args:
            market_cap: List of market cap categories (SMALL, MID, LARGE, MEGA)
            industry: List of industries
            sector: List of sectors
            limit: Maximum companies to return
            use_realtime_lookup: If True, uses Yahoo Finance API for all 14k+ companies
        
        Returns:
            List of company dicts matching the filters
        """
        all_companies = []
        
        try:
            # Step 1: Get all companies from SEC
            async with aiohttp.ClientSession() as session:
                url = "https://www.sec.gov/files/company_tickers.json"
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Convert to list
                        for key, company in data.items():
                            all_companies.append({
                                "cik": str(company.get("cik_str", "")).zfill(10),
                                "ticker": company.get("ticker", ""),
                                "name": company.get("title", "")
                            })
                    else:
                        logger.error(f"Failed to fetch SEC companies: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Error fetching companies from SEC: {e}")
            return []
        
        logger.info(f"Fetched {len(all_companies)} companies from SEC")
        
        # If no market cap filter, return first 'limit' companies
        if not market_cap:
            return all_companies[:limit]
        
        # Filter by market cap
        if use_realtime_lookup:
            filtered_companies = await self._filter_by_realtime_market_cap(
                all_companies, market_cap, limit
            )
        else:
            filtered_companies = self._filter_by_static_market_cap(
                all_companies, market_cap, limit
            )
        
        logger.info(f"Filtered to {len(filtered_companies)} companies matching {market_cap}")
        return filtered_companies
    
    async def _filter_by_realtime_market_cap(
        self,
        companies: List[Dict[str, Any]],
        market_cap_tiers: List[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Filter using real-time Yahoo Finance market cap lookup"""
        logger.info(f"Using real-time market cap lookup for filtering...")
        
        # OPTIMIZATION: Only check tickers until we have enough matches
        # Check in batches and stop early if we reach the limit
        filtered = []
        checked_count = 0
        
        # Process companies in chunks
        chunk_size = 50  # Check 50 companies at a time
        
        for i in range(0, len(companies), chunk_size):
            # Stop if we already have enough matches
            if len(filtered) >= limit:
                logger.info(f"Found {len(filtered)} matches, stopping early")
                break
            
            chunk = companies[i:i + chunk_size]
            tickers = [c["ticker"] for c in chunk if c.get("ticker")]
            
            if not tickers:
                continue
            
            checked_count += len(tickers)
            batch_num = (i // chunk_size) + 1
            
            logger.info(f"Checking batch {batch_num}: {len(tickers)} companies (checked {checked_count} total, found {len(filtered)} matches so far)")
            
            # Lookup this batch (reduced concurrency for reliability)
            ticker_to_tier = await self.market_cap_lookup.batch_lookup(tickers, max_concurrent=5)
            
            # Check matches in this batch
            for company in chunk:
                if len(filtered) >= limit:
                    break
                    
                ticker = company["ticker"]
                tier = ticker_to_tier.get(ticker)
                
                if tier and tier.value.upper() in [t.upper() for t in market_cap_tiers]:
                    company["market_cap_tier"] = tier.value.upper()
                    filtered.append(company)
                    logger.info(f"✓ Match found: {company['name']} ({ticker}) - {tier.value}")
        
        logger.info(f"Real-time lookup complete: Found {len(filtered)} matches after checking {checked_count} companies")
        return filtered
    
    def _filter_by_static_market_cap(
        self,
        companies: List[Dict[str, Any]],
        market_cap_tiers: List[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Filter using static market cap mapping (fast but limited to ~100 companies)"""
        logger.info(f"Using static market cap mapping")
        
        # Get static mappings
        static_mappings = self._get_market_cap_mappings()
        
        # Get allowed tickers from static mapping
        allowed_tickers = set()
        for tier in market_cap_tiers:
            tier_upper = tier.upper()
            for ticker, mapped_tier in static_mappings.items():
                if mapped_tier == tier_upper:
                    allowed_tickers.add(ticker)
        
        # Filter companies
        filtered = []
        for company in companies:
            if company["ticker"] in allowed_tickers:
                company["market_cap_tier"] = static_mappings.get(company["ticker"])
                filtered.append(company)
                
                if len(filtered) >= limit:
                    break
        
        return filtered
    
    def _get_market_cap_mappings(self) -> Dict[str, str]:
        """
        Get a mapping of ticker symbols to market cap categories.
        This is a static mapping for MVP. In production, fetch from real-time data.
        
        Returns:
            Dict mapping ticker to market cap category
        """
        return {
            # MEGA CAP (> $200B)
            "AAPL": "MEGA", "MSFT": "MEGA", "GOOGL": "MEGA", "GOOG": "MEGA",
            "AMZN": "MEGA", "NVDA": "MEGA", "META": "MEGA", "TSLA": "MEGA",
            "BRK.B": "MEGA", "BRK.A": "MEGA", "V": "MEGA", "JPM": "MEGA",
            "WMT": "MEGA", "UNH": "MEGA", "XOM": "MEGA", "JNJ": "MEGA",
            "MA": "MEGA", "PG": "MEGA", "HD": "MEGA", "CVX": "MEGA",
            "AVGO": "MEGA", "MRK": "MEGA", "LLY": "MEGA", "ABBV": "MEGA",
            "PEP": "MEGA", "COST": "MEGA", "KO": "MEGA", "ADBE": "MEGA",
            
            # LARGE CAP ($10B - $200B)
            "NFLX": "LARGE", "CSCO": "LARGE", "INTC": "LARGE", "AMD": "LARGE",
            "CRM": "LARGE", "NKE": "LARGE", "DIS": "LARGE", "ORCL": "LARGE",
            "QCOM": "LARGE", "TXN": "LARGE", "IBM": "LARGE", "AMGN": "LARGE",
            "HON": "LARGE", "UPS": "LARGE", "LOW": "LARGE", "BA": "LARGE",
            "GE": "LARGE", "SBUX": "LARGE", "CAT": "LARGE", "GS": "LARGE",
            "AXP": "LARGE", "MMM": "LARGE", "NOW": "LARGE", "ISRG": "LARGE",
            "SPGI": "LARGE", "BLK": "LARGE", "TJX": "LARGE", "BKNG": "LARGE",
            "SYK": "LARGE", "GILD": "LARGE", "MDLZ": "LARGE", "ZTS": "LARGE",
            "VRTX": "LARGE", "REGN": "LARGE", "LRCX": "LARGE", "AMAT": "LARGE",
            "ADI": "LARGE", "KLAC": "LARGE", "SNPS": "LARGE", "CDNS": "LARGE",
            "MRVL": "LARGE", "PANW": "LARGE", "MU": "LARGE", "NXPI": "LARGE",
            
            # MID CAP ($2B - $10B)
            "OKTA": "MID", "DDOG": "MID", "NET": "MID", "SNOW": "MID",
            "CRWD": "MID", "ZS": "MID", "PLTR": "MID", "TEAM": "MID",
            "DOCU": "MID", "TWLO": "MID", "MDB": "MID", "COUP": "MID",
            "ESTC": "MID", "SPLK": "MID", "ZM": "MID", "SHOP": "MID",
            "SQ": "MID", "PYPL": "MID", "ROKU": "MID", "LYFT": "MID",
            "UBER": "MID", "ABNB": "MID", "DASH": "MID", "COIN": "MID",
            
            # SMALL CAP (< $2B)
            "SMAR": "SMALL", "FROG": "SMALL", "BILL": "SMALL", "AI": "SMALL",
            "PATH": "SMALL", "GTLB": "SMALL", "S": "SMALL", "CFLT": "SMALL",
            "NCNO": "SMALL", "DT": "SMALL", "TENB": "SMALL", "ALRM": "SMALL",
            "QLYS": "SMALL", "VRNS": "SMALL", "PING": "SMALL", "FSLY": "SMALL",
        }



async def get_companies_by_names(
    company_names: List[str],
    user_agent: str
) -> List[Dict[str, str]]:
    """
    Search for specific companies by name.
    
    Args:
        company_names: List of company names to search
        user_agent: SEC API user agent
    
    Returns:
        List of matched companies with cik, name, ticker
    """
    from src.utils.sec_api import SECAPI
    
    api = SECAPI(user_agent)
    results = []
    
    for name in company_names:
        try:
            candidates = await api.search_company(name)
            if candidates:
                # Take best match (first one)
                results.append(candidates[0])
            await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            logger.error(f"Error searching for {name}: {e}")
    
    return results
