# Small Cap Company Focus Implementation

## Overview
This update modifies the autonomous scheduler to prioritize small cap companies (market cap < $2B) for analysis. This addresses feedback that the system was primarily analyzing large cap companies.

## Changes Made

### 1. Database Model Updates
**File:** `src/database/models.py`
- Changed `Company.market_cap_value` from `Float` to `Integer` to store actual market cap in dollars (not billions)
- This allows precise filtering and sorting by actual market cap value

### 2. Market Cap Lookup Service
**File:** `src/utils/market_cap_lookup.py`
- Updated `_fetch_sec_company_facts()` to return `market_cap_dollars` along with `market_cap_billions`
- Added `is_small_cap()` helper method to check if a company is below threshold (default $2B)
- Updated `batch_lookup_with_sector()` to include `market_cap_dollars` in results

### 3. Scheduler Updates
**File:** `src/services/scheduler_agent.py`
- Modified `_get_candidate_companies()` to support two filtering modes:
  - **TIERED MODE (default)**: Gradually expands market cap threshold to ensure candidates
  - **STRICT MODE**: Hard filter at specific threshold (configurable)
- Added logging to show filtering decisions
- Updated sorting logic to prioritize smaller market cap values
- Added market cap value to candidate data for better tracking

**Tiered Mode Logic (Default):**
The scheduler tries progressively larger thresholds until it finds enough candidates:
1. First tries: Companies < $2B (Small cap)
2. If insufficient: Companies < $4B (Small-to-Mid cap)
3. If insufficient: Companies < $10B (Mid cap)
4. If insufficient: Companies < $50B (Large cap)
5. If insufficient: All companies with known market cap

This ensures the scheduler **never returns empty** while still **prioritizing smaller companies**.

**Strict Mode:**
Set `strict_small_cap_threshold` in config to enforce a hard limit:
```python
config = {
    "strict_small_cap_threshold": 2_000_000_000  # Only < $2B, no expansion
}
```

**Key Implementation:**
```python
# Check config for strict mode
strict_threshold = self.config.get("strict_small_cap_threshold")
use_strict_mode = strict_threshold is not None

if use_strict_mode:
    # STRICT: Only companies < threshold, no fallback
    candidates = [c for c in all_candidates if c["market_cap_value"] < strict_threshold]
else:
    # TIERED: Try $2B -> $4B -> $10B -> $50B -> unlimited
    for tier_threshold in [2B, 4B, 10B, 50B, None]:
        candidates = [c for c in all_candidates if c["market_cap_value"] < tier_threshold]
        if len(candidates) >= limit:
            break  # Found enough candidates at this tier
```

Companies are always sorted by actual market cap value (smallest first), ensuring:
- Fastly ($1B) is selected before C3.ai ($1.5B)
- C3.ai ($1.5B) is selected before larger companies
- Within same market cap, priority score and staleness determine order

### 4. API Response Updates
**File:** `src/api/routes_v2.py`
- Added `market_cap_value` field to company search responses
- Added `company_market_cap_value` to analyses and pitches endpoints
- Allows frontend to display actual market cap values

### 5. Backfill Script
**File:** `scripts/backfill_market_cap.py`
- New script to populate market cap data for existing companies
- Uses SEC Company Facts API for reliable data
- Processes in batches with rate limiting
- Can backfill all companies or a specific company by CIK

**Usage:**
```bash
# Backfill all companies
python scripts/backfill_market_cap.py

# Backfill with custom batch size
python scripts/backfill_market_cap.py --batch-size 100

# Backfill specific number of companies
python scripts/backfill_market_cap.py --max 500

# Backfill specific company
python scripts/backfill_market_cap.py --cik 0001535527
```

### 6. Test Script
**File:** `scripts/test_small_cap_filter.py`
- Tests market cap lookup for sample companies
- Verifies `is_small_cap()` filter logic
- Shows database statistics on small vs large cap companies

**Usage:**
```bash
python scripts/test_small_cap_filter.py
```

## Implementation Steps

### Step 1: Run Database Migration (if needed)
If you use Alembic for migrations, create a migration for the column type change:
```bash
alembic revision -m "Change market_cap_value to Integer type"
alembic upgrade head
```

Or manually update the column:
```sql
ALTER TABLE companies ALTER COLUMN market_cap_value TYPE BIGINT;
```

### Step 2: Backfill Market Cap Data
Run the backfill script to populate market cap for existing companies:
```bash
cd c:\Projects\POC\agent10k\10K
python scripts/backfill_market_cap.py
```

This will:
- Fetch market cap from SEC Company Facts API
- Update `market_cap_value` (in dollars)
- Update `market_cap` tier (SMALL/MID/LARGE/MEGA)
- Update sector/industry if available

Expected output:
```
Found 200 companies without market cap data
Processing batch 1/4 (50 companies)...
  ✓ [1/200] Bill.com Holdings Inc (BILL): $4.52B 
  ✓ [2/200] Snowflake Inc (SNOW): $43.21B
  ...
✅ Backfill complete!
Total processed: 200
Successfully updated: 185
Failed: 15
Success rate: 92.5%
Small cap companies (< $2B): 67
```

### Step 3: Test the Changes
Run the test script to verify everything works:
```bash
python scripts/test_small_cap_filter.py
```

### Step 4: Restart Services
Restart the backend API and autonomous scheduler:
```bash
# Stop existing services
docker-compose down

# Start with updated code
docker-compose up -d
```

## Expected Behavior

