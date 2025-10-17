"""
Tests for company resolver node.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.nodes.company_resolver import company_resolver_node


@pytest.mark.asyncio
async def test_company_resolver_single_match():
    """Test company resolver with single match."""
    state = {
        "user_query": "Analyze Microsoft's 10-K",
        "config": {
            "openai_api_key": "test-key",
            "llm_model_name": "gpt-4o-mini",
            "sec_user_agent": "Test/1.0 (test@test.com)"
        },
        "trace": []
    }
    
    # Mock LLM response
    with patch("src.nodes.company_resolver.ChatOpenAI") as mock_llm:
        mock_chain = AsyncMock()
        mock_response = Mock()
        mock_response.content = "Microsoft"
        mock_chain.ainvoke.return_value = mock_response
        mock_llm.return_value.__or__ = Mock(return_value=mock_chain)
        
        # Mock SEC API
        with patch("src.nodes.company_resolver.SECAPI") as mock_sec:
            mock_api = AsyncMock()
            mock_api.search_company.return_value = [{
                "name": "Microsoft Corp",
                "ticker": "MSFT",
                "cik": "0000789019"
            }]
            mock_sec.return_value = mock_api
            
            result = await company_resolver_node(state)
            
            assert result["company"] == "Microsoft Corp"
            assert result["cik"] == "0000789019"
            assert result["ticker"] == "MSFT"
            assert "trace" in result


@pytest.mark.asyncio
async def test_company_resolver_disambiguation():
    """Test company resolver with multiple matches."""
    state = {
        "user_query": "Analyze Apple's risks",
        "config": {
            "openai_api_key": "test-key",
            "llm_model_name": "gpt-4o-mini",
            "sec_user_agent": "Test/1.0 (test@test.com)"
        },
        "trace": []
    }
    
    with patch("src.nodes.company_resolver.ChatOpenAI") as mock_llm:
        mock_chain = AsyncMock()
        mock_response = Mock()
        mock_response.content = "Apple"
        mock_chain.ainvoke.return_value = mock_response
        mock_llm.return_value.__or__ = Mock(return_value=mock_chain)
        
        with patch("src.nodes.company_resolver.SECAPI") as mock_sec:
            mock_api = AsyncMock()
            mock_api.search_company.return_value = [
                {"name": "Apple Inc", "ticker": "AAPL", "cik": "0000320193"},
                {"name": "Apple Hospitality", "ticker": "APLE", "cik": "0001418121"}
            ]
            mock_sec.return_value = mock_api
            
            result = await company_resolver_node(state)
            
            assert result["status"] == "disambiguation_required"
            assert len(result["candidates"]) == 2


@pytest.mark.asyncio
async def test_company_resolver_no_match():
    """Test company resolver with no matches."""
    state = {
        "user_query": "Analyze NonexistentCorp",
        "config": {
            "openai_api_key": "test-key",
            "llm_model_name": "gpt-4o-mini",
            "sec_user_agent": "Test/1.0 (test@test.com)"
        },
        "trace": []
    }
    
    with patch("src.nodes.company_resolver.ChatOpenAI") as mock_llm:
        mock_chain = AsyncMock()
        mock_response = Mock()
        mock_response.content = "NonexistentCorp"
        mock_chain.ainvoke.return_value = mock_response
        mock_llm.return_value.__or__ = Mock(return_value=mock_chain)
        
        with patch("src.nodes.company_resolver.SECAPI") as mock_sec:
            mock_api = AsyncMock()
            mock_api.search_company.return_value = []
            mock_sec.return_value = mock_api
            
            result = await company_resolver_node(state)
            
            assert "error" in result
            assert "No company found" in result["error"]
