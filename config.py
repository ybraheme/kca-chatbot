"""Central configuration loader (QUA-5, FR-40). All tunables come from .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / os.getenv("DB_PATH", "data/chatbot.db")
KB_SEED_DIR = ROOT_DIR / "knowledge_base" / "seed"
TEST_DATA_DIR = ROOT_DIR / "test_data"

# LLM providers (FR-40, FR-41)
PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "groq")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "llama-3.1-8b-instant")
FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "gemini")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Retrieval (SDS Table 12)
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.08"))
TOP_K = int(os.getenv("TOP_K", "3"))

# Cache (FR-44)
CACHE_TTL_S = int(os.getenv("CACHE_TTL_S", "60"))

# Admin bootstrap
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe!2026")

# Behavioural (SRS Appendix C item 6)
MAX_QUESTION_LEN = int(os.getenv("MAX_QUESTION_LEN", "500"))
HISTORY_WINDOW = int(os.getenv("HISTORY_WINDOW", "5"))
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "3"))
RETRY_BACKOFF_S = float(os.getenv("RETRY_BACKOFF_S", "2"))
SESSION_EXPIRY_MIN = int(os.getenv("SESSION_EXPIRY_MIN", "30"))
MAX_FAILED_LOGINS = int(os.getenv("MAX_FAILED_LOGINS", "5"))
RATE_LIMIT_QUESTIONS = int(os.getenv("RATE_LIMIT_QUESTIONS", "20"))
RATE_LIMIT_WINDOW_MIN = int(os.getenv("RATE_LIMIT_WINDOW_MIN", "10"))
REVIEW_INTERVAL_DAYS = int(os.getenv("REVIEW_INTERVAL_DAYS", "180"))
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))


def get_model_provider(which: str = "primary") -> dict:
    """Return a dict describing the requested provider (FR-40)."""
    if which == "primary":
        return {"provider": PRIMARY_PROVIDER, "model": PRIMARY_MODEL, "key": GROQ_API_KEY}
    return {"provider": FALLBACK_PROVIDER, "model": FALLBACK_MODEL, "key": GEMINI_API_KEY}


def secret_or_env(name: str, default: str = "") -> str:
    """Read a secret from Streamlit secrets if available, else env (SEC-2)."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)