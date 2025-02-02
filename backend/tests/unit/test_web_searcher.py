import pytest
from unittest.mock import AsyncMock, patch
import httpx
from src.core.searcher import WebSearcher

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_serper_response():
    return {
        "organic": [
            {
                "title": "Test Result 1",
                "link": "http://example.com/1",
                "snippet": "This is the first test result."
            },
            {
                "title": "Test Result 2",
                "link": "http://example.com/2",
                "snippet": "This is the second test result."
            }
        ]
    }

@pytest.fixture
def mock_azure_response():
    return {
        "webPages": {
            "value": [
                {
                    "name": "Test Result 1",
                    "url": "http://example.com/1",
                    "snippet": "This is the first test result."
                },
                {
                    "name": "Test Result 2",
                    "url": "http://example.com/2",
                    "snippet": "This is the second test result."
                }
            ]
        }
    }

async def test_search_with_serper(web_searcher, mock_serper_response):
    # Setup
    web_searcher.serper_api_key = "test-key"
    web_searcher.azure_api_key = None
    
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_serper_response
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        
        # Test search
        results = await web_searcher.search("test query")
        
        # Verify
        assert len(results) == 2
        for result in results:
            assert hasattr(result, "title")
            assert hasattr(result, "link")
            assert hasattr(result, "snippet")
        
        # Verify API call
        mock_client.return_value.post.assert_called_once()
        call_args = mock_client.return_value.post.call_args
        assert call_args[0][0] == "https://google.serper.dev/search"
        assert "X-API-KEY" in call_args[1]["headers"]
        assert call_args[1]["headers"]["X-API-KEY"] == "test-key"

async def test_search_with_azure(web_searcher, mock_azure_response):
    # Setup
    web_searcher.serper_api_key = None
    web_searcher.azure_api_key = "test-key"
    
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_azure_response
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test search
        results = await web_searcher.search("test query")
        
        # Verify
        assert len(results) == 2
        for result in results:
            assert hasattr(result, "title")
            assert hasattr(result, "link")
            assert hasattr(result, "snippet")

async def test_search_with_time_filter(web_searcher, mock_serper_response):
    # Setup
    web_searcher.serper_api_key = "test-key"
    web_searcher.azure_api_key = None
    
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_serper_response
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        
        # Test search with time filter
        results = await web_searcher.search("test query", time_filter="past_month")
        
        # Verify time filter in request
        call_args = mock_client.return_value.post.call_args
        assert "timeRange" in call_args[1]["json"]
        assert call_args[1]["json"]["timeRange"] == "past_month"

async def test_search_with_no_api_keys(web_searcher):
    # Setup
    web_searcher.serper_api_key = None
    web_searcher.azure_api_key = None
    
    # Test search with no API keys
    with pytest.raises(ValueError) as exc_info:
        await web_searcher.search("test query")
    
    assert "No search API key configured" in str(exc_info.value)

async def test_search_api_error(web_searcher):
    # Setup
    web_searcher.serper_api_key = "test-key"
    web_searcher.azure_api_key = None
    
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock error response
        mock_client.return_value.post = AsyncMock(side_effect=httpx.RequestError("API Error"))
        
        # Test search with API error
        with pytest.raises(httpx.RequestError) as exc_info:
            await web_searcher.search("test query")
        
        assert "API Error" in str(exc_info.value)

async def test_search_max_results(web_searcher, mock_serper_response):
    # Setup
    web_searcher.serper_api_key = "test-key"
    web_searcher.azure_api_key = None
    web_searcher.max_results = 1  # Set max results to 1
    
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_serper_response
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        
        # Test search
        results = await web_searcher.search("test query")
        
        # Verify max results
        assert len(results) <= web_searcher.max_results
        
        # Verify request
        call_args = mock_client.return_value.post.call_args
        assert call_args[1]["json"]["num"] == web_searcher.max_results 