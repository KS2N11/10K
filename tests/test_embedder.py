"""
Tests for embedder node.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from src.nodes.embedder import embedder_node


@pytest.mark.asyncio
async def test_embedder_success(tmp_path):
    """Test successful embedding creation."""
    # Create a test HTML file
    test_file = tmp_path / "test_10k.html"
    test_file.write_text("<html><body><h1>Item 1A Risk Factors</h1><p>Test content</p></body></html>")
    
    state = {
        "file_path": str(test_file),
        "company": "Test Corp",
        "config": {
            "openai_api_key": "test-key",
            "embedding_model_name": "text-embedding-3-large",
            "vector_store_dir": str(tmp_path / "vector"),
            "chunk_size": 1000,
            "chunk_overlap": 200
        },
        "trace": []
    }
    
    with patch("src.nodes.embedder.TextProcessor") as mock_processor:
        mock_proc = Mock()
        mock_proc.process_filing.return_value = [
            {"text": "chunk 1", "metadata": {"section": "Item 1A", "chunk_index": 0}},
            {"text": "chunk 2", "metadata": {"section": "Item 1A", "chunk_index": 1}}
        ]
        mock_processor.return_value = mock_proc
        
        with patch("src.nodes.embedder.EmbeddingClient") as mock_embed:
            mock_client = Mock()
            mock_vs = Mock()
            mock_client.create_vector_store.return_value = mock_vs
            mock_embed.return_value = mock_client
            
            result = await embedder_node(state)
            
            assert "vector_store" in result
            assert result["chunks"] == 2
            assert "collection_name" in result
            assert "trace" in result


@pytest.mark.asyncio
async def test_embedder_no_file_path():
    """Test embedder with missing file path."""
    state = {
        "company": "Test Corp",
        "config": {
            "openai_api_key": "test-key"
        },
        "trace": []
    }
    
    result = await embedder_node(state)
    
    assert "error" in result
    assert "No file path" in result["error"]


@pytest.mark.asyncio
async def test_embedder_processing_error(tmp_path):
    """Test embedder with processing error."""
    test_file = tmp_path / "test_10k.html"
    test_file.write_text("<html><body>Test</body></html>")
    
    state = {
        "file_path": str(test_file),
        "company": "Test Corp",
        "config": {
            "openai_api_key": "test-key",
            "embedding_model_name": "text-embedding-3-large",
            "vector_store_dir": str(tmp_path / "vector")
        },
        "trace": []
    }
    
    with patch("src.nodes.embedder.TextProcessor") as mock_processor:
        mock_processor.side_effect = Exception("Processing error")
        
        result = await embedder_node(state)
        
        assert "error" in result
