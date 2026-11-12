"""LLM client with retries and fallback (FR-40, FR-41, FR-42, FR-43)."""
import time
import config
from groq import Groq, APIError, RateLimitError


class LLMUnavailable(Exception):
    """Raised when both primary and fallback models fail."""


def _call_groq(prompt: str) -> str:
    """Call Groq (primary)."""
    client = Groq(api_key=config.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=config.PRIMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()


def _call_gemini(prompt: str) -> str:
    """Call Gemini (fallback) using the NEW google-genai SDK."""
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=config.FALLBACK_MODEL,
        contents=prompt,
    )
    return resp.text.strip()


def _retry(fn, prompt: str):
    """Retry a function with exponential backoff (FR-42)."""
    last_err = None
    for attempt in range(config.RETRY_COUNT):
        try:
            return fn(prompt)
        except (RateLimitError, APIError, Exception) as e:
            last_err = e
            if attempt < config.RETRY_COUNT - 1:
                time.sleep(config.RETRY_BACKOFF_S * (2 ** attempt))
    raise last_err


def generate(prompt: str) -> dict:
    """
    Try primary, then fallback. Returns {'text': str, 'model_used': str}.
    Raises LLMUnavailable if both fail (FR-43).
    """
    # Try primary
    try:
        text = _retry(_call_groq, prompt)
        return {"text": text, "model_used": f"{config.PRIMARY_PROVIDER}/{config.PRIMARY_MODEL}"}
    except Exception as e:
        print(f"[llm_client] Primary failed: {e}")

    # Try fallback
    try:
        text = _retry(_call_gemini, prompt)
        return {"text": text, "model_used": f"{config.FALLBACK_PROVIDER}/{config.FALLBACK_MODEL}"}
    except Exception as e:
        print(f"[llm_client] Fallback failed: {e}")

    raise LLMUnavailable(
        "Both primary and fallback models are unavailable. Please try again later."
    )