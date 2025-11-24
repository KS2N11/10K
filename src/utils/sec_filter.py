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
        
        # If no filters at all, return first 'limit' companies
        if not market_cap and not sector and not industry:
            return all_companies[:limit]
        
        # SMART ORDERING: For MEGA/LARGE caps, prioritize companies with tickers (likely larger)
        # For SMALL/MID caps, randomize for diversity
        import random
        if market_cap and any(tier in ["MEGA", "LARGE"] for tier in market_cap):
            # Prioritize companies WITH tickers (MEGA/LARGE caps almost always have tickers)
            companies_with_ticker = [c for c in all_companies if c.get("ticker")]
            companies_without_ticker = [c for c in all_companies if not c.get("ticker")]
            
            # Sort ticker companies by CIK (older CIKs = larger/older companies usually)
            companies_with_ticker.sort(key=lambda x: x.get("cik", ""))
            
            # Put tickers first, then shuffle no-ticker ones
            random.shuffle(companies_without_ticker)
            randomized_companies = companies_with_ticker + companies_without_ticker
            logger.info(f"Searching MEGA/LARGE caps: prioritizing {len(companies_with_ticker)} companies with tickers")
        else:
            # For SMALL/MID caps, full randomization works well (more of them in database)
            randomized_companies = list(all_companies)
            random.shuffle(randomized_companies)
            logger.info(f"Searching SMALL/MID caps: randomizing all {len(randomized_companies)} companies")
        
        # Filter by market cap (and optionally sector/industry)
        if use_realtime_lookup:
            filtered_companies = await self._filter_by_realtime_market_cap(
                randomized_companies, market_cap or [], limit,
                sector_filter=sector, industry_filter=industry
            )
        else:
            # Static mode only supports market cap filtering
            if sector or industry:
                logger.warning("Sector/Industry filtering only available with real-time lookup. Use use_realtime=True")
            filtered_companies = self._filter_by_static_market_cap(
                all_companies, market_cap or [], limit
            )
        
        logger.info(f"Filtered to {len(filtered_companies)} companies")
        return filtered_companies
    
    async def _filter_by_realtime_market_cap(
        self,
        companies: List[Dict[str, Any]],
        market_cap_tiers: List[str],
        limit: int,
        sector_filter: Optional[List[str]] = None,
        industry_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Filter using real-time Yahoo Finance market cap lookup with sector/industry filtering"""
        logger.info(f"Using real-time market cap lookup for filtering...")
        logger.info(f"Filters: market_cap={market_cap_tiers}, sectors={sector_filter}, industries={industry_filter}")
        

        
        # OPTIMIZATION: Only check tickers until we have enough matches
        # Check in batches and stop early if we reach the limit
        filtered = []
        checked_count = 0
        
        # Adaptive batch size based on market cap tier
        if any(tier in ["MEGA", "LARGE"] for tier in market_cap_tiers):
            chunk_size = 100  # MEGA/LARGE caps are rare, check many companies quickly
            max_companies_to_check = 1500  # Check up to 1500 to find all MEGA/LARGE (MSFT at pos ~1085)
        else:
            chunk_size = 50  # SMALL/MID caps are common, smaller batches work fine
            max_companies_to_check = 200  # Check up to 200 companies for SMALL/MID
        
        for i in range(0, min(len(companies), max_companies_to_check), chunk_size):
            # Stop if we already have enough matches
            if len(filtered) >= limit:
                logger.info(f"Found {len(filtered)} matches, stopping early")
                break
            
            # Stop if we've checked enough companies
            if checked_count >= max_companies_to_check:
                logger.info(f"Checked {checked_count} companies (limit: {max_companies_to_check}), stopping")
                break
            
            chunk = companies[i:i + chunk_size]
            # Filter out companies without ticker
            valid_companies = [c for c in chunk if c.get("ticker")]
            
            if not valid_companies:
                continue
            
            checked_count += len(valid_companies)
            batch_num = (i // chunk_size) + 1
            
            logger.info(f"Checking batch {batch_num}: {len(valid_companies)} companies (checked {checked_count} total, found {len(filtered)} matches so far)")
            
            # Lookup this batch with sector info - balanced concurrency (30 is sweet spot)
            ticker_to_info = await self.market_cap_lookup.batch_lookup_with_sector(valid_companies, max_concurrent=30)
            
            # Check matches in this batch
            for company in chunk:
                if len(filtered) >= limit:
                    break
                    
                ticker = company["ticker"]
                info = ticker_to_info.get(ticker)
                
                if not info:
                    continue
                
                tier = info.get("tier")
                sector = info.get("sector", "Unknown")
                industry = info.get("industry", "Unknown")
                
                # Check market cap tier
                if not tier or tier.value.upper() not in [t.upper() for t in market_cap_tiers]:
                    continue
                
                # Check sector filter (if provided) - MUST match, no "Unknown" allowed
                if sector_filter:
                    if sector == "Unknown" or sector not in sector_filter:
                        continue
                
                # Check industry filter (if provided) - MUST match, no "Unknown" allowed
                if industry_filter:
                    if industry == "Unknown" or industry not in industry_filter:
                        continue
                
                # All filters passed!
                company["market_cap_tier"] = tier.value.upper()
                company["sector"] = sector
                company["industry"] = industry
                filtered.append(company)
                logger.info(f"✓ Match: {company['name']} ({ticker}) - {tier.value}, {sector}, {industry}")
        
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
        
        # Filter companies - randomize order first
        filtered = []
        import random
        shuffled = list(companies)  # Create a copy
        random.shuffle(shuffled)  # Randomize order
        
        for company in shuffled:
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
