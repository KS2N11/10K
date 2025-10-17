"""
Tests for solution matcher subgraph.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.nodes.solution_matcher.problem_miner import problem_miner_node
from src.nodes.solution_matcher.fit_scorer import fit_scorer_node


@pytest.mark.asyncio
async def test_problem_miner():
    """Test problem miner node."""
    mock_vs = Mock()
    mock_vs.similarity_search_with_score.return_value = [
        (Mock(page_content="Risk content", metadata={"section": "Item 1A"}), 0.9),
        (Mock(page_content="Challenge content", metadata={"section": "Item 7"}), 0.8)
    ]
    
    state = {
        "vector_store": mock_vs,
        "user_query": "analyze risks",
        "config": {
            "openai_api_key": "test-key",
            "llm_model_name": "gpt-4o-mini",
            "llm_temperature": 0.0,
            "top_k_chunks": 10
        },
        "trace": []
    }
    
    with patch("src.nodes.solution_matcher.problem_miner.ChatOpenAI") as mock_llm:
        mock_chain = AsyncMock()
        mock_response = Mock()
        mock_response.content = '''```json
{
  "pains": [
    {
      "theme": "Supply Chain Risk",
      "rationale": "Significant challenges",
      "quotes": ["test quote"],
      "section": "Item 1A",
      "confidence": 0.85
    }
  ]
}```'''
        mock_chain.ainvoke.return_value = mock_response
        mock_llm.return_value.__or__ = Mock(return_value=mock_chain)
        
        result = await problem_miner_node(state)
        
        assert "pains" in result
        assert len(result["pains"]) > 0
        assert "citations" in result


@pytest.mark.asyncio
async def test_fit_scorer():
    """Test fit scorer node."""
    state = {
        "pains": [
            {
                "theme": "Cloud Costs",
                "rationale": "High cloud spending",
                "quotes": ["spending increased"],
                "confidence": 0.9
            }
        ],
        "candidate_products": [
            {
                "product_id": "cloud-optimizer",
                "title": "Cloud Optimizer",
                "summary": "Reduce cloud spend",
                "capabilities": ["cost optimization"]
            }
        ],
        "config": {
            "openai_api_key": "test-key",
            "llm_model_name": "gpt-4o-mini",
            "llm_temperature": 0.0
        },
        "trace": [],
        "citations": []
    }
    
    with patch("src.nodes.solution_matcher.fit_scorer.ChatOpenAI") as mock_llm:
        mock_chain = AsyncMock()
        mock_response = Mock()
        mock_response.content = '''```json
{
  "matches": [
    {
      "pain_theme": "Cloud Costs",
      "product_id": "cloud-optimizer",
      "score": 85,
      "why": "Directly addresses cloud cost optimization",
      "evidence": ["Avg 18% savings"]
    }
  ]
}```'''
        mock_chain.ainvoke.return_value = mock_response
        mock_llm.return_value.__or__ = Mock(return_value=mock_chain)
        
        result = await fit_scorer_node(state)
        
        assert "matches" in result
        assert len(result["matches"]) > 0
        assert result["matches"][0]["score"] == 85
