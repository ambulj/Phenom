"""
Phenom Active Visual Safety Shield (WKF-03.1, WKF-03.2)
Monitors on-screen visual buffers, OCR outputs, and DOM contents during macro execution.
Enforces:
- Rule 8: Payments and checkout completion are impossible by construction.
- Rule 11: Passwords, OTPs, and private credentials are never typed or stored.
- Rule 5: Financial trading and order placement are strictly prohibited.
- Hard SLA: Sub-25ms evaluation latency triggering instantaneous Guardian kill switch.
"""

from __future__ import annotations

import re
import time
import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.memory.temporal_graph_engine import Rule8ViolationError
from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.safety.visual_shield")


class ShieldTriggerCategory(str, Enum):
    PAYMENT_CHECKOUT = "PAYMENT_CHECKOUT"
    CREDENTIAL_PASSWORD = "CREDENTIAL_PASSWORD"
    OTP_AUTHENTICATION = "OTP_AUTHENTICATION"
    FINANCIAL_TRADING = "FINANCIAL_TRADING"


class VisualSafetyBarrierError(Rule8ViolationError):
    """Raised when Active Visual Safety Shield trips on prohibited screen contents."""
    def __init__(self, category: ShieldTriggerCategory, trigger_term: str, message: str):
        super().__init__(message)
        self.category = category
        self.trigger_term = trigger_term


