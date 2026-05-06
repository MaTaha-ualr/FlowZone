"""
FlowZone Input Sanitization
============================
Lightweight guards before storing or processing user/mentor content.
"""

import re
from typing import Tuple

# ------------------------------------------------------------------
# PII Patterns
# ------------------------------------------------------------------
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PHONE_PATTERN = re.compile(r"\b\d{3}-\d{3}-\d{4}\b")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# ------------------------------------------------------------------
# Prompt Injection Indicators
# ------------------------------------------------------------------
INJECTION_PATTERNS = [
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"DAN|jailbreak", re.IGNORECASE),
    re.compile(r"\{\{\s*\.System\s*\}\}", re.IGNORECASE),
]

# ------------------------------------------------------------------
# Profanity / Extreme language (basic, for mentor dashboard safety)
# ------------------------------------------------------------------
EXTREME_PROFANITY = re.compile(
    r"\b(fuck|shit|cunt|nigger|faggot|kill yourself|kys)\b",
    re.IGNORECASE,
)

def sanitize_chat_input(text: str) -> Tuple[str, dict]:
    """
    Clean and scan user chat input.

    Returns:
        (sanitized_text, flags_dict)
    """
    flags = {
        "pii_detected": False,
        "injection_detected": False,
        "extreme_language": False,
        "truncated": False,
    }

    # 1. Length cap (Pydantic already enforces max_length=5000, but double-check)
    if len(text) > 5000:
        text = text[:5000]
        flags["truncated"] = True

    # 2. PII detection (do NOT remove — just flag for mentor review)
    if SSN_PATTERN.search(text) or PHONE_PATTERN.search(text) or EMAIL_PATTERN.search(text):
        flags["pii_detected"] = True

    # 3. Prompt injection scan
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            flags["injection_detected"] = True
            break

    # 4. Extreme language scan
    if EXTREME_PROFANITY.search(text):
        flags["extreme_language"] = True

    return text, flags

def sanitize_mentor_input(text: str) -> Tuple[str, dict]:
    """
    Mentor notes go through the same guards.
    """
    return sanitize_chat_input(text)
