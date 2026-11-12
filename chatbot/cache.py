"""Semantic TTL cache (FR-44) — tolerant of typos and SMS-speak."""
import re
import time
from threading import Lock
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import config


def _normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    replacements = {
        " u ": " you ", " r ": " are ", " pls ": " please ", " thx ": " thanks ",
        " wat ": " what ", " dnt ": " do not ", " cant ": " cannot ",
        " im ": " i am ", " ive ": " i have ",
    }
    for s, l in replacements.items():
        text = f" {text} ".replace(s, l).strip()
    return text


class Cache:
    def __init__(self, ttl_s=None, similarity_threshold=0.80):
        self.ttl = ttl_s if ttl_s is not None else config.CACHE_TTL_S
        self.threshold = similarity_threshold
        self._store = {}
        self._lock = Lock()

    def _similarity(self, q1: str, q2: str) -> float:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        try:
            m = vec.fit_transform([_normalise(q1), _normalise(q2)])
            return float(cosine_similarity(m[0:1], m[1:2])[0][0])
        except ValueError:
            return 0.0

    def get(self, question: str):
        with self._lock:
            if not self._store:
                return None
            now = time.time()
            self._store = {k: v for k, v in self._store.items() if v[1] > now}
            if not self._store:
                return None
            best_score, best_value = 0.0, None
            for stored_q, (value, _) in self._store.items():
                score = self._similarity(question, stored_q)
                if score > best_score:
                    best_score, best_value = score, value
            return best_value if best_score >= self.threshold else None

    def set(self, question: str, value):
        with self._lock:
            self._store[question] = (value, time.time() + self.ttl)

    def invalidate(self):
        with self._lock:
            self._store.clear()


_singleton = Cache()


def get_cache() -> Cache:
    return _singleton