class VisualScanResult(BaseModel):
    """Evaluation result of a frame-by-frame visual surface or DOM scan."""
    safe: bool = True
    violation_detected: bool = False
    category: Optional[ShieldTriggerCategory] = None
    trigger_term: Optional[str] = None
    scan_latency_ms: float = 0.0
    matched_text_snippet: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class ActiveVisualSafetyShield:
    """Frame-by-frame visual and DOM keyword scanner with sub-25ms Guardian emergency stop."""

    # Prohibited Payment & Checkout Terms (Rule 8)
    # Notice: "cart", "view cart", "add to cart" are allowed under Rule 8 ("Fill carts and stop")
    _PAYMENT_TERMS = [
        "checkout",
        "proceed to checkout",
        "pay now",
        "payment method",
        "place order",
        "complete purchase",
        "credit card number",
        "debit card number",
        "card number",
        "cvv",
        "cvc",
        "expiration date",
        "exp date",
        "billing address",
        "paypal checkout",
        "stripe checkout",
        "razorpay",
        "upi pay",
        "upi pin",
        "enter pin to pay",
    ]

    # Prohibited Credential & Password Inputs (Rule 11)
    _CREDENTIAL_TERMS = [
        "enter password",
        "confirm password",
        "master password",
        "security pin",
        "bank pin",
        "atm pin",
        "private key",
        "seed phrase",
        "secret recovery phrase",
    ]

    # Prohibited Multi-Factor Authentication / OTP Fields (Rule 11)
    _OTP_TERMS = [
        "one-time password",
        "one time password",
        "enter otp",
        "sms code",
        "2fa code",
        "authenticator code",
        "verification code sent to",
        "security code sent to",
    ]

    # Prohibited Trading & Financial Order Placement (Rule 5)
    _TRADING_TERMS = [
        "place trade",
        "buy shares",
        "sell shares",
        "limit order",
        "market order",
        "stop loss order",
        "crypto swap",
        "confirm trade",
        "wire transfer",
        "transfer funds",
    ]

    def __init__(self) -> None:
        # Precompile regexes with word boundaries for microsecond evaluation
        self._payment_regex = self._compile_terms(self._PAYMENT_TERMS)
        self._credential_regex = self._compile_terms(self._CREDENTIAL_TERMS)
        self._otp_regex = self._compile_terms(self._OTP_TERMS)
        self._trading_regex = self._compile_terms(self._TRADING_TERMS)

    def _compile_terms(self, terms: List[str]) -> re.Pattern:
        pattern = r"(?i)\b(" + "|".join(re.escape(t) for t in terms) + r")\b"
        return re.compile(pattern)

    def scan_frame(
        self,
        surface_text: str,
        window_title: str = "",
        halt_on_violation: bool = True
    ) -> VisualScanResult:
        """Inspects active frame / DOM text with sub-25ms latency guarantee."""
        start = time.perf_counter()

        combined = f"{window_title} {surface_text}"

        # 1. Check Payment & Checkout (Rule 8)
        match = self._payment_regex.search(combined)
        if match:
            trigger = match.group(0)
            latency = (time.perf_counter() - start) * 1000.0
            if halt_on_violation:
                guardian.trigger(reason=f"visual_safety_shield:payment:{trigger}")
            return VisualScanResult(
                safe=False,
                violation_detected=True,
                category=ShieldTriggerCategory.PAYMENT_CHECKOUT,
                trigger_term=trigger,
                scan_latency_ms=latency,
                matched_text_snippet=self._extract_snippet(combined, match.start(), match.end()),
            )

        # 2. Check Credential & Password (Rule 11)
        match = self._credential_regex.search(combined)
        if match:
            trigger = match.group(0)
            latency = (time.perf_counter() - start) * 1000.0
            if halt_on_violation:
                guardian.trigger(reason=f"visual_safety_shield:credential:{trigger}")
            return VisualScanResult(
                safe=False,
                violation_detected=True,
                category=ShieldTriggerCategory.CREDENTIAL_PASSWORD,
                trigger_term=trigger,
                scan_latency_ms=latency,
                matched_text_snippet=self._extract_snippet(combined, match.start(), match.end()),
            )

        # 3. Check OTP & 2FA (Rule 11)
        match = self._otp_regex.search(combined)
        if match:
            trigger = match.group(0)
            latency = (time.perf_counter() - start) * 1000.0
            if halt_on_violation:
                guardian.trigger(reason=f"visual_safety_shield:otp:{trigger}")
            return VisualScanResult(
                safe=False,
                violation_detected=True,
                category=ShieldTriggerCategory.OTP_AUTHENTICATION,
                trigger_term=trigger,
                scan_latency_ms=latency,
                matched_text_snippet=self._extract_snippet(combined, match.start(), match.end()),
            )

        # 4. Check Financial Trading (Rule 5)
        match = self._trading_regex.search(combined)
        if match:
            trigger = match.group(0)
            latency = (time.perf_counter() - start) * 1000.0
            if halt_on_violation:
                guardian.trigger(reason=f"visual_safety_shield:trading:{trigger}")
            return VisualScanResult(
                safe=False,
                violation_detected=True,
                category=ShieldTriggerCategory.FINANCIAL_TRADING,
                trigger_term=trigger,
                scan_latency_ms=latency,
                matched_text_snippet=self._extract_snippet(combined, match.start(), match.end()),
            )

        latency = (time.perf_counter() - start) * 1000.0
        return VisualScanResult(
            safe=True,
            violation_detected=False,
            scan_latency_ms=latency,
        )

    def assert_frame_safe(self, surface_text: str, window_title: str = "") -> VisualScanResult:
        """Inspects frame and raises VisualSafetyBarrierError immediately if prohibited."""
        res = self.scan_frame(surface_text, window_title, halt_on_violation=True)
        if not res.safe:
            msg = (
                f"Active Visual Safety Barrier Tripped: Prohibited {res.category.value} "
                f"element detected ('{res.trigger_term}'). Execution halted."
            )
            raise VisualSafetyBarrierError(res.category, res.trigger_term, msg)
        return res

    def _extract_snippet(self, text: str, start: int, end: int, window: int = 40) -> str:
        s = max(0, start - window)
        e = min(len(text), end + window)
        snippet = text[s:e].replace("\n", " ")
        return f"...{snippet}..."


visual_safety_shield = ActiveVisualSafetyShield()
