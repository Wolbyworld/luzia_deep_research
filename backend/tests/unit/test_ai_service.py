import pytest
from unittest.mock import AsyncMock, MagicMock
import numpy as np
from src.services.ai_service import AIService

pytestmark = pytest.mark.asyncio

async def test_get_embedding(ai_service, mock_openai_client, sample_embedding):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=sample_embedding)]
    mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    # Test embedding generation
    result = await ai_service._get_embedding("test text")
    
    # Verify
    assert isinstance(result, list)
    assert len(result) == 1536
    mock_openai_client.embeddings.create.assert_called_once_with(
        model="text-embedding-ada-002",
        input="test text"
    )

async def test_get_all_embeddings(ai_service, mock_openai_client, sample_embedding):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=sample_embedding)]
    mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    # Test parallel embedding generation
    texts = ["text1", "text2", "text3"]
    results = await ai_service._get_all_embeddings(texts)
    
    # Verify
    assert len(results) == len(texts)
    assert all(len(emb) == 1536 for emb in results)
    assert mock_openai_client.embeddings.create.call_count == len(texts)

async def test_rerank_chunks_with_embeddings(ai_service, mock_openai_client, sample_chunks, sample_embedding):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=sample_embedding)]
    mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    # Test chunk reranking
    query = "test query"
    ranked_chunks = await ai_service._rerank_chunks_with_embeddings(query, sample_chunks)
    
    # Verify
    assert len(ranked_chunks) == len(sample_chunks)
    assert all(isinstance(chunk, dict) for chunk in ranked_chunks)
    assert all(key in chunk for chunk in ranked_chunks for key in ["title", "content", "url"])

async def test_generate_report(ai_service, mock_openai_client, sample_chunks):
    # Setup mock response for embeddings
    mock_emb_response = MagicMock()
    mock_emb_response.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_openai_client.embeddings.create = AsyncMock(return_value=mock_emb_response)
    
    # Setup mock response for report generation
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Test Report"))]
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    # Test report generation
    query = "test query"
    report = await ai_service.generate_report(query, sample_chunks)
    
    # Verify
    assert isinstance(report, str)
    assert report == "Test Report"
    assert mock_openai_client.chat.completions.create.called

def test_cosine_similarity(ai_service):
    # Test vectors
    a = [1, 0, 0]
    b = [0, 1, 0]
    c = [1, 0, 0]
    
    # Test orthogonal vectors (should be 0)
    assert ai_service._cosine_similarity(a, b) == 0
    
    # Test identical vectors (should be 1)
    assert ai_service._cosine_similarity(a, c) == 1
    
    # Test with actual embedding-like vectors
    v1 = np.random.rand(1536)
    v2 = np.random.rand(1536)
    similarity = ai_service._cosine_similarity(v1.tolist(), v2.tolist())
    assert -1 <= similarity <= 1

def test_build_context(ai_service, sample_chunks):
    # Test context building
    context = ai_service._build_context(sample_chunks)
    
    # Verify
    assert isinstance(context, str)
    for chunk in sample_chunks:
        assert chunk["title"] in context
        assert chunk["content"] in context
        assert chunk["url"] in context

def test_create_report_prompt(ai_service):
    # Test data
    query = "test query"
    context = "test context"
    
    # Test prompt creation
    prompt = ai_service._create_report_prompt(query, context)
    
    # Verify
    assert isinstance(prompt, str)
    assert query in prompt
    assert context in prompt 