"""
SEC Fetcher node - downloads the latest 10-K filing for a company.
"""
from typing import Dict, Any
from pathlib import Path

from ..utils.sec_api import SECAPI
from ..utils.logging import setup_logger, log_trace_event

logger = setup_logger(__name__)


async def sec_fetcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch the latest 10-K filing from SEC EDGAR.
    Uses cached filing if it exists and is the latest version.
    
    Args:
        state: Graph state with cik and company
    
    Returns:
        Updated state with filing_url, file_path, filing_date
    """
    cik = state.get("cik")
    company = state.get("company")
    config = state.get("config", {})
    
    if not cik:
        logger.error("No CIK provided to SEC fetcher")
        return {
            **state,
            "error": "No CIK available for fetching"
        }
    
    logger.info(f"Checking for latest 10-K for {company} (CIK: {cik})")
    
    # Initialize SEC API
    sec_api = SECAPI(config.get("sec_user_agent"))
    
    try:
        # Get latest 10-K info from SEC
        filing_url, accession, filing_date = await sec_api.get_latest_10k(cik)
        
        # Setup file paths
        output_dir = Path("data/filings")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename
        safe_name = company.replace(" ", "_").replace(".", "").replace(",", "")
        output_path = output_dir / f"{safe_name}_10K.html"
        metadata_path = output_dir / f"{safe_name}_10K.meta.json"
        
        # Check if we already have this filing
        use_cached = False
        if output_path.exists() and metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    cached_meta = json.load(f)
                
                cached_date = cached_meta.get('filing_date')
                cached_accession = cached_meta.get('accession')
                
                # Compare dates and accession numbers
                if cached_date == filing_date and cached_accession == accession:
                    use_cached = True
                    logger.info(f"✅ Using cached 10-K (filed {filing_date}) - already up to date")
                else:
                    logger.info(f"📥 Newer filing found (cached: {cached_date}, latest: {filing_date}) - downloading")
            except Exception as e:
                logger.warning(f"Could not read metadata: {e} - will re-download")
        
        # Download if needed
        if not use_cached:
            logger.info(f"📥 Downloading 10-K filed on {filing_date}")
            file_path = await sec_api.download_filing(filing_url, output_path)
            
            # Save metadata
            import json
            metadata = {
                'company': company,
                'cik': cik,
                'filing_date': filing_date,
                'accession': accession,
                'filing_url': filing_url,
                'downloaded_at': str(Path(file_path).stat().st_mtime)
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Downloaded and cached 10-K")
        else:
            file_path = str(output_path)
        
        # Log trace event
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "SECFetcher",
            "download_filing",
            f"{'Using cached' if use_cached else 'Downloaded'} 10-K filed on {filing_date}",
            {
                "filing_url": filing_url,
                "file_path": str(file_path),
                "filing_date": filing_date,
                "accession": accession,
                "cached": use_cached
            }
        ).to_dict())
        
        return {
            **state,
            "filing_url": filing_url,
            "file_path": str(file_path),
            "filing_date": filing_date,
            "accession": accession,
            "trace": trace
        }
    
    except Exception as e:
        logger.error(f"Error fetching 10-K: {str(e)}")
        trace = state.get("trace", [])
        trace.append(log_trace_event(
            logger,
            "SECFetcher",
            "error",
            f"Failed to fetch 10-K: {str(e)}",
            {"error": str(e)}
        ).to_dict())
        
        return {
            **state,
            "error": f"Failed to fetch 10-K: {str(e)}",
            "trace": trace
        }
