"""
Caching utilities for the Meme Coin Bot.
Provides Redis-based caching with in-memory fallback.
"""
import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Setup logging
logger = logging.getLogger(__name__)

# Type variables for better type hinting
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Try to import Redis, but don't fail if it's not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis package not installed. Using in-memory cache fallback.")

# Try to import functools.lru_cache for in-memory caching
try:
    from functools import lru_cache
    LRU_CACHE_AVAILABLE = True
except ImportError:
    LRU_CACHE_AVAILABLE = False
    logger.warning("functools.lru_cache not available. Using simple dict cache.")

# In-memory cache as fallback
_memory_cache: Dict[str, Dict[str, Any]] = {}

class Cache:
    """Cache implementation with Redis and in-memory fallback."""
    
    def __init__(self):
        """Initialize the cache with Redis if available."""
        self.redis_client = None
        self.use_redis = False
        
        # Try to connect to Redis if URL is provided
        redis_url = os.getenv("REDIS_URL")
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.use_redis = True
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                logger.info("Falling back to in-memory cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {str(e)}")
        
        # Fallback to in-memory cache
        cache_entry = _memory_cache.get(key)
        if cache_entry:
            # Check if entry is expired
            if cache_entry.get("expires_at", 0) > time.time():
                return cache_entry.get("value")
            else:
                # Remove expired entry
                del _memory_cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set a value in the cache with TTL."""
        # Serialize value to JSON
        serialized = json.dumps(value)
        
        if self.use_redis and self.redis_client:
            try:
                return bool(self.redis_client.setex(key, ttl_seconds, serialized))
            except Exception as e:
                logger.error(f"Redis set error: {str(e)}")
        
        # Fallback to in-memory cache
        _memory_cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }
        return True
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        if self.use_redis and self.redis_client:
            try:
                return bool(self.redis_client.delete(key))
            except Exception as e:
                logger.error(f"Redis delete error: {str(e)}")
        
        # Fallback to in-memory cache
        if key in _memory_cache:
            del _memory_cache[key]
            return True
        return False

# Singleton cache instance
_cache = Cache()

def cache_result(ttl_seconds: int = 300):
    """
    Decorator to cache function results with specified TTL.
    
    Args:
        ttl_seconds: Time to live in seconds for cached results.
        
    Returns:
        Decorated function with caching.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get cached result
            cached = _cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for {key}")
                return cached
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {key}")
            result = await func(*args, **kwargs)
            _cache.set(key, result, ttl_seconds)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get cached result
            cached = _cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for {key}")
                return cached
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {key}")
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl_seconds)
            return result
        
        # Return appropriate wrapper based on whether the function is async or not
        if asyncio_is_coroutine_function(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)
    
    return decorator

def asyncio_is_coroutine_function(func: Callable) -> bool:
    """Check if a function is a coroutine function."""
    try:
        import asyncio
        return asyncio.iscoroutinefunction(func)
    except (ImportError, AttributeError):
        # If asyncio is not available, assume it's not a coroutine function
        return False

# Expose the cache instance
cache = _cache
