"""
Phenom Untrusted Content Taint & Prompt-Injection Defense (Task 7a)
Enforces:
1. Taint Tracking: External inputs (Gmail, web scrapes, RSS, OCR, YouTube captions) are tagged as tainted.
2. Tool Escalation: Tainted contexts invalidate remembered approvals and enforce explicit on-screen confirmations.
3. Injection Detection: Scans external text against a corpus of prompt-injection and privilege-escalation attack patterns.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("phenom.taint")

# Corpus of 30 prompt-injection and jailbreak attack patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt\s+(override|bypass|reset)",
    r"you\s+are\s+now\s+(in\s+)?(developer|maintenance|god|jailbreak|unrestricted)\s+mode",
    r"disregard\s+(all\s+)?safety\s+(rules|guidelines|tiers)",
    r"do\s+not\s+(ask|prompt)\s+(for\s+)?(confirmation|approval|permission)",
    r"auto-?approve\s+(all\s+)?(actions|tools|commands|tier\s*[123])",
    r"phenom\s+safety\s+layer\s+is\s+(disabled|deactivated|offline)",
    r"bypass\s+(safety|guardian|kill\s*switch)",
    r"execute\s+(powershell|cmd|bash|sh|terminal)\s*:",
    r"powershell\s+(-enc|-encodedcommand|-nop|-w\s+hidden)",
    r"(curl|wget|invoke-webrequest|iwr|certutil)\s+https?://",
    r"exfiltrate\s+(tokens?|keys?|passwords?|credentials?)",
    r"send\s+(token|secret|password)\s+to\s+https?://",
    r"hidden\s+instruction\s*:\s*",
    r"<\s*im_start\s*>\s*system",
    r"\[\s*system\s*\]\s*:\s*",
    r"BEGIN\s+OVERRIDE",
    r"ADMIN_TOKEN\s*=\s*",
    r"sudo\s+phenom\s+force",
    r"override\s+tier\s*3\s+permanently",
    r"new\s+rule\s*:\s*always\s+say\s+yes",
    r"pretend\s+you\s+have\s+root\s+access",
    r"forget\s+all\s+constraints\s+and\s+execute",
    r"cat\s+/etc/shadow|type\s+C:\\Windows\\System32\\config\\SAM",
    r"format\s+[A-Z]:\s*/q",
    r"rmdir\s+/s\s+/q\s+C:\\",
    r"Delete\s+all\s+files\s+in\s+Phenom",
    r"Transfer\s+funds\s+immediately",
    r"Authorize\s+payment\s+without\s+preview",
    r"Disable\s+killswitch\s+permanently"
]

_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

class TaintTracker:
    def __init__(self):
        self._is_tainted: bool = False
        self._tainted_sources: List[str] = []
        self._detected_injections: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Resets the taint tracking state for a new clean turn."""
        self._is_tainted = False
        self._tainted_sources = []
        self._detected_injections = []

    @property
    def is_tainted(self) -> bool:
        return self._is_tainted

    @property
    def tainted_sources(self) -> List[str]:
        return list(self._tainted_sources)

    def mark_tainted(self, source: str, reason: str = "External untrusted content") -> None:
        """Explicitly flags the current session/turn as tainted by an untrusted source."""
        self._is_tainted = True
        if source not in self._tainted_sources:
            self._tainted_sources.append(source)
        logger.warning(f"[Security] Taint flag activated: source='{source}', reason='{reason}'")

    def inspect_and_sanitize(self, content: str, source: str) -> Tuple[str, bool, List[str]]:
        """
        Inspects content for known prompt injections.
        Marks session tainted if source is external or injections are detected.
        Returns (sanitized_content, was_injection_detected, matched_patterns).
        """
        if not content or not isinstance(content, str):
            return content, False, []

        matches = []
        for pattern in _COMPILED_INJECTION_PATTERNS:
            if pattern.search(content):
                matches.append(pattern.pattern)

        has_injection = len(matches) > 0
        if has_injection or source.lower() in ["gmail", "web_scrape", "youtube", "ocr", "research_paper", "rss"]:
            self.mark_tainted(source, reason=f"Injections found: {len(matches)}" if has_injection else "External untrusted source")

        if has_injection:
            record = {
                "source": source,
                "matches": matches,
                "content_preview": content[:150]
            }
            self._detected_injections.append(record)
            logger.critical(f"[Security Alert] Prompt injection pattern detected in '{source}': {matches}")

        # Wrap external content in safe boundary tags
        wrapped = f"<untrusted_external_content source='{source}' tainted='{self._is_tainted}'>\n{content}\n</untrusted_external_content>"
        return wrapped, has_injection, matches

    def check_tool_escalation(self, tool_name: str, requested_tier: int) -> Tuple[int, Optional[str]]:
        """
        Calculates effective security tier under active taint.
        Tainted context invalidates remembered choices and escalates execution scrutiny.
        """
        if not self._is_tainted:
            return requested_tier, None

        warning = f"SECURITY WARNING: Turn is tainted by external untrusted content ({', '.join(self._tainted_sources)}). Automatic approval is suspended."
        # If tool was Tier 1 with possible remembered folder approval, force to explicit preview
        if requested_tier == 1:
            return 2, warning  # Escalate to Tier 2 (never remembered)

        return requested_tier, warning

# Global taint tracker singleton
taint_tracker = TaintTracker()
