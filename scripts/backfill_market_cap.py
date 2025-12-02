"""
Backfill market cap data for existing companies in the database.
Uses SEC Company Facts API to fetch market cap values.
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.database.database import get_db
from src.database.models import Company, MarketCap
from src.utils.market_cap_lookup import MarketCapLookup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def backfill_market_cap_for_companies(batch_size: int = 50, 
                                            max_companies: Optional[int] = None):
    """
    Backfill market cap for companies missing data.
    
    Args:
        batch_size: Number of companies to process in parallel
        max_companies: Maximum number of companies to process (None = all)
    """
    print("Function called...")
    logger.info("=" * 80)
    logger.info("Starting market cap backfill...")
    logger.info("=" * 80)
    
    print("Creating lookup...")
    lookup = MarketCapLookup()
    total_updated = 0
    total_failed = 0
    total_processed = 0
    
    print("Getting database connection...")
    try:
        with get_db() as db:
            print("Connected to database...")
            
            # First, get total count of all companies
            print("Querying total company count...")
            total_company_count = db.query(Company).count()
            print(f"Total companies in database: {total_company_count}")
            logger.info(f"Total companies in database: {total_company_count}")
            
            # Get companies without market_cap_value
            print("Querying companies without market cap...")
            query = db.query(Company).filter(Company.market_cap_value.is_(None))
            
            if max_companies:
                query = query.limit(max_companies)
            
            print("Fetching companies from database...")
            companies = query.all()
            total_companies = len(companies)
            
            print(f"Found {total_companies} companies without market cap data")
            logger.info(f"Found {total_companies} companies without market cap data")
            
            if not companies:
                print("✅ No companies need backfill - all companies already have market cap data!")
                logger.info("✅ No companies need backfill - all companies already have market cap data!")
                logger.info("=" * 80)
                return
    except Exception as e:
        print(f"Error connecting to database: {e}")
        logger.error(f"Database connection error: {e}", exc_info=True)
        raise
        
        # Process in batches
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(companies) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} companies)...")
            
            # Prepare batch data
            batch_data = [
                {"cik": company.cik, "ticker": company.ticker}
                for company in batch
            ]
            
            # Fetch market cap for batch
            try:
                results = await lookup.batch_lookup_with_sector(batch_data, max_concurrent=20)
                
                # Update database
                for company in batch:
                    ticker_or_cik = company.ticker or company.cik
                    result = results.get(ticker_or_cik)
                    
                    if result and result.get("market_cap_dollars"):
                        # Update market cap value
                        company.market_cap_value = result["market_cap_dollars"]
                        
                        # Update tier
                        if result.get("tier"):
                            company.market_cap = result["tier"]
                        
                        # Update sector/industry if available
                        if result.get("sector") and result["sector"] != "Unknown":
                            company.sector = result["sector"]
                        if result.get("industry") and result["industry"] != "Unknown":
                            company.industry = result["industry"]
                        
                        total_updated += 1
                        
                        market_cap_billions = result["market_cap_dollars"] / 1_000_000_000
                        is_small_cap = "🎯" if result["market_cap_dollars"] < 2_000_000_000 else ""
                        
                        logger.info(
                            f"  ✓ [{total_processed + 1}/{total_companies}] {company.name} ({company.ticker}): "
                            f"${market_cap_billions:.2f}B {is_small_cap}"
                        )
                    else:
                        total_failed += 1
                        logger.warning(
                            f"  ✗ [{total_processed + 1}/{total_companies}] {company.name} ({company.ticker}): "
                            f"No market cap data available"
                        )
                    
                    total_processed += 1
                
                # Commit batch
                db.commit()
                logger.info(f"Batch {batch_num} committed to database")
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                total_failed += len(batch)
                total_processed += len(batch)
            
            # Rate limiting - be nice to SEC API
            if i + batch_size < len(companies):
                await asyncio.sleep(1)
        
        # Final summary
        logger.info("=" * 80)
        logger.info(f"✅ Backfill complete!")
        logger.info(f"Total processed: {total_processed}")
        logger.info(f"Successfully updated: {total_updated}")
        logger.info(f"Failed: {total_failed}")
        logger.info(f"Success rate: {(total_updated / total_processed * 100):.1f}%")
        
        # Count small cap companies
        small_cap_count = db.query(Company).filter(
            Company.market_cap_value < 2_000_000_000
        ).count()
        logger.info(f"Small cap companies (< $2B): {small_cap_count}")
        logger.info("=" * 80)


async def backfill_specific_company(cik: str):
    """Backfill market cap for a specific company by CIK."""
    logger.info(f"Fetching market cap for CIK {cik}...")
    
    lookup = MarketCapLookup()
    
    with get_db() as db:
        company = db.query(Company).filter(Company.cik == cik).first()
        
        if not company:
            logger.error(f"Company with CIK {cik} not found in database")
            return
        
        logger.info(f"Found company: {company.name} ({company.ticker})")
        
        # Fetch market cap
        info = await lookup.get_company_info(company.cik, company.ticker)
        
        if info and info.get("market_cap_dollars"):
            company.market_cap_value = info["market_cap_dollars"]
            
            # Determine tier
            market_cap_billions = info["market_cap_billions"]
            if market_cap_billions < 2:
                company.market_cap = MarketCap.SMALL
            elif market_cap_billions < 10:
                company.market_cap = MarketCap.MID
            elif market_cap_billions < 200:
                company.market_cap = MarketCap.LARGE
            else:
                company.market_cap = MarketCap.MEGA
            
            # Update sector/industry
            if info.get("sector") and info["sector"] != "Unknown":
                company.sector = info["sector"]
            if info.get("industry") and info["industry"] != "Unknown":
                company.industry = info["industry"]
            
            db.commit()
            
            is_small_cap = "🎯 SMALL CAP" if info["market_cap_dollars"] < 2_000_000_000 else ""
            logger.info(
                f"✅ Updated {company.name}: "
                f"${info['market_cap_billions']:.2f}B "
                f"({company.market_cap.value}) {is_small_cap}"
            )
        else:
            logger.error(f"Could not fetch market cap for {company.name}")


if __name__ == "__main__":
    import argparse
    
    print("Starting backfill script...")
    
    parser = argparse.ArgumentParser(description="Backfill market cap data for companies")
    parser.add_argument("--cik", type=str, help="Backfill specific company by CIK")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--max", type=int, help="Maximum number of companies to process")
    
    args = parser.parse_args()
    
    if args.cik:
        asyncio.run(backfill_specific_company(args.cik))
    else:
        asyncio.run(backfill_market_cap_for_companies(args.batch_size, args.max))
