"""
Hybrid market cap lookup using SEC Company Facts API for market cap
and Yahoo Finance for sector/industry (only when needed).

SEC API: Free, unlimited, authoritative for market cap
Yahoo Finance: Used sparingly only for sector/industry info
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple
from enum import Enum
import aiohttp
import time

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class MarketCapTier(str, Enum):
    """Market cap tiers"""
    SMALL = "SMALL"   # < $2B
    MID = "MID"       # $2B - $10B
    LARGE = "LARGE"   # $10B - $200B
    MEGA = "MEGA"     # > $200B


class MarketCapLookup:
    """
    Lookup market cap and sector for companies using SEC Company Facts API.
    Falls back to static mapping if SEC data unavailable.
    Results are cached in-memory to avoid repeated API calls.
    """
    
    # SIC code to sector mapping
    SIC_TO_SECTOR = {
        # Technology (7000-7999)
        range(7000, 8000): "Technology",
        # Healthcare (8000-8099)
        range(8000, 8100): "Healthcare",
        # Finance (6000-6999)
        range(6000, 7000): "Financial Services",
        # Manufacturing (2000-3999)
        range(2000, 4000): "Industrials",
        # Retail (5000-5999)
        range(5000, 6000): "Consumer Cyclical",
        # Energy (1000-1499, 2900-2999)
        range(1000, 1500): "Energy",
        range(2900, 3000): "Energy",
        # Utilities (4900-4999)
        range(4900, 5000): "Utilities",
        # Real Estate (6500-6599)
        range(6500, 6600): "Real Estate",
        # Transportation (4000-4799)
        range(4000, 4800): "Industrials",
    }
    
    def __init__(self, user_agent: str = "10K-Insight-Agent/1.0 (contact@example.com)"):
        # Cache format: {cik: {"market_cap_billions": float, "sector": str, "industry": str}}
        self.cache: Dict[str, Optional[Dict]] = {}
        self.user_agent = user_agent
        self.headers = {"User-Agent": user_agent}
    
    def _sic_to_sector(self, sic: Optional[int]) -> str:
        """Convert SIC code to sector name"""
        if not sic:
            return "Unknown"
        
        for sic_range, sector in self.SIC_TO_SECTOR.items():
            if sic in sic_range:
                return sector
        
        return "Other"
    
    async def _fetch_sec_company_facts(self, cik: str) -> Optional[Dict]:
        """
        Fetch company facts from SEC API including market cap from recent filings.
        
        Returns:
            Dict with market_cap_billions, sector, industry or None
        """
        try:
            cik_padded = cik.zfill(10)
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.debug(f"SEC API returned {response.status} for CIK {cik}")
                        return None
                    
                    data = await response.json()
                    
                    # Extract entity info
                    entity_name = data.get("entityName", "Unknown")
                    
                    # Get facts first
                    facts = data.get("facts", {})
                    
                    # SIC code might be in different places
                    sic = None
                    sic_description = "Unknown"
                    
                    # Get SIC from entity level (if available)
                    if "sic" in data:
                        try:
                            sic = int(data["sic"]) if data["sic"] else None
                        except:
                            pass
                    if "sicDescription" in data:
                        sic_description = data["sicDescription"]
                    
                    # Try to get market cap from EntityPublicFloat
                    market_cap_billions = None
                    
                    # Check DEI (Document and Entity Information) for EntityPublicFloat
                    dei = facts.get("dei", {})
                    us_gaap = facts.get("us-gaap", {})
                    
                    # Try EntityPublicFloat first (most recent public float) - in DEI taxonomy
                    if "EntityPublicFloat" in dei:
                        units = dei["EntityPublicFloat"].get("units", {})
                        usd_data = units.get("USD", [])
                        if usd_data:
                            # Get most recent value
                            latest = sorted(usd_data, key=lambda x: x.get("filed", ""), reverse=True)[0]
                            market_cap = latest.get("val")
                            if market_cap:
                                market_cap_billions = market_cap / 1_000_000_000
                                logger.debug(f"  Using EntityPublicFloat: ${market_cap_billions:.2f}B")
                    
                    # Fallback 1: Use StockholdersEquity as proxy (book value)
                    if not market_cap_billions and "StockholdersEquity" in us_gaap:
                        units = us_gaap["StockholdersEquity"].get("units", {})
                        usd_data = units.get("USD", [])
                        if usd_data:
                            latest = sorted(usd_data, key=lambda x: x.get("end", ""), reverse=True)[0]
                            equity = latest.get("val")
                            if equity:
                                # Use a 2x multiple for market cap estimate (conservative)
                                market_cap_billions = (equity * 2) / 1_000_000_000
                                logger.debug(f"  Using StockholdersEquity * 2: ${market_cap_billions:.2f}B")
                    
                    # Fallback 2: Use Assets as very rough proxy
                    if not market_cap_billions and "Assets" in us_gaap:
                        units = us_gaap["Assets"].get("units", {})
                        usd_data = units.get("USD", [])
                        if usd_data:
                            latest = sorted(usd_data, key=lambda x: x.get("end", ""), reverse=True)[0]
                            assets = latest.get("val")
                            if assets:
                                # Use a conservative 0.5x multiple for market cap estimate
                                market_cap_billions = (assets * 0.5) / 1_000_000_000
                                logger.debug(f"  Using Assets * 0.5: ${market_cap_billions:.2f}B")
                    
                    sector = self._sic_to_sector(sic) if sic else "Unknown"
                    
                    if market_cap_billions:
                        logger.debug(f"✓ CIK {cik} ({entity_name}): ${market_cap_billions:.2f}B, {sector}")
                        return {
                            "market_cap_billions": market_cap_billions,
                            "sector": sector,
                            "industry": sic_description,
                            "has_sec_data": True
                        }
                    else:
                        logger.debug(f"No market cap data found for CIK {cik}")
                        return None
                    
        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching SEC data for CIK {cik}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching SEC data for CIK {cik}: {e}")
            return None
    
    async def _enrich_with_yfinance(self, ticker: str) -> Optional[Dict]:
        """
        Get sector and industry from Yahoo Finance (used when SEC doesn't have it).
        Only called when necessary to minimize API calls.
        """
        if not YFINANCE_AVAILABLE or not ticker:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            info = await loop.run_in_executor(None, lambda: stock.info)
            
            return {
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown")
            }
        except Exception as e:
            logger.debug(f"Failed to get Yahoo Finance data for {ticker}: {e}")
            return None
    
    async def get_company_info(self, cik: str, ticker: Optional[str] = None, enrich_sector: bool = True) -> Optional[Dict]:
        """
        Get market cap, sector, and industry for a company by CIK.
        Uses cache to avoid repeated API calls.
        
        Args:
            cik: Company CIK number
            ticker: Optional ticker symbol (for sector enrichment and logging)
            enrich_sector: If True and SEC doesn't have sector, try Yahoo Finance
        
        Returns:
            Dict with market_cap_billions, sector, industry or None
        """
        # Check cache first
        cache_key = cik
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Fetch from SEC API (primary source for market cap)
        info = await self._fetch_sec_company_facts(cik)
        
        # Enrich with Yahoo Finance if sector is Unknown and we have a ticker
        if info and enrich_sector and ticker and info.get("sector") == "Unknown":
            yf_data = await self._enrich_with_yfinance(ticker)
            if yf_data:
                info["sector"] = yf_data.get("sector", info["sector"])
                info["industry"] = yf_data.get("industry", info["industry"])
                logger.debug(f"  Enriched with Yahoo Finance: {yf_data['sector']}")
        
        # Cache result (even if None to avoid retry)
        self.cache[cache_key] = info
        return info
    
    def categorize_market_cap(self, market_cap_billions: Optional[float]) -> Optional[MarketCapTier]:
        """Categorize market cap into tier"""
        if market_cap_billions is None:
            return None
        
        if market_cap_billions < 2:
            return MarketCapTier.SMALL
        elif market_cap_billions < 10:
            return MarketCapTier.MID
        elif market_cap_billions < 200:
            return MarketCapTier.LARGE
        else:
            return MarketCapTier.MEGA
    
    async def batch_lookup(
        self, 
        companies: list[Dict[str, str]], 
        max_concurrent: int = 20
    ) -> Dict[str, Optional[MarketCapTier]]:
        """
        Lookup market cap tiers for multiple companies.
        
        Args:
            companies: List of dicts with 'cik' and 'ticker' keys
            max_concurrent: Max concurrent requests
        
        Returns:
            Dict of ticker -> MarketCapTier
        """
        results = {}
        
        # SEC API is fast, we can use larger batches
        for i in range(0, len(companies), max_concurrent):
            batch = companies[i:i + max_concurrent]
            
            # Fetch all in parallel
            tasks = [
                self.get_company_info(c["cik"], c.get("ticker")) 
                for c in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for company, info in zip(batch, batch_results):
                ticker = company.get("ticker", company["cik"])
                if isinstance(info, Exception):
                    logger.debug(f"Exception for {ticker}: {info}")
                    results[ticker] = None
                elif info is None:
                    results[ticker] = None
                else:
                    market_cap = info.get("market_cap_billions")
                    tier = self.categorize_market_cap(market_cap)
                    results[ticker] = tier
            
            # Small delay between batches to respect SEC rate limits
            if i + max_concurrent < len(companies):
                await asyncio.sleep(0.2)
        
        return results
    
    async def batch_lookup_with_sector(
        self, 
        companies: list[Dict[str, str]], 
        max_concurrent: int = 20
    ) -> Dict[str, Optional[Dict]]:
        """
        Lookup market cap tier, sector, and industry for multiple companies.
        
        Args:
            companies: List of dicts with 'cik' and 'ticker' keys
            max_concurrent: Max concurrent requests (SEC API is fast, can handle 20+)
        
        Returns:
            Dict of ticker -> {"tier": MarketCapTier, "sector": str, "industry": str}
        """
        results = {}
        
        # SEC API is reliable and fast, can use larger batches
        for i in range(0, len(companies), max_concurrent):
            batch = companies[i:i + max_concurrent]
            
            # Fetch all in parallel
            tasks = [
                self.get_company_info(c["cik"], c.get("ticker")) 
                for c in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for company, info in zip(batch, batch_results):
                ticker = company.get("ticker", company["cik"])
                if isinstance(info, Exception) or info is None:
                    results[ticker] = None
                else:
                    market_cap = info.get("market_cap_billions")
                    tier = self.categorize_market_cap(market_cap)
                    results[ticker] = {
                        "tier": tier,
                        "sector": info.get("sector", "Unknown"),
                        "industry": info.get("industry", "Unknown")
                    }
            
            # Minimal delay between batches (SEC API is reliable and has no strict rate limit)
            if i + max_concurrent < len(companies):
                await asyncio.sleep(0.05)
        
        return results
