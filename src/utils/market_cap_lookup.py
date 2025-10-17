"""
Real-time market cap lookup for SEC companies using Yahoo Finance.
"""
import asyncio
import logging
from typing import Dict, Optional
import httpx
from enum import Enum

logger = logging.getLogger(__name__)


class MarketCapTier(str, Enum):
    """Market cap tiers"""
    SMALL = "SMALL"   # < $2B
    MID = "MID"       # $2B - $10B
    LARGE = "LARGE"   # $10B - $200B
    MEGA = "MEGA"     # > $200B


class MarketCapLookup:
    """
    Lookup market cap for companies using Yahoo Finance API.
    Includes caching to reduce API calls.
    """
    
    def __init__(self):
        self.cache: Dict[str, Optional[float]] = {}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    async def get_market_cap(self, ticker: str) -> Optional[float]:
        """
        Get market cap for a ticker in billions.
        Returns None if lookup fails.
        """
        if ticker in self.cache:
            return self.cache[ticker]
        
        try:
            url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
            params = {
                "modules": "price,summaryDetail"
            }
            
            # Increased timeout to 10 seconds
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    data = response.json()
                    market_cap_raw = data.get("quoteSummary", {}).get("result", [{}])[0].get("price", {}).get("marketCap", {}).get("raw")
                    
                    if market_cap_raw:
                        # Convert to billions
                        market_cap_billions = market_cap_raw / 1_000_000_000
                        self.cache[ticker] = market_cap_billions
                        logger.debug(f"Found market cap for {ticker}: ${market_cap_billions:.2f}B")
                        return market_cap_billions
        
        except httpx.TimeoutException:
            logger.warning(f"Timeout looking up market cap for {ticker}")
        except Exception as e:
            logger.debug(f"Failed to lookup market cap for {ticker}: {e}")
        
        self.cache[ticker] = None
        return None
    
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
    
    async def batch_lookup(self, tickers: list[str], max_concurrent: int = 5) -> Dict[str, Optional[MarketCapTier]]:
        """
        Lookup market cap for multiple tickers concurrently.
        Returns dict of ticker -> MarketCapTier
        
        Default max_concurrent reduced to 5 for better reliability.
        """
        results = {}
        total_tickers = len(tickers)
        
        logger.info(f"Starting batch lookup for {total_tickers} tickers (max {max_concurrent} concurrent)...")
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(tickers), max_concurrent):
            batch = tickers[i:i + max_concurrent]
            batch_num = (i // max_concurrent) + 1
            total_batches = (len(tickers) + max_concurrent - 1) // max_concurrent
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
            
            tasks = [self.get_market_cap(ticker) for ticker in batch]
            market_caps = await asyncio.gather(*tasks, return_exceptions=True)
            
            for ticker, mc in zip(batch, market_caps):
                if isinstance(mc, Exception):
                    logger.warning(f"Exception for {ticker}: {mc}")
                    results[ticker] = None
                else:
                    results[ticker] = self.categorize_market_cap(mc)
            
            # Small delay between batches to avoid rate limiting
            if i + max_concurrent < len(tickers):
                await asyncio.sleep(0.3)  # Reduced delay
        
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"Batch lookup complete: {successful}/{total_tickers} successful")
        
        return results
