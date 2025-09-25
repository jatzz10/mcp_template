"""
Caching system for MCP servers
"""

import json
import time
from typing import Any, Optional, Dict
from collections import OrderedDict
import threading


class TTLCache:
    """
    Thread-safe TTL cache implementation.
    
    Features:
    - Time-to-live expiration
    - LRU eviction when max size reached
    - Thread-safe operations
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        """Check if a cache entry is expired"""
        if key not in self._timestamps:
            return True
        
        ttl = self.default_ttl
        if isinstance(self._cache.get(key), dict) and 'ttl' in self._cache[key]:
            ttl = self._cache[key]['ttl']
        
        return time.time() - self._timestamps[key] > ttl
    
    def _evict_expired(self) -> None:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self._timestamps.items():
            ttl = self.default_ttl
            if key in self._cache and isinstance(self._cache[key], dict) and 'ttl' in self._cache[key]:
                ttl = self._cache[key]['ttl']
            
            if current_time - timestamp > ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def _evict_lru(self) -> None:
        """Remove least recently used entry"""
        if self._cache:
            key, _ = self._cache.popitem(last=False)
            self._timestamps.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache or self._is_expired(key):
                return None
            
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                del self._cache[key]
            
            # Evict expired entries first
            self._evict_expired()
            
            # Evict LRU if at max size
            while len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # Store with TTL info
            cache_value = value
            if ttl is not None:
                cache_value = {"value": value, "ttl": ttl}
            
            self._cache[key] = cache_value
            self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            self._evict_expired()
            return len(self._cache)
    
    def keys(self) -> list:
        """Get all non-expired cache keys"""
        with self._lock:
            self._evict_expired()
            return list(self._cache.keys())


class CacheManager:
    """
    Centralized cache management for MCP servers.
    
    Features:
    - Multiple cache types (query results, schemas, etc.)
    - Configurable TTL per cache type
    - Cache statistics and monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize different cache types
        self.query_cache = TTLCache(
            max_size=self.config.get('query_cache_size', 1000),
            default_ttl=self.config.get('query_cache_ttl', 300)
        )
        
        self.schema_cache = TTLCache(
            max_size=self.config.get('schema_cache_size', 100),
            default_ttl=self.config.get('schema_cache_ttl', 3600)
        )
        
        self.metadata_cache = TTLCache(
            max_size=self.config.get('metadata_cache_size', 500),
            default_ttl=self.config.get('metadata_cache_ttl', 1800)
        )
        
        # Cache statistics
        self.stats = {
            'query_hits': 0,
            'query_misses': 0,
            'schema_hits': 0,
            'schema_misses': 0,
            'metadata_hits': 0,
            'metadata_misses': 0
        }
    
    async def get(self, key: str, cache_type: str = "query") -> Optional[Any]:
        """
        Get value from specified cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache ('query', 'schema', 'metadata')
        """
        cache = self._get_cache(cache_type)
        value = cache.get(key)
        
        # Update statistics
        if value is not None:
            self.stats[f'{cache_type}_hits'] += 1
        else:
            self.stats[f'{cache_type}_misses'] += 1
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, cache_type: str = "query") -> None:
        """
        Set value in specified cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            cache_type: Type of cache ('query', 'schema', 'metadata')
        """
        cache = self._get_cache(cache_type)
        cache.set(key, value, ttl)
    
    async def delete(self, key: str, cache_type: str = "query") -> bool:
        """Delete key from specified cache"""
        cache = self._get_cache(cache_type)
        return cache.delete(key)
    
    async def clear(self, cache_type: Optional[str] = None) -> None:
        """Clear cache(s)"""
        if cache_type:
            cache = self._get_cache(cache_type)
            cache.clear()
        else:
            self.query_cache.clear()
            self.schema_cache.clear()
            self.metadata_cache.clear()
    
    def _get_cache(self, cache_type: str) -> TTLCache:
        """Get cache instance by type"""
        if cache_type == "query":
            return self.query_cache
        elif cache_type == "schema":
            return self.schema_cache
        elif cache_type == "metadata":
            return self.metadata_cache
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(self.stats[k] for k in self.stats if k.endswith('_hits'))
        total_misses = sum(self.stats[k] for k in self.stats if k.endswith('_misses'))
        total_requests = total_hits + total_misses
        
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_sizes': {
                'query': self.query_cache.size(),
                'schema': self.schema_cache.size(),
                'metadata': self.metadata_cache.size()
            }
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics"""
        for key in self.stats:
            self.stats[key] = 0
