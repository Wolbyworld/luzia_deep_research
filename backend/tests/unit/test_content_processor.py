import pytest
from src.utils.chunking import ContentProcessor

@pytest.fixture
def sample_content():
    return {
        "title": "Test Document",
        "content": "This is a test document with multiple sentences. " * 50,  # Long content
        "url": "http://example.com"
    }

@pytest.fixture
def sample_contents():
    return [
        {
            "title": "Document 1",
            "content": "This is the first document. " * 20,
            "url": "http://example.com/1"
        },
        {
            "title": "Document 2",
            "content": "This is the second document. " * 20,
            "url": "http://example.com/2"
        }
    ]

def test_process_contents_with_single_document(content_processor, sample_content):
    # Process single content
    chunks = content_processor.process_contents([sample_content])
    
    # Verify
    assert isinstance(chunks, list)
    assert len(chunks) > 1  # Should be split into multiple chunks
    
    for chunk in chunks:
        # Verify chunk structure
        assert isinstance(chunk, dict)
        assert "title" in chunk
        assert "content" in chunk
        assert "url" in chunk
        
        # Verify chunk content
        assert chunk["title"] == sample_content["title"]
        assert chunk["url"] == sample_content["url"]
        assert len(chunk["content"]) <= content_processor.chunk_size
        assert len(chunk["content"]) >= content_processor.min_chunk_length

def test_process_contents_with_multiple_documents(content_processor, sample_contents):
    # Process multiple contents
    chunks = content_processor.process_contents(sample_contents)
    
    # Verify
    assert isinstance(chunks, list)
    
    # Track chunks per document
    chunks_per_doc = {}
    for chunk in chunks:
        chunks_per_doc[chunk["url"]] = chunks_per_doc.get(chunk["url"], 0) + 1
    
    # Verify each document was processed
    for content in sample_contents:
        assert content["url"] in chunks_per_doc
        assert chunks_per_doc[content["url"]] > 0

def test_process_contents_with_empty_content(content_processor):
    # Test data
    empty_contents = [
        {
            "title": "Empty Document",
            "content": "",
            "url": "http://example.com/empty"
        }
    ]
    
    # Process empty content
    chunks = content_processor.process_contents(empty_contents)
    
    # Verify empty content is skipped
    assert isinstance(chunks, list)
    assert len(chunks) == 0

def test_process_contents_with_short_content(content_processor):
    # Test data
    short_content = {
        "title": "Short Document",
        "content": "Short content.",
        "url": "http://example.com/short"
    }
    
    # Process short content
    chunks = content_processor.process_contents([short_content])
    
    # Verify short content handling
    assert isinstance(chunks, list)
    if len(short_content["content"]) >= content_processor.min_chunk_length:
        assert len(chunks) == 1
        assert chunks[0]["content"] == short_content["content"]
    else:
        assert len(chunks) == 0

def test_chunk_overlap(content_processor):
    # Test data with specific sentence boundaries
    content = {
        "title": "Test Document",
        "content": "First sentence. Second sentence. Third sentence. Fourth sentence. " * 10,
        "url": "http://example.com"
    }
    
    # Process content
    chunks = content_processor.process_contents([content])
    
    # Verify overlap between consecutive chunks
    for i in range(len(chunks) - 1):
        current_chunk = chunks[i]["content"]
        next_chunk = chunks[i + 1]["content"]
        
        # Check if there's some overlap between chunks
        assert any(
            sentence in next_chunk 
            for sentence in current_chunk.split(". ")[-3:]  # Check last few sentences
            if sentence
        ) 