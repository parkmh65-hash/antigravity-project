import time
import functools
from typing import Any, Dict, Optional

# Global in-memory cache storage
# Structure: { key: { "data": Any, "expires_at": float } }
_api_cache: Dict[str, Dict[str, Any]] = {}

def get_cached_value(key: str) -> Optional[Any]:
    """Retrieves a value from cache if it exists and has not expired."""
    entry = _api_cache.get(key)
    if entry:
        if time.time() < entry["expires_at"]:
            return entry["data"]
        else:
            # Clean up expired entry
            del _api_cache[key]
    return None

def set_cached_value(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    """Stores a value in the cache with a Time-To-Live (TTL) in seconds."""
    _api_cache[key] = {
        "data": value,
        "expires_at": time.time() + ttl_seconds
    }

def clear_cache() -> None:
    """Clears all cached entries."""
    _api_cache.clear()

def cached_api_response(ttl_seconds: int = 3600):
    """
    Decorator to cache the response of API methods.
    Generates cache keys automatically based on function name and arguments.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Construct a unique string key based on arguments
            args_str = "-".join([str(a) for a in args])
            kwargs_str = "-".join([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = f"{func.__name__}_{args_str}_{kwargs_str}"
            
            # Look up cache
            cached_val = get_cached_value(cache_key)
            if cached_val is not None:
                return cached_val
                
            # Execute original function and store result
            result = func(*args, **kwargs)
            set_cached_value(cache_key, result, ttl_seconds)
            return result
        return wrapper
    return decorator
