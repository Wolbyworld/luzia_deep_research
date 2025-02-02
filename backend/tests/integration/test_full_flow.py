import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.services.ai_service import AIService
from src.core.searcher import WebSearcher
from src.core.content_extractor import ContentExtractor
from src.utils.chunking import ContentProcessor
from src.services.cache_service import CacheService

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_search_results():
    return [
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

@pytest.fixture
def mock_webpage_content():
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <main>
            <h1>Test Article</h1>
            <article>
                <p>This is a detailed test article about the topic.</p>
                <p>It contains multiple paragraphs of relevant information.</p>
            </article>
        </main>
    </body>
    </html>
    """

async def test_full_research_flow(
    mock_openai_client,
    mock_redis_client,
    mock_search_results,
    mock_webpage_content,
    mock_env
):
    # Initialize services
    web_searcher = WebSearcher()
    content_extractor = ContentExtractor()
    content_processor = ContentProcessor()
    cache_service = CacheService()
    ai_service = AIService()
    
    # Mock cache service
    cache_service.redis_client = mock_redis_client
    mock_redis_client.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_client.setex = AsyncMock()
    
    # Mock web search
    with patch('httpx.AsyncClient') as mock_client:
        # Mock search API response
        mock_search_response = AsyncMock()
        mock_search_response.json.return_value = {"organic": mock_search_results}
        mock_search_response.raise_for_status = AsyncMock()
        
        # Mock webpage content response
        mock_content_response = AsyncMock()
        mock_content_response.text = mock_webpage_content
        mock_content_response.raise_for_status = AsyncMock()
        
        # Setup mock client responses
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_search_response)
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_content_response)
        
        # Mock OpenAI responses
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)
        
        mock_completion_response = MagicMock()
        mock_completion_response.choices = [MagicMock(message=MagicMock(content="Generated Research Report"))]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion_response)
        
        # Execute full flow
        query = "test research query"
        
        # 1. Web Search
        search_results = await web_searcher.search(query)
        assert len(search_results) > 0
        
        # 2. Content Extraction
        extracted_contents = []
        for result in search_results:
            content = await content_extractor.extract_from_url(result.link)
            assert content["title"]
            assert content["content"]
            extracted_contents.append(content)
        
        # 3. Content Processing
        processed_chunks = content_processor.process_contents(extracted_contents)
        assert len(processed_chunks) > 0
        
        # 4. Report Generation
        report = await ai_service.generate_report(query, processed_chunks)
        assert report == "Generated Research Report"
        
        # Verify all steps were called
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()  # Search API call
        assert mock_client.return_value.__aenter__.return_value.get.call_count == len(search_results)  # Content extraction calls
        assert mock_openai_client.embeddings.create.called  # Embedding generation
        assert mock_openai_client.chat.completions.create.called  # Report generation

async def test_cached_report_flow(
    mock_redis_client,
    mock_env
):
    # Initialize services
    cache_service = CacheService()
    cache_service.redis_client = mock_redis_client
    
    # Mock cached report
    cached_report = "Cached Research Report"
    mock_redis_client.get = AsyncMock(return_value=cached_report)
    
    # Test retrieving cached report
    query = "test research query"
    urls = ["http://example.com/1", "http://example.com/2"]
    
    result = await cache_service.get_report(query, urls)
    assert result == cached_report
    mock_redis_client.get.assert_called_once()

async def test_error_handling_flow(
    mock_openai_client,
    mock_redis_client,
    mock_env
):
    # Initialize services
    web_searcher = WebSearcher()
    content_extractor = ContentExtractor()
    ai_service = AIService()
    
    # Mock failed web search
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Search API Error")
        )
        
        # Test search error handling
        with pytest.raises(httpx.RequestError):
            await web_searcher.search("test query")
    
    # Mock failed content extraction
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Content Extraction Error")
        )
        
        # Test content extraction error handling
        result = await content_extractor.extract_from_url("http://example.com")
        assert "error" in result
        assert "Content Extraction Error" in result["error"]
    
    # Mock OpenAI API error
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("OpenAI API Error")
    )
    
    # Test report generation error handling
    with pytest.raises(Exception) as exc_info:
        await ai_service.generate_report("test query", []) 