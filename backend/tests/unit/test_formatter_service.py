import pytest
from src.services.formatter_service import FormatterService
import re

@pytest.fixture
def sample_content():
    return """# Test Report
This is a test report with some markdown formatting.

## Section 1
* Bullet point 1
* Bullet point 2

## Section 2
1. Numbered item 1
2. Numbered item 2

[Link](http://example.com)
"""

@pytest.fixture
def sample_sources():
    return [
        "http://example.com/1",
        "http://example.com/2"
    ]

def test_format_text(formatter_service, sample_content, sample_sources):
    # Format as text
    result = formatter_service._format_text(sample_content, sample_sources, "Test Title")
    
    # Verify
    assert isinstance(result, dict)
    assert result["format"] == "text"
    assert result["mime_type"] == "text/plain"
    
    content = result["content"]
    assert "Test Title" in content
    assert "=" * len("Test Title") in content  # Title underline
    assert sample_content in content
    assert "Sources:" in content
    for source in sample_sources:
        assert source in content

def test_format_markdown(formatter_service, sample_content, sample_sources):
    # Format as markdown
    result = formatter_service._format_markdown(sample_content, sample_sources, "Test Title")
    
    # Verify
    assert isinstance(result, dict)
    assert result["format"] == "markdown"
    assert result["mime_type"] == "text/markdown"
    
    content = result["content"]
    assert "# Test Title" in content
    assert sample_content in content
    assert "## Sources" in content
    for source in sample_sources:
        assert f"* {source}" in content

def test_convert_markdown_to_html(formatter_service, sample_content):
    # Convert markdown to HTML
    html = formatter_service._convert_markdown_to_html(sample_content)
    
    # Verify basic HTML structure
    assert "<h1>Test Report</h1>" in html
    assert "<h2>Section 1</h2>" in html
    assert "<ul>" in html
    assert "<li>Bullet point 1</li>" in html
    assert "<ol>" in html
    assert "<li>Numbered item 1</li>" in html
    assert '<a href="http://example.com">Link</a>' in html

def test_clean_html_for_pdf(formatter_service):
    # Test HTML
    html = """
    <h1>Test Title</h1>
    <p>Test paragraph</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    <script>alert('test');</script>
    """
    
    # Clean HTML
    cleaned = formatter_service._clean_html_for_pdf(html)
    
    # Verify
    assert "Test Title" in cleaned
    assert "Test paragraph" in cleaned
    assert "• Item 1" in cleaned
    assert "• Item 2" in cleaned
    assert "script" not in cleaned
    assert "alert" not in cleaned

def test_format_pdf(formatter_service, sample_content, sample_sources):
    # Format as PDF
    result = formatter_service._format_pdf(sample_content, sample_sources, "Test Title")
    
    # Verify
    assert isinstance(result, dict)
    assert result["format"] == "pdf"
    assert result["mime_type"] == "application/pdf"
    assert isinstance(result["content"], bytes)
    
    # Basic PDF size check (should be non-empty)
    assert len(result["content"]) > 0

def test_format_output_invalid_format(formatter_service, sample_content, sample_sources):
    # Test invalid format
    with pytest.raises(ValueError) as exc_info:
        formatter_service.format_output(sample_content, sample_sources, "invalid_format")
    
    assert "Invalid output format" in str(exc_info.value)

def test_format_output_all_formats(formatter_service, sample_content, sample_sources):
    # Test all valid formats
    valid_formats = ["text", "markdown", "pdf"]
    
    for format_type in valid_formats:
        result = formatter_service.format_output(
            sample_content,
            sample_sources,
            format_type,
            "Test Title"
        )
        
        # Verify basic structure
        assert isinstance(result, dict)
        assert result["format"] == format_type
        assert "content" in result
        assert "mime_type" in result 