"""
Phenom In-Memory Credential Redaction & Secret Scrubber (MIR-01, Rule 11)
Sanitizes raw text, tokens, user home paths, and data structures in memory
before feature extraction or encrypted persistence.
"""

import re
from typing import Any, Dict, List, Union


# Credential patterns
RE_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z0-9_\- ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9_\- ]*PRIVATE KEY-----",
    re.MULTILINE,
)
RE_OPENAI_KEY = re.compile(r"\bsk-[a-zA-Z0-9_\-]{20,}\b")
RE_NVIDIA_KEY = re.compile(r"\bnvapi-[a-zA-Z0-9_\-]{20,}\b")
RE_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[a-zA-Z0-9]{36,}\b")
RE_GOOGLE_TOKEN = re.compile(r"\bya29\.[a-zA-Z0-9_\-]{20,}\b")
RE_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
RE_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{20,})\b")
RE_TELEGRAM_TOKEN = re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b")
RE_PASSWORD_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|auth[_-]?token)\s*([:=])\s*([\"']?)([^\s\"',;]+)(\3)"
)

# User paths and networking
RE_WINDOWS_USER_PATH = re.compile(r"[A-Za-z]:\\[Uu]sers\\[^\s\\\/\"\'\`]+")
RE_IP_ADDRESS = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")


def scrub_personal_secrets(text: str) -> str:
    """
    Sanitizes secrets, credentials, paths, and IP addresses in a string in-memory.
    Returns cleaned string with redacting markers.
    """
    if not isinstance(text, str):
        return text

    # 1. Private keys
    scrubbed = RE_PRIVATE_KEY.sub("[REDACTED_CREDENTIAL]", text)

    # 2. Known API key / token formats
    scrubbed = RE_OPENAI_KEY.sub("[REDACTED_CREDENTIAL]", scrubbed)
    scrubbed = RE_NVIDIA_KEY.sub("[REDACTED_CREDENTIAL]", scrubbed)
    scrubbed = RE_GITHUB_TOKEN.sub("[REDACTED_CREDENTIAL]", scrubbed)
    scrubbed = RE_GOOGLE_TOKEN.sub("[REDACTED_CREDENTIAL]", scrubbed)
    scrubbed = RE_AWS_KEY.sub("[REDACTED_CREDENTIAL]", scrubbed)
    scrubbed = RE_TELEGRAM_TOKEN.sub("[REDACTED_CREDENTIAL]", scrubbed)

    # 3. Bearer tokens
    scrubbed = RE_BEARER_TOKEN.sub(r"Bearer [REDACTED_CREDENTIAL]", scrubbed)

    # 4. Explicit password / secret assignments
    scrubbed = RE_PASSWORD_ASSIGNMENT.sub(r"\1\2 \3[REDACTED_CREDENTIAL]\5", scrubbed)

    # 5. Windows user home directories
    scrubbed = RE_WINDOWS_USER_PATH.sub(r"[REDACTED_PATH]", scrubbed)

    # 6. IP addresses
    scrubbed = RE_IP_ADDRESS.sub(r"[REDACTED_IP]", scrubbed)

    return scrubbed


def scrub_dict_or_list(data: Any) -> Any:
    """
    Recursively scrubs secrets across nested dictionaries, lists, tuples, or sets.
    """
    if isinstance(data, str):
        return scrub_personal_secrets(data)
    elif isinstance(data, dict):
        return {k: scrub_dict_or_list(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_dict_or_list(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(scrub_dict_or_list(item) for item in data)
    elif isinstance(data, set):
        return {scrub_dict_or_list(item) for item in data}
    return data
