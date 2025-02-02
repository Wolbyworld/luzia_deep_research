import redis
import json
import os
from typing import Optional, List, Any
import hashlib

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True
        )
        self.ttl = int(os.getenv("CACHE_TTL", "86400"))  # 24 hours default
        
    def _generate_key(self, prefix: str, data: str) -> str:
        """Generate a cache key for the data"""
        hash_object = hashlib.md5(data.encode())
        return f"{prefix}:{hash_object.hexdigest()}"
        
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        key = self._generate_key("embedding", text)
        cached = self.redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
        
    async def set_embedding(self, text: str, embedding: List[float]) -> None:
        """Store embedding in cache"""
        key = self._generate_key("embedding", text)
        self.redis_client.setex(
            key,
            self.ttl,
            json.dumps(embedding)
        )
        
    async def get_report(self, query: str, urls: List[str]) -> Optional[str]:
        """Get generated report from cache"""
        cache_data = f"{query}:{','.join(sorted(urls))}"
        key = self._generate_key("report", cache_data)
        return self.redis_client.get(key)
        
    async def set_report(self, query: str, urls: List[str], report: str) -> None:
        """Store generated report in cache"""
        cache_data = f"{query}:{','.join(sorted(urls))}"
        key = self._generate_key("report", cache_data)
        self.redis_client.setex(key, self.ttl, report)
        
    def clear_cache(self) -> None:
        """Clear all cache entries"""
        self.redis_client.flushdb() 