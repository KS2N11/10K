"""
Test script to verify small cap filtering logic.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.market_cap_lookup import MarketCapLookup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_market_cap_lookup():
    """Test market cap lookup for various companies."""
    
    lookup = MarketCapLookup()
    
    # Test companies with different market caps
    test_companies = [
        {"cik": "0000789019", "ticker": "MSFT", "expected": "MEGA"},  # Microsoft
        {"cik": "0001018724", "ticker": "AMZN", "expected": "MEGA"},  # Amazon
        {"cik": "0001364954", "ticker": "UBER", "expected": "LARGE"},  # Uber
        {"cik": "0001535527", "ticker": "BILL", "expected": "SMALL"},  # Bill.com
        {"cik": "0001616344", "ticker": "CRWD", "expected": "LARGE"},  # CrowdStrike
    ]
    
    logger.info("Testing market cap lookup for sample companies...\n")
    
    for company in test_companies:
        cik = company["cik"]
        ticker = company["ticker"]
        expected = company["expected"]
        
        logger.info(f"Testing {ticker} (CIK: {cik})...")
        
        info = await lookup.get_company_info(cik, ticker)
        
        if info:
            market_cap_dollars = info.get("market_cap_dollars")
            market_cap_billions = info.get("market_cap_billions")
            tier = lookup.categorize_market_cap(market_cap_billions)
            is_small = lookup.is_small_cap(market_cap_dollars)
            
            logger.info(f"  ✓ Market Cap: ${market_cap_billions:.2f}B (${market_cap_dollars:,})")
            logger.info(f"  ✓ Tier: {tier.value if tier else 'Unknown'} (expected: {expected})")
            logger.info(f"  ✓ Is Small Cap (< $2B): {is_small}")
            
            if tier and tier.value != expected:
                logger.warning(f"  ⚠️  Expected {expected} but got {tier.value}")
        else:
            logger.error(f"  ✗ Could not fetch market cap data")
        
        logger.info("")
    
    logger.info("=" * 60)
    logger.info("Testing is_small_cap filter...")
    logger.info("=" * 60)
    
    # Test small cap filtering
    test_values = [
        (500_000_000, True, "500M"),
        (1_500_000_000, True, "1.5B"),
        (2_000_000_000, False, "2B"),
        (5_000_000_000, False, "5B"),
        (None, True, "Unknown")
    ]
    
    for value, expected_small, label in test_values:
        is_small = lookup.is_small_cap(value)
        status = "✓" if is_small == expected_small else "✗"
        logger.info(f"{status} {label}: is_small_cap={is_small} (expected: {expected_small})")


async def test_scheduler_filter():
    """Test that scheduler correctly filters small cap companies."""
    from src.database.database import get_db
    from src.database.models import Company
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing database small cap filter...")
    logger.info("=" * 60)
    
    with get_db() as db:
        # Count companies by market cap
        all_companies = db.query(Company).count()
        companies_with_cap = db.query(Company).filter(
            Company.market_cap_value.isnot(None)
        ).count()
        
        small_cap_companies = db.query(Company).filter(
            Company.market_cap_value < 2_000_000_000
        ).count()
        
        large_cap_companies = db.query(Company).filter(
            Company.market_cap_value >= 2_000_000_000
        ).count()
        
        logger.info(f"Total companies in database: {all_companies}")
        logger.info(f"Companies with market cap data: {companies_with_cap}")
        logger.info(f"Small cap companies (< $2B): {small_cap_companies}")
        logger.info(f"Large cap companies (>= $2B): {large_cap_companies}")
        
        if companies_with_cap > 0:
            logger.info(f"Small cap percentage: {(small_cap_companies / companies_with_cap * 100):.1f}%")
        
        # Show some examples
        if small_cap_companies > 0:
            logger.info("\nSample small cap companies:")
            small_caps = db.query(Company).filter(
                Company.market_cap_value < 2_000_000_000
            ).limit(5).all()
            
            for c in small_caps:
                market_cap_b = c.market_cap_value / 1_000_000_000 if c.market_cap_value else 0
                logger.info(f"  🎯 {c.name} ({c.ticker}): ${market_cap_b:.2f}B")


if __name__ == "__main__":
    logger.info("Starting small cap filter tests...\n")
    
    # Run tests
    asyncio.run(test_market_cap_lookup())
    asyncio.run(test_scheduler_filter())
    
    logger.info("\n✅ All tests complete!")
