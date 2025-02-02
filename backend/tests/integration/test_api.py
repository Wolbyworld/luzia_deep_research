import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
from src.main import app

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_research_response():
    return {
        "report": "Test Research Report",
        "sources": [
            "http://example.com/1",
            "http://example.com/2"
        ]
    }

def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch("src.services.ai_service.AIService")
@patch("src.core.searcher.WebSearcher")
@patch("src.core.content_extractor.ContentExtractor")
def test_research_endpoint_success(
    mock_extractor,
    mock_searcher,
    mock_ai_service,
    test_client,
    mock_research_response
):
    # Mock successful responses
    mock_searcher.return_value.search = AsyncMock(return_value=[
        MagicMock(
            title="Test Result",
            link="http://example.com/1",
            snippet="Test snippet"
        )
    ])
    
    mock_extractor.return_value.extract_from_url = AsyncMock(return_value={
        "title": "Test Page",
        "content": "Test content",
        "url": "http://example.com/1"
    })
    
    mock_ai_service.return_value.generate_report = AsyncMock(
        return_value=mock_research_response["report"]
    )
    
    # Test request
    response = test_client.post(
        "/research",
        json={
            "query": "test query",
            "max_results": 5,
            "time_filter": "past_month"
        }
    )
    
    # Verify response
    assert response.status_code == 200
    result = response.json()
    assert "report" in result
    assert "sources" in result
    assert isinstance(result["sources"], list)

@patch("src.services.ai_service.AIService")
def test_research_endpoint_validation(mock_ai_service, test_client):
    # Test missing required field
    response = test_client.post(
        "/research",
        json={
            "max_results": 5  # Missing query
        }
    )
    assert response.status_code == 422
    
    # Test invalid max_results
    response = test_client.post(
        "/research",
        json={
            "query": "test",
            "max_results": -1
        }
    )
    assert response.status_code == 422
    
    # Test invalid time_filter
    response = test_client.post(
        "/research",
        json={
            "query": "test",
            "time_filter": "invalid_filter"
        }
    )
    assert response.status_code == 422

@patch("src.services.ai_service.AIService")
@patch("src.core.searcher.WebSearcher")
def test_research_endpoint_error_handling(
    mock_searcher,
    mock_ai_service,
    test_client
):
    # Mock search error
    mock_searcher.return_value.search = AsyncMock(
        side_effect=Exception("Search failed")
    )
    
    # Test request
    response = test_client.post(
        "/research",
        json={
            "query": "test query"
        }
    )
    
    # Verify error response
    assert response.status_code == 500
    assert "error" in response.json()

def test_research_endpoint_rate_limiting(test_client):
    # Make multiple requests quickly
    responses = []
    for _ in range(10):
        response = test_client.post(
            "/research",
            json={
                "query": "test query"
            }
        )
        responses.append(response)
    
    # Verify rate limiting
    assert any(r.status_code == 429 for r in responses)

@patch("src.services.ai_service.AIService")
def test_research_endpoint_formats(mock_ai_service, test_client):
    # Test different output formats
    formats = ["text", "markdown", "pdf"]
    
    for format_type in formats:
        response = test_client.post(
            "/research",
            json={
                "query": "test query",
                "output_format": format_type
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "format" in result
        assert result["format"] == format_type

@patch("src.services.cache_service.CacheService")
def test_research_endpoint_caching(mock_cache_service, test_client):
    # Mock cache hit
    mock_cache_service.return_value.get_report = AsyncMock(
        return_value="Cached Report"
    )
    
    # Test request
    response = test_client.post(
        "/research",
        json={
            "query": "test query"
        }
    )
    
    # Verify cached response
    assert response.status_code == 200
    result = response.json()
    assert result["report"] == "Cached Report"
    
    # Mock cache miss
    mock_cache_service.return_value.get_report = AsyncMock(return_value=None)
    
    # Test request again
    response = test_client.post(
        "/research",
        json={
            "query": "test query"
        }
    )
    
    # Verify non-cached response
    assert response.status_code == 200 