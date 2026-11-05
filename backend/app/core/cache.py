"""Redis-backed cache and rate limiter, with an in-process fallback for local development.

The fallback is per-process and therefore NOT suitable for multi-instance production deployments;
production configuration must set REDIS_URL.
"""

import json
import logging
import threading
import time
from typing import Any

from app.core.config import settings

log = logging.getLogger("goodsng.cache")


class _MemoryStore:
    def __init__(self):
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            exp, val = item
            if exp and exp < time.time():
                self._data.pop(key, None)
                return None
            return val

    def setex(self, key, ttl, value):
        with self._lock:
            self._data[key] = (time.time() + ttl, value)

    def incr_window(self, key, ttl) -> int:
        with self._lock:
            exp, val = self._data.get(key, (0, 0))
            if exp < time.time():
                exp, val = time.time() + ttl, 0
            val += 1
            self._data[key] = (exp, val)
            return val

    def delete_prefix(self, prefix):
        with self._lock:
            for k in [k for k in self._data if k.startswith(prefix)]:
                self._data.pop(k, None)

    def clear(self):
        with self._lock:
            self._data.clear()


class Cache:
    def __init__(self):
        self._redis = None
        self._mem = _MemoryStore()
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        if settings.redis_url:
            try:
                import redis

                client = redis.Redis.from_url(settings.redis_url, socket_timeout=0.5)
                client.ping()
                self._redis = client
            except Exception as exc:  # pragma: no cover - depends on environment
                if settings.is_production:
                    raise
                log.warning("redis_unavailable_using_memory", extra={"error": str(exc)})

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def get_json(self, key: str):
        if self._redis:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None
        return self._mem.get(key)

    def set_json(self, key: str, value, ttl: int = 60):
        if self._redis:
            self._redis.setex(key, ttl, json.dumps(value, default=str))
        else:
            self._mem.setex(key, ttl, json.loads(json.dumps(value, default=str)))

    def invalidate(self, prefix: str):
        if self._redis:
            for k in self._redis.scan_iter(f"{prefix}*"):
                self._redis.delete(k)
        else:
            self._mem.delete_prefix(prefix)

    def hit(self, key: str, window_seconds: int) -> int:
        """Increment a fixed-window counter and return the current count."""
        if self._redis:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = pipe.execute()
            return int(count)
        return self._mem.incr_window(key, window_seconds)

    def get_or_compute(self, key: str, ttl: int, fn):
        """Single-flight cache fill: concurrent misses wait for one computation instead of stampeding.

        In-process lock always; with Redis, a short SET NX lock also coordinates across instances.
        """
        val = self.get_json(key)
        if val is not None:
            return val
        with self._key_lock(key):
            val = self.get_json(key)
            if val is not None:
                return val
            if self._redis and not self._redis.set(f"lock:{key}", "1", nx=True, ex=10):
                for _ in range(50):  # another instance is computing: wait briefly for it
                    time.sleep(0.1)
                    val = self.get_json(key)
                    if val is not None:
                        return val
            try:
                val = fn()
                self.set_json(key, val, ttl)
            finally:
                if self._redis:
                    self._redis.delete(f"lock:{key}")
            return self.get_json(key)

    def _key_lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def reset(self):
        if self._redis:
            self._redis.flushdb()
        self._mem.clear()


cache = Cache()


def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    from app.core.errors import RateLimited

    if cache.hit(f"rl:{key}", window_seconds) > limit:
        raise RateLimited("Too many requests. Please wait and try again.")
