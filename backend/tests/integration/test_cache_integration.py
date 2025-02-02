import pytest
import json
from src.services.cache_service import CacheService

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="function")
def redis_cache(redis_server):
    """Create a fresh Redis cache for each test"""
    cache = CacheService()
    cache.redis_client.flushdb()  # Clear all data
    return cache

async def test_embedding_cache_integration(redis_cache, sample_embedding):
    # Test data
    text = "test text for embedding"
    
    # Initially, embedding should not be in cache
    cached_embedding = await redis_cache.get_embedding(text)
    assert cached_embedding is None
    
    # Store embedding in cache
    await redis_cache.set_embedding(text, sample_embedding)
    
    # Retrieve embedding from cache
    cached_embedding = await redis_cache.get_embedding(text)
    assert cached_embedding == sample_embedding
    
    # Verify TTL is set
    key = redis_cache._generate_key("embedding", text)
    ttl = redis_cache.redis_client.ttl(key)
    assert ttl > 0
    assert ttl <= redis_cache.ttl

async def test_report_cache_integration(redis_cache):
    # Test data
    query = "test research query"
    urls = ["http://example.com/1", "http://example.com/2"]
    report = "Test Research Report Content"
    
    # Initially, report should not be in cache
    cached_report = await redis_cache.get_report(query, urls)
    assert cached_report is None
    
    # Store report in cache
    await redis_cache.set_report(query, urls, report)
    
    # Retrieve report from cache
    cached_report = await redis_cache.get_report(query, urls)
    assert cached_report == report
    
    # Verify TTL is set
    key = redis_cache._generate_key("report", f"{query}:{','.join(sorted(urls))}")
    ttl = redis_cache.redis_client.ttl(key)
    assert ttl > 0
    assert ttl <= redis_cache.ttl

async def test_cache_clear_integration(redis_cache, sample_embedding):
    # Store test data
    text = "test text"
    report = "test report"
    query = "test query"
    urls = ["http://example.com"]
    
    # Store both embedding and report
    await redis_cache.set_embedding(text, sample_embedding)
    await redis_cache.set_report(query, urls, report)
    
    # Verify data is stored
    assert await redis_cache.get_embedding(text) == sample_embedding
    assert await redis_cache.get_report(query, urls) == report
    
    # Clear cache
    redis_cache.clear_cache()
    
    # Verify all data is cleared
    assert await redis_cache.get_embedding(text) is None
    assert await redis_cache.get_report(query, urls) is None

async def test_cache_expiration_integration(redis_cache, sample_embedding):
    # Test data
    text = "test text"
    
    # Set a very short TTL for testing
    original_ttl = redis_cache.ttl
    redis_cache.ttl = 1  # 1 second
    
    # Store embedding
    await redis_cache.set_embedding(text, sample_embedding)
    
    # Verify it's stored
    assert await redis_cache.get_embedding(text) == sample_embedding
    
    # Wait for expiration
    import asyncio
    await asyncio.sleep(2)
    
    # Verify it's expired
    assert await redis_cache.get_embedding(text) is None
    
    # Restore original TTL
    redis_cache.ttl = original_ttl

async def test_concurrent_cache_access(redis_cache, sample_embedding):
    # Test data
    texts = [f"test text {i}" for i in range(10)]
    
    # Concurrent store operations
    import asyncio
    store_tasks = [
        redis_cache.set_embedding(text, sample_embedding)
        for text in texts
    ]
    await asyncio.gather(*store_tasks)
    
    # Concurrent retrieve operations
    retrieve_tasks = [
        redis_cache.get_embedding(text)
        for text in texts
    ]
    results = await asyncio.gather(*retrieve_tasks)
    
    # Verify all operations succeeded
    assert all(result == sample_embedding for result in results)

async def test_cache_key_collision_handling(redis_cache):
    # Test data that might generate similar keys
    query1 = "test query"
    urls1 = ["http://example.com/1", "http://example.com/2"]
    report1 = "Report 1"
    
    query2 = "test query "  # Extra space
    urls2 = ["http://example.com/2", "http://example.com/1"]  # Different order
    report2 = "Report 2"
    
    # Store reports
    await redis_cache.set_report(query1, urls1, report1)
    await redis_cache.set_report(query2, urls2, report2)
    
    # Verify no collision
    assert await redis_cache.get_report(query1, urls1) == report1
    assert await redis_cache.get_report(query2, urls2) == report2
    
    # Verify URL order doesn't matter
    assert await redis_cache.get_report(query1, list(reversed(urls1))) == report1 