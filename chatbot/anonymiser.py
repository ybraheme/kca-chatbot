"""Anonymise PII before logging (FR-19, SEC-7, SDS Table 10)."""
import re

RULES = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),                 "[EMAIL]"),
    (re.compile(r"(\+?254|0)\s?7\d{2}[\s-]?\d{3}[\s-]?\d{3}"), "[PHONE]"),
    (re.compile(r"\b(REG[- ]?)?\d{2}[/-]\d{4,6}\b"),         "[REG]"),
    (re.compile(r"\b\d{7,8}\b"),                              "[ID]"),
]


def anonymise(text: str) -> tuple:
    """Return (masked_text, match_count)."""
    if not text:
        return "", 0
    out, flags = text, 0
    for pattern, token in RULES:
        out, n = pattern.subn(token, out)
        flags += n
    return out, flags