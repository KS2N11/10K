"""
Tests for SEC fetcher node.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from src.nodes.sec_fetcher import sec_fetcher_node


@pytest.mark.asyncio
async def test_sec_fetcher_success():
    """Test successful 10-K fetch."""
    state = {
        "cik": "0000789019",
        "company": "Microsoft Corp",
        "config": {
            "sec_user_agent": "Test/1.0 (test@test.com)"
        },
        "trace": []
    }
    
    with patch("src.nodes.sec_fetcher.SECAPI") as mock_sec:
        mock_api = AsyncMock()
        mock_api.get_latest_10k.return_value = (
            "https://sec.gov/test.html",
            "0000789019-23-000123",
            "2023-10-15"
        )
        mock_api.download_filing.return_value = Path("data/filings/Microsoft_Corp_10K.html")
        mock_sec.return_value = mock_api
        
        result = await sec_fetcher_node(state)
        
        assert result["filing_url"] == "https://sec.gov/test.html"
        assert result["filing_date"] == "2023-10-15"
        assert "file_path" in result
        assert "trace" in result


@pytest.mark.asyncio
async def test_sec_fetcher_no_cik():
    """Test SEC fetcher with missing CIK."""
    state = {
        "company": "Microsoft Corp",
        "config": {
            "sec_user_agent": "Test/1.0 (test@test.com)"
        },
        "trace": []
    }
    
    result = await sec_fetcher_node(state)
    
    assert "error" in result
    assert "No CIK" in result["error"]


@pytest.mark.asyncio
async def test_sec_fetcher_api_error():
    """Test SEC fetcher with API error."""
    state = {
        "cik": "0000789019",
        "company": "Microsoft Corp",
        "config": {
            "sec_user_agent": "Test/1.0 (test@test.com)"
        },
        "trace": []
    }
    
    with patch("src.nodes.sec_fetcher.SECAPI") as mock_sec:
        mock_api = AsyncMock()
        mock_api.get_latest_10k.side_effect = Exception("API Error")
        mock_sec.return_value = mock_api
        
        result = await sec_fetcher_node(state)
        
        assert "error" in result
        assert "API Error" in result["error"]
