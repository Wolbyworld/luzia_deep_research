import pytest
import os
from unittest.mock import AsyncMock
from openai import AsyncOpenAI
from redis import Redis
from src.config import Config
from src.services.ai_service import AIService
from src.services.cache_service import CacheService
from src.core.content_extractor import ContentExtractor
from src.utils.chunking import ContentProcessor
from src.services.formatter_service import FormatterService
from src.core.searcher import WebSearcher

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    client = AsyncMock(spec=AsyncOpenAI)
    return client

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = AsyncMock(spec=Redis)
    return client

@pytest.fixture
def sample_chunks():
    """Sample content chunks for testing"""
    return [
        {
            "title": "Test Document 1",
            "content": "This is a test content chunk 1",
            "url": "http://example.com/1"
        },
        {
            "title": "Test Document 2",
            "content": "This is a test content chunk 2",
            "url": "http://example.com/2"
        }
    ]

@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing"""
    return [0.1] * 1536  # OpenAI embeddings are 1536-dimensional

@pytest.fixture
def ai_service(mock_openai_client):
    """AIService instance with mocked OpenAI client"""
    service = AIService()
    service.openai_client = mock_openai_client
    return service

@pytest.fixture
def cache_service(mock_redis_client):
    """CacheService instance with mocked Redis client"""
    service = CacheService()
    service.redis_client = mock_redis_client
    return service

@pytest.fixture
def content_extractor():
    """ContentExtractor instance"""
    return ContentExtractor()

@pytest.fixture
def content_processor():
    """ContentProcessor instance"""
    return ContentProcessor()

@pytest.fixture
def formatter_service():
    """FormatterService instance"""
    return FormatterService()

@pytest.fixture
def web_searcher():
    """WebSearcher instance"""
    return WebSearcher()

@pytest.fixture
def mock_env(monkeypatch):
    """Setup mock environment variables"""
    env_vars = {
        "OPENAI_API_KEY": "test-api-key",
        "AZURE_SEARCH_KEY": "test-azure-key",
        "SERPER_API_KEY": "test-serper-key",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "MAX_SEARCH_RESULTS": "10",
        "CHUNK_SIZE": "1000",
        "CHUNK_OVERLAP": "100",
        "MIN_CHUNK_LENGTH": "100",
        "MAX_CHUNKS_FOR_REPORT": "5",
        "OPENAI_MODEL": "gpt-4-turbo-preview",
        "EMBEDDING_MODEL": "text-embedding-ada-002",
        "MAX_TOKENS": "4000",
        "TEMPERATURE": "0.3"
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value) 