### Before Changes
- Autonomous scheduler selected companies without market cap consideration
- Often analyzed large caps (Microsoft, Amazon, Apple, etc.)
- No easy way to filter or prioritize small caps

### After Changes
- Scheduler uses **tiered filtering** (default) or **strict filtering** (if configured)
- **Tiered mode**: Tries $2B → $4B → $10B → $50B → unlimited until enough candidates found
- **Strict mode**: Only companies below configured threshold, may return empty
- Companies **always sorted by market cap** (smallest first)
- Smaller companies prioritized within each tier
- **Never goes empty** in tiered mode

### Example Scheduler Log (Tiered Mode)
```
INFO - Using TIERED mode: $2B -> $4B -> $10B -> $50B -> unlimited
INFO - Fetching SMALL cap companies...
INFO - Found 150 total potential candidates
INFO - TIERED mode (< $2,000,000,000): Found 2 candidates
INFO - TIERED mode (< $4,000,000,000): Found 7 candidates
INFO - TIERED mode (< $10,000,000,000): Found 23 candidates
INFO - ✓ Sufficient candidates found at threshold: $10,000,000,000
INFO - Final candidate list: 23 companies sorted by market cap (smallest first)
INFO - Selected 10 companies for analysis: Fastly ($1B), C3.ai ($1.5B), Bill.com ($3.2B)...
```

### Example Scheduler Log (Strict Mode)
```
INFO - Using STRICT mode: Only companies < $2,000,000,000
INFO - Fetching SMALL cap companies...
INFO - Found 150 total potential candidates
INFO - STRICT mode: Filtered to 2 companies < $2,000,000,000
INFO - Final candidate list: 2 companies sorted by market cap (smallest first)
INFO - Selected 2 companies for analysis: Fastly ($1B), C3.ai ($1.5B)
```

## API Response Changes

### Companies Search Endpoint
**Before:**
```json
{
  "companies": [
    {
      "id": 123,
      "name": "Bill.com Holdings Inc",
      "ticker": "BILL",
      "market_cap": "SMALL"
    }
  ]
}
```

**After:**
```json
{
  "companies": [
    {
      "id": 123,
      "name": "Bill.com Holdings Inc",
      "ticker": "BILL",
      "market_cap": "SMALL",
      "market_cap_value": 4520000000
    }
  ]
}
```

### Frontend Display
The frontend can now display:
- "🎯 Small Cap - $1.5B" for companies < $2B
- "📊 Large Cap - $50B" for companies >= $2B
- "Data Pending" for companies without market cap

## Configuration

### Tiered Mode (Default - Recommended)
By default, the scheduler uses tiered expansion to ensure it always finds candidates:
```python
# No special config needed - tiered mode is default
# Scheduler will try: $2B -> $4B -> $10B -> $50B -> unlimited
```

**Advantages:**
- ✅ Never returns empty (always finds companies to analyze)
- ✅ Still prioritizes smaller companies first
- ✅ Expands only when necessary
- ✅ Sorted by market cap (smallest first)

### Strict Mode (Optional)
Set a hard threshold to enforce strict filtering with no fallback:
```python
# In scheduler config or environment
config = {
    "strict_small_cap_threshold": 2_000_000_000  # $2B - no expansion
}

# Or for $1B strict threshold:
config = {
    "strict_small_cap_threshold": 1_000_000_000  # $1B - very strict
}
```

**Advantages:**
- ✅ Guaranteed maximum market cap
- ✅ No large caps will ever be analyzed
- ⚠️ May return empty if no companies meet criteria

**When to use Strict Mode:**
- You have many small cap companies in database (> 10)
- You want absolute guarantee of market cap limit
- You're okay with occasional empty results

**When to use Tiered Mode (default):**
- You have few small cap companies (< 5)
- You want continuous operation
- You prefer "smaller is better" over "strict cutoff"

## Monitoring

### Check Small Cap Statistics
```python
from src.database.database import get_db
from src.database.models import Company

with get_db() as db:
    small_cap_count = db.query(Company).filter(
        Company.market_cap_value < 2_000_000_000
    ).count()
    print(f"Small cap companies: {small_cap_count}")
```

### Check Next Scheduled Companies
The autonomous scheduler will log which companies it's selecting:
```
INFO - 🤖 Scheduler agent deciding companies to analyze...
INFO - Found 67 candidate companies
INFO - Selected 50 companies for analysis
INFO - ✅ LLM selected 50 companies to analyze
```

## Rollback Plan

If you need to revert the changes:

1. **Stop scheduler:**
   ```bash
   # Disable autonomous scheduler in config
   ```

2. **Restore old scheduler logic:**
   ```bash
   git revert <commit-hash>
   ```

3. **Restart services:**
   ```bash
   docker-compose restart
   ```

## Notes

- Market cap data comes from SEC Company Facts API (free, unlimited, authoritative)
- Companies without market cap data are **included** (conservative approach)
- Market cap values are updated during backfill and when new companies are added
- The $2B threshold aligns with standard small-cap definition
- Unknown market caps are treated as small-cap to avoid false negatives

## Related Files

- `src/database/models.py` - Database schema
- `src/utils/market_cap_lookup.py` - Market cap fetching logic
- `src/services/scheduler_agent.py` - Autonomous scheduler
- `src/api/routes_v2.py` - API endpoints
- `scripts/backfill_market_cap.py` - Data population script
- `scripts/test_small_cap_filter.py` - Testing script

## Questions?

Contact the development team or check the feedback tracker in `feedback_instructions.md`.
