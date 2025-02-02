import pytest
from bs4 import BeautifulSoup
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.content_extractor import ContentExtractor

pytestmark = pytest.mark.asyncio

@pytest.fixture
def sample_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta property="og:title" content="OG Test Page">
    </head>
    <body>
        <nav>Navigation content</nav>
        <main>
            <h1>Main Heading</h1>
            <article>
                <p>This is the main content.</p>
                <p>More content here.</p>
            </article>
        </main>
        <script>console.log('test');</script>
        <footer>Footer content</footer>
    </body>
    </html>
    """

async def test_extract_from_url_success(content_extractor):
    # Test data
    url = "http://example.com"
    html_content = "<html><body><h1>Test</h1></body></html>"
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test extraction
        result = await content_extractor.extract_from_url(url)
        
        # Verify
        assert isinstance(result, dict)
        assert "title" in result
        assert "content" in result
        assert "url" in result
        assert result["url"] == url

async def test_extract_from_url_failure(content_extractor):
    # Test data
    url = "http://example.com"
    
    # Mock httpx client with error
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.RequestError("Test error"))
        
        # Test extraction
        result = await content_extractor.extract_from_url(url)
        
        # Verify error handling
        assert isinstance(result, dict)
        assert result["title"] == ""
        assert result["content"] == ""
        assert "error" in result
        assert "Test error" in result["error"]

def test_parse_content(content_extractor, sample_html):
    # Test data
    url = "http://example.com"
    
    # Parse content
    result = content_extractor._parse_content(sample_html, url)
    
    # Verify
    assert isinstance(result, dict)
    assert "title" in result
    assert "content" in result
    assert "url" in result
    assert result["url"] == url
    assert "Main Heading" in result["content"]
    assert "This is the main content" in result["content"]
    assert "Navigation content" not in result["content"]  # Should be removed
    assert "Footer content" not in result["content"]  # Should be removed
    assert "console.log" not in result["content"]  # Script should be removed

def test_extract_title_priority(content_extractor, sample_html):
    # Create soup object
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    # Test OG title priority
    title = content_extractor._extract_title(soup)
    assert title == "OG Test Page"  # Should use og:title
    
    # Remove OG title and test regular title
    soup.find("meta", property="og:title").decompose()
    title = content_extractor._extract_title(soup)
    assert title == "Test Page"  # Should use <title>
    
    # Remove title and test h1
    soup.title.decompose()
    title = content_extractor._extract_title(soup)
    assert title == "Main Heading"  # Should use <h1>

def test_extract_main_content(content_extractor, sample_html):
    # Create soup object
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    # Test main content extraction
    content = content_extractor._extract_main_content(soup)
    
    # Verify
    assert "This is the main content" in content
    assert "More content here" in content
    assert "Navigation content" not in content
    assert "Footer content" not in content
    
    # Test fallback to body when no main content containers found
    soup.main.decompose()
    soup.article.decompose()
    content = content_extractor._extract_main_content(soup)
    assert content.strip() != ""  # Should still get some content 