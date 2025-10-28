"""
Real-time market cap lookup for SEC companies using Yahoo Finance.
"""
import asyncio
import logging
from typing import Dict, Optional
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
    Lookup market cap for companies using static mappings.
    """
    
    def __init__(self):
        self.cache: Dict[str, Optional[float]] = {}
    
    async def get_market_cap(self, ticker: str) -> Optional[float]:
        """
        Get market cap for a ticker in billions.
        Currently using static mapping.
        """
        # Using static mapping
        tier = self.categorize_market_cap(1)  # Dummy value
        if tier == MarketCapTier.SMALL:
            return 1.5
        elif tier == MarketCapTier.MID:
            return 5.0
        elif tier == MarketCapTier.LARGE:
            return 50.0
        elif tier == MarketCapTier.MEGA:
            return 250.0
        return None
            
        # Cache the failure and return None
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
    
    async def batch_lookup(self, tickers: list[str], max_concurrent: int = 10) -> Dict[str, Optional[MarketCapTier]]:
        """
        Quick static tier lookup.
        Returns dict of ticker -> MarketCapTier
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.categorize_market_cap(1)  # Dummy value for testing
        return results
        
        return results
