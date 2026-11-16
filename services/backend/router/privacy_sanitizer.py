"""
Pre-Flight Cloud Privacy Sanitizer (Phase 47-05, ROUTER-02).
Guarantees zero unredacted personal data or secrets leave the host PC for cloud model inference (Rule 4).
Detects and masks:
- Indian PII: Aadhaar, PAN Card, Mobile Phone Numbers, UPI IDs, IFSC codes, Credit Cards (Luhn verified).
- API Secrets & Tokens: AWS keys, NVIDIA nvapi-, Google AIza, GitHub tokens, RSA private keys.
- Passwords and bearer tokens.
"""

import re
from typing import Dict, List, Tuple, Set
from pydantic import BaseModel, Field

from services.backend.router.privacy import (
    AADHAAR_REGEX,
    PAN_REGEX,
    PHONE_REGEX,
    UPI_REGEX,
    IFSC_REGEX,
    CREDIT_CARD_REGEX,
    AWS_KEY_REGEX,
    NVIDIA_KEY_REGEX,
    GOOGLE_KEY_REGEX,
    GITHUB_TOKEN_REGEX,
    PRIVATE_KEY_BLOCK_REGEX,
    is_valid_luhn
)


class SanitizationResult(BaseModel):
    """Payload carrying sanitized text and audit metrics."""
    sanitized_text: str = Field(..., description="Masked text safe for external transmission")
    redactions_count: int = Field(default=0, description="Total number of sensitive items masked")
    redacted_types: List[str] = Field(default_factory=list, description="Categories of masked information")
    contains_sensitive_data: bool = Field(default=False, description="True if any sensitive patterns were intercepted")


class PrivacySanitizer:
    """Sanitizes text and payloads before dispatching to external cloud inference APIs."""

    PASSWORD_REGEX = re.compile(
        r"""(?i)(?:password|passwd|secret_key|api_secret|auth_token)\s*[:=]\s*['"]?([a-zA-Z0-9_\-!@#$%^&*()+=]{6,})['"]?"""
    )
    BEARER_TOKEN_REGEX = re.compile(r"""(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{20,})\b""")

    def __init__(self):
        pass

    def sanitize(self, text: str) -> SanitizationResult:
        """
        Scans and redacts all PII and credentials from the input text string.
        Returns a structured SanitizationResult.
        """
        if not text:
            return SanitizationResult(
                sanitized_text="",
                redactions_count=0,
                redacted_types=[],
                contains_sensitive_data=False
            )

        sanitized = text
        redacted_types: Set[str] = set()
        count = 0

        # 1. RSA Private Keys
        if PRIVATE_KEY_BLOCK_REGEX.search(sanitized):
            sanitized = PRIVATE_KEY_BLOCK_REGEX.sub("[REDACTED_RSA_PRIVATE_KEY]", sanitized)
            redacted_types.add("RSA_PRIVATE_KEY")
            count += 1

        # 2. Aadhaar Numbers
        aadhaar_matches = AADHAAR_REGEX.findall(sanitized)
        if aadhaar_matches:
            sanitized = AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", sanitized)
            redacted_types.add("AADHAAR")
            count += len(aadhaar_matches)

        # 3. PAN Cards
        pan_matches = PAN_REGEX.findall(sanitized)
        if pan_matches:
            sanitized = PAN_REGEX.sub("[REDACTED_PAN]", sanitized)
            redacted_types.add("PAN")
            count += len(pan_matches)

        # 4. Indian Phone Numbers
        phone_matches = PHONE_REGEX.findall(sanitized)
        if phone_matches:
            sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
            redacted_types.add("PHONE")
            count += len(phone_matches)

        # 5. UPI IDs
        upi_matches = UPI_REGEX.findall(sanitized)
        if upi_matches:
            sanitized = UPI_REGEX.sub("[REDACTED_UPI]", sanitized)
            redacted_types.add("UPI")
            count += len(upi_matches)

        # 6. Credit Cards (Luhn verified)
        card_matches = CREDIT_CARD_REGEX.findall(sanitized)
        for card_str in card_matches:
            if is_valid_luhn(card_str):
                sanitized = sanitized.replace(card_str, "[REDACTED_CREDIT_CARD]")
                redacted_types.add("CREDIT_CARD")
                count += 1

        # 7. IFSC Codes
        ifsc_matches = IFSC_REGEX.findall(sanitized)
        if ifsc_matches:
            sanitized = IFSC_REGEX.sub("[REDACTED_IFSC]", sanitized)
            redacted_types.add("IFSC")
            count += len(ifsc_matches)

        # 8. API Keys & Cloud Secrets
        if AWS_KEY_REGEX.search(sanitized):
            m = AWS_KEY_REGEX.findall(sanitized)
            sanitized = AWS_KEY_REGEX.sub("[REDACTED_AWS_KEY]", sanitized)
            redacted_types.add("AWS_KEY")
            count += len(m)

        if NVIDIA_KEY_REGEX.search(sanitized):
            m = NVIDIA_KEY_REGEX.findall(sanitized)
            sanitized = NVIDIA_KEY_REGEX.sub("[REDACTED_NVIDIA_KEY]", sanitized)
            redacted_types.add("NVIDIA_KEY")
            count += len(m)

        if GOOGLE_KEY_REGEX.search(sanitized):
            m = GOOGLE_KEY_REGEX.findall(sanitized)
            sanitized = GOOGLE_KEY_REGEX.sub("[REDACTED_GOOGLE_KEY]", sanitized)
            redacted_types.add("GOOGLE_KEY")
            count += len(m)

        if GITHUB_TOKEN_REGEX.search(sanitized):
            m = GITHUB_TOKEN_REGEX.findall(sanitized)
            sanitized = GITHUB_TOKEN_REGEX.sub("[REDACTED_GITHUB_TOKEN]", sanitized)
            redacted_types.add("GITHUB_TOKEN")
            count += len(m)

        # 9. Passwords and Bearer Tokens
        def _mask_password(m):
            return m.group(0).replace(m.group(1), "[REDACTED_PASSWORD]")

        pw_matches = self.PASSWORD_REGEX.findall(sanitized)
        if pw_matches:
            sanitized = self.PASSWORD_REGEX.sub(_mask_password, sanitized)
            redacted_types.add("PASSWORD")
            count += len(pw_matches)

        bearer_matches = self.BEARER_TOKEN_REGEX.findall(sanitized)
        if bearer_matches:
            sanitized = self.BEARER_TOKEN_REGEX.sub("Bearer [REDACTED_BEARER_TOKEN]", sanitized)
            redacted_types.add("BEARER_TOKEN")
            count += len(bearer_matches)

        return SanitizationResult(
            sanitized_text=sanitized,
            redactions_count=count,
            redacted_types=sorted(list(redacted_types)),
            contains_sensitive_data=(count > 0)
        )


# Global singleton instance
privacy_sanitizer = PrivacySanitizer()
