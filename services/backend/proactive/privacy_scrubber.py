"""
Real-Time Privacy Scrubber (PRX-01, Permanent Rule 11, SAF-01).
Sanitizes sensitive tokens, API keys, credentials, and private keys from Win32 context events
before entering event buses, telemetry, or model reasoning loops.
"""

import re
from typing import Any, Dict, List, Tuple

# Comprehensive regex patterns for credentials and secrets
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("OPENAI_KEY", re.compile(r"sk-[a-zA-Z0-9]{20,}")),
    ("ANTHROPIC_KEY", re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}")),
    ("HUGGINGFACE_KEY", re.compile(r"hf_[a-zA-Z0-9]{20,}")),
    ("GITHUB_PAT", re.compile(r"ghp_[a-zA-Z0-9]{36}")),
    ("GITLAB_PAT", re.compile(r"glpat-[a-zA-Z0-9\-_]{20,}")),
    ("AWS_KEY_ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("BEARER_TOKEN", re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----")),
    ("PASSWORD_FIELD", re.compile(r"(?i)(password|passwd|secret_key|secret|token|api_key)\s*[:=]\s*['\"]?([^'\"\s\r\n,;]{4,})['\"]?")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
]


class PrivacyScrubber:
    """In-memory zero-leakage privacy scrubber enforcing Permanent Rule 11."""

    def __init__(self) -> None:
        self._total_scrubbed_count: int = 0

    @property
    def total_scrubbed_count(self) -> int:
        return self._total_scrubbed_count

    def scrub_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitize raw string, replacing sensitive tokens with redaction placeholders.
        Returns:
            Tuple of (scrubbed_text, list_of_redaction_categories)
        """
        if not text or not isinstance(text, str):
            return text, []

        categories_found: List[str] = []
        cleaned = text

        for name, pattern in SECRET_PATTERNS:
            if name == "PASSWORD_FIELD":
                # Special handling for password key=value pairs to preserve the key name
                def replace_password(match: re.Match) -> str:
                    key = match.group(1)
                    categories_found.append(name)
                    return f"{key}=[REDACTED_SECRET]"

                cleaned, count = pattern.subn(replace_password, cleaned)
                if count > 0 and name not in categories_found:
                    categories_found.append(name)
            else:
                matches = pattern.findall(cleaned)
                if matches:
                    categories_found.append(name)
                    cleaned = pattern.sub(f"[REDACTED_{name}]", cleaned)

        if categories_found:
            self._total_scrubbed_count += 1

        return cleaned, list(set(categories_found))

    def scrub_dict(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Recursively scrub strings within dictionary values."""
        if not isinstance(data, dict):
            return data, []

        scrubbed = {}
        all_categories: List[str] = []

        for key, val in data.items():
            # Check key name itself
            clean_key, key_cats = self.scrub_text(str(key))
            all_categories.extend(key_cats)

            if isinstance(val, str):
                clean_val, val_cats = self.scrub_text(val)
                scrubbed[clean_key] = clean_val
                all_categories.extend(val_cats)
            elif isinstance(val, dict):
                clean_val, sub_cats = self.scrub_dict(val)
                scrubbed[clean_key] = clean_val
                all_categories.extend(sub_cats)
            elif isinstance(val, list):
                clean_list = []
                for item in val:
                    if isinstance(item, str):
                        ci, icats = self.scrub_text(item)
                        clean_list.append(ci)
                        all_categories.extend(icats)
                    elif isinstance(item, dict):
                        cd, dcats = self.scrub_dict(item)
                        clean_list.append(cd)
                        all_categories.extend(dcats)
                    else:
                        clean_list.append(item)
                scrubbed[clean_key] = clean_list
            else:
                scrubbed[clean_key] = val

        return scrubbed, list(set(all_categories))


# Global singleton instance
privacy_scrubber = PrivacyScrubber()
