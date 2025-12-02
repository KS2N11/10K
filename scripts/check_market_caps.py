"""Check market cap values for companies selected by scheduler."""
from src.database.database import get_db
from src.database.models import Company

# First check overall stats
with get_db() as db:
    total = db.query(Company).count()
    with_value = db.query(Company).filter(Company.market_cap_value.isnot(None)).count()
    without_value = db.query(Company).filter(Company.market_cap_value.is_(None)).count()
    
    print("DATABASE STATISTICS:")
    print("="*80)
    print(f"Total companies: {total}")
    print(f"With market_cap_value: {with_value}")
    print(f"Without market_cap_value (NULL): {without_value}")
    print()

# Check specific tickers
tickers = ['FSLY', 'AI', 'BILL', 'PATH', 'ALRM', 'LYFT', 'GTLB']

with get_db() as db:
    companies = db.query(Company).filter(Company.ticker.in_(tickers)).all()
    
    print(f"Found {len(companies)} companies:")
    print("="*80)
    for c in companies:
        print(f"{c.ticker:6} - {c.name:40} - market_cap_value: ${c.market_cap_value:,}" if c.market_cap_value else f"{c.ticker:6} - {c.name:40} - market_cap_value: None")
    
    print("\n" + "="*80)
    small_cap_threshold = 2_000_000_000
    small_caps = [c for c in companies if c.market_cap_value and c.market_cap_value < small_cap_threshold]
    large_caps = [c for c in companies if c.market_cap_value and c.market_cap_value >= small_cap_threshold]
    unknown = [c for c in companies if c.market_cap_value is None]
    
    print(f"Small caps (< $2B): {len(small_caps)}")
    for c in small_caps:
        print(f"  - {c.ticker}: ${c.market_cap_value:,}")
    
    print(f"\nLarge/Mega caps (>= $2B): {len(large_caps)}")
    for c in large_caps:
        print(f"  - {c.ticker}: ${c.market_cap_value:,}")
    
    print(f"\nUnknown market cap: {len(unknown)}")
    for c in unknown:
        print(f"  - {c.ticker}")

print("\n" + "="*80)
print("ALL SMALL CAP COMPANIES IN DATABASE (< $2B):")
print("="*80)
with get_db() as db:
    all_small_caps = db.query(Company).filter(Company.market_cap_value < 2_000_000_000).all()
    print(f"Total small caps: {len(all_small_caps)}")
    for c in all_small_caps:
        print(f"  - {c.ticker:6} {c.name:50} ${c.market_cap_value:,}")
