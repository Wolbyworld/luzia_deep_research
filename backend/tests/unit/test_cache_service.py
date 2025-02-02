import pytest
from unittest.mock import AsyncMock
import json
from src.services.cache_service import CacheService

pytestmark = pytest.mark.asyncio

async def test_generate_key(cache_service):
    # Test data
    prefix = "test"
    data = "example_data"
    
    # Generate key
    key = cache_service._generate_key(prefix, data)
    
    # Verify
    assert isinstance(key, str)
    assert key.startswith(prefix)
    assert ":" in key
    
    # Test consistency
    key2 = cache_service._generate_key(prefix, data)
    assert key == key2  # Same input should generate same key

async def test_get_embedding(cache_service, mock_redis_client, sample_embedding):
    # Setup mock
    mock_redis_client.get = AsyncMock(return_value=json.dumps(sample_embedding))
    
    # Test getting embedding
    result = await cache_service.get_embedding("test text")
    
    # Verify
    assert result == sample_embedding
    mock_redis_client.get.assert_called_once()
    
    # Test cache miss
    mock_redis_client.get = AsyncMock(return_value=None)
    result = await cache_service.get_embedding("test text")
    assert result is None

async def test_set_embedding(cache_service, mock_redis_client, sample_embedding):
    # Setup mock
    mock_redis_client.setex = AsyncMock()
    
    # Test setting embedding
    await cache_service.set_embedding("test text", sample_embedding)
    
    # Verify
    mock_redis_client.setex.assert_called_once()
    args = mock_redis_client.setex.call_args[0]
    assert isinstance(args[0], str)  # key
    assert args[1] == cache_service.ttl  # ttl
    assert json.loads(args[2]) == sample_embedding  # value

async def test_get_report(cache_service, mock_redis_client):
    # Test data
    query = "test query"
    urls = ["http://example.com/1", "http://example.com/2"]
    expected_report = "Test Report Content"
    
    # Setup mock for cache hit
    mock_redis_client.get = AsyncMock(return_value=expected_report)
    
    # Test getting report
    result = await cache_service.get_report(query, urls)
    
    # Verify
    assert result == expected_report
    mock_redis_client.get.assert_called_once()
    
    # Test cache miss
    mock_redis_client.get = AsyncMock(return_value=None)
    result = await cache_service.get_report(query, urls)
    assert result is None

async def test_set_report(cache_service, mock_redis_client):
    # Test data
    query = "test query"
    urls = ["http://example.com/1", "http://example.com/2"]
    report = "Test Report Content"
    
    # Setup mock
    mock_redis_client.setex = AsyncMock()
    
    # Test setting report
    await cache_service.set_report(query, urls, report)
    
    # Verify
    mock_redis_client.setex.assert_called_once()
    args = mock_redis_client.setex.call_args[0]
    assert isinstance(args[0], str)  # key
    assert args[1] == cache_service.ttl  # ttl
    assert args[2] == report  # value

def test_clear_cache(cache_service, mock_redis_client):
    # Setup mock
    mock_redis_client.flushdb = AsyncMock()
    
    # Test clearing cache
    cache_service.clear_cache()
    
    # Verify
    mock_redis_client.flushdb.assert_called_once() 