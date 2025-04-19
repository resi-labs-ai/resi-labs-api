"""
Redis utility functions for caching and rate limiting
"""
import os
import redis
from typing import Dict, Any, Optional


class RedisClient:
    """Client for Redis operations with fallback to in-memory cache"""

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis client with fallback

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.connected = False
        self.client = None

        # In-memory fallback
        self.cache = {}
        self.counters = {}

        # Try to connect
        self._connect()

    def _connect(self):
        """Attempt to connect to Redis"""
        try:
            self.client = redis.from_url(self.redis_url)
            self.client.ping()  # Test connection
            self.connected = True
            print("Connected to Redis successfully")
        except Exception as e:
            print(f"Redis connection failed: {str(e)}. Using in-memory fallback.")
            self.connected = False

    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis with in-memory fallback"""
        if self.connected:
            try:
                return self.client.get(key)
            except Exception:
                print("Redis get failed, using in-memory fallback")

        # In-memory fallback
        return self.cache.get(key)

    def set(self, key: str, value: str, expire: int = None):
        """Set a value in Redis with in-memory fallback"""
        if self.connected:
            try:
                if expire:
                    self.client.setex(key, expire, value)
                else:
                    self.client.set(key, value)
                return
            except Exception:
                print("Redis set failed, using in-memory fallback")

        # In-memory fallback
        self.cache[key] = value

    def delete(self, key: str):
        """Delete a key from Redis with in-memory fallback"""
        if self.connected:
            try:
                self.client.delete(key)
                return
            except Exception:
                print("Redis delete failed, using in-memory fallback")

        # In-memory fallback
        if key in self.cache:
            del self.cache[key]

    def get_counter(self, key: str) -> int:
        """Get a counter value with in-memory fallback"""
        if self.connected:
            try:
                value = self.client.get(key)
                return int(value) if value else 0
            except Exception:
                print("Redis get_counter failed, using in-memory fallback")

        # In-memory fallback
        return self.counters.get(key, 0)

    def increment_counter(self, key: str, expire: int = 86400) -> int:
        """Increment a counter with in-memory fallback"""
        if self.connected:
            try:
                value = self.client.incr(key)
                # Set expiry if not already set
                if expire and not self.client.ttl(key):
                    self.client.expire(key, expire)
                return value
            except Exception:
                print("Redis increment_counter failed, using in-memory fallback")

        # In-memory fallback
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def cache_check(self, cache_key: str, check_func, *args, expire: int = 60, **kwargs) -> Any:
        """
        Check cache before calling a function

        Args:
            cache_key: Key to use for caching
            check_func: Function to call if not cached
            args, kwargs: Arguments to pass to check_func
            expire: Cache expiry time in seconds

        Returns:
            Result from cache or function call
        """
        # Check cache first
        cached = self.get(cache_key)
        if cached:
            if cached == b'1' or cached == '1':
                return True
            elif cached == b'0' or cached == '0':
                return False
            return cached

        # Call function and cache result
        result = check_func(*args, **kwargs)

        # Cache the result
        if isinstance(result, bool):
            self.set(cache_key, '1' if result else '0', expire)
        else:
            self.set(cache_key, str(result), expire)

        return result