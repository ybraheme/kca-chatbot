"""In-memory TTL cache for repeated identical questions (FR-44)."""
import time
from threading import Lock
import config


class Cache:
    def __init__(self, ttl_s=None):
        self.ttl = ttl_s if ttl_s is not None else config.CACHE_TTL_S
        self._store = {}
        self._lock = Lock()

    @staticmethod
    def normalise(q: str) -> str:
        return " ".join(q.lower().strip().split())

    def get(self, question: str):
        key = self.normalise(question)
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            value, expiry = entry
            if time.time() > expiry:
                del self._store[key]
                return None
            return value

    def set(self, question: str, value):
        key = self.normalise(question)
        with self._lock:
            self._store[key] = (value, time.time() + self.ttl)

    def invalidate(self):
        with self._lock:
            self._store.clear()


_singleton = Cache()


def get_cache() -> Cache:
    return _singleton