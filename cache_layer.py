"""Caching Layer — Streamlit cache_data + optional Redis (Upstash)"""
import os, json
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

def get_redis_client():
    if not REDIS_AVAILABLE: return None
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url: return None
    try: return redis.from_url(redis_url, decode_responses=True)
    except: return None

def cache_get(key: str):
    client = get_redis_client()
    if client is None: return None
    raw = client.get(key)
    return json.loads(raw) if raw else None

def cache_set(key: str, value, ttl_seconds: int = 300):
    client = get_redis_client()
    if client is None: return False
    client.setex(key, ttl_seconds, json.dumps(value, default=str))
    return True
