"""
Phenom Rule 11 Credential & Secret Sanitizer (CTX-01.3)
Scans arbitrary text, window titles, clipboard contents, and terminal outputs
and redacts sensitive credentials, tokens, and API keys before in-RAM storage.
"""

import re
from typing import Tuple, List

# Pre-compiled high-precision secret detection patterns
SECRET_PATTERNS = [
    # GitHub personal access tokens
    re.compile(r"\bgh[pours]_[a-zA-Z0-9]{36,}\b", re.I),
    # OpenAI API keys
    re.compile(r"\bsk-[a-zA-Z0-9_\-]{20,}\b", re.I),
    # NVIDIA API keys
    re.compile(r"\bnvapi-[a-zA-Z0-9_\-]{20,}\b", re.I),
    # Generic Bearer tokens
    re.compile(r"\bBearer\s+[a-zA-Z0-9_\-\.]{20,}\b", re.I),
    # AWS access keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Private SSH/RSA Keys
    re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----", re.I),
    # URI / Query string passwords & secrets
    re.compile(r"(?:password|passwd|secret|token|api_key|access_token|auth)=([^&\s]+)", re.I),
    # Basic auth in URLs
    re.compile(r"://[^:]+:([^@]+)@", re.I)
]


class ContextSanitizer:
    """
    High-speed in-RAM sanitizer ensuring zero credential storage under Rule 11.
    """

    def __init__(self):
        self._patterns = SECRET_PATTERNS

    def sanitize(self, text: str) -> Tuple[str, int]:
        """
        Redacts credentials from text, returning (sanitized_text, redaction_count).
        """
        if not text:
            return "", 0

        clean = text
        total_redacted = 0

        # URI password/secret parameter redaction (preserves param key, masks value)
        def _mask_param(match):
            nonlocal total_redacted
            total_redacted += 1
            full = match.group(0)
            val = match.group(1)
            return full.replace(val, "[REDACTED_CREDENTIAL]")

        clean = re.sub(r"((?:password|passwd|secret|token|api_key|access_token|auth)=)([^&\s]+)", r"\1[REDACTED_CREDENTIAL]", clean, flags=re.I)

        # Standard token and key patterns
        for pat in self._patterns:
            matches = pat.findall(clean)
            if matches:
                total_redacted += len(matches)
                clean = pat.sub("[REDACTED_CREDENTIAL]", clean)

        return clean, total_redacted


context_sanitizer = ContextSanitizer()
